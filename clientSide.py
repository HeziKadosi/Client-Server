import socket
import struct
import threading
import time

from tqdm import tqdm
import ANSI_colors as ac
from SeverSide import UDP_PAYLOAD_SIZE, TCP_PAYLOAD_SIZE

# ===== CONSTANTS =====
BROADCAST_PORT = 8082
UDP_TIMEOUT = 10
TCP_TIMEOUT = 10
MAGIC_COOKIE = 0xabcddcba
MESSAGE_TYPE = 0x3
RESPONSE_MESSAGE_TYPE = 0x4  # זה מתקבל בהודעת השרת
PAYLOAD_FMT = "!I B Q Q"     # פורמט המבנה (magic_cookie, message_type, total_segments, current_segment)
PAYLOAD_HEADER_SIZE = struct.calcsize(PAYLOAD_FMT)

# ===== פונקציית main =====
def main():
    # שלב 1: קבלת פרמטרים מהמשתמש
    size, tcp_count, udp_count = get_user_parameters()

    # שלב 2: מציאת שרת משדר באמצעות Broadcast
    discovered = discover_server()
    if not discovered:
        print(f"{ac.RED}No valid server offers were found. Exiting...{ac.RESET}")
        return
    udp_port, tcp_port, server_ip = discovered

    # הצגת פרטי השרת שנמצא
    print(f"{ac.GREEN}Server found!{ac.RESET}")
    print(f"UDP Port: {udp_port}, TCP Port: {tcp_port}, Server Address: {server_ip}")

    # שלב 3: ביצוע הבדיקות (TCP ו-UDP) בהתאם לפרמטרים שהמשתמש הזין
    perform_tests(size, tcp_count, udp_count, udp_port, tcp_port, server_ip)


# ===== שלב 1: פונקציית קבלת פרמטרים מהמשתמש =====
def get_user_parameters():
    print(f"{ac.CYAN}Welcome to the Speed Test Client!{ac.RESET}")
    size = prompt_for_positive_int("Enter the file size in bytes: ")
    tcp_count = prompt_for_non_negative_int("Enter the number of TCP connections: ")
    udp_count = prompt_for_non_negative_int("Enter the number of UDP connections: ")
    return size, tcp_count, udp_count


def prompt_for_positive_int(message):
    while True:
        try:
            val = int(input(f"{ac.BOLD}{ac.YELLOW}{message}{ac.RESET}"))
            if val > 0:
                return val
            else:
                print(f"{ac.RED}Please enter a positive number.{ac.RESET}")
        except ValueError:
            print(f"{ac.RED}Invalid input. Please enter a valid integer.{ac.RESET}")


def prompt_for_non_negative_int(message):
    while True:
        try:
            val = int(input(f"{ac.BOLD}{ac.YELLOW}{message}{ac.RESET}"))
            if val >= 0:
                return val
            else:
                print(f"{ac.RED}Please enter a non-negative integer.{ac.RESET}")
        except ValueError:
            print(f"{ac.RED}Invalid input. Please enter a valid integer.{ac.RESET}")


# ===== שלב 2: פונקציית גילוי השרת (Broadcast) =====
def discover_server():
    print(f"{ac.BOLD}● Listening for server offers on broadcast...{ac.RESET}")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.bind(("", BROADCAST_PORT))
        while True:
            try:
                data, address = s.recvfrom(1024)  # קבלת ההודעה
                if validate_offer(data):
                    # מבצעים פענוח של ההודעה
                    _, _, udp_port, tcp_port = struct.unpack("!I B H H", data)
                    return udp_port, tcp_port, address[0]
            except socket.timeout:
                # אם נרצה לאפשר יציאה אחרי זמן מסוים - לא ממומש פה
                break
            except Exception as e:
                print(f"{ac.RED}An error occurred while listening to offers: {e}{ac.RESET}")
                break
    return None


def validate_offer(message):
    if len(message) < 8:  # בודקים שהמבנה מינימלי
        return False
    try:
        cookie, msg_type, _, _ = struct.unpack("!I B H H", message)
        return (cookie == MAGIC_COOKIE) and (msg_type == MESSAGE_TYPE)
    except:
        return False


# ===== שלב 3: ביצוע בדיקות ה-TCP וה-UDP =====
def perform_tests(file_size, tcp_conns, udp_conns, udp_port, tcp_port, server_ip):
    print(f"{ac.GREEN}Starting speed tests...{ac.RESET}")

    # בדיקת TCP
    if tcp_conns > 0:
        print(f"{ac.CYAN}Starting TCP download test...{ac.RESET}")
        for i in range(tcp_conns):
            print(f"  {ac.YELLOW}→ TCP Connection #{i+1}{ac.RESET}")
            thr = threading.Thread(
                target=run_tcp_download,
                args=(file_size, tcp_port, server_ip, i+1)
            )
            thr.start()

    # בדיקת UDP
    if udp_conns > 0:
        print(f"{ac.CYAN}Starting UDP speed test...{ac.RESET}")
        for i in range(udp_conns):
            print(f"  {ac.YELLOW}→ UDP Connection #{i+1}{ac.RESET}")
            thr = threading.Thread(
                target=run_udp_speed_test,
                args=(file_size, udp_port, server_ip, i+1)
            )
            thr.start()

    print(f"{ac.GREEN}All tests have been initiated. Check logs above for details.{ac.RESET}")


