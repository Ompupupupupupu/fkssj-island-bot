# -*- coding: utf-8 -*-
"""极简 ADB 客户端：通过本机 adb server (127.0.0.1:5037) 执行 shell 命令。

用法:
    from pyadb import Adb
    adb = Adb()                      # 自动选唯一设备
    print(adb.shell('ps -A').decode())
"""
import socket


class Adb:
    def __init__(self, host: str = '127.0.0.1', port: int = 5037,
                 serial: str | None = None):
        self.host = host
        self.port = port
        self.serial = serial or self._pick_serial()

    def _conn(self) -> socket.socket:
        s = socket.create_connection((self.host, self.port), timeout=10)
        return s

    def _send(self, s: socket.socket, cmd: str) -> None:
        data = cmd.encode('utf-8')
        s.sendall(f'{len(data):04x}'.encode() + data)

    def _check(self, s: socket.socket) -> bytes:
        resp = s.recv(4)
        if resp != b'OKAY':
            msg = b''
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                msg += chunk
            raise RuntimeError(f'ADB FAIL: {msg}')
        return b'OKAY'

    def _pick_serial(self) -> str:
        s = self._conn()
        self._send(s, 'host:devices')
        self._check(s)
        # 长度前缀
        length = int(s.recv(4).decode(), 16)
        data = b''
        while len(data) < length:
            data += s.recv(length - len(data))
        s.close()
        devices = []
        for line in data.decode().strip().split('\n'):
            line = line.strip()
            if line:
                devices.append(line.split('\t')[0])
        if not devices:
            raise RuntimeError('no devices')
        return devices[0]

    def shell(self, cmd: str, timeout: float = 30) -> bytes:
        s = self._conn()
        s.settimeout(timeout)
        self._send(s, f'host:transport:{self.serial}')
        self._check(s)
        self._send(s, f'shell:{cmd}')
        self._check(s)
        out = b''
        while True:
            try:
                chunk = s.recv(65536)
            except socket.timeout:
                break
            if not chunk:
                break
            out += chunk
        s.close()
        return out

    def execout_to_file(self, cmd: str, local_path: str, timeout: float = 300) -> int:
        """通过 exec: 服务（无 PTY，二进制安全）把命令输出写入本地文件。"""
        s = self._conn()
        s.settimeout(timeout)
        self._send(s, f'host:transport:{self.serial}')
        self._check(s)
        self._send(s, f'exec:{cmd}')
        self._check(s)
        total = 0
        with open(local_path, 'wb') as f:
            while True:
                chunk = s.recv(131072)
                if not chunk:
                    break
                f.write(chunk)
                total += len(chunk)
        s.close()
        return total

    def shell_to_file(self, cmd: str, local_path: str, timeout: float = 120) -> int:
        """把 shell 命令输出直接流式写入本地文件（用于大块 dump）。"""
        s = self._conn()
        s.settimeout(timeout)
        self._send(s, f'host:transport:{self.serial}')
        self._check(s)
        self._send(s, f'shell:{cmd}')
        self._check(s)
        total = 0
        with open(local_path, 'wb') as f:
            while True:
                chunk = s.recv(131072)
                if not chunk:
                    break
                f.write(chunk)
                total += len(chunk)
        s.close()
        return total

    def push_file(self, local_path: str, device_path: str, mode: int = 0o755,
                  timeout: float = 300) -> None:
        """通过 sync 协议推送本地文件（支持大文件、二进制安全）。"""
        import os
        import struct
        import time
        s = self._conn()
        s.settimeout(timeout)
        self._send(s, f'host:transport:{self.serial}')
        self._check(s)
        self._send(s, 'sync:')
        self._check(s)

        size = os.path.getsize(local_path)
        header = f'{device_path},{mode}'.encode('utf-8')
        s.sendall(b'SEND' + struct.pack('<I', len(header)) + header)
        mtime = int(time.time())
        with open(local_path, 'rb') as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                s.sendall(b'DATA' + struct.pack('<I', len(chunk)) + chunk)
                self._read_sync_status(s)
        s.sendall(b'DONE' + struct.pack('<I', mtime))
        self._read_sync_status(s)
        s.close()
        print(f'pushed {size} bytes -> {device_path}')

    @staticmethod
    def _read_sync_status(s: socket.socket) -> None:
        import struct
        tag = b''
        while len(tag) < 4:
            tag += s.recv(4 - len(tag))
        length = struct.unpack('<I', s.recv(4))[0]
        msg = b''
        while len(msg) < length:
            msg += s.recv(length - len(msg))
        if tag != b'OKAY':
            raise RuntimeError(f'sync FAIL {tag} {msg}')


if __name__ == '__main__':
    import sys
    adb = Adb()
    print('serial:', adb.serial)
    print(adb.shell(' '.join(sys.argv[1:]) or 'id').decode('utf-8', 'replace'))
