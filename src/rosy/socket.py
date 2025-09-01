import platform
import socket


def setup_socket(
    sock: socket.socket,
    send_buffer_size: int = None,
    send_timeout_ms: int = 5000,
    keepalive_idle_s: int = 5,
    keepalive_interval_s: int = 5,
    keepalive_count: int = 5,
) -> None:
    """
    Set up a socket for more realtime communication and faster connection
    failure detection.

    Args:
        sock:
            Socket to set up.
        send_buffer_size:
            Send buffer size (in bytes). If None, the default is used.
        send_timeout_ms:
            Max time (ms) data packets go unacked before declaring the connection dead.
        keepalive_idle_s:
            Send keepalive packets after this many seconds of idle time.
        keepalive_interval_s:
            Interval between keepalive packets.
        keepalive_count:
            Number of unacked keepalive packets to send before declaring the connection dead.
    """

    if send_buffer_size is not None:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, send_buffer_size)

    if hasattr(socket, "TCP_USER_TIMEOUT"):
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_USER_TIMEOUT, send_timeout_ms)

    # Disable Nagle's algorithm for lower latency
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    # Enable keepalive
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

    system = platform.system()
    if system == "Linux":
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, keepalive_idle_s)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, keepalive_interval_s)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, keepalive_count)
    elif system == "Darwin":
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPALIVE, keepalive_idle_s)
        try:
            sock.setsockopt(
                socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, keepalive_interval_s
            )
        except AttributeError:
            pass
        try:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, keepalive_count)
        except AttributeError:
            pass
