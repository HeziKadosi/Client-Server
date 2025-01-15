import socket
import struct
import threading
import time

MAGIC_COOKIE = 0xabcddcba
OFFER_TYPE = 0x2
REQUEST_TYPE = 0x3
PAYLOAD_TYPE = 0x4
SERVER_TCP_PORT = 4000
SERVER_UDP_PORT = 3000
BROADCAST_PORT=8000
BUFFER_SIZE = 1024

RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"

def broadcast_offers():
    """Broadcast UDP offer messages to clients."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as udp_socket:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        message = build_message(OFFER_TYPE, f"{SERVER_UDP_PORT} {SERVER_TCP_PORT}")
        while True:
            udp_socket.sendto(message, ('<broadcast>', BROADCAST_PORT))
            print_in_color("Broadcast offer message sent.", color='yellow')
            time.sleep(1)


def print_in_color(message, color):
    """Print messages in color."""
    print(f"{color}{message}\033[0m")


def build_message(message_type, content=''):
    """Builds a formatted UDP message."""
    return struct.pack('>IB', MAGIC_COOKIE, message_type) + content.encode()

def start_tcp_server(ip_server, server_port):
    """TCP server to handle incoming connections and send data."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
        tcp_socket.bind(("", SERVER_TCP_PORT))
        tcp_socket.listen()
        while True:
            client_conn, client_addr = tcp_socket.accept()
            print_in_color(f"DBG: Server listening on {ip_server}:{server_port}", GREEN)
            threading.Thread(target=handle_tcp_client, args=(client_conn, client_addr)).start()

def handle_tcp_client(client_socket, address):
    try:
        data = client_socket.recv(1024).decode().strip()
        if data:
            file_size = int(data)
            print(f"TCP request for {file_size} bytes from {address}")
            sent = 0
            while sent < file_size:
                to_send = min(1024, file_size - sent)
                client_socket.send(b'A' * to_send)
                sent += to_send
    except Exception as e:
        print(f"Error handling TCP client {address}: {e}")
    finally:
        client_socket.close()
        print(f"TCP connection closed with {address}")

def start_udp_server(udp_port):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        server_socket.bind(('', udp_port))
        print(f"UDP Server is listening on port {udp_port}")
        handle_udp_client(server_socket, 1024)

def handle_udp_client(server_socket, buffer_size, timeout=1):
    server_socket.settimeout(timeout)
    try:
        while True:
            data, address = server_socket.recvfrom(buffer_size)
            file_size = int(data.decode().strip())
            print(f"UDP request for {file_size} bytes from {address}")
            segments = (file_size + buffer_size - 1) // buffer_size
            for i in range(segments):
                payload = b'B' * min(buffer_size, file_size - (i * buffer_size))
                server_socket.sendto(payload, address)
            print(f"All UDP packets sent to {address}")
    except socket.timeout:
        print("UDP listen timed out - no data received for 1 second")
    finally:
        print("UDP server socket closed")

def send_payload(sock, addr, file_size):
    segments = (file_size + 1023) // 1024
    for i in range(segments):
        payload = b'A' * min(1024, file_size - (i * 1024))
        packet = struct.pack('>IBQQ', MAGIC_COOKIE, PAYLOAD_TYPE, segments, i + 1) + payload
        sock.sendto(packet, addr)
        print(f"Sent segment {i + 1}/{segments}to{addr}")

def main():
    """Main function to start TCP and UDP servers."""
    # Start UDP offer broadcasting in a separate thread
    print_in_color("Starting offer broadcasting...", CYAN)
    threading.Thread(target=broadcast_offers, daemon=True).start()

    # Start UDP server in a separate thread
    print_in_color("Starting UDP server...", CYAN)
    threading.Thread(target=start_udp_server, args=(SERVER_UDP_PORT,), daemon=True).start()

    # Start TCP server in the main thread
    print_in_color("Starting TCP server...", CYAN)
    start_tcp_server("", SERVER_TCP_PORT)


if __name__ == "__main__":
    print_in_color("Server is starting...", BOLD)
    try:
        main()
    except KeyboardInterrupt:
        print_in_color("\nServer shutting down gracefully.", RED)
    except Exception as e:
        print_in_color(f"Unexpected error occurred: {e}", RED)
