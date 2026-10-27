#!/usr/bin/env bash
# Set up (first time) and start the Case Management System on macOS/Linux.
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
fi
.venv/bin/python run.py