# === פונקציית עזר לבניית הודעת בקשה (מתקבלת ע"י השרת) ===
def create_request_packet(file_size):
    # כאן 3 השדות: magic_cookie, message_type, file_size
    return struct.pack("!I B Q", MAGIC_COOKIE, MESSAGE_TYPE, file_size)


# === פונקציית עזר לפענוח הנתונים שמגיעים מהשרת (לפי הפורמט) ===
def decode_payload(data):
    try:
        header_part = data[:PAYLOAD_HEADER_SIZE]
        cookie, msg_type, total_segs, current_seg = struct.unpack(PAYLOAD_FMT, header_part)
        payload = data[PAYLOAD_HEADER_SIZE:]
        if cookie != MAGIC_COOKIE or msg_type != RESPONSE_MESSAGE_TYPE:
            # הודעה לא תקינה/שגויה
            return None
        return total_segs, current_seg, payload
    except struct.error as err:
        print(f"{ac.RED}Error decoding server payload: {err}{ac.RESET}")
        return None


# === Test Functions (TCP) ===
def run_tcp_download(file_size, tcp_port, server_ip, conn_id):
    request = create_request_packet(file_size)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_sock:
        tcp_sock.settimeout(TCP_TIMEOUT)
        try:
            print(f"[TCP-{conn_id}] Connecting to {server_ip}:{tcp_port}...")
            tcp_sock.connect((server_ip, tcp_port))
            print(f"[TCP-{conn_id}] Connected. Sending request...")
            tcp_sock.sendall(request)

            total_received = 0
            # כל עוד לא קיבלנו את כל הבייטים
            while total_received < file_size:
                data = tcp_sock.recv(TCP_PAYLOAD_SIZE + PAYLOAD_HEADER_SIZE)
                if not data:
                    print(f"[TCP-{conn_id}] Server closed the connection unexpectedly.")
                    break

                decoded = decode_payload(data)
                if decoded is None:
                    continue

                _, _, payload = decoded
                total_received += len(payload)
                print(f"[TCP-{conn_id}] Received {total_received}/{file_size} bytes.")

            print(f"[TCP-{conn_id}] Download complete! Total bytes: {total_received}")

        except socket.timeout:
            print(f"[TCP-{conn_id}] Connection timed out after {TCP_TIMEOUT} seconds.")
        except Exception as e:
            print(f"[TCP-{conn_id}] Error: {e}")


# === Test Functions (UDP) ===
def run_udp_speed_test(file_size, udp_port, server_ip, conn_id):
    packet = create_request_packet(file_size)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_sock:
        udp_sock.settimeout(UDP_TIMEOUT)

        try:
            start = time.time()
            print(f"[UDP-{conn_id}] Sending request to {server_ip}:{udp_port}...")
            udp_sock.sendto(packet, (server_ip, udp_port))

            segments_received = {}
            total_segments = None

            with tqdm(total=file_size, unit='B', unit_scale=True, desc=f"[UDP-{conn_id}] Downloading") as pbar:
                while True:
                    response, addr = udp_sock.recvfrom(UDP_PAYLOAD_SIZE + PAYLOAD_HEADER_SIZE)
                    decoded = decode_payload(response)
                    if decoded is None:
                        continue

                    t_segments, current_seg, payload_data = decoded
                    # אם עדיין לא הכרנו את כמות הסגמנטים, נשמור אותה
                    if total_segments is None:
                        total_segments = t_segments

                    # שומרים רק סגמנטים חדשים
                    if current_seg not in segments_received:
                        segments_received[current_seg] = payload_data
                        pbar.update(len(payload_data))
                    if len(segments_received) == total_segments:
                        break

            end = time.time()
            total_downloaded = sum(len(seg) for seg in segments_received.values())
            duration = end - start
            speed_kb = (total_downloaded / duration) / 1024

            print(f"[UDP-{conn_id}] Received {len(segments_received)}/{total_segments} segments.")
            print(f"[UDP-{conn_id}] Total size: {total_downloaded} bytes.")
            print(f"[UDP-{conn_id}] Time elapsed: {duration:.2f} seconds.")
            print(f"[UDP-{conn_id}] Approx. speed: {speed_kb:.2f} KB/s")

        except socket.timeout:
            print(f"[UDP-{conn_id}] No response within {UDP_TIMEOUT} seconds.")
        except Exception as e:
            print(f"[UDP-{conn_id}] An error occurred: {e}")


if __name__ == "_main_":
    main()