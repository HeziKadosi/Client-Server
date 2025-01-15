import socket
import struct
import threading
import time

MAGIC_COOKIE = 0xabcddcba
OFFER_TYPE = 0x2
REQUEST_TYPE = 0x3
PAYLOAD_TYPE = 0x4

# === SERVER CODE ===
def broadcast_offer(udp_port, tcp_port):
    """Broadcast UDP offer messages."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        message = struct.pack(">IBHH", MAGIC_COOKIE, OFFER_TYPE, udp_port, tcp_port)
        while True:
            sock.sendto(message, ("<broadcast>", udp_port))
            time.sleep(1)

def handle_tcp_connection(conn, file_data):
    """Handle a TCP connection."""
    try:
        request = conn.recv(1024).decode().strip()
        file_size = int(request)
        conn.sendall(file_data[:file_size])
    except (ValueError, IndexError):
        conn.sendall(b"Invalid request")
    finally:
        conn.close()

def handle_udp_connection(client_address, file_data, udp_socket):
    """Send UDP packets to the client."""
    total_segments = len(file_data) // 1024 + (1 if len(file_data) % 1024 != 0 else 0)
    for segment in range(total_segments):
        payload = file_data[segment * 1024:(segment + 1) * 1024]
        message = struct.pack(">IBQQ", MAGIC_COOKIE, PAYLOAD_TYPE, total_segments, segment) + payload
        udp_socket.sendto(message, client_address)

def start_server(tcp_port, udp_port, file_size):
    """Start the multi-threaded server."""
    file_data = b"X" * file_size
    print(f"Server started, listening on IP address {socket.gethostbyname(socket.gethostname())}")
    threading.Thread(target=broadcast_offer, args=(udp_port, tcp_port), daemon=True).start()

    tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_server.bind(("", tcp_port))
    tcp_server.listen(5)

    udp_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_server.bind(("", udp_port))

    while True:
        # Handle TCP connections
        conn, addr = tcp_server.accept()
        threading.Thread(target=handle_tcp_connection, args=(conn, file_data), daemon=True).start()

        # Handle UDP requests
        try:
            data, client_address = udp_server.recvfrom(1024)
            threading.Thread(target=handle_udp_connection, args=(client_address, file_data, udp_server), daemon=True).start()
        except socket.error:
            pass

# === CLIENT CODE ===
def listen_for_offers(udp_port):
    """Listen for server offer messages."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(("", udp_port))
        print("Client started, listening for offer requests...")
        while True:
            data, addr = sock.recvfrom(1024)
            try:
                magic_cookie, message_type, server_udp_port, server_tcp_port = struct.unpack(">IBHH", data)
                if magic_cookie == MAGIC_COOKIE and message_type == OFFER_TYPE:
                    print(f"Received offer from {addr[0]}: UDP Port {server_udp_port}, TCP Port {server_tcp_port}")
                    return addr[0], server_tcp_port, server_udp_port
            except struct.error:
                continue

def tcp_transfer(server_ip, tcp_port, file_size):
    """Perform a TCP file transfer."""
    start_time = time.time()
    with socket.create_connection((server_ip, tcp_port)) as sock:
        sock.sendall(f"{file_size}\n".encode())
        received_data = b""
        while len(received_data) < file_size:
            chunk = sock.recv(1024)
            if not chunk:
                break
            received_data += chunk
    total_time = time.time() - start_time
    speed = (len(received_data) * 8) / total_time
    print(f"TCP transfer finished, total time: {total_time:.2f} seconds, total speed: {speed:.2f} bits/second")

def udp_transfer(server_ip, udp_port, file_size):
    """Perform a UDP file transfer."""
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.settimeout(1)
    request_message = struct.pack(">IBQ", MAGIC_COOKIE, REQUEST_TYPE, file_size)
    udp_socket.sendto(request_message, (server_ip, udp_port))

    start_time = time.time()
    received_segments = set()
    total_segments = None
    while True:
        try:
            data, _ = udp_socket.recvfrom(2048)
            magic_cookie, message_type, total_segments, current_segment = struct.unpack(">IBQQ", data[:21])
            if magic_cookie != MAGIC_COOKIE or message_type != PAYLOAD_TYPE:
                continue
            received_segments.add(current_segment)
        except socket.timeout:
            break

    total_time = time.time() - start_time
    speed = (len(received_segments) * 1024 * 8) / total_time
    success_rate = (len(received_segments) / total_segments) * 100 if total_segments else 0
    print(f"UDP transfer finished, total time: {total_time:.2f} seconds, total speed: {speed:.2f} bits/second, success rate: {success_rate:.2f}%")
    udp_socket.close()

def start_client(file_size, tcp_connections, udp_connections):
    """Start the client."""
    server_ip, tcp_port, udp_port = listen_for_offers(udp_port=13117)

    # Start TCP connections
    for i in range(tcp_connections):
        threading.Thread(target=tcp_transfer, args=(server_ip, tcp_port, file_size), daemon=True).start()

    # Start UDP connections
    for i in range(udp_connections):
        threading.Thread(target=udp_transfer, args=(server_ip, udp_port, file_size), daemon=True).start()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Multi-threaded UDP/TCP transfer.")
    parser.add_argument("role", choices=["server", "client"], help="Start as server or client.")
    parser.add_argument("--file_size", type=int, default=1024 * 1024 * 1024, help="Size of the file to transfer in bytes.")
    parser.add_argument("--tcp_port", type=int, default=8080, help="TCP port for the server.")
    parser.add_argument("--udp_port", type=int, default=9090, help="UDP port for the server.")
    parser.add_argument("--tcp_connections", type=int, default=1, help="Number of TCP connections (client only).")
    parser.add_argument("--udp_connections", type=int, default=2, help="Number of UDP connections (client only).")

    args = parser.parse_args()

    if args.role == "server":
        start_server(args.tcp_port, args.udp_port, args.file_size)
    elif args.role == "client":
        start_client(args.file_size, args.tcp_connections, args.udp_connections)

