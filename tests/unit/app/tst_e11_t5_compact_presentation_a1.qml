import QtQuick
import QtTest
import CompactPresentationA1Acceptance 1.0

// Only dispatch into C++ tests over the original public rendered module.
TestCase {
    name: "E11T5CompactPresentationA1"
    when: windowShown
    function test_human_compact_captions_and_whitelist() {
        const result=CompactPresentationA1Proof.captionsAndWhitelist();
        verify(result.ok, "The real compact row must retain human-only caption/error-kind precedence: " + result.error);
    }
    function test_truthful_status_and_command_precedence() {
        const result=CompactPresentationA1Proof.statusAndCommandPrecedence();
        verify(result.ok, "The rendered status/tooltip must not confirm older or partial native/command outcomes: " + result.error);
    }
    function test_native_labels_and_original_translation_contexts() {
        const result=CompactPresentationA1Proof.nativeLabelsAndTranslationContexts();
        verify(result.ok, "The FIRST native human labels and original translation contexts must survive the migration: " + result.error);
    }
}
