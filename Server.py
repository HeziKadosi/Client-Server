import socket
import struct
import threading
import random
import time


MAGIC_COOKIE = 0xabcddcba
OFFER_TYPE = 0x2
REQUEST_TYPE = 0x3
PAYLOAD_TYPE = 0x4
SERVER_TCP_PORT = 4000
SERVER_UDP_PORT = 3000
BUFFER_SIZE = 1024

def broadcast_offers():
    """Broadcast UDP offer messages to clients."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as udp_socket:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        message = struct.pack('>IBHH', MAGIC_COOKIE, OFFER_TYPE, SERVER_UDP_PORT, SERVER_TCP_PORT)
        while True:
            udp_socket.sendto(message, ('<broadcast>', 37020))
            time.sleep(1)

def handle_tcp_client(connection, address):
    """Handle incoming TCP connection."""
    print(f"TCP connection from {address}")
    try:
        data = connection.recv(BUFFER_SIZE).decode()
        filesize = int(data.strip())
        for _ in range(filesize // BUFFER_SIZE):
            connection.send(b'A' * BUFFER_SIZE)
        if filesize % BUFFER_SIZE != 0:
            connection.send(b'A' * (filesize % BUFFER_SIZE))
    finally:
        connection.close()

def tcp_server():
    """TCP server to handle incoming connections and send data."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
        tcp_socket.bind(("", SERVER_TCP_PORT))
        tcp_socket.listen()
        while True:
            client_conn, client_addr = tcp_socket.accept()
            threading.Thread(target=handle_tcp_client, args=(client_conn, client_addr)).start()


def send_payload(sock, addr, file_size):
    segments = (file_size + 1023) // 1024
    for i in range(segments):
        payload = b'A' * min(1024, file_size - (i * 1024))
        packet = struct.pack('>IBQQ', MAGIC_COOKIE, PAYLOAD_TYPE, segments, i + 1) + payload
        sock.sendto(packet, addr)
        print(f"Sent segment {i + 1}/{segments}to{addr}")

def build_message(message_type, content):
    """
    Builds a formatted UDP message.

    :param message_type: The type of the message.
    :param content: The content to send.
    :return: The formatted message.
    """
    magic_cookie = 0xabcddcba
    return struct.pack('>IB', magic_cookie, message_type) + content.encode()


def send_udp_message(host, port, message, segment_size=512):
    """
    Sends a UDP message to a specific address and port in segments.

    :param host: The target IP address.
    :param port: The target port.
    :param message: The message content to be sent.
    :param segment_size: The size of each UDP payload segment.
    """
    message_type = 0x3  # Assuming a predefined message type for simplicity.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        total_length = len(message)
        total_segments = (total_length + segment_size - 1) // segment_size  # Calculate how many segments are needed
        for segment_number in range(total_segments):
            start_index = segment_number * segment_size
            end_index = min(start_index + segment_size, total_length)
            segment_content = message[start_index:end_index]
            message_packet = build_message(message_type, segment_content)
            sock.sendto(message_packet, (host, port))
            print(f"Message segment {segment_number + 1}/{total_segments} sent to{host}:{port}")


def handle_udp_request(sock, data, addr):
    try:
        header = struct.unpack('>I', data[:4])[0]
        if header != MAGIC_COOKIE:
            print(f"Received message with invalid cookie from {addr}")
            return
        message_type = struct.unpack('>B', data[4:5])[0]
        if message_type == REQUEST_TYPE:
            file_size = struct.unpack('>Q', data[5:13])[0]
            print(f"Request from {addr} for file size {file_size} bytes")
            send_payload(sock, addr, file_size)
        else:
            print(f"Received unknown or unexpected message type from {addr}")
    except struct.error as e:
        print(f"Error parsing message from {addr}: {e}")

def start_server():
    """Start the server."""
    threading.Thread(target=broadcast_offers, daemon=True).start()
    tcp_server()

if __name__ == "_main_":
  start_server()
