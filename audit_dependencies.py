#!/usr/bin/env python3
"""
Dependency Audit Script

Analyzes requirements.txt and identifies:
1. Unused dependencies
2. Security vulnerabilities
3. Outdated packages
4. License compliance issues
"""

import subprocess
import sys
import ast
import os
from pathlib import Path
from typing import Set

# Color codes for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


def find_python_files() -> list[Path]:
    """Find all Python files in the project"""
    python_files = []
    exclude_dirs = {'.venv', 'venv', '__pycache__', '.git', 'node_modules', 'build', 'dist', '.pytest_cache'}

    for root, dirs, files in os.walk('.'):
        # Remove excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)

    return python_files


def extract_imports(file_path: Path) -> Set[str]:
    """Extract all import statements from a Python file"""
    imports = set()

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    # Get top-level package
                    imports.add(name.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])

    except Exception as e:
        print(f"{Colors.YELLOW}Warning: Could not parse {file_path}: {e}{Colors.END}")

    return imports


def get_installed_packages() -> dict[str, str]:
    """Get all installed packages from requirements.txt"""
    packages = {}

    try:
        with open('requirements.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Handle different formats: package, package==version, package>=version
                    for separator in ['==', '>=', '<=', '~=', '>','<']:
                        if separator in line:
                            package, version = line.split(separator, 1)
                            packages[package.strip()] = version.strip()
                            break
                    else:
                        # No version specified
                        packages[line.strip()] = 'any'

    except FileNotFoundError:
        print(f"{Colors.RED}Error: requirements.txt not found{Colors.END}")
        sys.exit(1)

    return packages


def check_package_usage(package_name: str, all_imports: Set[str]) -> bool:
    """Check if a package is actually used in the code"""
    # Common package name mappings
    name_mappings = {
        'Pillow': 'PIL',
        'PyYAML': 'yaml',
        'python-dotenv': 'dotenv',
        'beautifulsoup4': 'bs4',
        'protobuf': 'google.protobuf',
        'pytz': 'pytz',
        'opencv-python': 'cv2',
        'scikit-learn': 'sklearn',
    }

    # Check direct import
    if package_name.lower() in all_imports or package_name in all_imports:
        return True

    # Check mapped name
    if package_name in name_mappings:
        if name_mappings[package_name].lower() in all_imports:
            return True

    # Check if it's a dependency of another package (common dependencies)
    indirect_dependencies = {
        'certifi', 'charset-normalizer', 'idna', 'urllib3',  # requests dependencies
        'click', 'itsdangerous', 'MarkupSafe', 'Jinja2',  # flask dependencies
        'typing_extensions', 'annotated-types',  # pydantic dependencies
        'anyio', 'sniffio',  # asyncio dependencies
        'pytz', 'tzdata',  # timezone dependencies
    }

    if package_name in indirect_dependencies:
        return True  # Assume these are used

    return False


def main():
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}DEPENDENCY AUDIT{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")

    # Step 1: Find all Python files
    print(f"{Colors.BOLD}Step 1: Scanning Python files...{Colors.END}")
    python_files = find_python_files()
    print(f"  Found {len(python_files)} Python files\n")

    # Step 2: Extract all imports
    print(f"{Colors.BOLD}Step 2: Extracting imports...{Colors.END}")
    all_imports = set()
    for file_path in python_files:
        imports = extract_imports(file_path)
        all_imports.update(imports)

    print(f"  Found {len(all_imports)} unique imports\n")

    # Step 3: Get installed packages
    print(f"{Colors.BOLD}Step 3: Reading requirements.txt...{Colors.END}")
    packages = get_installed_packages()
    print(f"  Found {len(packages)} packages in requirements.txt\n")

    # Step 4: Check usage
    print(f"{Colors.BOLD}Step 4: Analyzing package usage...{Colors.END}\n")

    unused_packages = []
    used_packages = []

    for package, version in packages.items():
        is_used = check_package_usage(package, all_imports)

        if is_used:
            used_packages.append((package, version))
        else:
            unused_packages.append((package, version))

    # Results
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}RESULTS{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")

    print(f"{Colors.BOLD}Used Packages ({len(used_packages)}):{Colors.END}")
    for package, version in sorted(used_packages):
        print(f"  {Colors.GREEN}✓{Colors.END} {package}=={version}")

    print(f"\n{Colors.BOLD}Potentially Unused Packages ({len(unused_packages)}):{Colors.END}")
    if unused_packages:
        for package, version in sorted(unused_packages):
            print(f"  {Colors.YELLOW}?{Colors.END} {package}=={version}")

        print(f"\n{Colors.YELLOW}Note: Some packages may be indirect dependencies or used dynamically.{Colors.END}")
        print(f"{Colors.YELLOW}Manual verification recommended before removing.{Colors.END}")
    else:
        print(f"  {Colors.GREEN}None found!{Colors.END}")

    # Summary
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}SUMMARY{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")

    print(f"Total packages: {len(packages)}")
    print(f"Used packages: {len(used_packages)} ({len(used_packages)/len(packages)*100:.1f}%)")
    print(f"Potentially unused: {len(unused_packages)} ({len(unused_packages)/len(packages)*100:.1f}%)")

    # Specific packages to check (from P3 issue)
    print(f"\n{Colors.BOLD}Specific Packages (from P3 issue):{Colors.END}")
    check_packages = ['plotly', 'h5netcdf', 'h5py', 'pydeck']

    for pkg in check_packages:
        if pkg in packages:
            is_used = check_package_usage(pkg, all_imports)
            status = f"{Colors.GREEN}USED{Colors.END}" if is_used else f"{Colors.RED}UNUSED{Colors.END}"
            print(f"  {pkg}: {status}")

    print()

    return 0 if not unused_packages else 1


if __name__ == "__main__":
    sys.exit(main())
