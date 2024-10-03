import socket
import os
import time

# Path to the Unix Domain Socket (ensure it matches the server's socket path)
SOCKET_PATH = "/tmp/gst_detection.sock"

def main():
    # Create a Unix Domain Socket
    client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    try:
        # Connect to the server's socket
        client_socket.connect(SOCKET_PATH)
        print(f"Connected to Unix Domain Socket at {SOCKET_PATH}")

        # Set the socket to non-blocking mode
        client_socket.setblocking(False)

        # Listen for messages from the server
        while True:
            try:
                # Try to receive data without blocking
                data = client_socket.recv(1024)
                if data:
                    print(f"Received data: {data.decode('utf-8')}")
                else:
                    print("Server disconnected")
                    break
            
            except BlockingIOError:
                # No data available, continue loop
                pass
            
            # You can add a small sleep to prevent busy looping
            time.sleep(0.01)

    except FileNotFoundError:
        print(f"Socket path '{SOCKET_PATH}' does not exist. Please ensure the server is running.")
    
    except ConnectionRefusedError:
        print("Could not connect to the server. Please make sure the server is running and accessible.")

    except KeyboardInterrupt:
        print("Client shut down by user")

    finally:
        # Close the socket
        client_socket.close()

if __name__ == "__main__":
    main()
