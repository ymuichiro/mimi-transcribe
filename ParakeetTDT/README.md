# ParakeetTDT - macOS Native App

SwiftUI-based macOS application for audio recording and transcription using the Parakeet model via PythonKit.

## Overview

This is a native macOS application that provides a SwiftUI interface while leveraging the existing Python-based audio recording and transcription logic through PythonKit.

## Requirements

- macOS 13.0 or later (Ventura+)
- Xcode 15.0 or later
- Python 3.13 or compatible version
- uv package manager

## Project Structure

```
ParakeetTDT/
├── Package.swift              # Swift Package Manager configuration
├── Sources/
│   └── ParakeetTDT/
│       ├── ParakeetTDTApp.swift          # Main app entry point
│       ├── Views/
│       │   └── ContentView.swift         # Main UI view
│       └── Services/
│           ├── TranscriptionService.swift # Service layer for UI
│           └── PythonBridge.swift        # Bridge to Python code
├── Tests/
│   └── ParakeetTDTTests/
└── Info.plist                # App configuration including microphone permissions
```

## Setup

### 1. Install Dependencies

First, ensure you have the required tools:

```bash
# Install uv if not already installed
pip3 install uv

# Run the development setup script
./scripts/dev-setup.sh
```

This script will:
- Check for required tools (Swift, Python, uv)
- Create and configure a Python virtual environment
- Install Python dependencies
- Detect your Python installation and provide environment variables

### 2. Configure Environment Variables

For development, you need to set these environment variables to point to your Python installation:

```bash
export PYTHON_LIBRARY="/path/to/Python.framework/Versions/3.13"
export PYTHON_MODULE_PATH="/path/to/parakeet-tdt-ui"
```

The `dev-setup.sh` script will suggest the correct paths for your system.

### 3. Build and Run

Using Swift Package Manager:

```bash
cd ParakeetTDT
swift build
swift run ParakeetTDT
```

Or open the Package.swift in Xcode and configure the environment variables in your scheme:
1. Product → Scheme → Edit Scheme
2. Run → Arguments → Environment Variables
3. Add `PYTHON_LIBRARY` and `PYTHON_MODULE_PATH`

## Architecture

### Swift Layer

- **ParakeetTDTApp.swift**: Main app entry point with SwiftUI lifecycle
- **ContentView.swift**: Main UI with recording button, status display, and transcription results
- **TranscriptionService.swift**: Observable service managing recording and transcription state
- **PythonBridge.swift**: Low-level bridge to Python modules using PythonKit

### Python Layer

The Swift app reuses the existing Python modules:
- `app.recorder.AudioRecorder`: Handles microphone recording
- `app.transcriber.transcribe_audio`: Performs audio transcription using Parakeet MLX

### Communication Flow

```
SwiftUI View
    ↓
TranscriptionService (ObservableObject)
    ↓
PythonBridge (PythonKit)
    ↓
Python Modules (recorder, transcriber)
    ↓
Parakeet MLX Model
```

## Permissions

The app requires microphone access. The `NSMicrophoneUsageDescription` key in Info.plist explains to users why microphone access is needed.

## Development Notes

### Environment Variables

- `PYTHON_LIBRARY`: Path to Python.framework (e.g., `/Library/Frameworks/Python.framework/Versions/3.13`)
- `PYTHON_MODULE_PATH`: Path to the repository root containing the `app` module

### Python Module Resolution

The PythonBridge attempts to locate Python modules in this order:
1. Environment variable `PYTHON_MODULE_PATH`
2. App bundle Resources/python directory (for production builds)
3. Parent directory of current working directory (fallback for development)

### Error Handling

Python exceptions are caught and converted to Swift errors, which are then displayed to the user via SwiftUI alerts.

## Building for Distribution

(To be completed in Phase 5)

This section will document:
- How to embed Python runtime in the app bundle
- Installing dependencies in Resources/python
- Code signing and notarization process
- Creating a distributable .app bundle

## Testing

Run tests with:

```bash
cd ParakeetTDT
swift test
```

## Troubleshooting

### "Could not find Python library" error

Make sure you've set the `PYTHON_LIBRARY` environment variable correctly. Use the `dev-setup.sh` script to detect the correct path.

### "Failed to import Python modules" error

Ensure `PYTHON_MODULE_PATH` points to the repository root directory containing the `app` module.

### Microphone permission denied

Check macOS System Settings → Privacy & Security → Microphone to ensure the app has permission.

## Future Enhancements

- [ ] Native Swift recording using AVFoundation (eliminate Python recorder dependency)
- [ ] Progress indicators for model loading and transcription
- [ ] Configurable transcription settings (model selection, FP32 toggle)
- [ ] Export transcription results
- [ ] Batch processing of audio files

## License

(Same as parent project)
