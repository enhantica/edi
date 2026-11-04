import QtQuick
import QtTest
import SentFileMetadataAcceptance 1.0

TestCase {
    name: "E11T5SentFileMetadata"
    when: windowShown
    function test_original_metadata_lengths_types_and_all_or_empty() {
        const result=SentFileMetadataProof.metadataAdmission();
        verify(result.ok, "Original sent-file admission must preserve exact metadata types, code-unit limits and all-or-empty behavior: " + result.error);
    }
    function test_original_first_invalid_short_circuits_and_borrows() {
        const result=SentFileMetadataProof.orderedAccessAndColdPrivacy();
        verify(result.ok, "Original metadata traversal must preserve short circuits, borrowed references and cold privacy: " + result.error);
    }
    function test_original_visible_sent_file_labels_and_size() {
        const result=SentFileMetadataProof.visibleFileLines();
        verify(result.ok, "Individual original file lines must preserve literal names, decimal sizes, export cues and accessibility: " + result.error);
    }
    function test_original_live_kind_payload_and_status_updates() {
        const result=SentFileMetadataProof.liveUpdates();
        verify(result.ok, "Original live kind, status and payload changes must update or clear file lines without stale admission: " + result.error);
    }
}
