#!/bin/bash
# Development environment setup script for ParakeetTDT SwiftUI app

set -e

echo "=== ParakeetTDT Development Setup ==="
echo ""

# Check for required tools
echo "Checking for required tools..."

if ! command -v swift &> /dev/null; then
    echo "❌ Swift is not installed. Please install Xcode or Swift toolchain."
    exit 1
fi
echo "✓ Swift found: $(swift --version | head -n 1)"

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed."
    exit 1
fi
echo "✓ Python found: $(python3 --version)"

if ! command -v uv &> /dev/null; then
    echo "⚠️  uv is not installed. Installing via pip..."
    pip3 install uv
fi
echo "✓ uv found"

# Setup Python environment
echo ""
echo "Setting up Python environment..."
cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment with uv..."
    uv venv
fi

echo "Installing Python dependencies..."
uv pip install -e .

# Find Python installation
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo ""
echo "Python version: $PYTHON_VERSION"

# Determine Python framework path
if [ -d "/Library/Frameworks/Python.framework/Versions/$PYTHON_VERSION" ]; then
    PYTHON_LIBRARY="/Library/Frameworks/Python.framework/Versions/$PYTHON_VERSION"
elif [ -d "/usr/local/Frameworks/Python.framework/Versions/$PYTHON_VERSION" ]; then
    PYTHON_LIBRARY="/usr/local/Frameworks/Python.framework/Versions/$PYTHON_VERSION"
elif [ -d "/opt/homebrew/opt/python@$PYTHON_VERSION/Frameworks/Python.framework/Versions/$PYTHON_VERSION" ]; then
    PYTHON_LIBRARY="/opt/homebrew/opt/python@$PYTHON_VERSION/Frameworks/Python.framework/Versions/$PYTHON_VERSION"
else
    echo "⚠️  Could not automatically locate Python.framework"
    echo "   Please set PYTHON_LIBRARY environment variable manually"
    PYTHON_LIBRARY=""
fi

# Get absolute path to Python modules
PYTHON_MODULE_PATH="$(pwd)"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To run the app in Xcode, set these environment variables in your scheme:"
echo ""
echo "PYTHON_LIBRARY=$PYTHON_LIBRARY"
echo "PYTHON_MODULE_PATH=$PYTHON_MODULE_PATH"
echo ""
echo "Or export them in your shell before running:"
echo ""
echo "export PYTHON_LIBRARY=\"$PYTHON_LIBRARY\""
echo "export PYTHON_MODULE_PATH=\"$PYTHON_MODULE_PATH\""
echo ""
echo "Then you can build and run with:"
echo "  cd ParakeetTDT"
echo "  swift build"
echo "  swift run ParakeetTDT"
echo ""
