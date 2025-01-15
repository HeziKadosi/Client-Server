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
BUFFER_SIZE = 1024

def start_server(tcp_port, udp_port):
    tcp_thread = threading.Thread(target=start_tcp_server, args=(tcp_port,))
    udp_thread = threading.Thread(target=start_udp_server, args=(udp_port,))
    tcp_thread.start()
    udp_thread.start()
    tcp_thread.join()
    udp_thread.join()


def broadcast_offers():
    """Broadcast UDP offer messages to clients."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as udp_socket:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        message = build_message(OFFER_TYPE, f"{SERVER_UDP_PORT} {SERVER_TCP_PORT}")
        while True:
            udp_socket.sendto(message, ('<broadcast>', 37020))
            print_in_color("Broadcast offer message sent.", color='yellow')
            time.sleep(1)


def start_tcp_server(ip_server, server_port):
    """TCP server to handle incoming connections and send data."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
        tcp_socket.bind(("", SERVER_TCP_PORT))
        tcp_socket.listen()
        while True:
            client_conn, client_addr = tcp_socket.accept()
            print_in_color(f"DBG: Server listening on {ip_server}:{server_port}", color="green") #לשנות
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

def start_udp_server(udp_port):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        server_socket.bind(('', udp_port))
        print(f"UDP Server is listening on port {udp_port}")
        handle_udp_client(server_socket, 1024)

def send_payload(sock, addr, file_size):
    segments = (file_size + 1023) // 1024
    for i in range(segments):
        payload = b'A' * min(1024, file_size - (i * 1024))
        packet = struct.pack('>IBQQ', MAGIC_COOKIE, PAYLOAD_TYPE, segments, i + 1) + payload
        sock.sendto(packet, addr)
        print(f"Sent segment {i + 1}/{segments}to{addr}")


def build_message(message_type, content=''):
    """Builds a formatted UDP message."""
    return struct.pack('>IB', MAGIC_COOKIE, message_type) + content.encode()


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


def parse_offer_message(data):
    """Parse an offer message."""
    try:
        format = '>IBHH'  # Big-endian: 4 bytes, 1 byte, 2 bytes, 2 bytes
        magic_cookie, msg_type, udp_port, tcp_port = struct.unpack(format, data)
        if magic_cookie != 0xabcddcba or msg_type != 0x2:
            raise ValueError("Invalid offer message")
        return {
            "magic_cookie": magic_cookie,
            "msg_type": msg_type,
            "udp_port": udp_port,
            "tcp_port": tcp_port
        }
    except struct.error:
        raise ValueError("Malformed offer message")


def print_in_color(message, color):
    """Print messages in color."""
    print(f"{color}{message}\033[0m")  # Assuming ANSI color codes



def tcp_transfer(server_ip, server_tcp_port, file_size, transfer_id):
    try:
        start_time = time.time()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
            tcp_socket.connect((server_ip, server_tcp_port))
            tcp_socket.sendall(f"{file_size}\n".encode())

            received_data = b''
            while len(received_data) < file_size:
                data = tcp_socket.recv(1024)
                if not data:
                    break
                received_data += data

            end_time = time.time()
            transfer_time = end_time - start_time
            speed = (len(received_data) * 8) / transfer_time  # speed in bits/second

            print(f"TCP transfer #{transfer_id} finished, total time: {transfer_time:.2f} seconds, total speed: {speed:.2f} bits/second")

    except Exception as e:
        print(f"Error during TCP transfer #{transfer_id}: {e}")

def udp_transfer(server_ip, server_udp_port, file_size, transfer_id):
    try:
        start_time = time.time()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.sendto(f"{file_size}".encode(), (server_ip, server_udp_port))

            received_size = 0
            expected_packets = (file_size + 1023) // 1024
            received_packets = 0

            while received_size < file_size:
                udp_socket.settimeout(1.5)  # Set a timeout longer than the server's send interval
                try:
                    data, _ = udp_socket.recvfrom(1024)
                    received_packets += 1
                    received_size += len(data)
                except socket.timeout:
                    break  # Break the loop if no data received for 1 second

            end_time = time.time()
            transfer_time = end_time - start_time
            speed = (received_size * 8) / transfer_time  # speed in bits/second
            success_rate = (received_packets / expected_packets) * 100 if expected_packets > 0 else 100

            print(f"UDP transfer #{transfer_id} finished, total time: {transfer_time:.2f} seconds, total speed: {speed:.2f} bits/second, percentage of packets received successfully: {success_rate:.2f}%")

    except Exception as e:
        print(f"Error during UDP transfer #{transfer_id}: {e}")

def start_transfers(server_ip, server_tcp_port, server_udp_port, file_size):
    tcp_thread = threading.Thread(target=tcp_transfer, args=(server_ip, server_tcp_port, file_size, 1))
    udp_thread = threading.Thread(target=udp_transfer, args=(server_ip, server_udp_port, file_size, 2))
    tcp_thread.start()
    udp_thread.start()
    tcp_thread.join()
    udp_thread.join()





if __name__ == "_main_":
    start_server(SERVER_TCP_PORT, SERVER_UDP_PORT)
    server_ip = '192.168.1.5'  # Server IP address
    file_size = 1024 * 1024 * 1  # File size of 1MB for example
    start_transfers(server_ip, SERVER_TCP_PORT, SERVER_UDP_PORT, file_size)
