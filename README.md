# Inky Frame

MicroPython applications and framework for Pimoroni Inky Frame 7.3".

## Getting Started

### 1. Configuration (`secrets.py`)

Sensitive network credentials and API keys are stored in `secrets.py`, which is ignored by git.

Create your local configuration from the example template:

```bash
cp secrets.py.example secrets.py
```

Edit `secrets.py` to set:
- **`WIFI_SSID` / `WIFI_PASSWORD`**: Your local Wi-Fi network credentials.
- **`TRMNL_BASE_URL`**: Base URL of your self-hosted TRMNL BYOS/BYOD-S server (e.g. `http://192.168.1.100:3000`).
- **`TRMNL_API_KEY`**: Device API access token (optional if auto-provisioning via `/api/setup`).
- **`TRMNL_DEVICE_ID`**: MAC address override (leave empty to use device hardware MAC).

### 2. Development

Run linter, formatter check, and type checks:

```bash
uv run scripts/lint.py check
```

Watch local files and auto-sync changes to the Inky Frame over `mpremote`:

```bash
uv run watch_and_upload.py
```
