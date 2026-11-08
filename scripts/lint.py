# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pyright>=1.1.414",
#     "ruff>=0.17.0",
# ]
# ///
"""
scripts/lint.py
Unified linting, type-checking, and autofixing tool for inky-frame using uv.

Usage:
    uv run scripts/lint.py [COMMAND] [OPTIONS]

Commands:
    check     Run all checks (ruff lint, ruff format check, pyright) [default]
    fix       Autofix lint issues and reformat code
    format    Format all files using ruff
    pyright   Run pyright static type analysis
    ruff      Run ruff linter check
    sonar     Run SonarQube operations (scan, status, issues, start, stop, open)
"""

import argparse
import os
import shutil
import subprocess
import sys

# ANSI Colors
CLR_RESET = "\033[0m"
CLR_BOLD = "\033[1m"
CLR_GREEN = "\033[32m"
CLR_YELLOW = "\033[33m"
CLR_RED = "\033[31m"
CLR_CYAN = "\033[36m"
CLR_DIM = "\033[2m"


def log_info(msg: str) -> None:
    print(f"{CLR_CYAN}[INFO]{CLR_RESET} {msg}")


def log_success(msg: str) -> None:
    print(f"{CLR_GREEN}[SUCCESS]{CLR_RESET} {msg}")


def log_warning(msg: str) -> None:
    print(f"{CLR_YELLOW}[WARNING]{CLR_RESET} {msg}")


def log_error(msg: str) -> None:
    print(f"{CLR_RED}[ERROR]{CLR_RESET} {msg}")


def get_tool(tool_name: str) -> list[str]:
    """Resolve executable path for a tool inside current venv or PATH."""
    venv_bin = os.path.join(os.path.dirname(sys.executable), tool_name)
    if os.path.exists(venv_bin):
        return [venv_bin]
    found = shutil.which(tool_name)
    if found:
        return [found]
    return ["uv", "run", tool_name]


def run_command(cmd: list[str], description: str) -> int:
    log_info(f"Running {description}: {CLR_DIM}{' '.join(cmd)}{CLR_RESET}")
    result = subprocess.run(cmd)
    if result.returncode == 0:
        log_success(f"{description} passed.")
    else:
        log_error(f"{description} failed with exit code {result.returncode}.")
    return result.returncode


def cmd_check(args: argparse.Namespace) -> int:
    """Run lint, format verification, and type checking."""
    failures = 0
    ruff_bin = get_tool("ruff")
    pyright_bin = get_tool("pyright")

    if not args.skip_ruff:
        # 1. Ruff lint check
        ret = run_command([*ruff_bin, "check", "."], "Ruff Linter")
        if ret != 0:
            failures += 1

        # 2. Ruff format check
        ret = run_command([*ruff_bin, "format", "--check", "."], "Ruff Formatter Check")
        if ret != 0:
            failures += 1

    if not args.skip_pyright:
        # 3. Pyright type check
        ret = run_command([*pyright_bin], "Pyright Type Check")
        if ret != 0:
            failures += 1

    if getattr(args, "with_sonar", False):
        # 4. SonarQube quality gate check
        sonar_script = os.path.join(os.path.dirname(__file__), "sonar.py")
        ret = run_command(["uv", "run", sonar_script, "scan", "--strict"], "SonarQube Quality Gate")
        if ret != 0:
            failures += 1

    print()
    if failures == 0:
        log_success("All checks passed successfully! ✨")
        return 0
    else:
        log_error(f"{failures} check(s) failed. Run 'uv run scripts/lint.py fix' to autofix format/lint issues.")
        return 1


def cmd_fix(args: argparse.Namespace) -> int:
    """Autofix ruff lint errors and format files."""
    log_info("Applying autofixes and formatting...")
    ruff_bin = get_tool("ruff")
    pyright_bin = get_tool("pyright")

    # 1. Ruff check --fix
    fix_cmd = [*ruff_bin, "check", "--fix"]
    if args.unsafe:
        fix_cmd.append("--unsafe-fixes")
    fix_cmd.append(".")
    run_command(fix_cmd, "Ruff Autofix")

    # 2. Ruff format
    run_command([*ruff_bin, "format", "."], "Ruff Formatter")

    # 3. Run Pyright to check remaining type issues
    if not args.no_typecheck:
        run_command([*pyright_bin], "Pyright Verification")

    log_success("Autofixes and formatting complete.")
    return 0


def cmd_format(args: argparse.Namespace) -> int:
    """Format all code files."""
    ruff_bin = get_tool("ruff")
    cmd = [*ruff_bin, "format"]
    if args.check:
        cmd.append("--check")
    cmd.append(".")
    return run_command(cmd, "Ruff Formatter")


