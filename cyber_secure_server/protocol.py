import json
import struct

def send_message(sock, message_dict):
    """Encodes a dictionary as JSON and sends it with a length prefix."""
    try:
        msg_bytes = json.dumps(message_dict).encode('utf-8')
        # 4-byte length prefix
        prefix = struct.pack('!I', len(msg_bytes))
        sock.sendall(prefix + msg_bytes)
        return True
    except Exception as e:
        print(f"Send error: {e}")
        return False

def recv_message(sock):
    """Receives a length-prefixed JSON message and returns a dictionary."""
    try:
        # Read the 4-byte length prefix
        raw_msglen = recvall(sock, 4)
        if not raw_msglen:
            return None
        msglen = struct.unpack('!I', raw_msglen)[0]
        # Read the message data
        msg_bytes = recvall(sock, msglen)
        if not msg_bytes:
            return None
        return json.loads(msg_bytes.decode('utf-8'))
    except Exception as e:
        print(f"Recv error: {e}")
        return None

def recvall(sock, n):
    """Helper to receive exactly n bytes."""
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return bytes(data)
