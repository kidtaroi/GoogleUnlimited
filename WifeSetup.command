#!/bin/bash
# Double-click this file on macOS to open the Google Photos backup setup window.
cd "$(dirname "$0")" || exit 1
exec python3 wife_setup.py
