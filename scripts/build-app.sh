#!/bin/bash
# Build script for creating a distributable ParakeetTDT.app bundle

set -e

echo "=== ParakeetTDT Build Script ==="
echo ""

# Configuration
APP_NAME="ParakeetTDT"
BUNDLE_ID="com.parakeet.tdt"
BUILD_DIR="build"
PYTHON_VERSION="3.13"

# Check prerequisites
if ! command -v swift &> /dev/null; then
    echo "❌ Swift not found. Please install Xcode."
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found."
    exit 1
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Build Swift application
echo "Building Swift application..."
cd ParakeetTDT
swift build -c release
cd ..

# Create app bundle structure
echo "Creating app bundle..."
APP_BUNDLE="$BUILD_DIR/$APP_NAME.app"
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"
mkdir -p "$APP_BUNDLE/Contents/Resources/python"

# Copy executable
cp "ParakeetTDT/.build/release/$APP_NAME" "$APP_BUNDLE/Contents/MacOS/"

# Copy Info.plist
cp "ParakeetTDT/Info.plist" "$APP_BUNDLE/Contents/"

# Update bundle identifier in Info.plist
/usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier $BUNDLE_ID" "$APP_BUNDLE/Contents/Info.plist"

# Embed Python runtime and dependencies
echo "Embedding Python runtime..."

# Create a minimal Python environment
python3 -m venv "$APP_BUNDLE/Contents/Resources/python/venv"
source "$APP_BUNDLE/Contents/Resources/python/venv/bin/activate"

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -e .

# Copy app modules
echo "Copying Python app modules..."
cp -r app "$APP_BUNDLE/Contents/Resources/python/"

# Deactivate venv
deactivate

echo ""
echo "=== Build Complete ==="
echo ""
echo "App bundle created at: $APP_BUNDLE"
echo ""
echo "⚠️  Note: This is a basic build. For distribution, you need to:"
echo "   1. Sign the application with your Developer ID"
echo "   2. Notarize the application with Apple"
echo "   3. Create a DMG or PKG installer"
echo ""
echo "To test the app bundle:"
echo "  open $APP_BUNDLE"
echo ""
