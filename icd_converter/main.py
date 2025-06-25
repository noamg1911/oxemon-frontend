import socket
import json
import icd
import converter
from hydration import Message

# Configuration
LISTEN_IP = "0.0.0.0"
LISTEN_PORT = 8765

def main():
    with open("example/oxemon_dictionary.json", "r") as f:
        hash_converter = converter.create_conversion_map(json.load(f))

    # Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Bind to the IP and port
    sock.bind((LISTEN_IP, LISTEN_PORT))
    print(f"Listening for UDP packets on {LISTEN_IP}:{LISTEN_PORT}...")

    try:
        while True:
            data, addr = sock.recvfrom(4096)  # 4096 bytes buffer
            print(f"\nReceived {len(data)} bytes from {addr}:")
            print(f"Raw bytes: {data}")

            try:
                event = converter.convert_incoming_message(
                    message=data,
                    conversion_map=hash_converter
                )
                print(event)
            except ValueError as e:
                print("Got invalid message: ", e)
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        sock.close()

if __name__ == "__main__":
    main()
