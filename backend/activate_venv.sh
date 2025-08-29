#!/bin/bash
# Script to activate the Python virtual environment
source .venv/bin/activate
echo "Virtual environment activated!"
echo "Python executable: $(which python)"
echo "Python version: $(python --version)"
echo ""
echo "To deactivate, type: deactivate"
