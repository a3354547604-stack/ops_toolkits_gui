from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OnlineUser:
    user: str
    tty: str
    login_time: str
    source: str


@dataclass(frozen=True)
class SudoEvent:
    time: str
    user: str
    command: str


@dataclass(frozen=True)
class UserActivityData:
    login_success_last_24h: int
    login_failed_last_24h: int
    sudo_users: list[str]
    online_users: list[OnlineUser]
    recent_sudo_events_last_24h: list[SudoEvent]
    abnormal_login_times_last_7d: list[str]
    rare_login_ips_last_7d: list[str]
    notes: list[str]
