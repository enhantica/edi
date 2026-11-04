import QtQuick
import QtTest
import DataSummaryAcceptance 1.0

// C++ owns original cells/arithmetic/schema. No JS aggregator or alternate parser.
TestCase {
    name: "E11T5DataSummary"
    when: windowShown
    function test_exact_populations_coverage_witnesses_and_units() {
        const result=DataSummaryProof.populationCoverageAndWitnesses();
        verify(result.ok, "Compact inspection must preserve original cell/population/metadata meanings: " + result.error);
    }
    function test_native_partitions_masks_axis_identity_and_binary64_extremes() {
        const result=DataSummaryProof.partitionsMasksAxesAndExtremes();
        verify(result.ok, "Unknown masks, missing scalars, bins or arithmetic limits must not invent physical evidence: " + result.error);
    }
    function test_legacy_raw_and_strict_same_tool_admission() {
        const result=DataSummaryProof.rawCompatibilityAndStrictAdmission();
        verify(result.ok, "Raw ranges stay exact and summary crossfields refuse before capture: " + result.error);
    }
    function test_closed_outgoing_projection_keeps_declared_summary_and_backend_evidence() {
        const result=DataSummaryProof.closedOutgoingProjection();
        verify(result.ok, "Actual outgoing roles must preserve complete declared summary while retaining full backend originals: " + result.error);
    }
    function test_original_sc_file_order_and_noncurrent_fit_frame() {
        const result=DataSummaryProof.originalSingleCrystalOwner();
        verify(result.ok, "SC file/fit-use/frame evidence must retain its actual original owner: " + result.error);
    }
}
