import socket
import ssl
from protocol import send_message, recv_message

class SecureClient:
    def __init__(self, host='127.0.0.1', port=8443):
        self.host = host
        self.port = port
        self.conn = None

    def connect(self):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        context.minimum_version = ssl.TLSVersion.TLSv1_3

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn = context.wrap_socket(sock, server_hostname=self.host)
        try:
            self.conn.connect((self.host, self.port))
            print(f"[CLIENT] Connected to secure server {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"[CLIENT] Connection failed: {e}")
            return False

    def interact(self):
        while True:
            print("\n--- SECURE VAULT MENU ---")
            print("1. Register")
            print("2. Login")
            print("3. Save Data")
            print("4. Get Data")
            print("5. External API Integration (Get a Joke)")
            print("6. Exit")
            choice = input("Select an option: ")

            if choice == '1':
                user = input("Username: ")
                pwd = input("Password: ")
                send_message(self.conn, {"command": "REGISTER", "username": user, "password": pwd})
            elif choice == '2':
                user = input("Username: ")
                pwd = input("Password: ")
                send_message(self.conn, {"command": "LOGIN", "username": user, "password": pwd})
            elif choice == '3':
                data = input("Enter sensitive data to vault: ")
                send_message(self.conn, {"command": "SAVE_DATA", "data": data})
            elif choice == '4':
                send_message(self.conn, {"command": "GET_DATA"})
            elif choice == '5':
                send_message(self.conn, {"command": "EXTERNAL_API"})
            elif choice == '6':
                break
            else:
                print("Invalid choice.")
                continue

            # Wait for response
            response = recv_message(self.conn)
            if response:
                print(f"[SERVER RESPONSE] Status: {response.get('status')}")
                if response.get('data'):
                    print(f"Data: {response.get('data')}")
                if response.get('message'):
                    print(f"Message: {response.get('message')}")
            else:
                print("[CLIENT] Connection lost.")
                break

        if self.conn:
            self.conn.close()
            print("[CLIENT] Disconnected.")

if __name__ == "__main__":
    client = SecureClient()
    if client.connect():
        client.interact()
