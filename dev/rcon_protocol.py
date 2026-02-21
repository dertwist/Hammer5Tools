import socket
import threading

def receive(client):
    while True:
        try:
            data = client.recv(4096)
            if not data:
                print("Connection closed by server")
                break
            print(f"< {data.decode('utf-8')}", end="")
        except OSError:
            break

def main():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(("127.0.0.1", 2121))
    print("Connected to CS2 console. Type commands (Ctrl+C to quit):\n")

    # Start listener thread
    listener = threading.Thread(target=receive, args=(client,), daemon=True)
    listener.start()

    try:
        while True:
            cmd = input("> ")
            client.sendall((cmd + "\n").encode("utf-8"))
    except (KeyboardInterrupt, EOFError):
        print("\nDisconnecting...")
    finally:
        client.close()

if __name__ == "__main__":
    main()
