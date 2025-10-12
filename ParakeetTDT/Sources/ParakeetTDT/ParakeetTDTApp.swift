import SwiftUI

@main
struct ParakeetTDTApp: App {
    @StateObject private var transcriptionService = TranscriptionService()
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(transcriptionService)
        }
        .commands {
            CommandGroup(replacing: .newItem) { }
        }
    }
}
