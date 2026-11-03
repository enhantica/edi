import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import ReportBoundaryAcceptance 1.0

Rectangle {
    width: 900
    height: 700
    TestCase {
        name: "ReportPhysicalPublication"
        when: windowShown
        function cleanup() {
            Session.closeProject();
        }
        function test_actual_app_save_stays_in_its_loader_domain_data() {
            const cases = [];
            for (const rule of ["iucr_19", "iucr_99"])
                for (const saveAs of [false, true])
                    for (const geometry of ["endpoint", "joint", "ordinary", "fixed"])
                        cases.push({
                            tag: [rule, saveAs, geometry].join("-"),
                            rule,
                            saveAs,
                            geometry
                        });
            return cases;
        }
        function test_actual_app_save_stays_in_its_loader_domain(data) {
            const location = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/correlations/polynomial-3"));
            const original = SettingsProof.text(location, "structures/phase.edi");
            const replacements = data.geometry === "joint" ? {
                alpha: "60.049(3.0)",
                beta: "60.049(3.0)",
                gamma: "120.051(3.0)"
            } : {
                gamma: data.geometry === "fixed" ? "179.99" : data.geometry === "ordinary" ? "97.1234(0.003)" : "179.99(3.0)"
            };
            let structure = original;
            for (const key of Object.keys(replacements))
                structure = structure.replace(new RegExp("(_cell\\.angle_" + key + "\\s+)\\S+"), "$1" + replacements[key]);
            verify(structure !== original, "The app witness states a distinct valid pre-rounding cell in its input record");
            verify(SettingsProof.write(location, "structures/phase.edi", structure), "The authored scientific cell reaches the real app loader");
            verify(SettingsProof.write(location, "project.edi", SettingsProof.text(location, "project.edi") + "\n_su_format.rule " + data.rule + "\n"), "The app uses the independently selected IUCr rule");
            verify(Session.openProject(location), "The app loader accepts the original cell before any save: " + Session.lastError);
            tryCompare(Session.project, "calculating", false, 10000, "The actual initial projection settles before Save");
            Session.project.title = "Scientific publication domain witness";
            const before = BoundaryProof.inventory(location);
            const destination = data.saveAs ? SettingsProof.copyProject(location) : location;
            const previous = BoundaryProof.inventory(destination);
            const saved = data.saveAs ? Session.saveAs(destination) : Session.save();
            if (!saved) {
                verify(data.geometry !== "ordinary" && data.geometry !== "fixed", "App Save must retain success for fixed and ordinary rounded controls");
                compare(JSON.stringify(BoundaryProof.inventory(location)), JSON.stringify(before), "A physical-domain refusal preserves every source byte");
                compare(JSON.stringify(BoundaryProof.inventory(destination)), JSON.stringify(previous), "A physical-domain refusal preserves every previous destination byte");
            } else {
                if (data.saveAs)
                    compare(JSON.stringify(BoundaryProof.inventory(location)), JSON.stringify(before), "A successful scientific Save as retains the source");
                Session.closeProject();
                verify(Session.openProject(destination), "Every successful app Save or Save as remains readable by its actual loader: " + Session.lastError);
            }
        }
    }
}
