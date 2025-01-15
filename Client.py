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

def start_client():
    """Start the client."""
    threading.Thread(target=receive_offers, daemon=True).start()
    while True:
        time.sleep(1)

if __name__ == "_main_":
  start_client()
