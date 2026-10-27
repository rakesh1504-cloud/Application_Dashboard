#!/usr/bin/env bash
# Set up (first time) and start the Case Management System on macOS/Linux.
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
# Installs anything new in requirements.txt; quick when nothing changed.
.venv/bin/pip install -q -r requirements.txt
.venv/bin/python run.py
