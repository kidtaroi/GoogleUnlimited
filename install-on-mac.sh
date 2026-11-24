#!/bin/bash
# One-time installer for the user-friendly setup helper on macOS.
set -euo pipefail

cd "$(dirname "$0")"

echo "Installing Python dependencies..."
python3 -m pip install --user playwright
python3 -m playwright install chromium

echo "Installing GoogleUnlimited dependencies..."
./google-unlimited.sh setup

chmod +x WifeSetup.command wife_setup.py google-unlimited.sh
echo "Done. Double-click WifeSetup.command to sign in and start backups."
