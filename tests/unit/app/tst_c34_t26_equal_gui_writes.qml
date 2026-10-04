import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0

TestCase {
    name: "C34T26EqualGuiWrites"

    function init() { Session.closeProject(); }
    function cleanup() { Session.closeProject(); }

    function test_equal_gui_write_data() {
        return [
            {tag: "background position", route: "background"},
            {tag: "excluded start", route: "excludedStart"},
            {tag: "excluded end", route: "excludedEnd"},
            {tag: "orientation structure", route: "orientationStructure"},
            {tag: "orientation h", route: "orientationH"},
            {tag: "orientation k", route: "orientationK"},
            {tag: "orientation l", route: "orientationL"},
            {tag: "space group name", route: "spaceName"},
            {tag: "space group setting", route: "spaceCode"},
            {tag: "space group absent number", route: "spaceNumber"},
            {tag: "scattering length", route: "scatteringLength"},
            {tag: "peak cutoff", route: "cutoff"},
            {tag: "linked structure", route: "linkedStructure"},
            {tag: "dataset weight", route: "datasetWeight"},
            {tag: "parameter editor control", route: "parameter"}
        ];
    }

    function test_equal_gui_write(data) {
        // The default neutron example has background, exclusions and orientation rows.
        // The scattering-length route uses a one-element Si example; both open fresh.
        const fixture = data.route === "scatteringLength"
            ? "docs/user/cli/pd-neut-tof_si-sepd_start-2/project"
            : "docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project";
        Session.openProject(Probe.repoUrl(fixture));
        verify(Session.hasProject, ": the committed GUI fixture must open: " + Session.lastError);
        const project = Session.project;
        const experiment = project.currentExperiment;
        const structure = project.currentStructure;
        verify(experiment !== null && structure !== null,
               ": the GUI fixture needs a linked experiment and structure");
        if (data.route === "scatteringLength") {
            // A declared map replaces the default table. Cover the Si fixture's one atom type
            // through the real GUI routes before witnessing the equal-value write.
            structure.scatteringLengths.append();
            verify(structure.scatteringLengths.setTypeSymbol(0, "Si"),
                   ": custom scattering setup must name the fixture's Si atom");
            verify(structure.scatteringLengths.setLengthFm(0, 1.0),
                   ": custom scattering setup must assign a finite Si length");
            tryVerify(function() { return Probe.computedCurrent(experiment); }, 10000,
                      ": the scattering-length setup must recalculate before the equal write");
        }
        verify(Probe.computedCurrent(experiment),
               ": an equal-write witness must start with current computed categories");

        const background = experiment.background;
        const excluded = experiment.excludedRegions;
        const orientation = experiment.preferredOrientation;
        const space = structure.spaceGroup;
        const row = function(model, role) { return Probe.rows(model)[0][role]; };
        let accepted = true;
        switch (data.route) {
        case "background": accepted = background.setPosition(0, row(background, "position")); break;
        case "excludedStart": accepted = excluded.setStart(0, row(excluded, "start")); break;
        case "excludedEnd": accepted = excluded.setEnd(0, row(excluded, "end")); break;
        case "orientationStructure": accepted = orientation.setStructureId(0, row(orientation, "structureId")); break;
        case "orientationH": accepted = orientation.setIndex(0, "h", row(orientation, "indexH")); break;
        case "orientationK": accepted = orientation.setIndex(0, "k", row(orientation, "indexK")); break;
        case "orientationL": accepted = orientation.setIndex(0, "l", row(orientation, "indexL")); break;
        case "spaceName": accepted = Probe.writeProperty(space, "nameHM", space.nameHM); break;
        case "spaceCode": accepted = Probe.writeProperty(space, "coordSystemCode", space.coordSystemCode); break;
        case "spaceNumber": accepted = Probe.writeProperty(space, "itNumber", 0); break;
        case "scatteringLength": accepted = structure.scatteringLengths.setLengthFm(0, row(structure.scatteringLengths, "lengthFm")); break;
        case "cutoff": accepted = Probe.writeProperty(experiment, "cutoffFwhm", experiment.cutoffFwhm); break;
        case "linkedStructure": accepted = Probe.writeProperty(experiment, "linkedStructureId", experiment.linkedStructureId); break;
        case "datasetWeight": accepted = Probe.writeProperty(experiment, "datasetWeight", experiment.datasetWeight); break;
        case "parameter": accepted = Probe.writeProperty(experiment.scale, "value", experiment.scale.value); break;
        default: fail(": unknown GUI write route " + data.route);
        }
        verify(accepted, ": the GUI must admit the equal write through " + data.route);
        // No event-loop yield occurs between the setter and this read. The queued
        // recalculation must not be needed to reject the previous computed units.
        verify(!Probe.computedCurrent(experiment),
               " I4: equal GUI input write must stale categories before recalculation: " + data.route);
    }
}
