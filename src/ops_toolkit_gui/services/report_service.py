from __future__ import annotations

import html
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ops_toolkit_gui.models.common import CollectorResult
from ops_toolkit_gui.models.filesystem import FilesystemData
from ops_toolkit_gui.models.logs import LogData
from ops_toolkit_gui.models.performance import PerformanceData
from ops_toolkit_gui.models.user_activity import UserActivityData


@dataclass(frozen=True)
class ReportBundle:
    text: str
    html: str


class ReportService:
    def build_report(
        self,
        *,
        perf: CollectorResult[PerformanceData] | None,
        activity: CollectorResult[UserActivityData] | None,
        fs: CollectorResult[FilesystemData] | None,
        logs: CollectorResult[LogData] | None,
    ) -> ReportBundle:
        now = datetime.now().strftime("%F %T")

        lines: list[str] = [f"Ops Toolkit Report @ {now}", ""]
        lines.append(self._section_perf(perf))
        lines.append(self._section_activity(activity))
        lines.append(self._section_fs(fs))
        lines.append(self._section_logs(logs))
        text_out = "\n".join(lines).strip() + "\n"

        html_out = self._wrap_html(text_out)
        return ReportBundle(text=text_out, html=html_out)

    def default_report_path(self) -> Path:
        base = Path.home() / "ops_toolkit_reports"
        base.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        return base / f"ops_report_{ts}.html"

    def write_html(self, path: str | os.PathLike[str], html_str: str) -> str:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(html_str, encoding="utf-8")
        return str(p)

    def _section_perf(self, r: CollectorResult[PerformanceData] | None) -> str:
        if r is None:
            return "[Performance]\n- no data\n"
        d = r.data
        return (
            "[Performance]\n"
            f"- ts: {r.ts:%F %T}\n"
            f"- status: {r.status} (warnings={r.warning_count})\n"
            f"- cpu_total: {d.cpu_total_percent:.1f}%\n"
            f"- mem_used: {d.memory.used_percent}% ({d.memory.used_mb}/{d.memory.total_mb} MB)\n"
            f"- load: {d.load.load1:.2f}, {d.load.load5:.2f}, {d.load.load15:.2f}\n"
        )

    def _section_activity(self, r: CollectorResult[UserActivityData] | None) -> str:
        if r is None:
            return "[Activity]\n- no data\n"
        d = r.data
        return (
            "[Activity]\n"
            f"- ts: {r.ts:%F %T}\n"
            f"- status: {r.status} (warnings={r.warning_count})\n"
            f"- login_success_24h: {d.login_success_last_24h}\n"
            f"- login_failed_24h: {d.login_failed_last_24h}\n"
            f"- sudo_users: {', '.join(d.sudo_users) if d.sudo_users else '(none)'}\n"
        )

    def _section_fs(self, r: CollectorResult[FilesystemData] | None) -> str:
        if r is None:
            return "[Filesystem]\n- no data\n"
        d = r.data
        top_mounts = sorted(d.mounts, key=lambda m: m.used_percent, reverse=True)[:5]
        mounts_str = "\n".join(
            [f"  - {m.mountpoint}: {m.used_percent}% ({m.used_gb:.2f}/{m.total_gb:.2f} GB)" for m in top_mounts]
        )
        return (
            "[Filesystem]\n"
            f"- ts: {r.ts:%F %T}\n"
            f"- status: {r.status} (warnings={r.warning_count})\n"
            f"- top_mounts:\n{mounts_str}\n"
        )

    def _section_logs(self, r: CollectorResult[LogData] | None) -> str:
        if r is None:
            return "[Logs]\n- no data\n"
        d = r.data
        hits = ", ".join([f"{h.keyword}:{h.count}" for h in d.keyword_hits]) if d.keyword_hits else "(none)"
        return (
            "[Logs]\n"
            f"- ts: {r.ts:%F %T}\n"
            f"- status: {r.status} (warnings={r.warning_count})\n"
            f"- path: {d.path}\n"
            f"- keyword_hits: {hits}\n"
        )

    def _wrap_html(self, text_out: str) -> str:
        escaped = html.escape(text_out)
        return (
            "<!doctype html>"
            "<html><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<title>Ops Toolkit Report</title>"
            "<style>body{font-family:ui-monospace,Menlo,Consolas,monospace;margin:24px;}"
            "pre{white-space:pre-wrap;line-height:1.35;}"
            "</style></head><body>"
            "<h1>Ops Toolkit Report</h1>"
            f"<pre>{escaped}</pre>"
            "</body></html>"
        )
