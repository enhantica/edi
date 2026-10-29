import QtQuick
import QtTest
import WebHumanA2aAcceptance 1.0

// Same real AssistantMessage methods before and after A2a; no new production seam.
TestCase {
    name: "E11T5WebHumanA2a"
    when: windowShown
    function test_original_single_line_literal_semantics() {
        const result = WebHumanA2aProof.normalizationLiteralSemantics();
        verify(result.ok, "FIRST human single-line normalization preserves exact types/Unicode without rewriting literal inputs: " + result.error);
    }
    function test_original_web_shapes_and_consumed_callers() {
        const result = WebHumanA2aProof.webShapesAndConsumedCallers();
        verify(result.ok, "FIRST search/open/find captions preserve exact shapes and expanded/default-copy composition: " + result.error);
    }
    function test_original_serializer_dependencies_and_cold_boundary() {
        const result = WebHumanA2aProof.serializationDependenciesAndColdBoundary();
        verify(result.ok, "FIRST JSON exceptions/dependencies/translation remain original and collapsed disclosure stays cold: " + result.error);
    }
}
