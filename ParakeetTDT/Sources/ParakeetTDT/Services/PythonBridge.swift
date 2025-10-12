import Foundation
import PythonKit

/// Bridge to Python modules for audio recording and transcription
class PythonBridge {
    private let sys: PythonObject
    private let recorderModule: PythonObject
    private let transcriberModule: PythonObject
    
    enum BridgeError: Error {
        case pythonImportFailed(String)
        case recorderCreationFailed(String)
        case recordingFailed(String)
        case transcriptionFailed(String)
        case pythonPathNotConfigured
    }
    
    init() {
        // Initialize Python
        guard let pythonLibrary = findPythonLibrary() else {
            fatalError("Could not find Python library. Please configure PYTHON_LIBRARY environment variable.")
        }
        
        setenv("PYTHONHOME", pythonLibrary, 1)
        
        sys = Python.import("sys")
        
        // Add the app module path to Python sys.path
        if let appPath = getAppPythonModulePath() {
            sys.path.insert(0, PythonObject(appPath))
        }
        
        do {
            // Import Python modules
            let app = try Python.attemptImport("app")
            recorderModule = app.recorder
            transcriberModule = app.transcriber
        } catch {
            fatalError("Failed to import Python modules: \(error)")
        }
    }
    
    func createRecorder() throws -> PythonObject {
        do {
            let AudioRecorder = recorderModule.AudioRecorder
            return AudioRecorder()
        } catch {
            throw BridgeError.recorderCreationFailed(String(describing: error))
        }
    }
    
    func startRecording(recorder: PythonObject, path: URL) throws {
        do {
            let pathString = path.path
            recorder.start(PythonObject(pathString))
        } catch {
            throw BridgeError.recordingFailed("Start failed: \(error)")
        }
    }
    
    func stopRecording(recorder: PythonObject) throws {
        do {
            recorder.stop()
        } catch {
            throw BridgeError.recordingFailed("Stop failed: \(error)")
        }
    }
    
    func transcribeAudio(path: URL) async throws -> String {
        return try await withCheckedThrowingContinuation { continuation in
            DispatchQueue.global(qos: .userInitiated).async { [weak self] in
                guard let self = self else {
                    continuation.resume(throwing: BridgeError.transcriptionFailed("Bridge deallocated"))
                    return
                }
                
                do {
                    let pathString = path.path
                    let TranscriberConfig = self.transcriberModule.TranscriberConfig
                    let transcribe_audio = self.transcriberModule.transcribe_audio
                    
                    let config = TranscriberConfig()
                    let result = transcribe_audio(PythonObject(pathString), config)
                    let text = String(result.text)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
                    
                    continuation.resume(returning: text)
                } catch {
                    continuation.resume(throwing: BridgeError.transcriptionFailed(String(describing: error)))
                }
            }
        }
    }
    
    // MARK: - Helper Methods
    
    private func findPythonLibrary() -> String? {
        // Check environment variable first
        if let envPath = ProcessInfo.processInfo.environment["PYTHON_LIBRARY"] {
            return envPath
        }
        
        // Check common Python locations for development
        let possiblePaths = [
            "/usr/local/Frameworks/Python.framework/Versions/3.13",
            "/Library/Frameworks/Python.framework/Versions/3.13",
            "/opt/homebrew/opt/python@3.13/Frameworks/Python.framework/Versions/3.13",
        ]
        
        for path in possiblePaths {
            if FileManager.default.fileExists(atPath: path) {
                return path
            }
        }
        
        return nil
    }
    
    private func getAppPythonModulePath() -> String? {
        // In development, point to the repository root
        if let envPath = ProcessInfo.processInfo.environment["PYTHON_MODULE_PATH"] {
            return envPath
        }
        
        // In production, the Python modules should be in the app bundle
        if let resourcePath = Bundle.main.resourcePath {
            let pythonModulePath = (resourcePath as NSString).appendingPathComponent("python")
            if FileManager.default.fileExists(atPath: pythonModulePath) {
                return pythonModulePath
            }
        }
        
        // For development, try to find relative to the current working directory
        let currentPath = FileManager.default.currentDirectoryPath
        let parentPath = (currentPath as NSString).deletingLastPathComponent
        if FileManager.default.fileExists(atPath: (parentPath as NSString).appendingPathComponent("app")) {
            return parentPath
        }
        
        return nil
    }
}

// Extension to handle Python import errors
extension Python {
    static func attemptImport(_ moduleName: String) throws -> PythonObject {
        do {
            return Python.import(moduleName)
        } catch {
            throw PythonBridge.BridgeError.pythonImportFailed("Failed to import '\(moduleName)': \(error)")
        }
    }
}
