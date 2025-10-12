import SwiftUI

struct ContentView: View {
    @EnvironmentObject var transcriptionService: TranscriptionService
    @State private var showError = false
    @State private var errorMessage = ""
    
    var body: some View {
        VStack(spacing: 20) {
            // Status Label
            Text(statusText)
                .font(.headline)
                .foregroundColor(statusColor)
                .padding()
            
            // Record Button
            Button(action: toggleRecording) {
                Text(buttonText)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(buttonColor)
                    .foregroundColor(.white)
                    .cornerRadius(10)
            }
            .disabled(transcriptionService.isTranscribing)
            .padding(.horizontal)
            
            // Transcription Result
            ScrollView {
                Text(transcriptionService.transcriptionText.isEmpty ? 
                     "ここに音声の書き起こし結果が表示されます" : 
                     transcriptionService.transcriptionText)
                    .textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding()
            }
            .background(Color(.textBackgroundColor))
            .cornerRadius(10)
            .padding(.horizontal)
        }
        .padding()
        .frame(minWidth: 480, minHeight: 360)
        .alert("エラー", isPresented: $showError) {
            Button("OK") { }
        } message: {
            Text(errorMessage)
        }
        .onReceive(transcriptionService.$error) { error in
            if let error = error {
                errorMessage = error
                showError = true
            }
        }
    }
    
    private var statusText: String {
        if transcriptionService.isRecording {
            return "録音中…もう一度ボタンを押すと停止します"
        } else if transcriptionService.isTranscribing {
            return "書き起こし中です。しばらくお待ちください…"
        } else {
            return "マイク入力の準備ができています"
        }
    }
    
    private var statusColor: Color {
        if transcriptionService.isRecording {
            return .red
        } else if transcriptionService.isTranscribing {
            return .orange
        } else {
            return .green
        }
    }
    
    private var buttonText: String {
        transcriptionService.isRecording ? "録音停止" : "録音開始"
    }
    
    private var buttonColor: Color {
        transcriptionService.isRecording ? .red : .blue
    }
    
    private func toggleRecording() {
        if transcriptionService.isRecording {
            transcriptionService.stopRecording()
        } else {
            transcriptionService.startRecording()
        }
    }
}

#Preview {
    ContentView()
        .environmentObject(TranscriptionService())
}
