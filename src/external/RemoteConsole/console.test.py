def send_vconsole_command(command: str):
    """Send a command to CS2 via VConsole socket (port 29000)"""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(("127.0.0.1", 29000))

        # VConsole2 protocol: send command with newline
        sock.send(f"{command}\n".encode('utf-8'))
        sock.close()
    except socket.timeout:
        # Timeout is expected if CS2 console isn't responding
        pass
    except Exception as e:
        # Log but don't fail - VConsole may not be available
        print(f"VConsole send error: {e}")




send_vconsole_command("say d")