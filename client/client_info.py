import re
import socket
import subprocess
import time

DNS_SERVER = "10.136.0.253"
# 反向 DNS 最大重试次数
DNS_RETRY_COUNT = 5
# 每次 DNS 重试间隔，单位：秒
DNS_RETRY_INTERVAL = 2


def get_wwan_ip():
    """
    从 ifconfig 中获取 WWAN 接口 IPv4 地址。

    支持常见的 WWAN 接口名称：
        wwan0
        wwan1
        wwan2
        ...

    返回：
        str: WWAN IPv4 地址
        None: 未获取到 WWAN IPv4 地址
    """
    try:
        result = subprocess.run(
            ["ifconfig"], capture_output=True, text=True, check=True
        )
        output = result.stdout
        current_interface = None
        for line in output.splitlines():
            # 接口行，例如：
            #
            # wwan0: flags=...
            # wwan0    Link encap:Ethernet ...
            interface_match = re.match(r"^([a-zA-Z0-9_.-]+)", line)
            if interface_match and not line.startswith(" "):
                current_interface = interface_match.group(1)
            if current_interface and current_interface.startswith("wwan"):
                # Linux ifconfig IPv4 格式：
                #
                # inet 10.136.1.100
                #
                match = re.search(r"\binet\s+(\d+\.\d+\.\d+\.\d+)", line)
                if match:
                    return match.group(1)
    except Exception:
        pass
    return None


def reverse_dns(ip):
    """
    对 IPv4 地址进行反向 DNS 查询。

    使用 Python 系统 resolver：
        socket.gethostbyaddr()

    DNS_SERVER 变量保留用于记录当前系统所使用的内部 DNS
    配置，但 socket.gethostbyaddr() 本身由系统 resolver
    决定实际使用哪个 DNS 服务器。

    例如：
        192.168.101.1
            ↓
        SA000009.cmiot

    为避免 systemd 开机启动时网络/DNS 尚未完全就绪，
    DNS 查询失败后会进行多次重试。

    返回：
        str: 解析得到的主机名
        None: 解析失败
    """
    if not ip:
        return None
    for attempt in range(1, DNS_RETRY_COUNT + 1):
        try:
            hostname, aliases, addresses = socket.gethostbyaddr(ip)
            if hostname:
                return hostname.rstrip(".")
        except (socket.herror, socket.gaierror, OSError):
            pass
        if attempt < DNS_RETRY_COUNT:
            time.sleep(DNS_RETRY_INTERVAL)
    return None


def get_client_info():
    """
    获取客户端信息。

    返回：
        {
            "ip": WWAN_IP,
            "name": 反向 DNS 名称
        }

    如果反向 DNS 无法解析，则使用 IP 作为 name。
    """
    ip = get_wwan_ip()
    if not ip:
        return {"ip": None, "name": None}
    hostname = reverse_dns(ip)
    return {"ip": ip, "name": hostname if hostname else ip}
