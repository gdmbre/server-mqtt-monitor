"""Notify about new successful SSH authentications from systemd journal.

Requires journalctl access (the packaged systemd service normally runs as root).
The first run stores a baseline and does not report historical logins.
"""

import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from .base import BaseCheck


class LastLoginCheck(BaseCheck):
    NAME = "last_login"
    ACCEPTED = re.compile(
        r"^Accepted\s+(?P<method>\S+)\s+for\s+(?P<user>\S+)\s+"
        r"from\s+(?P<address>\S+)\s+port\s+(?P<port>\d+)\b"
    )

    def __init__(self, settings, mqtt):
        super().__init__(settings, mqtt)
        self.state_file = Path(
            self.config.get("state_file", "/var/lib/server-monitor/last_login.json")
        )

    def _entries(self, *, cursor=None, since=None, lines=None):
        cmd = [
            "journalctl", "-u", "ssh", "-u", "sshd",
            "--output=json", "--no-pager", "--quiet",
        ]
        if cursor:
            cmd.append(f"--after-cursor={cursor}")
        elif since is not None:
            cmd.append(f"--since=@{int(since)}")
        if lines is not None:
            cmd.extend(["-n", str(lines)])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(
                "last_login: failed to read SSH journal: "
                + (result.stderr.strip() or f"exit={result.returncode}")
            )

        entries = []
        for line in result.stdout.splitlines():
            if line.strip():
                entries.append(json.loads(line))
        return entries

    def _save(self, state):
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        temp = self.state_file.with_name(self.state_file.name + ".tmp")
        temp.write_text(json.dumps(state, ensure_ascii=False) + "\n", encoding="utf-8")
        temp.replace(self.state_file)

    def run(self):
        if not self.state_file.exists():
            # First launch: do not treat the entire existing journal as new logins.
            recent = self._entries(lines=1)
            state = {"since": int(time.time())}
            if recent:
                state["cursor"] = recent[-1].get("__CURSOR")
            self._save(state)
            print("last_login: journal baseline saved; waiting for new SSH logins", flush=True)
            return

        state = json.loads(self.state_file.read_text(encoding="utf-8"))
        entries = self._entries(cursor=state.get("cursor"), since=state.get("since"))
        if not entries:
            return

        for entry in entries:
            message = entry.get("MESSAGE", "")
            match = self.ACCEPTED.search(message if isinstance(message, str) else "")
            if not match:
                continue

            when = entry.get("__REALTIME_TIMESTAMP")
            try:
                timestamp = datetime.fromtimestamp(
                    int(when) / 1_000_000, tz=timezone.utc
                ).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
            except (TypeError, ValueError, OverflowError, OSError):
                timestamp = "unknown"

            self.mqtt.warning(
                f"🔐 SSH login on {self.settings.device_name}: "
                f"user={match.group('user')}, "
                f"IP={match.group('address')}, "
                f"auth={match.group('method')}, "
                f"time={timestamp}"
            )

        # Advance only after the entries have been handled.
        last = entries[-1]
        if last.get("__CURSOR"):
            state["cursor"] = last["__CURSOR"]
        if last.get("__REALTIME_TIMESTAMP"):
            state["since"] = int(last["__REALTIME_TIMESTAMP"]) // 1_000_000
        self._save(state)
