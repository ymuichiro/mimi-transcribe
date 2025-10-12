import Foundation
import Combine
import PythonKit

/// Service that manages audio recording and transcription by bridging to Python code
@MainActor
class TranscriptionService: ObservableObject {
    @Published var isRecording = false
    @Published var isTranscribing = false
    @Published var transcriptionText = ""
    @Published var error: String?
    
    private var pythonRecorder: PythonObject?
    private var recordingPath: URL?
    private let pythonBridge: PythonBridge
    
    init() {
        self.pythonBridge = PythonBridge()
    }
    
    func startRecording() {
        guard !isRecording else { return }
        
        do {
            let tempDir = FileManager.default.temporaryDirectory
            let filename = "parakeet-recording-\(UUID().uuidString).wav"
            let path = tempDir.appendingPathComponent(filename)
            
            recordingPath = path
            pythonRecorder = try pythonBridge.createRecorder()
            try pythonBridge.startRecording(recorder: pythonRecorder!, path: path)
            
            isRecording = true
            transcriptionText = ""
            error = nil
            
        } catch {
            self.error = "録音を開始できません: \(error.localizedDescription)"
        }
    }
    
    func stopRecording() {
        guard isRecording else { return }
        guard let recorder = pythonRecorder else { return }
        
        do {
            try pythonBridge.stopRecording(recorder: recorder)
            isRecording = false
            
            if let path = recordingPath {
                Task {
                    await performTranscription(audioPath: path)
                }
            }
        } catch {
            self.error = "録音を停止できません: \(error.localizedDescription)"
            isRecording = false
        }
    }
    
    private func performTranscription(audioPath: URL) async {
        isTranscribing = true
        
        do {
            let text = try await pythonBridge.transcribeAudio(path: audioPath)
            transcriptionText = text
            error = nil
            
            // Clean up temporary file
            try? FileManager.default.removeItem(at: audioPath)
            recordingPath = nil
            
        } catch {
            self.error = "書き起こしでエラーが発生しました: \(error.localizedDescription)"
        }
        
        isTranscribing = false
    }
}
