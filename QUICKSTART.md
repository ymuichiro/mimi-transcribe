# Quick Start Guide - ParakeetTDT macOS App

## Prerequisites

- macOS 13.0+ (Ventura or later)
- Xcode 15.0+
- Python 3.13+
- uv package manager

## Setup (5 minutes)

### 1. Clone and Setup

```bash
git clone https://github.com/ymuichiro/parakeet-tdt-ui.git
cd parakeet-tdt-ui
./scripts/dev-setup.sh
```

The script will output environment variables like:

```bash
export PYTHON_LIBRARY="/Library/Frameworks/Python.framework/Versions/3.13"
export PYTHON_MODULE_PATH="/path/to/parakeet-tdt-ui"
```

### 2. Set Environment Variables

```bash
# Copy the exports from dev-setup.sh output
export PYTHON_LIBRARY="..."
export PYTHON_MODULE_PATH="..."
```

### 3. Run the App

**Option A: Command Line**

```bash
cd ParakeetTDT
swift run ParakeetTDT
```

**Option B: Xcode**

1. Open `ParakeetTDT/Package.swift` in Xcode
2. Edit Scheme (Product → Scheme → Edit Scheme)
3. Add environment variables under Run → Arguments → Environment Variables
4. Press ⌘R to run

## Project Structure

```
ParakeetTDT/
├── Package.swift              # Swift Package configuration
├── Sources/
│   └── ParakeetTDT/
│       ├── ParakeetTDTApp.swift          # App entry point
│       ├── Views/
│       │   └── ContentView.swift         # Main UI
│       └── Services/
│           ├── TranscriptionService.swift # Business logic
│           └── PythonBridge.swift        # Python integration
```

## How It Works

1. **Swift UI Layer** (ContentView.swift)
   - SwiftUI views for recording button and results
   - Observes state changes from TranscriptionService

2. **Service Layer** (TranscriptionService.swift)
   - Manages recording and transcription state
   - Coordinates between UI and Python bridge

3. **Python Bridge** (PythonBridge.swift)
   - Uses PythonKit to call Python functions
   - Imports `app.recorder` and `app.transcriber`
   - Handles error conversion

4. **Python Layer** (existing code)
   - `app.recorder.AudioRecorder` - Records audio
   - `app.transcriber.transcribe_audio` - Transcribes using Parakeet MLX

## Common Issues

### "Could not find Python library"

Make sure you've set `PYTHON_LIBRARY` environment variable:

```bash
export PYTHON_LIBRARY="/Library/Frameworks/Python.framework/Versions/3.13"
```

### "Failed to import Python modules"

Make sure you've set `PYTHON_MODULE_PATH` to the repository root:

```bash
export PYTHON_MODULE_PATH="/path/to/parakeet-tdt-ui"
```

### Microphone Permission Denied

1. Open System Settings → Privacy & Security → Microphone
2. Enable permission for your terminal or Xcode

## Development Workflow

### Making Changes

1. Edit Swift code in `ParakeetTDT/Sources/`
2. Build: `swift build`
3. Test: `swift test`
4. Run: `swift run ParakeetTDT`

### Modifying Python Code

The app uses the existing Python code in `app/`. Any changes to Python files will be automatically picked up when you restart the app.

### Adding Dependencies

**Swift:**
Edit `ParakeetTDT/Package.swift` and add to the `dependencies` array.

**Python:**
Edit `pyproject.toml` and run `uv pip install -e .`

## Building for Distribution

See `docs/BUILD_GUIDE.md` for complete instructions.

Quick build:

```bash
./scripts/build-app.sh
```

This creates a basic `.app` bundle in the `build/` directory.

## Testing

```bash
cd ParakeetTDT
swift test
```

## Documentation

- **Quick Start**: This file (QUICKSTART.md)
- **Build Guide**: docs/BUILD_GUIDE.md - Complete build and distribution guide
- **Implementation Details**: docs/IMPLEMENTATION_SUMMARY.md - Technical overview
- **Project README**: ParakeetTDT/README.md - Swift project documentation

## Next Steps

1. Try recording and transcribing (requires microphone permission)
2. Review the code in `ParakeetTDT/Sources/`
3. Read the Build Guide for distribution instructions
4. Customize the UI in `ContentView.swift`

## Support

For issues or questions:
- Check the troubleshooting section in `docs/BUILD_GUIDE.md`
- Review the implementation summary in `docs/IMPLEMENTATION_SUMMARY.md`
- Open an issue on GitHub

---

Happy coding! 🎉
