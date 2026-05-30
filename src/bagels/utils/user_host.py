import getpass
import socket

from rich.text import Text


def get_user_host_string() -> Text:
    try:
        username = getpass.getuser()
        hostname = socket.gethostname()
        return f"{username}@{hostname}"
    except Exception:
        return "unknown@unknown"
