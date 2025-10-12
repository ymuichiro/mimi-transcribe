# Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         macOS User                          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      SwiftUI Layer                          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              ContentView.swift                        │  │
│  │  • Recording button                                   │  │
│  │  • Status display                                     │  │
│  │  • Transcription result text area                     │  │
│  │  • Error alerts                                       │  │
│  └─────────────────────────┬─────────────────────────────┘  │
│                            │ @ObservedObject               │
└────────────────────────────┼─────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer (Swift)                    │
│  ┌───────────────────────────────────────────────────────┐  │
│  │       TranscriptionService.swift                      │  │
│  │  • Recording state management                         │  │
│  │  • Transcription state management                     │  │
│  │  • Error handling                                     │  │
│  │  @Published properties:                               │  │
│  │    - isRecording                                      │  │
│  │    - isTranscribing                                   │  │
│  │    - transcriptionText                                │  │
│  │    - error                                            │  │
│  └─────────────────────────┬─────────────────────────────┘  │
│                            │                               │
└────────────────────────────┼─────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                 Python Bridge Layer (Swift)                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              PythonBridge.swift                       │  │
│  │  • PythonKit integration                              │  │
│  │  • Python module imports                              │  │
│  │  • Error conversion (Python → Swift)                  │  │
│  │  • Async/await wrappers                               │  │
│  │  Methods:                                             │  │
│  │    - createRecorder() → PythonObject                  │  │
│  │    - startRecording(recorder, path)                   │  │
│  │    - stopRecording(recorder)                          │  │
│  │    - transcribeAudio(path) async → String             │  │
│  └─────────────────────────┬─────────────────────────────┘  │
│                            │ PythonKit calls               │
└────────────────────────────┼─────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                  Python Layer (Existing)                    │
│  ┌──────────────────────┐    ┌─────────────────────────┐   │
│  │   app.recorder       │    │   app.transcriber       │   │
│  │  AudioRecorder class │    │  transcribe_audio()     │   │
│  │  • start(path)       │    │  • Loads Parakeet model │   │
│  │  • stop()            │    │  • Processes audio      │   │
│  │  • is_recording      │    │  • Returns AlignedResult│   │
│  └──────────┬───────────┘    └──────────┬──────────────┘   │
│             │                           │                  │
└─────────────┼───────────────────────────┼──────────────────┘
              │                           │
              ▼                           ▼
    ┌──────────────────┐        ┌──────────────────┐
    │  sounddevice     │        │  parakeet-mlx    │
    │  soundfile       │        │  mlx.core        │
    │  (Audio I/O)     │        │  (ML inference)  │
    └──────────────────┘        └──────────────────┘
```

## Data Flow

### Recording Flow

```
User clicks "録音開始"
    ↓
ContentView.toggleRecording()
    ↓
TranscriptionService.startRecording()
    ↓
PythonBridge.createRecorder() → PythonObject
    ↓
Python: AudioRecorder()
    ↓
PythonBridge.startRecording(recorder, tempFile)
    ↓
Python: recorder.start(path)
    ↓
sounddevice starts recording to WAV
    ↓
(User speaks into microphone)
    ↓
User clicks "録音停止"
    ↓
TranscriptionService.stopRecording()
    ↓
PythonBridge.stopRecording(recorder)
    ↓
Python: recorder.stop()
    ↓
WAV file saved
```

### Transcription Flow

```
Recording stopped
    ↓
TranscriptionService.performTranscription(audioPath)
    ↓
PythonBridge.transcribeAudio(path) [async]
    ↓
Python: transcribe_audio(path, config)
    ↓
Python: ParakeetModelManager.get_model(config)
    ↓
Python: model.transcribe(path) [MLX inference]
    ↓
AlignedResult returned
    ↓
PythonBridge extracts result.text
    ↓
TranscriptionService updates @Published transcriptionText
    ↓
SwiftUI updates ContentView
    ↓
User sees transcription result
```

## State Management

```
TranscriptionService (ObservableObject)
│
├── @Published isRecording: Bool
│   └── Controls button text and state indicator
│
├── @Published isTranscribing: Bool
│   └── Shows "書き起こし中..." status
│
├── @Published transcriptionText: String
│   └── Displayed in ScrollView text area
│
└── @Published error: String?
    └── Triggers alert dialog when set
```

## Environment Configuration

### Development

```
Environment Variables:
┌────────────────────────────────────────┐
│ PYTHON_LIBRARY                         │
│   → /Library/Frameworks/Python.../3.13 │
│                                        │
│ PYTHON_MODULE_PATH                     │
│   → /path/to/parakeet-tdt-ui          │
└────────────────────────────────────────┘
         ↓
PythonBridge.init()
         ↓
Sets PYTHONHOME
Adds module path to sys.path
Imports app.recorder, app.transcriber
```

### Production (App Bundle)

```
App Bundle Structure:
ParakeetTDT.app/
├── Contents/
│   ├── MacOS/
│   │   └── ParakeetTDT (executable)
│   ├── Resources/
│   │   └── python/
│   │       ├── venv/ (embedded Python)
│   │       └── app/ (Python modules)
│   └── Info.plist
│
PythonBridge auto-detects bundle resources
```

## Error Handling

```
Python Exception
    ↓
try/catch in PythonBridge
    ↓
Convert to BridgeError
    ↓
throw BridgeError
    ↓
catch in TranscriptionService
    ↓
Set @Published error
    ↓
SwiftUI .alert() triggered
    ↓
User sees error dialog
```

## Threading Model

```
Main Thread (UI)
    └── SwiftUI Views
    └── TranscriptionService @MainActor
            │
            ├── Recording (sync) → Python GIL
            │
            └── Transcription (async) 
                    ↓
                Background Thread
                    └── Python inference
                            ↓
                        Main Thread
                            └── Update @Published
```

## File Locations

### Development
- Source Code: `parakeet-tdt-ui/ParakeetTDT/Sources/`
- Python Modules: `parakeet-tdt-ui/app/`
- Temp Recordings: `/tmp/parakeet-recording-*.wav`

### Production
- App: `ParakeetTDT.app`
- Python: `ParakeetTDT.app/Contents/Resources/python/`
- Model Cache: `~/.cache/huggingface/`
- Logs: `~/Library/Logs/parakeet-tdt-study/`

---

This architecture provides:
- ✅ Native macOS UI (SwiftUI)
- ✅ Reuse of existing Python logic
- ✅ Clean separation of concerns
- ✅ Type-safe error handling
- ✅ Reactive UI updates
- ✅ Async transcription