def cmd_pyright(args: argparse.Namespace) -> int:
    """Run Pyright type checking."""
    pyright_bin = get_tool("pyright")
    cmd = [*pyright_bin]
    if args.files:
        cmd.extend(args.files)
    return run_command(cmd, "Pyright")


def cmd_ruff(args: argparse.Namespace) -> int:
    """Run Ruff linting."""
    ruff_bin = get_tool("ruff")
    cmd = [*ruff_bin, "check"]
    if args.fix:
        cmd.append("--fix")
    if args.unsafe:
        cmd.append("--unsafe-fixes")
    cmd.append(".")
    return run_command(cmd, "Ruff")


def cmd_sonar(args: argparse.Namespace) -> int:
    """Run SonarQube operations via scripts/sonar.py."""
    sonar_script = os.path.join(os.path.dirname(__file__), "sonar.py")
    subcmd = args.action or "scan"
    cmd = ["uv", "run", sonar_script, subcmd]
    if getattr(args, "strict", False):
        cmd.append("--strict")
    if getattr(args, "open", False):
        cmd.append("--open")
    if getattr(args, "lines", None):
        cmd.extend(["--lines", str(args.lines)])
    if getattr(args, "severity", None):
        cmd.extend(["--severity", args.severity])
    if getattr(args, "type", None):
        cmd.extend(["--type", args.type])
    return run_command(cmd, f"SonarQube ({subcmd})")


def main() -> int:
    parser = argparse.ArgumentParser(description="Unified lint, type check, and format runner for inky-frame using uv.")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # check command
    check_parser = subparsers.add_parser("check", help="Run all checks (ruff check, ruff format --check, pyright)")
    check_parser.add_argument("--skip-ruff", action="store_true", help="Skip ruff lint and format checks")
    check_parser.add_argument("--skip-pyright", action="store_true", help="Skip pyright type check")
    check_parser.add_argument("--with-sonar", action="store_true", help="Include SonarQube scan and quality gate check")

    # fix command
    fix_parser = subparsers.add_parser("fix", help="Autofix ruff issues and format code")
    fix_parser.add_argument("--unsafe", action="store_true", default=True, help="Include unsafe fixes (default: true)")
    fix_parser.add_argument("--no-unsafe", dest="unsafe", action="store_false", help="Do not include unsafe fixes")
    fix_parser.add_argument("--no-typecheck", action="store_true", help="Skip running pyright after fixing")

    # format command
    format_parser = subparsers.add_parser("format", help="Format code with ruff")
    format_parser.add_argument(
        "--check", action="store_true", help="Only check if files are formatted, do not reformat"
    )

    # pyright command
    pyright_parser = subparsers.add_parser("pyright", help="Run pyright type checker")
    pyright_parser.add_argument("files", nargs="*", help="Optional specific files to check")

    # ruff command
    ruff_parser = subparsers.add_parser("ruff", help="Run ruff linter directly")
    ruff_parser.add_argument("--fix", action="store_true", help="Autofix fixable errors")
    ruff_parser.add_argument("--unsafe", action="store_true", help="Include unsafe fixes")

    # sonar command
    sonar_parser = subparsers.add_parser(
        "sonar", help="Run SonarQube operations (scan, status, issues, open, start, stop, logs)"
    )
    sonar_parser.add_argument(
        "action",
        nargs="?",
        default="scan",
        choices=["scan", "status", "issues", "start", "stop", "logs", "open"],
        help="SonarQube action to execute (default: scan)",
    )
    sonar_parser.add_argument("--strict", action="store_true", help="Fail if Quality Gate does not pass (scan only)")
    sonar_parser.add_argument("--open", action="store_true", help="Open browser dashboard after scan")
    sonar_parser.add_argument("--lines", type=int, default=100, help="Log lines to display (logs only)")
    sonar_parser.add_argument(
        "--severity",
        "-s",
        default=None,
        choices=["BLOCKER", "CRITICAL", "MAJOR", "MINOR", "INFO"],
        help="Filter issues by severity",
    )
    sonar_parser.add_argument(
        "--type",
        "-t",
        default=None,
        choices=["BUG", "VULNERABILITY", "CODE_SMELL", "SECURITY_HOTSPOT"],
        help="Filter issues by type",
    )

    args = parser.parse_args()

    if args.command is None or args.command == "check":
        if args.command is None:
            args.skip_ruff = False
            args.skip_pyright = False
            args.with_sonar = False
        return cmd_check(args)
    elif args.command == "fix":
        return cmd_fix(args)
    elif args.command == "format":
        return cmd_format(args)
    elif args.command == "pyright":
        return cmd_pyright(args)
    elif args.command == "ruff":
        return cmd_ruff(args)
    elif args.command == "sonar":
        return cmd_sonar(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
