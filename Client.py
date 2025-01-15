import socket
import struct
import threading
import time


MAGIC_COOKIE = 0xabcddcba
OFFER_TYPE = 0x2
BUFFER_SIZE = 1024

def receive_offers():
    """Listen for UDP offers from servers."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.bind(("", 37020))
        while True:
            data, server = udp_socket.recvfrom(1024)
            cookie, message_type, udp_port, tcp_port = struct.unpack('>IBHH', data)
            if cookie == MAGIC_COOKIE and message_type == OFFER_TYPE:
                print(f"Received offer from {server[0]} on TCP port {tcp_port}")
                perform_tcp_test(server[0], tcp_port)

def perform_tcp_test(server_ip, tcp_port):
    """Perform a TCP test by requesting data."""
    file_size = int(input("Enter the file size in bytes: "))
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
        tcp_socket.connect((server_ip, tcp_port))
        tcp_socket.sendall(f"{file_size}\n".encode())
        received_data = 0
        start_time = time.time()
        while received_data < file_size:
            data = tcp_socket.recv(BUFFER_SIZE)
            if not data:
                break
            received_data += len(data)
        end_time = time.time()
        print(f"TCP transfer completed in {end_time - start_time:.2f} seconds.")


def get_user_input():
    file_size_gb = float(input("Please enter the file size to download in gigabytes (e.g., 1 for 1GB): "))
    file_size_bytes = int(file_size_gb * 1024 * 1024 * 1024)  # 1GB = 1024^3 bytes
    tcp_connections = int(input("Please enter the number of TCP connections: "))
    udp_connections = int(input("Please enter the number of UDP connections: "))
    return file_size_bytes, tcp_connections, udp_connections





def send_tcp_request(server_ip, server_tcp_port, file_size):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
            tcp_socket.connect((server_ip, server_tcp_port))
            tcp_socket.sendall(f"{file_size}\n".encode())
            print(f"TCP request sent to {server_ip}:{server_tcp_port} for file size {file_size} bytes")
    except Exception as e:
        print(f"Error in TCP request: {e}")


def send_udp_request(server_ip, server_udp_port, file_size):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            message = f"{file_size}".encode()
            udp_socket.sendto(message, (server_ip, server_udp_port))
            print(f"UDP request sent to {server_ip}:{server_udp_port} for file size {file_size} bytes")
    except Exception as e:
        print(f"Error in UDP request: {e}")


def start_transfer(server_ip, server_tcp_port, server_udp_port, file_size):
    start_time = time.time()
    print("Starting the transfer...")
    tcp_thread = threading.Thread(target=send_tcp_request, args=(server_ip, server_tcp_port, file_size))
    udp_thread = threading.Thread(target=send_udp_request, args=(server_ip, server_udp_port, file_size))
    tcp_thread.start()
    udp_thread.start()
    tcp_thread.join()
    udp_thread.join()
    end_time = time.time()
    transfer_time = end_time - start_time
    print(f"Transfer completed in {transfer_time} seconds")




def start_client():
    """Start the client."""
    threading.Thread(target=receive_offers, daemon=True).start()
    while True:
        time.sleep(1)

if __name__ == "_main_":
  start_client()
