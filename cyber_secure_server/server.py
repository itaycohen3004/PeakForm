import socket
import ssl
import threading
from protocol import send_message, recv_message
from database_manager import SecureDatabase

class ClientHandler(threading.Thread):
    """Handles communication with a single client."""
    def __init__(self, conn, addr, db):
        super().__init__()
        self.conn = conn
        self.addr = addr
        self.db = db
        self.username = None

    def run(self):
        print(f"[SERVER] Connection established from {self.addr}")
        try:
            while True:
                msg = recv_message(self.conn)
                if not msg:
                    break
                self.handle_message(msg)
        except Exception as e:
            print(f"[SERVER] Error with {self.addr}: {e}")
        finally:
            print(f"[SERVER] Connection closed from {self.addr}")
            self.conn.close()

    def handle_message(self, msg):
        cmd = msg.get("command")
        
        if cmd == "REGISTER":
            username = msg.get("username")
            password = msg.get("password")
            success, info = self.db.register_user(username, password)
            send_message(self.conn, {"status": "SUCCESS" if success else "ERROR", "message": info})
            
        elif cmd == "LOGIN":
            username = msg.get("username")
            password = msg.get("password")
            success, info = self.db.verify_login(username, password)
            if success:
                self.username = username
            send_message(self.conn, {"status": "SUCCESS" if success else "ERROR", "message": info})
            
        elif cmd == "SAVE_DATA":
            if not self.username:
                send_message(self.conn, {"status": "ERROR", "message": "Not authenticated."})
                return
            data = msg.get("data")
            success, info = self.db.save_data(self.username, data)
            send_message(self.conn, {"status": "SUCCESS" if success else "ERROR", "message": info})
            
        elif cmd == "GET_DATA":
            if not self.username:
                send_message(self.conn, {"status": "ERROR", "message": "Not authenticated."})
                return
            success, info = self.db.get_data(self.username)
            send_message(self.conn, {"status": "SUCCESS" if success else "ERROR", "data": info if success else None, "message": info if not success else "Data retrieved."})
            
        elif cmd == "EXTERNAL_API":
            # External Integration Example
            try:
                import urllib.request
                import json
                req = urllib.request.Request("https://official-joke-api.appspot.com/random_joke", headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    joke_data = json.loads(response.read().decode())
                    joke = f"{joke_data['setup']} - {joke_data['punchline']}"
                send_message(self.conn, {"status": "SUCCESS", "message": joke})
            except Exception as e:
                send_message(self.conn, {"status": "ERROR", "message": f"External API failed: {e}"})
            
        else:
            send_message(self.conn, {"status": "ERROR", "message": "Unknown command."})

class ServerEngine:
    """Main TLS Secure Server Engine."""
    def __init__(self, host='127.0.0.1', port=8443, certfile='cert.pem', keyfile='key.pem'):
        self.host = host
        self.port = port
        self.certfile = certfile
        self.keyfile = keyfile
        self.db = SecureDatabase()

    def start(self):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        try:
            context.load_cert_chain(certfile=self.certfile, keyfile=self.keyfile)
        except FileNotFoundError:
            print(f"[SERVER] Error: Certificates not found. Please run cert_gen.py first.")
            return

        # Enforce TLS 1.3 Minimum
        context.minimum_version = ssl.TLSVersion.TLSv1_3

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0) as sock:
            sock.bind((self.host, self.port))
            sock.listen(5)
            with context.wrap_socket(sock, server_side=True) as ssock:
                print(f"[SERVER] Listening securely on {self.host}:{self.port}...")
                try:
                    while True:
                        conn, addr = ssock.accept()
                        handler = ClientHandler(conn, addr, self.db)
                        handler.start()
                except KeyboardInterrupt:
                    print("\n[SERVER] Shutting down...")

if __name__ == "__main__":
    server = ServerEngine()
    server.start()
