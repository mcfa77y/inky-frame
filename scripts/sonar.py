# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
scripts/sonar.py
CLI tool to manage and run SonarQube scans for inky-frame using uv.

Usage:
    uv run scripts/sonar.py [COMMAND] [OPTIONS]

Commands:
    scan      Run SonarScanner on project sources (default)
    status    Show SonarQube container health, API status, and latest project metrics
    start     Start or launch the local SonarQube Docker container
    stop      Stop the SonarQube Docker container
    logs      Show recent logs from the SonarQube container
    open      Open the SonarQube project dashboard in the default web browser
"""

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

DEFAULT_HOST = "http://localhost:9000"
DEFAULT_PROJECT = "inky-frame"

# ANSI Colors
CLR_RESET = "\033[0m"
CLR_BOLD = "\033[1m"
CLR_GREEN = "\033[32m"
CLR_RED = "\033[31m"
CLR_YELLOW = "\033[33m"
CLR_BLUE = "\033[34m"
CLR_CYAN = "\033[36m"


def load_dotenv():
    env_file = os.path.join(os.getcwd(), ".env")
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip('"').strip("'")


def get_docker_containers():
    """Find SonarQube and DB containers if present."""
    try:
        res = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}"],
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception:
        return []

    containers = []
    for line in res.stdout.strip().splitlines():
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 4:
            cid, name, img, status = parts[0], parts[1], parts[2], parts[3]
            if "sonar" in name.lower() or "sonar" in img.lower():
                is_running = status.lower().startswith("up")
                containers.append({
                    "id": cid,
                    "name": name,
                    "image": img,
                    "status": status,
                    "running": is_running,
                    "is_app": "sonarqube" in img.lower() or name == "sonarqube",
                })
    return containers


def check_api_health(host_url):
    url = f"{host_url}/api/system/status"
    try:
        with urllib.request.urlopen(url, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            return data.get("status") == "UP", data.get("status", "DOWN"), data.get("version", "unknown")
    except Exception:
        return False, "UNREACHABLE", "unknown"


def validate_token(host_url, token):
    if not token:
        return False
    url = f"{host_url}/api/authentication/validate"
    req = urllib.request.Request(url)
    creds = base64.b64encode(f"{token}:".encode()).decode()
    req.add_header("Authorization", f"Basic {creds}")
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            return data.get("valid", False)
    except Exception:
        return False


def ensure_project_and_token(host_url, project_key):
    auth_b64 = base64.b64encode(b"admin:admin").decode()
    headers = {"Authorization": f"Basic {auth_b64}"}

    # Ensure project exists
    try:
        search_url = f"{host_url}/api/projects/search?projects={project_key}"
        req = urllib.request.Request(search_url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            if data.get("paging", {}).get("total", 0) == 0:
                print(f"{CLR_CYAN}[INFO]{CLR_RESET} Initializing project '{project_key}' in SonarQube...")
                create_data = urllib.parse.urlencode({"project": project_key, "name": project_key}).encode()
                create_req = urllib.request.Request(f"{host_url}/api/projects/create", data=create_data, headers=headers)
                urllib.request.urlopen(create_req, timeout=5)
    except Exception as e:
        print(f"{CLR_YELLOW}[WARN]{CLR_RESET} Project verification failed: {e}")

    # Generate user token
    token_name = f"auto-token-{int(time.time())}"
    token_data = urllib.parse.urlencode({"name": token_name, "type": "USER_TOKEN"}).encode()
    token_req = urllib.request.Request(f"{host_url}/api/user_tokens/generate", data=token_data, headers=headers)
    try:
        with urllib.request.urlopen(token_req, timeout=5) as resp:
            token_resp = json.loads(resp.read().decode())
            new_token = token_resp.get("token")
            print(f"{CLR_GREEN}[OK]{CLR_RESET} Generated analysis token: {token_name}")
            return new_token
    except Exception as e:
        print(f"{CLR_YELLOW}[WARN]{CLR_RESET} Could not generate token via admin credentials: {e}")
        return None


def fetch_metrics(host_url, project_key, token=None):
    metrics = ["bugs", "vulnerabilities", "code_smells", "duplicated_lines_density", "coverage", "ncloc"]
    url = f"{host_url}/api/measures/component?component={project_key}&metricKeys={','.join(metrics)}"
    req = urllib.request.Request(url)
    if token:
        creds = base64.b64encode(f"{token}:".encode()).decode()
        req.add_header("Authorization", f"Basic {creds}")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            measures = data.get("component", {}).get("measures", [])
            return {m["metric"]: m.get("value", "N/A") for m in measures}
    except Exception:
        return {}


def wait_for_analysis_report(host_url, project_key, token=None, timeout_seconds=30):
    """Wait for SonarQube Compute Engine task to finish."""
    url = f"{host_url}/api/ce/component?component={project_key}"
    req = urllib.request.Request(url)
    if token:
        creds = base64.b64encode(f"{token}:".encode()).decode()
        req.add_header("Authorization", f"Basic {creds}")

    # Give CE a moment to register the uploaded report task
    time.sleep(1.5)
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        try:
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                current = data.get("current", {})
                queue = data.get("queue", [])
                if not current and not queue:
                    return True
                status = current.get("status")
                if status == "SUCCESS":
                    return True
                elif status in ("FAILED", "CANCELED"):
                    print(f"{CLR_RED}[ERROR]{CLR_RESET} Compute engine task ended with status '{status}'")
                    return False
        except Exception:
            pass
        time.sleep(1)
    return True


def cmd_scan(args, host_url, project_key, token):
    is_up, status_str, _ = check_api_health(host_url)
    if not is_up:
        print(f"{CLR_RED}[ERROR]{CLR_RESET} SonarQube server is not accessible at {host_url} (status: {status_str}).")
        print(f"       Run '{CLR_CYAN}uv run scripts/sonar.py start{CLR_RESET}' to start the container.")
        return 1

    if not token or not validate_token(host_url, token):
        print(f"{CLR_CYAN}[INFO]{CLR_RESET} No valid token found in environment. Generating a fresh token...")
        token = ensure_project_and_token(host_url, project_key)
        if not token:
            print(f"{CLR_RED}[ERROR]{CLR_RESET} Authentication failed. Please provide --token or set SONAR_TOKEN.")
            return 1

    print(f"{CLR_BOLD}Starting SonarQube scan for '{project_key}'...{CLR_RESET}")
    if shutil.which("sonar-scanner"):
        cmd = [
            "sonar-scanner",
            f"-Dsonar.host.url={host_url}",
            f"-Dsonar.token={token}",
            f"-Dsonar.projectKey={project_key}",
        ]
        print(f"{CLR_CYAN}[EXEC]{CLR_RESET} sonar-scanner -Dsonar.host.url={host_url} -Dsonar.projectKey={project_key}")
    else:
        print(f"{CLR_YELLOW}[WARN]{CLR_RESET} 'sonar-scanner' CLI not found on PATH. Falling back to Docker scanner...")
        docker_host = host_url.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{os.getcwd()}:/usr/src",
            "-e", f"SONAR_HOST_URL={docker_host}",
            "-e", f"SONAR_TOKEN={token}",
            "sonarsource/sonar-scanner-cli",
            f"-Dsonar.projectKey={project_key}",
        ]
        print(f"{CLR_CYAN}[EXEC]{CLR_RESET} docker run ... sonarsource/sonar-scanner-cli")

    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        print(f"{CLR_RED}[ERROR]{CLR_RESET} Scanner execution failed.")
        return proc.returncode

    if args.wait:
        print(f"{CLR_CYAN}[INFO]{CLR_RESET} Waiting for report processing in SonarQube Compute Engine...")
        wait_for_analysis_report(host_url, project_key, token)

    # Fetch Quality Gate Status
    qg_url = f"{host_url}/api/qualitygates/project_status?projectKey={project_key}"
    qg_req = urllib.request.Request(qg_url)
    creds = base64.b64encode(f"{token}:".encode()).decode()
    qg_req.add_header("Authorization", f"Basic {creds}")
    qg_status = "UNKNOWN"
    try:
        with urllib.request.urlopen(qg_req, timeout=5) as resp:
            qg_data = json.loads(resp.read().decode())
            qg_status = qg_data.get("projectStatus", {}).get("status", "UNKNOWN")
    except Exception as e:
        print(f"{CLR_YELLOW}[WARN]{CLR_RESET} Could not retrieve quality gate: {e}")

    # Fetch metrics
    metrics = fetch_metrics(host_url, project_key, token)

    status_color = CLR_GREEN if qg_status == "OK" else CLR_RED
    print("\n" + "=" * 54)
    print(f" {CLR_BOLD}SonarQube Analysis Summary{CLR_RESET}")
    print("=" * 54)
    print(f" Project Key      : {project_key}")
    print(f" Quality Gate     : {status_color}{CLR_BOLD}{qg_status}{CLR_RESET}")
    print(f" Lines of Code    : {metrics.get('ncloc', 'N/A')}")
    print(f" Bugs             : {metrics.get('bugs', 'N/A')}")
    print(f" Vulnerabilities  : {metrics.get('vulnerabilities', 'N/A')}")
    print(f" Code Smells      : {metrics.get('code_smells', 'N/A')}")
    print(f" Duplication      : {metrics.get('duplicated_lines_density', 'N/A')}%")
    print(f" Dashboard URL    : {CLR_CYAN}{host_url}/dashboard?id={project_key}{CLR_RESET}")
    print("=" * 54 + "\n")

    if args.open:
        webbrowser.open(f"{host_url}/dashboard?id={project_key}")

    if args.strict and qg_status != "OK":
        print(f"{CLR_RED}[FAIL]{CLR_RESET} Quality Gate did not pass ({qg_status}). Strict mode enabled.")
        return 1

    return 0


def cmd_status(host_url, project_key, token):
    print(f"\n{CLR_BOLD}=== SonarQube Environment Status ==={CLR_RESET}\n")

    # 1. Docker containers
    containers = get_docker_containers()
    if containers:
        print(f"{CLR_BOLD}Docker Containers:{CLR_RESET}")
        for c in containers:
            tag = f"{CLR_GREEN}Running{CLR_RESET}" if c["running"] else f"{CLR_RED}Stopped{CLR_RESET}"
            print(f"  • {c['name']} ({c['image']}): {tag} - {c['status']}")
    else:
        print(f"{CLR_YELLOW}Docker Containers:{CLR_RESET} No SonarQube containers detected.")

    # 2. Server API status
    is_up, status_str, version = check_api_health(host_url)
    api_color = CLR_GREEN if is_up else CLR_RED
    print(f"\n{CLR_BOLD}Server API:{CLR_RESET}")
    print(f"  • Host URL : {host_url}")
    print(f"  • Status   : {api_color}{status_str}{CLR_RESET}")
    print(f"  • Version  : {version}")

    # 3. Project status & metrics if available
    if is_up:
        if not token or not validate_token(host_url, token):
            token = ensure_project_and_token(host_url, project_key)
        metrics = fetch_metrics(host_url, project_key, token)
        if metrics:
            print(f"\n{CLR_BOLD}Project '{project_key}' Metrics:{CLR_RESET}")
            print(f"  • Lines of Code   : {metrics.get('ncloc', 'N/A')}")
            print(f"  • Bugs            : {metrics.get('bugs', 'N/A')}")
            print(f"  • Vulnerabilities : {metrics.get('vulnerabilities', 'N/A')}")
            print(f"  • Code Smells     : {metrics.get('code_smells', 'N/A')}")
            print(f"  • Duplication     : {metrics.get('duplicated_lines_density', 'N/A')}%")
            print(f"  • Dashboard       : {CLR_CYAN}{host_url}/dashboard?id={project_key}{CLR_RESET}")

    print()
    return 0


def cmd_start(host_url):
    containers = get_docker_containers()
    sonar_containers = [c for c in containers if c["is_app"]]
    db_containers = [c for c in containers if not c["is_app"]]

    # Start DB first if exists
    for db in db_containers:
        if not db["running"]:
            print(f"{CLR_CYAN}[INFO]{CLR_RESET} Starting DB container '{db['name']}'...")
            subprocess.run(["docker", "start", db["name"]], check=True)

    if sonar_containers:
        app = sonar_containers[0]
        if not app["running"]:
            print(f"{CLR_CYAN}[INFO]{CLR_RESET} Starting SonarQube container '{app['name']}'...")
            subprocess.run(["docker", "start", app["name"]], check=True)
        else:
            print(f"{CLR_GREEN}[OK]{CLR_RESET} SonarQube container '{app['name']}' is already running.")
    else:
        print(f"{CLR_CYAN}[INFO]{CLR_RESET} No existing SonarQube container found. Creating 'sonarqube' container...")
        cmd = [
            "docker", "run", "-d",
            "--name", "sonarqube",
            "-p", "9000:9000",
            "sonarqube:community"
        ]
        subprocess.run(cmd, check=True)

    print(f"{CLR_CYAN}[INFO]{CLR_RESET} Waiting for SonarQube API to become ready at {host_url}...")
    for _ in range(60):
        is_up, _, _ = check_api_health(host_url)
        if is_up:
            print(f"{CLR_GREEN}[OK]{CLR_RESET} SonarQube is UP and ready!")
            return 0
        time.sleep(2)
        print(".", end="", flush=True)

    print(f"\n{CLR_YELLOW}[WARN]{CLR_RESET} SonarQube is still starting up. Check 'uv run scripts/sonar.py status'.")
    return 1


def cmd_stop():
    containers = get_docker_containers()
    if not containers:
        print(f"{CLR_YELLOW}[INFO]{CLR_RESET} No SonarQube containers found to stop.")
        return 0

    for c in containers:
        if c["running"]:
            print(f"{CLR_CYAN}[INFO]{CLR_RESET} Stopping container '{c['name']}'...")
            subprocess.run(["docker", "stop", c["name"]], check=True)
            print(f"{CLR_GREEN}[OK]{CLR_RESET} Stopped '{c['name']}'.")
        else:
            print(f"{CLR_YELLOW}[INFO]{CLR_RESET} Container '{c['name']}' is already stopped.")
    return 0


def cmd_logs(lines):
    containers = [c for c in get_docker_containers() if c["is_app"]]
    if not containers:
        print(f"{CLR_RED}[ERROR]{CLR_RESET} No SonarQube container found.")
        return 1
    cname = containers[0]["name"]
    subprocess.run(["docker", "logs", "--tail", str(lines), cname])
    return 0


def cmd_open(host_url, project_key):
    url = f"{host_url}/dashboard?id={project_key}"
    print(f"Opening {url} in browser...")
    webbrowser.open(url)
    return 0


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Manage and run SonarQube scans using uv",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="scan",
        choices=["scan", "status", "start", "stop", "logs", "open"],
        help="Action to execute (default: scan)",
    )
    parser.add_argument("--host", default=None, help=f"SonarQube host URL (default: {DEFAULT_HOST})")
    parser.add_argument("--project", default=None, help=f"Sonar project key (default: {DEFAULT_PROJECT})")
    parser.add_argument("--token", default=None, help="SonarQube token")
    parser.add_argument("--wait", action="store_true", default=True, help="Wait for compute engine analysis (default: true)")
    parser.add_argument("--no-wait", dest="wait", action="store_false", help="Do not wait for compute engine analysis")
    parser.add_argument("--strict", action="store_true", help="Exit with code 1 if Quality Gate fails")
    parser.add_argument("--open", action="store_true", help="Automatically open dashboard after scan")
    parser.add_argument("--lines", type=int, default=100, help="Number of log lines to show (for 'logs' command)")

    args = parser.parse_args()

    host_url = args.host or os.environ.get("SONAR_HOST_URL", DEFAULT_HOST)
    project_key = args.project or os.environ.get("SONAR_PROJECT_KEY", DEFAULT_PROJECT)
    token = args.token or os.environ.get("SONAR_TOKEN")

    if args.command == "scan":
        sys.exit(cmd_scan(args, host_url, project_key, token))
    elif args.command == "status":
        sys.exit(cmd_status(host_url, project_key, token))
    elif args.command == "start":
        sys.exit(cmd_start(host_url))
    elif args.command == "stop":
        sys.exit(cmd_stop())
    elif args.command == "logs":
        sys.exit(cmd_logs(args.lines))
    elif args.command == "open":
        sys.exit(cmd_open(host_url, project_key))


if __name__ == "__main__":
    main()
