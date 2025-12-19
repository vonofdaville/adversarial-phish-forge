#!/usr/bin/env python3
"""
CHIMERA CLI Setup Script

Installs the CHIMERA CLI tool system-wide for easy access.
"""

import sys
import subprocess
from pathlib import Path

def install_cli():
    """Install the CHIMERA CLI tool."""
    project_root = Path(__file__).parent.parent
    cli_script = project_root / "chimera" / "cli" / "main.py"

    if not cli_script.exists():
        print("Error: CLI script not found")
        sys.exit(1)

    # Create symlink or copy to /usr/local/bin
    cli_command = "/usr/local/bin/chimera-cli"

    try:
        # Create symlink
        subprocess.run([
            "sudo", "ln", "-sf", str(cli_script), cli_command
        ], check=True)

        # Make executable
        subprocess.run([
            "sudo", "chmod", "+x", cli_command
        ], check=True)

        print("✓ CHIMERA CLI installed successfully")
        print(f"  Command: {cli_command}")
        print("  Usage: chimera-cli --help"

    except subprocess.CalledProcessError as e:
        print(f"Error installing CLI: {e}")
        print("You may need to run this script with sudo")
        sys.exit(1)

if __name__ == "__main__":
    install_cli()


