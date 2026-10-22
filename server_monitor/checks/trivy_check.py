"""Trivy CVE check for gdmbre/server-mqtt-monitor.

The check runs in a background thread because scanning several images can take
many minutes. It uses the existing MQTT publisher and the Diun image list.
"""

import json
import os
import subprocess
import threading
from pathlib import Path

from .base import BaseCheck


class TrivyCheck(BaseCheck):
    NAME = "trivy"

    def __init__(self, settings, mqtt):
        super().__init__(settings, mqtt)
        self._worker = None

    def run(self):
        # Do not stall the regular one-second monitor loop.
        if self._worker and self._worker.is_alive():
            return
        self._worker = threading.Thread(
            target=self._safe_scan,
            name="server-monitor-trivy",
            daemon=True,
        )
        self._worker.start()

    def _safe_scan(self):
        try:
            self._scan()
        except Exception as exc:
            print(f"Trivy check failed: {exc}", flush=True)
            self.mqtt.warning(f"NAS: ошибка проверки Trivy: {str(exc)[:240]}")

    def _images(self):
        configured = self.config.get("images")
        if configured:
            return list(dict.fromkeys(configured))

        # Compatible with Diun provider-file YAML: '- name: image:tag'.
        filename = Path(self.config.get("images_file", "/home/ratkill/diun/images.yml"))
        images = []
        for line in filename.read_text(encoding="utf-8").splitlines():
            entry = line.split("#", 1)[0].strip()
            if entry.startswith("- name:"):
                image = entry.split(":", 1)[1].strip().strip("\"'")
                if image:
                    images.append(image)
        if not images:
            raise ValueError(f"Нет Docker-образов в {filename}")
        return list(dict.fromkeys(images))

    def _vulnerabilities(self, image):
        cmd = [
            "docker", "run", "--rm", "-e", "GODEBUG=http2client=0",
            "--security-opt", "no-new-privileges", "--cap-drop", "ALL",
            "-v", "trivy-cache:/root/.cache/",
            self.config.get("trivy_image", "ghcr.io/aquasecurity/trivy:latest"),
            "image", "--image-src", "remote", "--scanners", "vuln",
            "--severity", "HIGH,CRITICAL", "--format", "json",
            "--quiet", "--timeout", "20m", image,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1320)
        if result.returncode:
            raise RuntimeError(
                result.stderr.strip()[-350:] or f"Trivy exit code {result.returncode}"
            )
        report = json.loads(result.stdout)
        current = {}
        for target in report.get("Results", []):
            for finding in target.get("Vulnerabilities") or []:
                if finding.get("Status") == "not_affected":
                    continue
                cve = finding.get("VulnerabilityID")
                if not cve:
                    continue
                package = finding.get("PkgName", "-")
                key = "|".join((target.get("Target", ""), cve, package))
                current[key] = {
                    "id": cve,
                    "pkg": package,
                    "severity": finding.get("Severity", ""),
                    "fixed": bool(finding.get("FixedVersion")),
                }
        return current

    def _scan(self):
        images = self._images()
        state_file = Path(self.config.get(
            "state_file", "/var/lib/server-monitor/trivy-state.json"
        ))
        if state_file.exists():
            state = json.loads(state_file.read_text(encoding="utf-8"))
        else:
            state = {"images": {}, "errors": []}

        previous_images = state.get("images", {})
        old_errors = set(state.get("errors", []))
        new_images = dict(previous_images)
        errors = []

        for image in images:
            try:
                current = self._vulnerabilities(image)
                previous = previous_images.get(image)
                if previous is None:
                    print(f"Trivy BASELINE {image}: {len(current)} CVE", flush=True)
                else:
                    changes = []
                    for key, item in current.items():
                        old = previous.get(key)
                        new_critical = item["severity"] == "CRITICAL" and (
                            old is None or old.get("severity") != "CRITICAL"
                        )
                        new_fix = item["fixed"] and (old is None or not old.get("fixed"))
                        if new_critical or new_fix:
                            changes.append(item)
                    if changes:
                        lines = [f"NAS: новые уязвимости — {image} ({len(changes)})"]
                        for item in changes[:6]:
                            fix = "есть исправление" if item["fixed"] else "без исправления"
                            lines.append(
                                f"{item['severity']} {item['id']} / {item['pkg']} — {fix}"
                            )
                        if len(changes) > 6:
                            lines.append(f"...и ещё {len(changes) - 6}")
                        self.mqtt.warning("\n".join(lines))
                        print(f"Trivy ALERT {image}: {len(changes)}", flush=True)
                    else:
                        print(f"Trivy OK {image}: новых приоритетных CVE нет", flush=True)
                new_images[image] = current
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
                errors.append(image)
                print(f"Trivy ERROR {image}: {exc}", flush=True)
                if image not in old_errors:
                    self.mqtt.warning(f"NAS: Trivy не смог проверить {image}: {str(exc)[:180]}")

        state_file.parent.mkdir(parents=True, exist_ok=True)
        data = {"images": new_images, "errors": errors}
        temp = state_file.with_suffix(".tmp")
        with temp.open("w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o600)
            json.dump(data, stream, ensure_ascii=False, indent=2)
        temp.replace(state_file)
        if old_errors and not errors:
            self.mqtt.info("NAS: сканирование Trivy снова работает без ошибок")
