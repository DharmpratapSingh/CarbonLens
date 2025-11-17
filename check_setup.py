#!/usr/bin/env python3
"""
ClimateGPT Setup Validation Script
===================================

Quick diagnostic tool to check if your ClimateGPT setup is correct.
Run this before starting the application to catch configuration issues early.

Usage:
    python check_setup.py
"""

import os
import sys
import requests
from pathlib import Path
from typing import Dict, List, Tuple

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text: str):
    """Print a section header."""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")

def print_check(name: str, status: bool, details: str = ""):
    """Print a check result."""
    icon = f"{GREEN}✅{RESET}" if status else f"{RED}❌{RESET}"
    print(f"{icon} {name}")
    if details:
        print(f"   {details}")

def print_warning(text: str):
    """Print a warning message."""
    print(f"{YELLOW}⚠️  {text}{RESET}")

def print_error(text: str):
    """Print an error message."""
    print(f"{RED}❌ {text}{RESET}")

def print_success(text: str):
    """Print a success message."""
    print(f"{GREEN}✅ {text}{RESET}")

def check_file_exists(filepath: str) -> Tuple[bool, str]:
    """Check if a file exists."""
    exists = Path(filepath).exists()
    if exists:
        return True, f"Found at: {filepath}"
    return False, f"Not found: {filepath}"

def check_env_file() -> Tuple[bool, Dict[str, str]]:
    """Check if .env file exists and load it."""
    env_file = Path(".env")
    if not env_file.exists():
        return False, {}

    env_vars = {}
    try:
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
        return True, env_vars
    except Exception as e:
        return False, {}

def check_env_variable(name: str, required: bool = True, format_check=None) -> Tuple[bool, str]:
    """Check if an environment variable is set correctly."""
    value = os.environ.get(name)

    if not value:
        if required:
            return False, f"Not set (required)"
        return True, f"Not set (using default)"

    if format_check:
        valid, msg = format_check(value)
        if not valid:
            return False, msg

    # Don't print sensitive values
    if "KEY" in name.upper() or "PASS" in name.upper():
        return True, "Set (value hidden)"
    return True, f"Set to: {value}"

def check_api_key_format(value: str) -> Tuple[bool, str]:
    """Check if API key is in correct format."""
    if value == "your_username:your_password":
        return False, "Still has template value - please set your actual credentials"
    if ':' not in value:
        return False, "Must be in format 'username:password'"
    return True, "Format looks correct"

def check_python_packages() -> List[Tuple[str, bool]]:
    """Check if required Python packages are installed."""
    packages = [
        'streamlit',
        'requests',
        'fastapi',
        'pandas',
        'altair',
        'dotenv',
        'uvicorn'
    ]

    results = []
    for package in packages:
        try:
            __import__(package)
            results.append((package, True))
        except ImportError:
            results.append((package, False))

    return results

def check_service_running(name: str, url: str) -> Tuple[bool, str]:
    """Check if a service is running."""
    try:
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            return True, f"Running at {url}"
        return False, f"HTTP {response.status_code} at {url}"
    except requests.exceptions.ConnectionError:
        return False, f"Not reachable at {url}"
    except requests.exceptions.Timeout:
        return False, f"Timeout at {url}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    """Run all checks."""
    print_header("🌍 ClimateGPT Setup Validation")

    all_passed = True
    warnings = []
    errors = []

    # Check 1: Required files
    print_header("📁 File System Checks")

    files_to_check = [
        ("enhanced_climategpt_with_personas.py", True),
        ("mcp_http_bridge.py", True),
        ("mcp_server_stdio.py", True),
        ("climategpt_persona_engine.py", True),
        (".env", True),
    ]

    for filename, required in files_to_check:
        exists, details = check_file_exists(filename)
        print_check(filename, exists, details)
        if not exists and required:
            all_passed = False
            errors.append(f"Missing required file: {filename}")

    # Check 2: Environment file
    print_header("⚙️  Environment Configuration")

    env_exists, env_vars = check_env_file()
    print_check(".env file", env_exists)

    if env_exists:
        # Load env vars for subsequent checks
        for key, value in env_vars.items():
            os.environ.setdefault(key, value)
    else:
        all_passed = False
        errors.append(".env file not found - run setup_and_start.sh to create it")

    # Check 3: Required environment variables
    print_header("🔑 Environment Variables")

    api_key_ok, api_key_msg = check_env_variable(
        "OPENAI_API_KEY",
        required=True,
        format_check=check_api_key_format
    )
    print_check("OPENAI_API_KEY", api_key_ok, api_key_msg)
    if not api_key_ok:
        all_passed = False
        errors.append("OPENAI_API_KEY is not set correctly")

    base_url_ok, base_url_msg = check_env_variable("OPENAI_BASE_URL", required=False)
    print_check("OPENAI_BASE_URL", base_url_ok, base_url_msg)

    mcp_url_ok, mcp_url_msg = check_env_variable("MCP_URL", required=False)
    print_check("MCP_URL", mcp_url_ok, mcp_url_msg)

    # Check 4: Python packages
    print_header("📦 Python Dependencies")

    package_results = check_python_packages()
    for package, installed in package_results:
        print_check(package, installed)
        if not installed:
            all_passed = False
            errors.append(f"Missing Python package: {package}")

    # Check 5: Running services
    print_header("🚀 Service Status")

    mcp_running, mcp_msg = check_service_running(
        "MCP Bridge",
        os.environ.get("MCP_URL", "http://127.0.0.1:8010") + "/health"
    )
    print_check("MCP Bridge Server", mcp_running, mcp_msg)
    if not mcp_running:
        warnings.append("MCP Bridge not running - start it with: python mcp_http_bridge.py")

    streamlit_running, streamlit_msg = check_service_running(
        "Streamlit",
        "http://localhost:8501"
    )
    print_check("Streamlit UI", streamlit_running, streamlit_msg)
    if not streamlit_running:
        warnings.append("Streamlit not running - start it with: streamlit run enhanced_climategpt_with_personas.py")

    # Summary
    print_header("📊 Summary")

    if all_passed and not warnings:
        print_success("All checks passed! ✨")
        if mcp_running and streamlit_running:
            print("\n🌍 ClimateGPT is ready!")
            print(f"   Open http://localhost:8501 in your browser")
        else:
            print("\n💡 Next step: Start the services")
            print("   Run: ./setup_and_start.sh")
        return 0

    if errors:
        print_error("Critical issues found:")
        for error in errors:
            print(f"   • {error}")
        print("\n📝 See SETUP_INSTRUCTIONS.md for help")

    if warnings:
        print_warning("Warnings:")
        for warning in warnings:
            print(f"   • {warning}")

    if not errors and warnings:
        print("\n💡 Configuration looks good, but services need to be started")
        print("   Run: ./setup_and_start.sh")
        return 0

    return 1

if __name__ == "__main__":
    sys.exit(main())
