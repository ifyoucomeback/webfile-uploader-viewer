"""通过反向 DNS 获取客户端名称。"""

import re
import subprocess


class ClientResolver:
    """通过反向 DNS 获取客户端名称。"""

    def __init__(self, config):
        self.dns_server = config["dns"]["server"]
        self.dns_timeout = int(config["dns"]["timeout"])

    def reverse_dns(self, ip):
        def parse_nslookup_output(output):
            if not output:
                return None
            for line in output.splitlines():
                line = line.strip()
                if not line:
                    continue
                match = re.match(r"^name\s*:\s*(.+?)\s*$", line, re.IGNORECASE)
                if match:
                    hostname = match.group(1).strip()
                    if hostname:
                        hostname = hostname.rstrip(".")
                        if hostname:
                            return hostname
                match = re.search(r"\bname\s*=\s*(.+?)\s*$", line, re.IGNORECASE)
                if match:
                    hostname = match.group(1).strip()
                    if hostname:
                        hostname = hostname.rstrip(".")
                        if hostname:
                            return hostname
            return None

        try:
            result = subprocess.run(
                ["nslookup", ip, self.dns_server],
                capture_output=True,
                text=True,
                timeout=self.dns_timeout,
            )
            output = result.stdout + "\n" + result.stderr
            hostname = parse_nslookup_output(output)
            if hostname:
                return hostname
        except Exception as e:
            print(
                f"[DNS] 使用指定 DNS 查询失败: {ip}, DNS={self.dns_server}, 错误: {e}"
            )
        try:
            result = subprocess.run(
                ["nslookup", ip],
                capture_output=True,
                text=True,
                timeout=self.dns_timeout,
            )
            output = result.stdout + "\n" + result.stderr
            hostname = parse_nslookup_output(output)
            if hostname:
                return hostname
        except Exception as e:
            print(f"[DNS] 使用系统 DNS 查询失败: {ip}, 错误: {e}")
        return None

    def get_client_name(self, client_ip):
        hostname = self.reverse_dns(client_ip)
        if hostname:
            return hostname
        return client_ip
