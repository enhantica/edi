import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import ProjectTextAcceptance 1.0
import EasyApplication.Gui.Style as Style
import "RenderedTable.js" as Render

Item {
    width: 900
    height: 900
    Component {
        id: textFactory
        TextTab {
            width: 700
            height: 820
            underContinue: false
        }
    }
    Component {
        id: exportFactory
        ExportGroup {
            width: 700
            shown: true
        }
    }
    TestCase {
        name: "ProjectText"
        when: windowShown
        property var tab
        property int oldTheme
        ProjectTextProof {
            id: proof
        }
        SignalSpy {
            id: reportSaved
            signalName: "saved"
        }
        SignalSpy {
            id: saveAsAsked
            target: AppState
            signalName: "saveAsRequested"
        }
        function init() {
            oldTheme = Style.Colors.theme;
            Session.closeProject();
            verify(Session.openProject(proof.project()), "The independently authored two-structure text witness opens");
        }
        function cleanup() {
            if (tab)
                tab.destroy();
            tab = null;
            reportSaved.target = null;
            Session.closeProject();
            Style.Colors.theme = oldTheme;
        }
        function openText(block) {
            tab = textFactory.createObject(parent, {
                source: block.text
            });
            verify(tab !== null, "The actual production Text tab is instantiated with a real block");
            const editor = findChild(tab, "text.view");
            verify(editor !== null, "The production Text tab exposes its real editor");
            return editor;
        }
        function applyButton() {
            const buttons = Render.descendants(tab).filter(item => typeof item.clicked === "function" && (item.objectName === "text.apply" || item.text === "✓" || /^check(?:-circle)?$/.test(item.fontIcon ?? "")));
            compare(buttons.length, 1, "The Text tab offers exactly one apply action");
            return buttons[0];
        }
        function showChoice() {
            const boxes = Render.descendants(tab).filter(item => typeof item.textAt === "function" && item.count === 2 && item.textAt(0) === "Editable" && item.textAt(1) === "Everything");
            compare(boxes.length, 1, "The Show selector offers Editable and Everything in the declared order");
            return boxes[0];
        }
        function choose(box, index) {
            box.currentIndex = index;
            box.activated(index);
        }
        function click(control) {
            verify(control.visible && control.enabled, "The requested Text-tab action is enabled and visible");
            mouseClick(control, control.width / 2, control.height / 2);
        }
        function snapshot() {
            return JSON.stringify(Probe.rows(Session.project.parameters).map(row => ({
                        name: row.path,
                        value: row.parameter ? row.parameter.value : row.value,
                        free: row.parameter ? row.parameter.free : row.free
                    })));
        }
        function test_apply_and_single_undo() {
            const block = Session.project.currentStructure;
            const editor = openText(block), apply = applyButton(), show = showChoice();
            compare(show.currentIndex, 0, "A Text tab opens with Editable selected");
            compare(editor.readOnly, false, "The default Text view permits editing");
            compare(apply.enabled, false, "Apply is disabled while the editor equals the project");
            const initial = editor.text, before = snapshot();
            verify(!/^_edi\./m.test(initial), "Editable omits the output file-header category");
            const edited = initial.replace(/(_cell\.length_[abc]\s+)\S+/g, "$1" + "5.4317");
            verify(edited !== initial, "The valid edit changes the nontrivial cell lengths");
            editor.text = edited;
            tryCompare(apply, "enabled", true, 1000, "Changing the text enables Apply");
            const applyPosition = apply.mapToItem(tab, 0, 0), showPosition = show.mapToItem(tab, 0, 0);
            verify(showPosition.x + show.width <= applyPosition.x + 1, "Show sits to the left of the top-right apply action");
            verify(applyPosition.y < tab.height / 5 && applyPosition.x > tab.width / 2, "Apply sits at the top right");
            click(apply);
            tryCompare(block.cell.lengthA, "value", 5.4317, 1000, "A valid text edit reaches the real model");
            compare(apply.enabled, false, "Successful apply adopts the editor as the new project text");
            const after = snapshot();
            verify(after !== before, "The text edit changes observable project values");
            const control = SettingsProof.copyProject(proof.project());
            const complete = proof.structureText();
            verify(/^_edi\.schema_version[ \t]+\d+/m.test(complete), "The independent standalone file retains its declared output schema header");
            const fileEdit = complete.replace(/(_cell\.length_[abc]\s+)\S+/g, "$1" + "5.4317");
            verify(fileEdit !== complete, "The ordinary-reader control receives the same nontrivial cell edits");
            verify(SettingsProof.write(control, "structures/structure.edi", fileEdit), "The file-open control carries the same edited inputs in a complete EDI document");
            Session.project.undo();
            compare(snapshot(), before, "One undo restores every model parameter changed by one text apply");
            verify(Session.openProject(control), "The ordinary project reader opens the same edited text");
            compare(snapshot(), after, "Text apply and ordinary file open produce the same project values");
        }
        function test_invalid_edits_are_atomic_data() {
            return [
                {
                    tag: "unknown-item",
                    kind: 0
                },
                {
                    tag: "unknown-category",
                    kind: 1
                },
                {
                    tag: "invalid-number",
                    kind: 2
                },
                {
                    tag: "short-loop-row",
                    kind: 3
                },
                {
                    tag: "invalid-block-name",
                    kind: 4
                }
            ];
        }
        function test_invalid_edits_are_atomic(data) {
            const block = Session.project.currentStructure;
            const editor = openText(block), apply = applyButton();
            compare(editor.readOnly, false, "Validation is exercised through the editable Text view");
            const original = editor.text, before = snapshot(), sourceBefore = block.text.text;
            const lines = original.split("\n"), row = lines.findIndex(line => line.startsWith("Li1 "));
            verify(row >= 0, "The invalid-loop witness reaches an existing atom row");
            const short = lines.slice();
            short[row] = short[row].trim().split(/\s+/).slice(0, -1).join(" ");
            const invalid = [
                {
                    text: original + "\n_cell.unknown_length 3.5\n",
                    problem: /unknown|unrecogn|item/i
                },
                {
                    text: original + "\n_unknown_category.setting 3.5\n",
                    problem: /unknown|unrecogn|category/i
                },
                {
                    text: original.replace(/(_cell\.length_a\s+)\S+/, "$1not_a_number"),
                    problem: /number|numeric|float|length_a/i
                },
                {
                    text: short.join("\n"),
                    problem: /loop|row|column|width/i
                },
                {
                    text: original.replace(/^data_\S+/m, "data_"),
                    problem: /block|data_|name/i
                }
            ];
            const witness = invalid[data.kind];
            const warning = findChild(tab, "text.refusal");
            verify(warning !== null, "The production Text tab owns a rendered refusal label");
            compare(warning.text, "", "Each invalid input starts with a fresh tab and no stale refusal");
            verify(witness.text !== original, "Every invalid edit actually changes the input text");
            editor.text = witness.text;
            tryCompare(apply, "enabled", true, 1000, "Each invalid edit remains eligible for validation");
            click(apply);
            compare(snapshot(), before, "Refusing invalid text changes no project parameter");
            compare(block.text.text, sourceBefore, "Refusing invalid text preserves the committed block text");
            compare(editor.text, witness.text, "An invalid edit stays available for correction");
            verify(witness.problem.test(warning.text) || /\bline[ \t]+[1-9]\d*[ \t]*:[ \t]*\S+/i.test(warning.text), "The refusal identifies the invalid input by its tag/class or a source line with the reader's reason: " + warning.text);
            tryVerify(() => Render.texts(tab).includes(warning) && warning.text.trim() !== "", 1000, "The refusal is displayed in the actual Text-tab warning, not only retained in an error property; visible=" + warning.visible + ", size=" + warning.width + "x" + warning.height + ", text=" + warning.text);
        }
        function test_everything_is_read_only() {
            tryCompare(Session.project, "calculating", false, 5000, "The calculated-data witness finishes its real model calculation");
            const editor = openText(Session.project.currentExperiment), apply = applyButton(), show = showChoice();
            const reference = proof.dictionary();
            verify(reference.categories && reference.categories.length > 0, "The filter reference reads the captured dictionary YAML independently");
            const editableCategories = new Set((editor.text.match(/^_[A-Za-z0-9_]+\./gm) ?? []).map(tag => tag.slice(1, -1)));
            verify(!/_data\.intensity_meas\b/.test(editor.text), "Editable omits measured output categories");
            choose(show, 1);
            tryCompare(editor, "readOnly", true, 1000, "Everything is view-only");
            verify(/_data\.intensity_meas\b/.test(editor.text), "Everything includes the actual measured data");
            for (const tag of ["_data.d_spacing", "_data.intensity_calc", "_data.intensity_bkg", "_data.calc_status", "_pd_calc.component_intensities_net"])
                verify(editor.text.includes(tag), "Everything exposes every required calculated-data column and both structure curves: " + tag);
            const points = Probe.rows(Session.project.currentExperiment.pattern);
            verify(points.length > 0, "The measured-data table has real calculated rows");
            for (const point of points)
                verify(Math.abs(point.residual - (point.intensityMeas - point.intensityCalc)) <= 1e-12 * Math.max(1, Math.abs(point.intensityCalc)), "The measured-data residual is the observed intensity less the calculated intensity");
            const everythingCategories = new Set((editor.text.match(/^_[A-Za-z0-9_]+\./gm) ?? []).map(tag => tag.slice(1, -1)));
            for (const row of reference.categories) {
                if (!everythingCategories.has(row.id))
                    continue;
                const marks = Object.keys(row).filter(key => ["input", "output"].includes(row[key]));
                compare(marks.length, 1, "Every carried category has exactly one SDK input-or-output mark");
                compare(editableCategories.has(row.id), row[marks[0]] === "input", "Editable contains exactly the input categories of Everything");
            }
            compare(apply.enabled, false, "Everything disables the apply action");
            verify(/Editable/i.test(apply.ToolTip.text), "The disabled action tells the user to switch to Editable");
            const before = editor.text;
            editor.forceActiveFocus();
            keyClick(Qt.Key_A);
            compare(editor.text, before, "Keyboard input cannot change Everything text");
            choose(show, 0);
            tryCompare(editor, "readOnly", false, 1000, "Returning to Editable restores editing");
        }
        function luminance(color) {
            function channel(v) {
                return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
            }
            return .2126 * channel(color.r) + .7152 * channel(color.g) + .0722 * channel(color.b);
        }
        function test_syntax_colours() {
            const editor = openText(Session.project.currentStructure);
            for (const theme of [Style.Colors.LightTheme, Style.Colors.DarkTheme]) {
                Style.Colors.theme = theme;
                const witnesses = [
                    {
                        token: "data_",
                        kind: "orange"
                    },
                    {
                        token: "_cell.length_a",
                        kind: "blue"
                    },
                    {
                        token: "_atom_site.id",
                        kind: "green"
                    },
                    {
                        token: "loop_",
                        kind: "grey"
                    }
                ];
                for (const witness of witnesses) {
                    const offset = editor.text.indexOf(witness.token);
                    verify(offset >= 0, "The syntax witness reaches each required token class");
                    let span;
                    tryVerify(() => {
                        span = proof.formats(editor).find(row => row.start <= offset && row.start + row.length > offset);
                        return span !== undefined;
                    }, 1000, "The actual text document applies a colour format to the token");
                    const c = span.color;
                    const family = witness.kind === "orange" ? c.r > c.g && c.g > c.b : witness.kind === "blue" ? c.b > c.r && c.b > c.g : witness.kind === "green" ? c.g > c.r && c.g > c.b : Math.max(c.r, c.g, c.b) - Math.min(c.r, c.g, c.b) < .04;
                    verify(family, "The rendered token uses the owner's orange, blue, green or grey colour family");
                    const a = luminance(c), b = luminance(Style.Colors.textViewBackground);
                    verify((Math.max(a, b) + .05) / (Math.min(a, b) + .05) >= 4.5, "Syntax text meets the normal-text readability ratio on each theme background");
                }
            }
        }
        function options() {
            return Session.project.currentStructure.viewOptions ?? Session.project.structureViewOptions;
        }
        function setAppearance(first) {
            const o = options();
            o.atomView = first ? "vdw" : "covalent";
            o.atomScale = first ? .37 : .81;
            o.adpProbability = first ? .63 : .91;
            o.colorScheme = first ? "vesta" : "jmol";
            o.showLabels = first;
            o.atoms = first ? "asymmetric" : "all";
            o.bonds = first;
            o.cell = !first;
            o.axes = first;
        }
        function appearance() {
            const o = options();
            return JSON.stringify({
                atomView: o.atomView,
                atomScale: o.atomScale,
                adpProbability: o.adpProbability,
                colorScheme: o.colorScheme,
                showLabels: o.showLabels,
                atoms: o.atoms,
                bonds: o.bonds,
                cell: o.cell,
                axes: o.axes
            });
        }
        function test_per_structure_appearance() {
            Session.project.currentStructureIndex = 0;
            setAppearance(true);
            const first = appearance();
            Session.project.currentStructureIndex = 1;
            setAppearance(false);
            const second = appearance();
            verify(first !== second, "The two structures have independently chosen nondefault appearances");
            Session.project.currentStructureIndex = 0;
            compare(appearance(), first, "Selecting another structure does not overwrite the first appearance");
            const editor = openText(Session.project.currentStructure);
            verify(/(?:appearance|atom_view|atom_scale)/i.test(editor.text), "The structure's appearance is visible in its Text tab");
            verify(Session.save(), "The normal save persists per-structure appearance");
            Session.closeProject();
            verify(Session.openProject(proof.project()), "The normal reader reopens the saved appearances");
            const initiallyShown = appearance();
            Session.project.currentStructureIndex = 1;
            compare(appearance(), second, "The second structure's full appearance survives reopen");
            Session.project.currentStructureIndex = 0;
            compare(appearance(), first, "Reselecting the first structure restores its saved appearance");
            compare(initiallyShown, first, "The first structure's full appearance survives reopen before any reselection");
        }
        function test_scattering_lengths_save_only_user_overrides() {
            Session.project.currentStructureIndex = 0;
            const lengths = Session.project.currentStructure.scatteringLengths;
            compare(lengths.count, 0, "Built-in scattering tables create no user override rows");
            lengths.append();
            verify(lengths.setTypeSymbol(0, "Li"), "The override witness chooses an actual element");
            verify(lengths.setLengthFm(0, 12.3456), "The override witness supplies a nondefault value in femtometres");
            verify(Session.save(), "The normal project save persists user scattering overrides");
            Session.closeProject();
            verify(Session.openProject(proof.project()), "The ordinary reader reopens the saved scattering override");
            const rows = Probe.rows(Session.project.currentStructure.scatteringLengths);
            compare(rows.length, 1, "Only the one user override is written rather than the built-in table");
            compare(rows[0].typeSymbol, "Li", "The override retains its declared element");
            compare(rows[0].lengthFm, 12.3456, "The user override survives save and reopen in femtometres");
            Session.project.currentStructureIndex = 1;
            compare(Session.project.currentStructure.scatteringLengths.count, 0, "A scattering override belongs only to its structure");
        }
        function test_exact_classic_archive_opens_and_saves() {
            const archive = proof.classicArchive();
            verify(archive.toString() !== "", "An independent classic writer creates the exact-count archive");
            compare(proof.archiveMembers(archive).length, 65535, "The independent archive really has the exact classic file count");
            Session.closeProject();
            verify(Session.openProject(archive), "A classic ZIP with exactly 65535 files is a valid project archive: " + Session.lastError);
            verify(Session.save(), "The normally opened classic-limit archive saves to its location");
            Session.closeProject();
            verify(Session.openProject(archive), "The saved classic-limit project archive reopens");
            compare(Session.project.structures.count, 2, "The count boundary preserves both structures through save and reopen");
        }
        function test_report_is_written_inside_opened_zip() {
            const archive = proof.classicArchive(12);
            Session.closeProject();
            verify(Session.openProject(archive), "The report witness opens an independently written ZIP project");
            const report = Session.project.report;
            report.writesHtml = true;
            report.writesPdf = false;
            tab = exportFactory.createObject(parent, {
                report: report
            });
            verify(tab !== null, "The production report Export group loads for the ZIP project");
            reportSaved.target = report;
            reportSaved.clear();
            const save = findChild(tab, "report.save");
            verify(save !== null, "The actual Save report action is available");
            click(save);
            tryCompare(reportSaved, "count", 1, 5000, "Save report publishes a finished report");
            const members = proof.archiveMembers(archive);
            verify(members.some(name => /^reports\/.+\.html$/.test(name)), "Save report rewrites the opened ZIP with its HTML under reports");
            Session.closeProject();
            verify(Session.openProject(archive), "The ZIP project still opens after report publication");
        }
        function test_report_asks_for_location_data() {
            return [
                {
                    tag: "bundled",
                    readonlyZip: false
                },
                {
                    tag: "readonly-zip",
                    readonlyZip: true
                }
            ];
        }
        function test_report_asks_for_location(data) {
            Session.closeProject();
            if (data.readonlyZip) {
                const archive = proof.classicArchive(12);
                verify(proof.readOnlyArchive(archive), "The report witness removes write permission from its ZIP");
                verify(Session.openProject(archive), "A read-only ZIP still opens for viewing");
            } else {
                verify(Session.openExample("pd-neut-cwl_lbco-hrpt"), "The report witness opens a real bundled example");
            }
            const report = Session.project.report;
            report.writesHtml = true;
            report.writesPdf = false;
            tab = exportFactory.createObject(parent, {
                report: report
            });
            verify(tab !== null, "The real Export group opens for a project without a writable destination");
            saveAsAsked.clear();
            reportSaved.target = report;
            reportSaved.clear();
            click(findChild(tab, "report.save"));
            tryCompare(saveAsAsked, "count", 1, 5000, "Save report asks for a location when the opened source cannot be rewritten");
            compare(reportSaved.count, 0, "Reports are not published at an unchosen substitute location");
        }
    }
}
