# server-mqtt-monitor

A small configurable Linux monitoring service written in Python. It publishes
metrics and warnings to MQTT and is designed to use the same code on multiple
servers with a different TOML configuration per host.

## Checks

- CPU temperature
- CPU load
- Network interface throughput
- systemd service state
- Network interface state
- `/var/run/reboot-required`
- New login detection
- Raspberry Pi throttling / under-voltage via `vcgencmd`
- USB / kernel warnings from `journalctl`
- SMART health and disk temperature via `smartctl`

Every check can be enabled or disabled independently and has its own interval.

## MQTT topic layout

Set a unique `topic_prefix` on each machine:

```toml
topic_prefix = "servers/nas"
```

Typical topics:

```text
servers/nas/cpu_temp
servers/nas/cpu_load
servers/nas/network/enp2s0/mbps
servers/nas/smart/dev_sda/healthy
servers/nas/smart/dev_sda/temperature
servers/nas/warning
servers/nas/info
```

For another machine:

```toml
topic_prefix = "servers/router"
```

## Quick test from a cloned repository

Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y python3 python3-venv smartmontools

python3 -m venv .venv
source .venv/bin/activate
pip install .

cp config.example.toml config.toml
nano config.toml

server-monitor --config config.toml
```

`config.toml` is ignored by Git so credentials are not accidentally committed.

## System installation

Clone the repository and run:

```bash
sudo ./install.sh
```

Then edit:

```bash
sudo nano /etc/server-monitor/config.toml
```

Start the service:

```bash
sudo systemctl start server-monitor
```

Check status and logs:

```bash
systemctl status server-monitor
sudo journalctl -u server-monitor -f
```

## Update from GitHub

Inside the cloned repository:

```bash
git pull
sudo /opt/server-monitor/venv/bin/pip install .
sudo systemctl restart server-monitor
```

## Notes

`rpi_throttled` should normally be enabled only on Raspberry Pi.

SMART checks require `smartmontools`. The included systemd service runs as
root so `smartctl` and kernel journal access work on typical Ubuntu/Debian
systems.

On virtual machines, CPU temperature may not be exposed by the hypervisor. In
that case disable `checks.cpu_temp` in the config.

Before publishing this repository, never commit a real MQTT password.
