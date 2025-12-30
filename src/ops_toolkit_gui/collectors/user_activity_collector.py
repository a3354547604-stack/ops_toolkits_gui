from __future__ import annotations

import os
import platform
import re
import subprocess
from datetime import datetime, timedelta

from ops_toolkit_gui.models.common import CollectorResult
from ops_toolkit_gui.models.user_activity import OnlineUser, SudoEvent, UserActivityData


class UserActivityCollector:
    def __init__(
        self,
        auth_log_paths: tuple[str, ...] = ("/var/log/auth.log", "/var/log/secure"),
    ) -> None:
        self.auth_log_paths = auth_log_paths

    def collect(self) -> CollectorResult[UserActivityData]:
        ts = datetime.now()
        warnings: list[str] = []
        notes: list[str] = []

        online = self._online_users(notes)
        succ, fail, rare_ips, abnormal = self._authlog_stats(notes)
        sudo_users, sudo_events = self._sudo_stats(notes)

        status = "OK" if not warnings else "WARN"
        data = UserActivityData(
            login_success_last_24h=succ,
            login_failed_last_24h=fail,
            sudo_users=sudo_users,
            online_users=online,
            recent_sudo_events_last_24h=sudo_events,
            abnormal_login_times_last_7d=abnormal,
            rare_login_ips_last_7d=rare_ips,
            notes=notes,
        )
        return CollectorResult(
            ts=ts,
            status=status,
            warning_count=len(warnings),
            warnings=warnings,
            data=data,
        )

    def _online_users(self, notes: list[str]) -> list[OnlineUser]:
        if platform.system().lower() != "linux":
            notes.append("Online users: supported on Linux only")
            return []

        try:
            out = subprocess.check_output(["who"], text=True, stderr=subprocess.DEVNULL)
        except Exception as e:
            notes.append(f"who failed: {e}")
            return []

        rows: list[OnlineUser] = []
        for line in out.splitlines():
            parts = line.split()
            if len(parts) < 4:
                continue
            user = parts[0]
            tty = parts[1]
            login_time = " ".join(parts[2:4])
            source = ""
            m = re.search(r"\(([^)]+)\)", line)
            if m:
                source = m.group(1)
            rows.append(OnlineUser(user=user, tty=tty, login_time=login_time, source=source))
        return rows

    def _authlog_stats(self, notes: list[str]) -> tuple[int, int, list[str], list[str]]:
        if platform.system().lower() != "linux":
            notes.append("Login history analysis: supported on Linux only")
            return 0, 0, [], []

        auth_path = next((p for p in self.auth_log_paths if os.path.exists(p)), "")
        if not auth_path:
            notes.append("No auth log found (/var/log/auth.log or /var/log/secure)")
            return 0, 0, [], []

        try:
            with open(auth_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()[-20000:]
        except Exception as e:
            notes.append(f"Read auth log failed: {e}")
            return 0, 0, [], []

        since_24h = datetime.now() - timedelta(hours=24)
        since_7d = datetime.now() - timedelta(days=7)

        succ = 0
        fail = 0
        ip_counter: dict[str, int] = {}
        abnormal_lines: list[str] = []

        rx_time = re.compile(r"^(\w{3}\s+\d+\s+\d{2}:\d{2}:\d{2})\s+")
        rx_ip = re.compile(r"(\d{1,3}(?:\.\d{1,3}){3})")

        for line in lines:
            tmatch = rx_time.search(line)
            if not tmatch:
                continue

            ts = self._parse_syslog_time(tmatch.group(1))
            if ts is None:
                continue

            if "Accepted password" in line or "Accepted publickey" in line:
                if ts >= since_24h:
                    succ += 1
                if ts >= since_7d:
                    ip = self._extract_ip(rx_ip, line)
                    if ip:
                        ip_counter[ip] = ip_counter.get(ip, 0) + 1

                    if ts.hour < 6 or ts.hour >= 23:
                        abnormal_lines.append(line.strip())

            if "Failed password" in line or "authentication failure" in line:
                if ts >= since_24h:
                    fail += 1

        rare_ips = [ip for ip, c in ip_counter.items() if c == 1][:10]
        return succ, fail, rare_ips, abnormal_lines[:20]

    def _sudo_stats(self, notes: list[str]) -> tuple[list[str], list[SudoEvent]]:
        if platform.system().lower() != "linux":
            notes.append("Sudo audit: supported on Linux only")
            return [], []

        auth_path = next((p for p in self.auth_log_paths if os.path.exists(p)), "")
        if not auth_path:
            return [], []

        try:
            with open(auth_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()[-20000:]
        except Exception as e:
            notes.append(f"Read auth log failed: {e}")
            return [], []

        since_24h = datetime.now() - timedelta(hours=24)
        rx_time = re.compile(r"^(\w{3}\s+\d+\s+\d{2}:\d{2}:\d{2})\s+")
        rx_sudo = re.compile(r"sudo: \s*(\w+)\s*:\s*.*COMMAND=(.*)$")

        users: set[str] = set()
        events: list[SudoEvent] = []

        for line in lines:
            if "sudo:" not in line:
                continue

            tmatch = rx_time.search(line)
            if not tmatch:
                continue
            ts = self._parse_syslog_time(tmatch.group(1))
            if ts is None or ts < since_24h:
                continue

            mm = rx_sudo.search(line)
            if not mm:
                continue

            user = mm.group(1)
            cmd = mm.group(2).strip()
            users.add(user)
            events.append(SudoEvent(time=ts.strftime("%F %T"), user=user, command=cmd))

        events = events[-50:]
        return sorted(users), events

    def _parse_syslog_time(self, s: str) -> datetime | None:
        try:
            dt = datetime.strptime(s, "%b %d %H:%M:%S")
            return dt.replace(year=datetime.now().year)
        except Exception:
            return None

    def _extract_ip(self, rx_ip: re.Pattern[str], line: str) -> str:
        m = rx_ip.search(line)
        return m.group(1) if m else ""
