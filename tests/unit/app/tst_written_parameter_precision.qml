// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import EasyApplication.Gui.Style as Style

Item {
    id: surface
    width: 1000
    height: 500
    TextMetrics {
        id: ink
    }
    Component {
        id: cellFactory
        ParameterCell { x: 40; y: 50; width: 360; height: 40 }
    }
    Component {
        id: fieldFactory
        ParameterField { x: 40; y: 130; width: 360; height: 40; label: "" }
    }
    TestCase {
        id: test
        name: "WrittenParameterPrecision"
        when: windowShown

        function init() {
            failOnWarning(/.*/);
            Session.closeProject();
        }
        function cleanup() {
            Session.closeProject();
        }
        function cases() {
            // Existing independent Decimal/IUCr references, never formatter output.
            const references = JSON.parse(Probe.readFile("tests/fixtures/uncertainty_display/expected.json"));
            const integers = references.integers;
            const rows = [];
            for (const rule of ["iucr_19", "iucr_99"]) {
                for (const ref of integers[rule])
                    rows.push({tag: rule + "-" + ref.token, rule, token: ref.token,
                        value: ref.value, su: ref.su, hasSu: true, free: true,
                        written: Number(ref.value_text), scientific: ref.value_scientific});
                const decimals = references.rules[rule].filter(ref => ref.su > 0).slice(0, 3);
                const negative = references.rules[rule].find(ref => ref.su > 0 && ref.value < 0);
                verify(negative !== undefined, "The independent decimal matrix includes a negative positive-SU witness");
                decimals.push(negative);
                for (const ref of decimals)
                    rows.push({tag: rule + "-decimal-" + ref.token, rule, token: ref.token,
                        value: ref.value, su: ref.su, hasSu: true, free: true,
                        written: Number(ref.value_text), scientific: ref.value_scientific});
                // 100000 -> 1.0e5 under either rule: last place 1e4, so 2.290e7.
                for (const sign of [1, -1])
                    rows.push({tag: rule + "-signed-owner-" + sign, rule,
                        token: (sign < 0 ? "-" : "") + "22900000(100000)",
                        value: sign * 22900000, su: 100000, hasSu: true, free: true,
                        written: sign * 22900000,
                        scientific: (sign < 0 ? "-" : "") + "2.290e7"});
                // Native EDI bare fixed values adopt engaged zero; () is absent/free.
                for (const optional of ["", "()", "(0)"])
                    rows.push({tag: rule + "-optional-" + (optional || "fixed"), rule,
                        token: "0.0001234" + optional, value: 0.0001234, su: 0,
                        hasSu: optional !== "()", free: optional !== "",
                        written: 0.0001234, scientific: "1.234e-4"});
                rows.push({tag: rule + "-six-digit-save", rule, token: "12345678.9()",
                    value: 12345678.9, su: 0, hasSu: false, free: true,
                    written: 12345700, scientific: "1.23457e7"});
                rows.push({tag: rule + "-zero", rule, token: "0(0)",
                    value: 0, su: 0, hasSu: true, free: true,
                    written: 0, scientific: "0"});
                rows.push({tag: rule + "-exponent-input", rule,
                    token: "2.29e7", value: 22900000, su: 0,
                    hasSu: true, free: false, written: 22900000, scientific: "2.29e7"});
            }
            return rows;
        }
        function open(ref) {
            const directory = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/table_display"));
            const file = "experiments/experiment.edi";
            const original = SettingsProof.text(directory, file);
            const anchor = "1 20.25 22900000(100000)";
            compare(original.split(anchor).length, 2, "The independent input has exactly one addressed background parameter");
            verify(SettingsProof.write(directory, file, original.replace(anchor, "1 20.25 " + ref.token)), "The ordinary parser receives the independently supplied parameter token");
            const project = SettingsProof.text(directory, "project.edi");
            verify(!project.includes("_su_format.rule"), "The independent project has no conflicting uncertainty declaration");
            verify(SettingsProof.write(directory, "project.edi", project + "\n_su_format.rule " + ref.rule + "\n"), "The project rule is an ordinary file input before opening");
            verify(Session.openProject(directory), "The written precision input opens normally: " + Session.lastError);
            const parameter = Probe.rows(Session.project.parameters).map(row => row.parameter).find(item => item.category === "background" && item.name === "intensity" && item.rowLabel === "1");
            verify(parameter !== undefined, "The normal registry supplies the exact authored background row");
            compare(parameter.value, ref.value, "The real typed item retains the independently supplied core value");
            compare(parameter.uncertainty, ref.su, "The real typed item retains the supplied numerical uncertainty");
            compare(parameter.hasUncertainty, ref.hasSu, "Optional uncertainty presence is distinct from numerical zero");
            compare(parameter.free, ref.free, "The normal parser retains the supplied free flag");
            verify(parameter.fileValue !== "", "The tested item has a genuine canonical written spelling");
            compare(Number(parameter.fileValue), ref.written, "The published file spelling has the independent Decimal/save meaning");
            if (ref.su > 0) {
                verify(parameter.fileSu !== "", "A positive supplied SU retains its canonical written uncertainty");
                compare(Number(parameter.fileSu), ref.su, "The written uncertainty retains the independently supplied rounded meaning");
            }
            compare(Session.project.suRule, ref.rule, "The native project owns the requested uncertainty rule");
            compare(Session.project.modified, false, "Rendering starts from an unedited loaded project");
            return {item: parameter, directory, file, source: SettingsProof.text(directory, file)};
        }
        function state(item) {
            return JSON.stringify({value: item.value, su: item.uncertainty,
                hasSu: item.hasUncertainty, free: item.free,
                fileValue: item.fileValue, fileSu: item.fileSu});
        }
        function test_same_pair_wide_narrow_and_back_data() {
            return cases();
        }
        function test_same_pair_wide_narrow_and_back(ref) {
            const loaded = open(ref), item = loaded.item;
            const before = state(item);
            const controls = [createTemporaryObject(cellFactory, surface, {item}),
                              createTemporaryObject(fieldFactory, surface, {item})];
            for (const control of controls) {
                verify(control !== null && control.item === item, "Both supported consumers hold the same original typed parameter");
                for (const width of [360, 1, 360, 1, 360]) {
                    const narrow = width === 1;
                    control.width = narrow ? control.leftPadding + control.rightPadding + 1 : width;
                    verify(waitForPolish(control), "Each real width transition completes the existing layout gate");
                    const room = control.width - control.leftPadding - control.rightPadding;
                    ink.font = control.font;
                    ink.text = item.fileValue;
                    const fullInk = ink.advanceWidth;
                    console.log("WRITTEN_PRECISION " + JSON.stringify({tag: ref.tag,
                        consumer: control === controls[0] ? "cell" : "field",
                        width: control.width, requestedStep: width, fullInk,
                        text: control.text, canonical: item.fileValue, su: item.fileSu,
                        hasSu: item.hasUncertainty, free: item.free,
                        contentWidth: control.contentWidth,
                        room: control.width - control.leftPadding - control.rightPadding}));
                    if (narrow) {
                        compare(room, 1, "Both actual consumers receive the same authored positive content room");
                        verify(fullInk > room, "The independently measured complete canonical token genuinely exceeds its positive narrow viewport");
                    } else {
                        verify(room >= fullInk, "The original wide viewport genuinely fits the complete canonical token");
                    }
                    const expected = narrow ? ref.scientific : item.fileValue;
                    tryCompare(control, "text", expected, 2000, "Actual displayed text retains the file pair's own digits at each width");
                    verify(!String(control.text).includes("…"), "Numeric display never substitutes an ellipsis");
                    compare(control.editText, item.fileValue, "The full canonical editing token survives every display-only resize");
                    compare(state(item), before, "Narrow display never mutates the real scientific value, SU, free flag or file pair");
                    compare(control.item, item, "Resizing cannot substitute another parameter owner");
                }
            }
            compare(controls[0].text, controls[1].text, "Cell and standalone field agree again at the same wide size");
            compare(SettingsProof.text(loaded.directory, loaded.file), loaded.source, "Display-only transitions never rewrite the source file");
            compare(Session.project.modified, false, "Display-only precision conversion cannot make the project dirty");
        }
        function test_nonpositive_room_keeps_canonical_then_recovers_data() {
            return [{tag: "cell", component: cellFactory}, {tag: "field", component: fieldFactory}];
        }
        function test_nonpositive_room_keeps_canonical_then_recovers(data) {
            const ref = cases().find(row => row.tag === "iucr_99-signed-owner-1");
            verify(ref !== undefined, "The allocation guard uses the independent positive-SU written pair");
            const loaded = open(ref), item = loaded.item, before = state(item);
            const control = createTemporaryObject(data.component, surface, {item});
            verify(control !== null && waitForPolish(control), "The guard exercise retains an actual typed production consumer");
            verify(!control.activeFocus, "The allocation guard is observed outside an active manual editor");
            verify(item.fileValue !== ref.scientific, "Canonical and narrow literals genuinely distinguish the guard and conversion branches");
            for (const requestedRoom of [0, -1, 1, 0, -1, 1]) {
                control.width = control.leftPadding + control.rightPadding + requestedRoom;
                verify(waitForPolish(control), "Each allocation transition completes the existing layout gate");
                const room = control.width - control.leftPadding - control.rightPadding;
                ink.font = control.font;
                ink.text = item.fileValue;
                console.log("WRITTEN_PRECISION_ALLOCATION " + JSON.stringify({
                    consumer: data.tag, requestedRoom, room, width: control.width,
                    text: control.text, canonical: item.fileValue,
                    fullInk: ink.advanceWidth, state: before}));
                compare(room, requestedRoom, "The real control reaches the authored zero, negative or positive content allocation");
                verify(ink.advanceWidth > room, "The canonical token exceeds the allocation independently of the formatter under test");
                tryCompare(control, "text", requestedRoom > 0 ? ref.scientific : item.fileValue, 2000,
                    "Nonpositive allocation preserves canonical text and return to positive room activates the independent narrow literal");
                compare(control.editText, item.fileValue, "Allocation guards preserve the complete canonical editing token");
                compare(state(item), before, "Allocation transitions cannot mutate the original value, SU presence or free flag");
                compare(control.item, item, "Allocation transitions retain the original typed owner");
                verify(!String(control.text).includes("…"), "Unallocated and narrow text never substitute an ellipsis");
            }
            control.width = 360;
            verify(waitForPolish(control), "The existing wide allocation returns through ordinary layout");
            ink.font = control.font;
            ink.text = item.fileValue;
            verify(control.width - control.leftPadding - control.rightPadding >= ink.advanceWidth,
                "The returned original wide viewport independently fits the complete token");
            tryCompare(control, "text", item.fileValue, 2000, "Returning wide restores the complete canonical token");
            compare(state(item), before, "The guard exercise leaves the scientific and canonical pair exact");
            compare(SettingsProof.text(loaded.directory, loaded.file), loaded.source, "Allocation guards cannot rewrite the original source file");
            compare(Session.project.modified, false, "Allocation guards cannot make the original project dirty");
        }
        function test_fit_digits_preserves_full_token() {
            const ref = cases().find(row => row.tag === "iucr_99-120000(2.0)");
            verify(ref !== undefined, "The fitDigits witness uses an independently specified seven-digit written integer");
            const loaded = open(ref), item = loaded.item, before = state(item);
            const cell = createTemporaryObject(cellFactory, surface, {item, fitDigits: true});
            verify(cell !== null && waitForPolish(cell), "The real fitDigits consumer completes wide layout");
            ink.font = cell.font;
            ink.text = item.fileValue;
            const narrowWidth = Math.ceil(ink.advanceWidth / 2) + cell.leftPadding + cell.rightPadding;
            verify(narrowWidth < cell.width, "Independent text metrics require a real font-fitting transition");
            const wideSize = cell.font.pixelSize;
            cell.width = narrowWidth;
            verify(waitForPolish(cell), "The existing font-fitting layout completes at the narrower size");
            compare(cell.text, item.fileValue, "fitDigits keeps the entire canonical token rather than retargeting its precision");
            verify(cell.font.pixelSize < wideSize, "fitDigits actually reduces the live font when the supplied full token needs it");
            verify(cell.contentWidth <= cell.width - cell.leftPadding - cell.rightPadding + 1, "The complete live text fits the independently chosen available room");
            cell.width = 360;
            verify(waitForPolish(cell), "Returning to the wide cell completes the ordinary layout gate");
            compare(cell.font.pixelSize, wideSize, "The same cell restores its original full-size font");
            compare(state(item), before, "Font fitting preserves the original scientific and canonical state");
        }
        function test_noop_and_manual_draft_data() {
            return [{tag: "cell", component: cellFactory}, {tag: "field", component: fieldFactory}];
        }
        function test_noop_and_manual_draft(data) {
            const ref = cases().find(row => row.tag === "iucr_99-signed-owner-1");
            const loaded = open(ref), item = loaded.item, before = state(item);
            const control = createTemporaryObject(data.component, surface, {item});
            verify(control !== null && waitForPolish(control), "The actual editable consumer lays out before pointer and keyboard input");
            mouseClick(control, control.width / 2, control.height / 2);
            tryCompare(control, "activeFocus", true, 2000, "A real click admits editing on the original parameter consumer");
            tryCompare(control, "text", item.fileValue, 2000, "Editing exposes every canonical digit");
            verify(SettingsProof.key(control, Qt.Key_Return), "No-op editing commits through an actual window key event");
            compare(state(item), before, "Accepting an untouched full token writes no scientific value or uncertainty");
            compare(Session.project.modified, false, "No-op acceptance cannot dirty the original project");
            mouseClick(control, control.width / 2, control.height / 2);
            tryCompare(control, "activeFocus", true, 2000, "The same live consumer admits a genuine manual draft");
            verify(SettingsProof.type(control, "9.125"), "Actual key events supply an uncommitted numerical draft");
            compare(control.text, "9.125", "The real input contains the manual draft");
            control.width = 80;
            verify(waitForPolish(control), "A width change during editing completes without bypassing the input owner");
            compare(control.text, "9.125", "Display fitting cannot erase or reformat a live manual draft");
            compare(state(item), before, "A draft is not a scientific commit");
            verify(SettingsProof.key(control, Qt.Key_Escape), "The original input receives a real cancel key");
            compare(state(item), before, "Cancelling the manual draft retains the exact original pair and free flag");
            compare(Session.project.modified, false, "Cancelled manual input leaves the project unmodified");
            compare(SettingsProof.text(loaded.directory, loaded.file), loaded.source, "No-op and cancelled drafts cannot rewrite the project file");
        }
    }
}
