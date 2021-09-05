import os.path
from xdg.BaseDirectory import get_runtime_dir

def get_socket_path():
    return os.path.join(get_runtime_dir(), "ulauncher_control")
