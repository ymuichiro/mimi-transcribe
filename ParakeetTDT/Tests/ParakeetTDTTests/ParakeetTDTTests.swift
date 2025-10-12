import XCTest
@testable import ParakeetTDT

final class ParakeetTDTTests: XCTestCase {
    func testTranscriptionServiceInitialization() {
        let service = TranscriptionService()
        XCTAssertFalse(service.isRecording)
        XCTAssertFalse(service.isTranscribing)
        XCTAssertTrue(service.transcriptionText.isEmpty)
    }
}
