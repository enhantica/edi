// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtQuick.Shapes
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import OnboardingAcceptance 1.0
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render
import "TutorialGeometry.js" as Geometry
import "TutorialStates.js" as States
import "ExampleProjects.js" as Examples
import EasyApplication.Gui.Style as Style

TestCase {
    id: test
    name: "TutorialNavigation"
    when: windowShown
    property var app
    property var panel
    property var chooser
    property var popupButton
    property bool tourLogOpen: false
    property bool tourFitStarted: false
    Connections {
        target: Session.project ? Session.project.fit : null
        function onRunningChanged() {
            if (test.panel && test.panel.tutorial && test.panel.tutorial.id === "interface" && Session.project.fit.running)
                test.tourFitStarted = true;
        }
    }
    FontMetrics {
        id: chevronMetrics
    }
    property int clockTicks: 0
    Timer {
        id: sentinel
        interval: 100
        repeat: true
        onTriggered: ++test.clockTicks
    }
    SignalSpy {
        id: clicked
        signalName: "clicked"
    }
    Component {
        id: application
        Main {}
    }
    function objects(root) {
        const owned = Probe.objectsWithProperty(root, "objectName");
        // List delegates belong to the visual tree, not necessarily the popup's
        // QObject ownership tree after the Examples-row reuse.
        for (const item of Render.descendants(root.contentItem || root))
            if (!owned.includes(item))
                owned.push(item);
        return owned;
    }
    function one(root, name) {
        const found = objects(root).filter(item => item.objectName === name);
        compare(found.length, 1, "The actual tutorial exposes exactly one control named " + name);
        return found[0];
    }
    function init() {
        Session.closeProject();
        tourFitStarted = false;
        Preferences.engineThreads = 1;
        app = application.createObject(null);
        verify(app !== null, "Tutorial navigation uses the real application window");
        app.width = 1200;
        app.height = 800;
        AppState.open(AppState.Page.Home);
        verify(waitForRendering(app.contentItem), "The Home entry point is rendered before tutorial input");
        panel = one(app, "tutorial");
        chooser = one(app, "tutorials");
    }
    function cleanup() {
        sentinel.stop();
        lessonWalking = false;
        if (tourLogOpen)
            OnboardingProbe.finishHostLog();
        tourLogOpen = false;
        OnboardingProbe.stopClock();
        clicked.target = null;
        if (panel && panel.visible)
            panel.stop();
        Session.closeProject();
        if (app)
            app.destroy();
        app = null;
        panel = null;
        chooser = null;
    }
    function press(item, why) {
        tryVerify(() => item.visible && item.enabled && Ui.exposed(item), 2000, "The real tutorial action is exposed and enabled: " + why);
        verify(waitForPolish(item), "Tutorial input follows its control's layout: " + why);
        app.update();
        clicked.target = item;
        clicked.clear();
        verify(clicked.valid, "Tutorial navigation uses a button's real clicked signal: " + why);
        const point = Ui.clickPoint(item);
        verify(point !== null, "Tutorial input stays in the visible control rectangle: " + why);
        mouseClick(item, point.x, point.y);
        compare(clicked.count, 1, "One user click reaches the real tutorial action: " + why);
        settleTour();
    }
    function settleTour() {
        OnboardingProbe.advanceClock(1000);
        OnboardingProbe.advanceClock(1000);
        verify(waitForPolish(app), "The tutorial's injected transition clock settles before ordinary input checks");
    }
    function clickTutorialRow(row, fraction) {
        verify(waitForPolish(row), "The tutorial row finishes layout before pointer input");
        verify(Ui.exposed(row) && row.enabled, "The actual tutorial row is exposed and enabled");
        mouseClick(row, row.width * fraction, row.height / 2, Qt.LeftButton, Qt.NoModifier, 0);
    }
    function hoverTreatment(row) {
        mouseMove(app.contentItem, 1, 1, 0);
        OnboardingProbe.advanceClock(1000);
        app.update();
        verify(waitForRendering(row), "The unhovered Examples-style row is rendered");
        const before = grabImage(row);
        mouseMove(row, row.width * 0.85, row.height / 2, 0);
        OnboardingProbe.advanceClock(1000);
        app.update();
        verify(waitForRendering(row), "The actual pointer hover is rendered on the row");
        const after = grabImage(row);
        verify(!before.equals(after), "Pointer hover visibly highlights an actionable row");
        const areas = Probe.objectsWithProperty(row, "cursorShape");
        verify(areas.some(item => item.cursorShape === Qt.PointingHandCursor && (item.containsMouse || item.hovered)), "The hovered row shows the same pointing-hand cursor as Examples");
    }
    function start(id) {
        const links = Probe.objectsWithProperty(app, "text").filter(item => item.visible && item.text === "Tutorials" && typeof item.clicked === "function");
        compare(links.length, 1, "The tour starts through the Home Tutorials link");
        // The injected clock completes popup transitions without waiting for wall time.
        OnboardingProbe.startClock();
        press(links[0], "Home Tutorials");
        OnboardingProbe.advanceClock(1000);
        tryCompare(chooser, "opened", true, 2000, "Home opens the real Tutorials chooser");
        popupButton = chooser.standardButton(Dialog.Close);
        verify(popupButton !== null && popupButton.flat, "The popup supplies the independent light-button component reference");
        clickTutorialRow(one(chooser, "tutorials.row." + id), 0.5);
        OnboardingProbe.advanceClock(1000);
        settleTour();
        tryCompare(chooser, "visible", false, 2000, "The chooser closes before tutorial navigation");
        tryCompare(panel, "opened", true, 2000, "The selected tutorial opens before navigation");
    }
    function progress(number, total) {
        tryVerify(() => {
            OnboardingProbe.advanceClock(16);
            OnboardingProbe.incubate(app);
            return one(panel, "tutorial.progress").text === "Step " + number + " of " + total;
        }, 5000, "Every actual navigation input publishes the requested step and total after its injected transition");
    }
    function next(number, total) {
        press(one(panel, "tutorial.next"), "Next at step " + (number - 1));
        progress(number, total);
    }
    function tourSteps() {
        // The script is content under test, never a source for expected geometry or behavior.
        const entries = scripts();
        const tour = entries.find(entry => entry.id === "interface");
        verify(tour && tour.steps.length > 1, "The Interface tour has a nonempty sequence of written controls");
        return tour.steps;
    }
    function reach(index) {
        verify(Session.openProject(SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"))), "A populated real project exposes every workflow control for callout placement");
        AppState.open(AppState.Page.Home);
        start("interface");
        const steps = tourSteps();
        verify(index < steps.length, "The requested tour step exists in the shipped script");
        for (let n = 1; n <= index; ++n)
            next(n + 1, steps.length);
        finishPages();
        verify(waitForPolish(app), "The callout and target finish their layout before scene measurement");
        return steps[index];
    }
    function finishPages() {
        tryVerify(() => {
            // Spend each readiness poll incubating real pages, rather than adding
            // a timer gap after every small incubation slice.
            for (let slice = 0; slice < 10 && app.pagesBuilt !== app.pagesWanted; ++slice)
                OnboardingProbe.incubate(app);
            return app.pagesBuilt === app.pagesWanted;
        }, 5000, "The actual asynchronous workflow pages finish incubating before tutorial state is checked");
    }
    function target(name) {
        const matches = Render.descendants(Ui.windowRoot(app)).filter(item => item.objectName === name && Ui.rendered(item));
        compare(matches.length, 1, "A visible named target is measured independently of the tour locator: " + name);
        return matches[0];
    }
    function targetRows() {
        return tourSteps().map((step, index) => ({
                    tag: String(index + 1) + "-" + step.target,
                    index: index
                }));
    }
    function test_callout_is_next_to_its_named_control_data() {
        return targetRows();
    }
    function test_callout_is_next_to_its_named_control(data) {
        const step = reach(data.index);
        for (const size of [[1200, 800], [1440, 1000]]) {
            app.width = size[0];
            app.height = size[1];
            verify(waitForPolish(app), "Callout placement responds to the actual resized window");
            if (mainAreaStep(step)) {
                pageAreaCallout(step);
                continue;
            }
            const item = target(step.target), body = panel.background;
            const bodyBox = test.bodyBox(), targetBox = Geometry.rect(item, app.contentItem);
            const gap = Geometry.distance(bodyBox, targetBox);
            verify(Geometry.overlap(bodyBox, targetBox) <= 0.05 * Math.min(bodyBox.width * bodyBox.height, targetBox.width * targetBox.height), "An adjacent callout does not obscure the control it explains");
            verify(gap <= 2 * one(panel, "tutorial.text").font.pixelSize, "A callout is within two text heights of its named control, not fixed in a window corner: " + step.target + " gap=" + gap);
        }
    }
    function test_pointer_faces_and_reaches_the_named_control_data() {
        return targetRows();
    }
    function bodyBox() {
        const origin = panel.contentItem.mapToItem(app.contentItem, -panel.leftPadding, -panel.topPadding);
        return {
            x: origin.x,
            y: origin.y,
            width: panel.width,
            height: panel.height
        };
    }
    function outline() {
        const shapes = Render.descendants(panel.background).filter(item => OnboardingProbe.inheritsType(item, "QQuickShape"));
        compare(shapes.length, 1, "The box and pointer are painted by one shape item");
        const shape = shapes[0], paths = Array.from(shape.data).filter(item => item.fillColor !== undefined && item.strokeColor !== undefined);
        compare(paths.length, 1, "The callout has exactly one filled and stroked outline, without a triangle seam");
        compare(shape.preferredRendererType, Shape.CurveRenderer, "The single callout outline uses Qt's smooth curve renderer");
        compare(paths[0].strokeWidth, 1, "The callout uses the agreed one-pixel border");
        compare(paths[0].fillColor.a, 1, "The callout background colour is fully opaque");
        compare(shape.opacity, 1, "The single shape does not make its opaque background translucent");
        return {
            shape: shape,
            path: paths[0]
        };
    }
    function paintedPointer(expectAbsent = false) {
        const surface = outline().shape, body = bodyBox();
        verify(waitForRendering(surface), "The single callout outline is rendered before silhouette measurement");
        const painted = grabImage(surface), opacity = surface.opacity;
        surface.opacity = 0;
        verify(waitForRendering(app.contentItem), "The pointer observer captures the actual underlying scene");
        const baseline = grabImage(surface);
        surface.opacity = opacity;
        const bounds = Geometry.rect(surface, app.contentItem), sx = painted.width / surface.width, sy = painted.height / surface.height;
        let left = painted.width, right = -1, top = painted.height, bottom = -1;
        for (let y = 0; y < painted.height; ++y) {
            for (let x = 0; x < painted.width; ++x) {
                const px = bounds.x + x / sx, py = bounds.y + y / sy;
                const margin = expectAbsent ? 2 : 0;
                if (px >= body.x - margin && px < body.x + body.width + margin && py >= body.y - margin && py < body.y + body.height + margin)
                    continue;
                if (painted.pixel(x, y) === baseline.pixel(x, y))
                    continue;
                left = Math.min(left, x);
                right = Math.max(right, x);
                top = Math.min(top, y);
                bottom = Math.max(bottom, y);
            }
        }
        if (expectAbsent) {
            verify(right < left && bottom < top, "A whole-page instruction paints no pointer toward empty space");
            return null;
        }
        verify(right > left && bottom > top, "The one outline paints a real pointer outside its box");
        const box = {
            x: bounds.x + left / sx,
            y: bounds.y + top / sy,
            width: (right - left + 1) / sx,
            height: (bottom - top + 1) / sy
        };
        const a = Geometry.center(box), b = Geometry.center(body), horizontal = Math.abs(a.x - b.x) / body.width > Math.abs(a.y - b.y) / body.height;
        const positive = horizontal ? a.x > b.x : a.y > b.y;
        function crop(image) {
            return {
                width: right - left + 1,
                height: bottom - top + 1,
                pixel: (x, y) => image.pixel(left + x, top + y)
            };
        }
        verify(Geometry.pointerTapers(crop(painted), crop(baseline), horizontal, positive), "The single outline's painted pointer tapers toward the control");
        return {
            box: box,
            intersects: target => {
                for (let y = top; y <= bottom; ++y)
                    for (let x = left; x <= right; ++x) {
                        const px = bounds.x + x / sx, py = bounds.y + y / sy;
                        if (px >= target.x && px < target.x + target.width && py >= target.y && py < target.y + target.height && painted.pixel(x, y) !== baseline.pixel(x, y))
                            return true;
                    }
                return false;
            },
            tip: {
                x: horizontal ? (positive ? box.x + box.width : box.x) : a.x,
                y: horizontal ? a.y : (positive ? box.y + box.height : box.y)
            }
        };
    }
    function test_pointer_faces_and_reaches_the_named_control(data) {
        const step = reach(data.index);
        if (mainAreaStep(step)) {
            pageAreaCallout(step);
            return;
        }
        const pointer = paintedPointer(), targetBox = Geometry.rect(target(step.target), app.contentItem);
        verify(Geometry.distance(pointer.box, bodyBox()) <= 3, "The actual pointer joins the callout boundary");
        verify(Geometry.pointDistance(pointer.tip, targetBox) <= 2 * one(panel, "tutorial.text").font.pixelSize, "The painted pointer reaches toward the actual named control");
    }
    function test_callout_is_one_opaque_curve_outline() {
        reach(1);
        paintedPointer();
        verify(!objects(app).some(item => item.objectName === "tutorial.pointer" && OnboardingProbe.inheritsType(item, "QQuickShape") && item !== outline().shape), "No separately painted triangle remains under the single outline");
    }
    function plainCalloutIcon(button, state) {
        // The icon belongs to contentItem. Only its background subtree is chrome.
        for (const item of Render.descendants(button.background)) {
            let opacity = 1;
            for (let parent = item; parent; parent = parent.parent)
                opacity *= parent.opacity;
            if (!Ui.rendered(item) || opacity <= 0)
                continue;
            verify(item.color === undefined || item.color.a === 0, "Callout navigation has no background fill in its " + state + " state");
            verify(item.border === undefined || item.border.width === 0 || item.border.color.a === 0, "Callout navigation has no painted border in its " + state + " state");
            verify(item.fillColor === undefined || item.fillColor.a === 0, "Callout navigation has no shape fill in its " + state + " state");
            verify(item.strokeColor === undefined || item.strokeWidth === 0 || item.strokeColor.a === 0, "Callout navigation has no shape outline in its " + state + " state");
            verify(item.source === undefined || String(item.source) === "", "Callout navigation does not substitute an image for its forbidden background");
        }
    }
    function test_navigation_uses_icon_buttons_with_tooltips() {
        start("interface");
        const reference = one(app, "appBar.button.preferences");
        const symbols = {
            back: /chevron.*left|angle.*left/,
            next: /chevron.*right|angle.*right/,
            stop: /^(x|xmark|times|close)$/
        };
        for (const action of ["back", "next", "stop"]) {
            const button = one(panel, "tutorial." + action);
            verify(button.visible && button.text === "", "Tour actions are visible icon buttons without text labels: " + action);
            verify(symbols[action].test(button.fontIcon), "Tour navigation paints its close or directional chevron icon: " + action);
            compare(button.ToolTip.text || button.toolTip, action[0].toUpperCase() + action.slice(1), "Every tour icon has its exact action tooltip");
            compare(button.Accessible.role, reference.Accessible.role, "Tour icons retain the app icon button's accessible role");
            plainCalloutIcon(button, button.enabled ? "normal" : "disabled");
            if (button.enabled) {
                mouseMove(button, button.width / 2, button.height / 2, 0);
                settleTour();
                verify(button.hovered, "The no-background witness reaches the icon's actual hovered state");
                plainCalloutIcon(button, "hovered");
                mousePress(button, button.width / 2, button.height / 2, Qt.LeftButton, Qt.NoModifier, 0);
                settleTour();
                verify(button.pressed, "The no-border witness reaches the icon's actual pressed state");
                plainCalloutIcon(button, "pressed");
                // Release outside the control so this style witness cannot navigate.
                mouseMove(app.contentItem, 1, 1, 0);
                mouseRelease(app.contentItem, 1, 1, Qt.LeftButton, Qt.NoModifier, 0);
            }
            mouseMove(app.contentItem, 1, 1, 0);
            settleTour();
        }
        const back = Geometry.rect(one(panel, "tutorial.back"), panel.contentItem), forward = Geometry.rect(one(panel, "tutorial.next"), panel.contentItem), stop = Geometry.rect(one(panel, "tutorial.stop"), panel.contentItem);
        verify(stop.x < back.x && back.x < forward.x && Math.abs(stop.y - forward.y) <= 1, "Stop, Back and Next share one bottom row in that order");
        const stopGap = back.x - stop.x - stop.width, nextGap = forward.x - back.x - back.width;
        verify(stopGap >= 0 && nextGap >= 0, "The callout navigation buttons do not overlap");
        fuzzyCompare(stopGap, nextGap, 1, "The callout uses equal Stop/Back and Back/Next gaps");
        verify(Math.abs(forward.x + forward.width - panel.contentItem.width) <= 1, "The callout's navigation group is aligned at the bottom right");
        const total = tourSteps().length;
        next(2, total);
        press(one(panel, "tutorial.back"), "Back");
        progress(1, total);
        press(one(panel, "tutorial.stop"), "Stop");
        tryCompare(panel, "visible", false, 2000, "The Stop icon actually ends the tour");
    }
    function test_arrow_keys_navigate_and_escape_stops() {
        start("interface");
        const total = tourSteps().length;
        keyClick(Qt.Key_Right, Qt.NoModifier, 0);
        progress(2, total);
        keyClick(Qt.Key_Left, Qt.NoModifier, 0);
        progress(1, total);
        keyClick(Qt.Key_Escape, Qt.NoModifier, 0);
        tryCompare(panel, "visible", false, 2000, "Escape stops the tour through actual keyboard input");
        verify(!Session.hasProjectSetAside, "Escape also releases the tour's temporary-project ownership");
    }
    function test_progress_is_at_the_step_title_right() {
        start("simulation");
        const steps = scripts().find(entry => entry.id === "simulation").steps;
        next(2, steps.length);
        const title = one(panel, "tutorial.title"), progressLabel = one(panel, "tutorial.progress");
        compare(title.text, steps[1].title, "The callout paints the current step's own title");
        const a = Geometry.rect(title, panel.contentItem), b = Geometry.rect(progressLabel, panel.contentItem);
        verify(Math.abs(Geometry.center(a).y - Geometry.center(b).y) <= 1 && b.x >= a.x + a.width, "Step N of M shares the title row to its right");
        const available = progressLabel.width - (progressLabel.leftPadding || 0) - (progressLabel.rightPadding || 0);
        const inset = progressLabel.horizontalAlignment === Text.AlignRight ? available - progressLabel.contentWidth : progressLabel.horizontalAlignment === Text.AlignHCenter ? (available - progressLabel.contentWidth) / 2 : 0;
        const textRight = progressLabel.mapToItem(panel.contentItem, (progressLabel.leftPadding || 0) + inset + progressLabel.contentWidth, 0).x;
        verify(Math.abs(textRight - panel.contentItem.width) <= 1, "Progress text ends at the title row's trailing edge regardless of the label's anchoring strategy");
    }
    function test_invisible_target_has_an_explained_panel_fallback() {
        reach(0);
        const item = target(tourSteps()[0].target);
        const visible = item.visible;
        item.visible = false; // Accident: the target becomes unavailable while its step is open.
        tryVerify(() => /not (?:currently )?visible|not (?:currently )?(?:on screen|shown)|unavailable|cannot (?:be )?(?:shown|found)/i.test(Ui.text(panel.contentItem)), 2000, "An invisible target explains why this step is shown at the panel fallback");
        const rect = Geometry.rect(panel.background, app.contentItem);
        const em = one(panel, "tutorial.text").font.pixelSize;
        verify(rect.x <= 2 * em && Math.abs(app.contentItem.height - rect.y - rect.height) <= 5 * em, "An unavailable target uses the bottom-left panel fallback instead of a stale target position");
        verify(!objects(app).some(object => object.objectName === "tutorial.pointer" && Ui.rendered(object)), "An unavailable target never retains a misleading pointer");
        item.visible = visible;
    }
    function test_elapsed_time_never_advances_the_tour_data() {
        return targetRows();
    }
    function test_elapsed_time_never_advances_the_tour(data) {
        reach(data.index);
        const total = tourSteps().length;
        OnboardingProbe.startClock();
        clockTicks = 0;
        sentinel.start();
        OnboardingProbe.advanceClock(60000);
        verify(clockTicks > 0, "The injected clock actually fires QML timers during the no-auto-advance witness");
        progress(data.index + 1, total);
        sentinel.stop();
        OnboardingProbe.stopClock();
        if (data.index + 1 < total)
            next(data.index + 2, total);
    }
    function test_tour_visits_every_workflow_page() {
        reach(0);
        const total = tourSteps().length, visited = new Set();
        for (let index = 0; index < total; ++index) {
            progress(index + 1, total);
            visited.add(app.appBarCentralTabs.currentIndex);
            if (index + 1 < total)
                next(index + 2, total);
        }
        for (const page of [AppState.Page.Home, AppState.Page.Project, AppState.Page.Structure, AppState.Page.Experiment, AppState.Page.Analysis, AppState.Page.Report])
            verify(visited.has(page), "The Interface tour visits every workflow page instead of describing all of them from Home: " + page);
    }
    function noStateHint() {
        const text = Ui.text(panel.contentItem);
        verify(!/You should see/i.test(text), "Callouts never display the former proactive expected-state line");
        verify(!/Not yet:/i.test(text), "Next performs an action instead of ever displaying an unmet-state hint");
    }
    function test_tour_omits_expected_state_lines_data() {
        return targetRows();
    }
    function test_tour_omits_expected_state_lines(data) {
        reach(data.index);
        noStateHint();
    }
    function test_lesson_starts_without_a_state_hint_data() {
        return ["simulation", "fitting"].map(id => ({
                    tag: id,
                    tutorial: id
                }));
    }
    function test_lesson_starts_without_a_state_hint(data) {
        start(data.tutorial);
        finishPages();
        noStateHint();
    }
    function test_next_alone_performs_every_lesson_action_data() {
        return ["simulation", "fitting"].map(id => ({
                    tag: id,
                    tutorial: id
                }));
    }
    function assertActionResult(step, prior, fits) {
        // The script enumerates the exercised input, never supplies a boolean oracle.
        // Expected physical values below come from the written lessons and saved example.
        const p = Session.project, target = step.target, check = step.check || "";
        if (target === "home.start") {
            compare(app.appBarCentralTabs.currentIndex, AppState.Page.Project, "Next performs Home Start before advancing");
            compare(p, null, "Home Start does not silently create the learner's project");
        } else if (target === "project.create") {
            const dialog = SettingsProof.creationDialog(app);
            verify(dialog !== null && dialog.visible, "Next opens the actual Create dialog before the name step");
        } else if (target === "createProject.name") {
            verify(p !== null && p !== prior.project, "Next on Create makes a new tutorial-owned project");
            compare(p.name, "lbco", "Next creates the named lbco tutorial project");
            compare(Probe.rows(p.structures).length, 0, "The newly created project has no preloaded structure");
            compare(Probe.rows(p.experiments).length, 0, "The newly created project has no preloaded experiment");
        } else if (check.startsWith("structure:") || /structures\.(create|load)$/.test(target)) {
            verify(p && p.currentStructure && p.currentStructure.name === "lbco", "Next creates or loads the actual lbco structure");
            if (target === "structures.load") {
                const input = OnboardingProbe.sourceText("docs/user/cli/pd-neut-cwl_lbco-hrpt/project/structures/lbco.edi");
                const number = value => Number(value.replace(/\([^)]*\)$/, ""));
                for (const pair of [["length_a", "lengthA"], ["length_b", "lengthB"], ["length_c", "lengthC"], ["angle_alpha", "angleAlpha"], ["angle_beta", "angleBeta"], ["angle_gamma", "angleGamma"]]) {
                    const line = input.split(/\r?\n/).find(line => line.startsWith("_cell." + pair[0] + " "));
                    verify(line !== undefined, "The independent example supplies every imported cell value");
                    compare(p.currentStructure.cell[pair[1]].value, number(line.trim().split(/\s+/)[1]), "Next imports the CIF cell before any fitting can change it");
                }
                const sourceAtoms = input.split(/\r?\n/).filter(line => /^(La|Ba|Co|O)\s/.test(line)).map(line => line.trim().split(/\s+/));
                const atoms = Probe.rows(p.currentStructure.atomSites), adps = Probe.rows(p.currentStructure.atomSiteAdps);
                compare(atoms.length, sourceAtoms.length, "Next imports all atoms from the example's original CIF");
                for (const row of sourceAtoms) {
                    const atom = atoms.find(item => item.label === row[0]), adp = adps.find(item => item.label === row[0]);
                    verify(atom !== undefined && adp !== undefined, "Next imports each source atom and displacement");
                    for (const pair of [["fractX", 2], ["fractY", 3], ["fractZ", 4], ["occupancy", 6]])
                        compare(atom[pair[0]].value, number(row[pair[1]]), "The loaded CIF preserves every source position and occupancy");
                    compare(adp.adpIso.value, number(row[7]), "The loaded CIF preserves every source Biso before fitting");
                }
            }
        } else if (check.startsWith("space-group:")) {
            compare(p.currentStructure.spaceGroup.itNumber, 221, "Next establishes the lesson's cubic space group 221");
        } else if (check.startsWith("cell-a:")) {
            for (const value of [p.currentStructure.cell.lengthA, p.currentStructure.cell.lengthB, p.currentStructure.cell.lengthC])
                compare(value.value, 3.89, "Next establishes all three cubic lengths at 3.89 angstroms");
        } else if (check.startsWith("atom-sites:")) {
            const sites = Probe.rows(p.currentStructure.atomSites), expected = [["La", 0, 0, 0, 0.5], ["Ba", 0, 0, 0, 0.5], ["Co", 0.5, 0.5, 0.5, 1], ["O", 0, 0.5, 0.5, 1]];
            compare(sites.length, 4, "Next creates every atom site in the written structure");
            for (const atom of expected) {
                const site = sites.find(row => row.label === atom[0]);
                verify(site !== undefined, "Next creates the declared atom label: " + atom[0]);
                ["fractX", "fractY", "fractZ", "occupancy"].forEach((role, index) => compare(site[role].value, atom[index + 1], "Next preserves each written atom coordinate and occupancy"));
            }
        } else if (target === "experiments.create" || check === "experiment") {
            compare(Probe.rows(p.experiments).length, prior.experiments + 1, "Next adds the actual experiment once");
        } else if (check.startsWith("experiment-type:")) {
            compare(p.currentExperiment.sampleFormToken, "powder", "The tutorial establishes a powder sample");
            compare(p.currentExperiment.radiationProbeToken, "neutron", "The tutorial establishes neutron radiation");
            compare(p.currentExperiment.beamModeToken, "constant wavelength", "The tutorial establishes constant wavelength");
        } else if (check.startsWith("wavelength:")) {
            const row = Probe.rows(p.currentExperiment.instrument).find(row => row.parameter && row.parameter.name === "setup_wavelength");
            verify(row !== undefined && row.parameter.value === 1.494, "Next sets the lesson wavelength to 1.494 angstroms");
        } else if (check === "linked-structure") {
            verify(Probe.rows(p.currentExperiment.linkedStructures).some(row => row.structureId === "lbco"), "The actual experiment links the lesson's lbco structure");
        } else if (check.startsWith("background-estimate:")) {
            compare(p.currentExperiment.backgroundEstimateMode, "auto", "Next selects automatic background estimation");
        } else if (target === "background.estimate" || check === "background-points") {
            verify(Probe.rows(p.currentExperiment.background).length > 1, "Next estimates actual background points");
        } else if (check === "constraint") {
            const ba = Probe.rows(p.currentStructure.atomSiteAdps).find(row => row.label === "Ba");
            verify(Probe.rows(p.analysis.constraints).length > 0 && ba && !ba.adpIso.free, "Next establishes the dependent Ba displacement constraint");
        } else if (target === "statusBar.fit.button" || check.startsWith("fits:")) {
            verify(p.fit.canUndo && p.fit.outcome !== "failed" && fits > prior.fits, "Next runs and completes a real fit before advancing");
        } else if (check === "all-free") {
            verify(Probe.rows(p.parameters).filter(row => row.parameter && row.parameter.fittable).every(row => row.parameter.free), "Next frees the actual fittable parameters");
        } else if (target.startsWith("group.")) {
            compare(prior.control.collapsed, false, "Next explicitly unfolds the named group");
        } else if (target.includes(".tab.")) {
            verify(prior.control.checked, "Next explicitly selects the named tab");
        } else if (check) {
            fail("Every new action contract needs an independent post-action state witness: " + target + " / " + check);
        }
    }
    property int lessonFitStarts: 0
    property bool lessonWalking: false
    property bool lessonOpenedFileDialog: false
    Connections {
        target: Session.project ? Session.project.fit : null
        function onRunningChanged() {
            if (test.lessonWalking && Session.project.fit.running)
                ++test.lessonFitStarts;
        }
    }
    Timer {
        interval: 1
        repeat: true
        running: test.lessonWalking
        onTriggered: {
            if (SettingsProof.projectFileDialogs(test.app, true).length || Probe.objectsWithProperty(test.app, "selectedFile").some(item => item.visible))
                test.lessonOpenedFileDialog = true;
        }
    }
    function lessonWavelength() {
        const experiment = Session.project.currentExperiment;
        verify(experiment !== null, "The wavelength lesson uses the experiment created during the walk");
        const row = Probe.rows(experiment.instrument).find(row => row.parameter && row.parameter.name === "setup_wavelength");
        verify(row !== undefined, "The actual constant-wavelength instrument has a wavelength");
        return row.parameter.value;
    }
    function test_next_alone_performs_every_lesson_action(data) {
        // Accident: a first-time learner uses Next for every instruction, including
        // Create and file imports, instead of knowing which underlying control to use.
        start(data.tutorial);
        const steps = scripts().find(entry => entry.id === data.tutorial).steps;
        compare(steps[0].target, "home.start", "The Next-only lesson starts at Home Start");
        lessonFitStarts = 0;
        lessonOpenedFileDialog = false;
        lessonWalking = true;
        let wavelengthChanged = false;
        for (let index = 0; index + 1 < steps.length; ++index) {
            progress(index + 1, steps.length);
            finishPages();
            noStateHint();
            const p = Session.project, step = steps[index];
            const prior = {
                project: p,
                experiments: p ? Probe.rows(p.experiments).length : 0,
                fits: lessonFitStarts,
                control: Ui.control(Probe, app, step.target)
            };
            if (step.target === "createProject.name") {
                const dialog = SettingsProof.creationDialog(app);
                verify(dialog !== null && dialog.visible, "The tutorial names its own scratch project");
                dialog.projectParentDirectory = String(SettingsProof.emptyDirectory());
            }
            const wavelengthStep = step.target === "instrument.setup_wavelength";
            if (wavelengthStep)
                compare(lessonWavelength(), 1, "The new experiment starts at one angstrom before the HRPT lesson changes it");
            press(one(panel, "tutorial.next"), "Next-only lesson step " + (index + 1));
            tryVerify(() => {
                OnboardingProbe.advanceClock(16);
                return panel.step === index + 1;
            }, 15000, "One Next performs the written action and advances exactly one step");
            if (Session.project) {
                tryCompare(Session.project.fit, "running", false, 15000, "A Next-started fit completes in the actual worker");
                tryCompare(Session.project, "calculating", false, 15000, "Next's model changes finish calculating before their state is checked");
            }
            assertActionResult(step, prior, lessonFitStarts);
            if (wavelengthStep) {
                compare(lessonWavelength(), 1.494, "Next sets the actual HRPT instrument wavelength");
                wavelengthChanged = true;
            }
            noStateHint();
            verify(!lessonOpenedFileDialog, "A Next-only tutorial never opens a file chooser, even transiently");
        }
        progress(steps.length, steps.length);
        lessonWalking = false;
        verify(wavelengthChanged, "The completed lesson teaches the learner to change the wavelength");
        const project = Session.project;
        verify(project && project.currentStructure && project.currentExperiment, "Next alone reaches a real structure and experiment at the last step");
        compare(project.currentStructure.name, "lbco", "The completed lesson contains lbco rather than an unrelated prepared structure");
        const pattern = Probe.rows(project.currentExperiment.pattern);
        verify(pattern.some(row => Number.isFinite(row.intensityCalc) && row.intensityCalc > 0), "Next alone produces a real calculated pattern");
        if (data.tutorial === "fitting") {
            compare(project.name, "lbco", "The fitting Next-only walk creates project lbco");
            const lines = OnboardingProbe.sourceText("tests/fixtures/background_estimate/meas-lbco-hrpt.xye").trim().split(/\r?\n/).filter(line => /^\s*[+\-\d.]/.test(line));
            compare(pattern.length, lines.length, "Next imports every point from the independent HRPT source");
            for (let i = 0; i < lines.length; ++i) {
                const values = lines[i].trim().split(/\s+/).map(Number);
                compare(pattern[i].intensityMeas, values[1], "Every measured ordinate comes from hrpt.xye");
            }
            verify(lessonFitStarts >= 2, "Next alone executes both required fitting stages");
            const pin = JSON.parse(OnboardingProbe.sourceText("docs/user/cli/pd-neut-cwl_lbco-hrpt/expected.json")).quantities.reduced_chi_square;
            const match = /_fit_result\.reduced_chi_square\s+(\S+)/.exec(project.analysis.text.text);
            verify(match !== null, "Next-only fitting publishes its reduced chi-square");
            const tolerance = pin.tol_abs === null ? Math.abs(pin.value) * pin.tol_rel : pin.tol_abs;
            verify(Math.abs(Number(match[1]) - pin.value) <= tolerance, "Next-only fitting reaches the example's existing regression tolerance");
        }
    }
    function test_next_advances_after_each_stated_state_data() {
        return ["interface", "simulation"].map(id => ({
                    tag: id,
                    tutorial: id
                }));
    }
    function test_next_advances_after_each_stated_state(data) {
        if (data.tutorial === "interface") {
            verify(Session.openProject(SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"))), "A populated user project makes every Interface tour state available");
            AppState.open(AppState.Page.Home);
        }
        start(data.tutorial);
        const steps = scripts().find(entry => entry.id === data.tutorial).steps;
        const total = steps.length;
        for (let index = 0; index < total; ++index) {
            progress(index + 1, total);
            establishWrittenState(data.tutorial, index, steps);
            noStateHint();
            // No assignment to panel.step and no call to next(): only actual user input.
            if (index + 1 < total) {
                if (panel.step === index)
                    next(index + 2, total);
                else
                    progress(index + 2, total);
            }
        }
    }
    function test_tour_preserves_the_set_aside_project_data() {
        return ["stop", "finish"].map(ending => ({
                    tag: ending,
                    ending: ending
                }));
    }
    function test_tour_preserves_the_set_aside_project(data) {
        // Accident: inspecting the interface while a saved project has unsaved work.
        verify(Session.openProject(SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"))), "The tour accident starts with a saved user project");
        tryCompare(Session.project, "calculating", false, 5000, "The user project is ready before the tour accident");
        Session.project.description = "unsaved work before inspecting the interface";
        OnboardingProbe.rememberProject(Session.project);
        const path = Session.project.path, location = Session.projectLocation, needsSaveAs = Session.needsSaveAs;
        const folder = Session.projectDirectoryUrl(path);
        const bytes = JSON.stringify(SettingsProof.projectFolderBytes(folder));
        AppState.open(AppState.Page.Home);
        start("interface");
        verify(!OnboardingProbe.isRemembered(Session.project), "The Interface tour opens its own temporary project, never the user's project");
        verify(OnboardingProbe.rememberedAlive(), "Entering the tour keeps the user's actual project alive");
        verify(Session.project.path !== path, "The tour's LBCO example has its own backing directory");
        compare(Session.project.currentStructure.name, "lbco", "The Interface tour opens the LBCO example so workflow pages are available");
        verify(Probe.rows(Session.project.experiments).length > 0, "The tour's LBCO example includes an experiment");
        if (data.ending === "finish") {
            const steps = tourSteps();
            for (let index = 1; index < steps.length; ++index)
                next(index + 1, steps.length);
            press(one(panel, "tutorial.discard"), "Finish the Interface tour and return to the user project");
        } else {
            press(one(panel, "tutorial.stop"), "Stop inspecting the interface");
        }
        tryCompare(panel, "visible", false, 2000, "Stop and Finish both end the Interface tour");
        verify(OnboardingProbe.isRemembered(Session.project), "Stop and Finish restore the exact user's set-aside object");
        compare(Session.project.description, "unsaved work before inspecting the interface", "The user's unsaved edits survive the whole Interface tour");
        verify(Session.project.modified, "The tour never saves the user's unsaved changes");
        compare(Session.project.path, path, "The tour never moves the user's backing directory");
        compare(Session.projectLocation, location, "The tour preserves the user's original save destination");
        compare(Session.needsSaveAs, needsSaveAs, "The tour preserves Save versus Save as behavior");
        compare(JSON.stringify(SettingsProof.projectFolderBytes(folder)), bytes, "The tour never changes any bytes in the user's project directory");
    }
    function test_every_page_tab_and_group_has_an_anchored_tour_step_data() {
        const rows = [];
        for (const page of ["project", "structure", "experiment", "analysis", "report"])
            for (const kind of ["appbar", "main", "sidebar", "groups"])
                rows.push({
                    tag: page + "-" + kind,
                    page: page,
                    kind: kind
                });
        return rows;
    }
    function test_every_page_tab_and_group_has_an_anchored_tour_step(data) {
        // Independent census: discover the actual UI before opening the tour.
        // The script is only the candidate being checked against that census.
        // App-bar tabs exist before a project; the tour must supply its own
        // example to enable and open them. Inner-page census needs the model.
        if (data.kind !== "appbar")
            verify(Examples.bundled(test, Session, "pd-neut-cwl_lbco-hrpt"), "The tab census uses the real bundled LBCO example");
        finishPages();
        const pageIndex = {
            project: AppState.Page.Project,
            structure: AppState.Page.Structure,
            experiment: AppState.Page.Experiment,
            analysis: AppState.Page.Analysis,
            report: AppState.Page.Report
        }[data.page];
        AppState.open(pageIndex);
        verify(waitForPolish(app), "The independent workflow census follows page layout");
        const page = Ui.page(app), names = [];
        if (data.kind === "appbar") {
            names.push("appBar.tab." + data.page);
        } else if (data.kind === "main") {
            for (const tab of Render.descendants(page))
                if (tab.objectName.startsWith("mainArea." + data.page + ".tab.") && tab.visible && (tab.enabled || /^(Stacked|Map)$/.test(tab.text)))
                    names.push(tab.objectName);
            verify(names.length > 0, "Every non-Home workflow page exposes main-view tabs to explain");
        } else {
            for (const suffix of ["basic", "extras", "text", "settings"]) {
                const name = "sideBar.tab." + suffix;
                const tab = one(page, name);
                if (data.kind === "sidebar") {
                    if (tab.enabled)
                        names.push(name);
                } else if (tab.enabled) {
                    Ui.click(test, Probe, app, name);
                    for (const group of Render.descendants(page))
                        if (group.objectName.startsWith("group.") && Ui.inPane(Ui.target(group)) && !names.includes(group.objectName))
                            names.push(group.objectName);
                }
            }
        }
        verify(names.length > 0, "The real page contributes a nonempty tab or key-group census: " + data.page + " " + data.kind);
        const steps = tourSteps();
        const indices = names.map(name => {
            const found = steps.findIndex(step => step.page === data.page && step.target === name);
            verify(found >= 0, "Every actual page tab and key group has its own written tour step: " + data.page + " " + name);
            return found;
        }).sort((a, b) => a - b);
        AppState.open(AppState.Page.Home);
        start("interface");
        let current = 0;
        for (const index of indices) {
            while (current < index) {
                next(current + 2, steps.length);
                ++current;
            }
            finishPages();
            compare(app.appBarCentralTabs.currentIndex, pageIndex, "A tour step opens the workflow page it describes");
            const item = target(steps[index].target);
            if (steps[index].target.includes(".tab.") && item.enabled)
                verify(item.checked, "The tour actually opens the available tab it explains: " + steps[index].target);
            const anchor = Ui.target(item);
            verify(Ui.rendered(anchor), "The described tab or group header is visible beside its callout");
            verify(Geometry.distance(Geometry.rect(panel.background, app.contentItem), Geometry.rect(anchor, app.contentItem)) <= 2 * one(panel, "tutorial.text").font.pixelSize, "Every tab and key-group callout is beside its own visible control");
            if (mainAreaStep(steps[index]))
                pageAreaCallout(steps[index]);
            else
                paintedPointer();
        }
    }
    function scripts() {
        const entries = JSON.parse(OnboardingProbe.sourceText("app/tutorials/manifest.json")).tutorials;
        for (const entry of entries) {
            if (!entry.steps && entry.tour) {
                const pages = JSON.parse(OnboardingProbe.sourceText("app/tutorials/" + entry.tour)).pages;
                entry.steps = pages.reduce((steps, page) => steps.concat(page.steps.map(step => Object.assign({}, step, {
                            page: page.page
                        }))), []);
            }
        }
        return entries;
    }
    function lessonRows(fieldsOnly = false) {
        const rows = [];
        for (const tutorial of scripts().filter(entry => fieldsOnly || entry.id !== "interface")) {
            tutorial.steps.forEach((step, index) => {
                if (/^(appBar|workflow|mainArea|statusBar|group|sideBar)\./.test(step.target) || /freeHeader$/.test(step.target))
                    return;
                if (fieldsOnly && /\.(create|append|estimate|clearFilters|apply)$/.test(step.target))
                    return;
                rows.push({
                    tag: tutorial.id + "-" + (index + 1),
                    tutorial: tutorial.id,
                    index: index
                });
            });
        }
        return rows;
    }
    function prepareLessonProject(id) {
        if (Session.project === null) {
            Ui.click(test, Probe, app, "home.start");
            tryCompare(app.appBarCentralTabs, "currentIndex", AppState.Page.Project, 2000, "The geometry setup follows the learner's Home Start action");
            createLessonProject("placement_" + id);
        }
        if (Probe.rows(Session.project.structures).length === 0)
            verify(Session.project.loadStructure(Probe.repoUrl("tests/fixtures/onboarding/simulation-structure.edi")), "Placement setup supplies the independently authored LBCO structure");
        if (Probe.rows(Session.project.experiments).length === 0) {
            verify(Session.project.createExperiment(), "Placement setup supplies a real experiment");
            if (id === "fitting")
                verify(Session.project.loadDataInto(Session.project.currentExperiment, Probe.repoUrl("tests/fixtures/background_estimate/meas-lbco-hrpt.xye")), "Fitting placement setup loads the independently vendored measured input");
            else
                Session.project.currentExperiment.setRange(10, 80, 0.25);
        }
    }
    function isolateLessonStep(data) {
        // Placement and predecessor checks isolate a script step in the real host.
        // Sequential user navigation has its own gate; this does not pretend to replay it.
        start(data.tutorial);
        prepareLessonProject(data.tutorial);
        finishPages();
        panel.step = data.index;
        panel.show();
        settleTour();
        finishPages();
        verify(waitForPolish(app), "The isolated script step and its actual workflow page finish layout");
        return scripts().find(entry => entry.id === data.tutorial).steps;
    }
    function discoverStepControl(step) {
        tryVerify(() => !Ui.moving(app.contentItem), 2000, "The script page finishes entering the viewport before target discovery");
        const page = Ui.page(app);
        const outside = /^(appBar|workflow|mainArea|statusBar)\./.test(step.target);
        if (outside) {
            const item = Ui.find(Ui.windowRoot(app), step.target, true);
            verify(item !== null, "The page or global target exists before field discovery: " + step.target);
            return {
                item: item,
                tab: ""
            };
        }
        for (const suffix of ["basic", "extras", "text", "settings"]) {
            const tab = one(page, "sideBar.tab." + suffix);
            if (!tab.enabled)
                continue;
            // Census setup only. Placement assertions never use this to claim reveal.
            Ui.click(test, Probe, app, tab.objectName);
            verify(waitForPolish(app), "The target census instantiates the selected tab's real controls");
            const found = Ui.find(page, step.target, true);
            if (found) {
                const groups = [];
                for (let parent = found.parent; parent; parent = parent.parent)
                    if (parent.objectName.startsWith("group.") && parent.collapsible)
                        groups.unshift(parent);
                for (const group of groups)
                    Ui.expandGroup(test, Probe, app, group.objectName);
                Ui.scrollIntoView(found);
                verify(waitForPolish(app), "The discovered control finishes expansion and scrolling before input");
                return {
                    item: found,
                    tab: tab.objectName
                };
            }
        }
        const matches = Render.descendants(Ui.windowRoot(app)).filter(item => item.objectName === step.target && Ui.rendered(item));
        verify(matches.length > 0, "Every written lesson target resolves in its actual project: " + step.target);
        return {
            item: matches[0],
            tab: ""
        };
    }
    function test_field_has_an_explicit_group_and_tab_predecessor_data() {
        return lessonRows();
    }
    function test_field_has_an_explicit_group_and_tab_predecessor(data) {
        const steps = isolateLessonStep(data), step = steps[data.index];
        const found = discoverStepControl(step);
        let group = found.item.parent;
        while (group && !group.objectName.startsWith("group."))
            group = group.parent;
        if (!group || !group.collapsible)
            return; // This step describes a page/tab, not a field in a closed group.
        const earlier = steps.slice(0, data.index);
        const headerIndex = earlier.findIndex(item => item.page === step.page && item.target === group.objectName);
        verify(headerIndex >= 0, "Every grouped field has an earlier explicit open-group step; silent reveal cannot replace instruction: " + step.target + " in " + group.objectName);
        if (found.tab && found.tab !== "sideBar.tab.basic")
            verify(earlier.some(item => item.page === step.page && item.target === found.tab), "A field in another sidebar tab has an explicit preceding tab-switch step: " + step.target);
        // Accident: a learner reaches a group that starts closed.
        group.collapsed = true;
        panel.step = headerIndex;
        panel.show();
        settleTour();
        verify(waitForPolish(app), "The explicit open-group callout is laid out before the learner acts");
        verify(group.collapsed, "The explicit open-group step leaves the opening action to the learner");
        verify(Ui.rendered(group.titleArea), "The opening step exposes the actual group header");
        verify(Geometry.distance(Geometry.rect(panel.background, app.contentItem), Geometry.rect(group.titleArea, app.contentItem)) <= 2 * one(panel, "tutorial.text").font.pixelSize, "The explicit opening callout points beside the group's header");
        Ui.click(test, Probe, app, group.objectName);
        tryCompare(group, "collapsed", false, 2000, "The learner's actual header click completes the open-group state");
        tryVerify(() => panel.step > headerIndex, 2000, "An explicit group-opening action advances once the learner opens the group");
    }
    function test_field_pointer_aims_at_the_input_center_data() {
        return lessonRows(true);
    }
    function test_field_pointer_aims_at_the_input_center(data) {
        // Class: label-wrapper anchoring aims above the actual editable control.
        // The independent scene rectangle excludes the title even when the
        // production locator resolves a titled field wrapper.
        const step = scripts().find(entry => entry.id === data.tutorial).steps[data.index];
        if (/^(appBar|workflow|mainArea|statusBar)\./.test(step.target))
            return; // A page or global description is not an input-field target.
        const steps = isolateLessonStep(data), found = discoverStepControl(steps[data.index]);
        const inputs = Render.descendants(found.item).filter(item => item.background && (typeof item.selectAll === "function" || item.popup !== undefined));
        if (!inputs.length)
            return; // The rule applies to fields and combo boxes, not page descriptions.
        const input = inputs[0], surface = input.background;
        Ui.scrollIntoView(input);
        panel.step = data.index;
        panel.show();
        settleTour();
        verify(waitForPolish(app), "The pointer and the actual input finish layout before geometry is measured");
        verify(Ui.rendered(surface), "The target input surface is actually visible");
        const pointer = paintedPointer(), field = Geometry.rect(input, app.contentItem);
        verify(Math.abs(pointer.tip.y - Geometry.center(field).y) <= 1, "The single outline's tip aligns with the input's vertical centre, excluding its title");
        verify(Geometry.pointDistance(pointer.tip, field) <= 2 * one(panel, "tutorial.text").font.pixelSize, "The centred pointer reaches the actual input rather than a different row");
    }

    function relativeLuminance(c) {
        const linear = value => value <= 0.04045 ? value / 12.92 : Math.pow((value + 0.055) / 1.055, 2.4);
        return 0.2126 * linear(c.r) + 0.7152 * linear(c.g) + 0.0722 * linear(c.b);
    }
    function test_callout_uses_readable_opaque_accent_blue_data() {
        return ["light", "dark"].map(theme => ({
                    tag: theme,
                    theme: theme
                }));
    }
    function test_callout_uses_readable_opaque_accent_blue(data) {
        const saved = Style.Colors.theme;
        try {
            Style.Colors.theme = data.theme === "light" ? Style.Colors.LightTheme : Style.Colors.DarkTheme;
            start("interface");
            const rendered = outline(), body = rendered.shape;
            verify(waitForRendering(body), "The single callout shape is painted in the selected theme");
            const fill = rendered.path.fillColor, border = rendered.path.strokeColor, accent = Style.Colors.themeAccent;
            compare(fill.a, 1, "The callout uses a fully opaque background in both themes");
            for (const color of [fill, border]) {
                verify(color.b > color.r && color.b >= color.g, "The callout's fill and border are visibly blue, not neutral grey");
                const hueGap = Math.abs(color.hslHue - accent.hslHue);
                verify(Math.min(hueGap, 1 - hueGap) <= 0.04, "The blue callout palette derives its hue from the application accent");
            }
            verify(rendered.path.strokeWidth === 1 && border.a > 0, "The accent-blue border is actually drawn");
            verify(data.theme === "light" ? fill.hslLightness > 0.9 : fill.hslLightness < 0.5, "The light theme uses a light-blue surface and the dark theme a dark-blue tint");
            const labels = Render.texts(panel.contentItem).filter(item => Ui.rendered(item));
            verify(labels.length > 0, "Readable contrast is checked on actual rendered callout text");
            // Read each label's real background with only that label hidden, so
            // translucency is composited over the actual application scene.
            for (const label of labels) {
                const opacity = label.opacity;
                label.opacity = 0;
                verify(waitForRendering(app.contentItem), "The text contrast observer captures the composited background");
                const image = grabImage(app.contentItem), point = label.mapToItem(app.contentItem, label.width / 2, label.height / 2);
                const scale = image.width / app.contentItem.width;
                const background = image.pixel(Math.floor(point.x * scale), Math.floor(point.y * scale));
                label.opacity = opacity;
                let effective = label.color.a;
                for (let parent = label; parent; parent = parent.parent)
                    effective *= parent.opacity;
                const ink = Qt.rgba(label.color.r * effective + background.r * (1 - effective), label.color.g * effective + background.g * (1 - effective), label.color.b * effective + background.b * (1 - effective), 1);
                const a = relativeLuminance(ink), b = relativeLuminance(background);
                verify((Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05) >= 4.5, "Actual callout text retains the normal-text 4.5:1 readability contrast in both themes");
            }
        } finally {
            Style.Colors.theme = saved;
        }
    }
    function test_real_action_advances_without_next_data() {
        return [
            {
                tag: "create-experiment",
                tutorial: "simulation",
                target: "experiments.create"
            },
            {
                tag: "automatic-background",
                tutorial: "fitting",
                target: "background_estimate.mode"
            }
        ];
    }
    function test_real_action_advances_without_next(data) {
        start(data.tutorial);
        const steps = scripts().find(entry => entry.id === data.tutorial).steps;
        const index = steps.findIndex(step => step.target === data.target);
        verify(index >= 0, "The scientific tutorial includes the independently specified action: " + data.target);
        if (data.tutorial === "simulation") {
            verify(Session.project.loadStructure(Probe.repoUrl("tests/fixtures/onboarding/simulation-structure.edi")), "The experiment action starts with a real LBCO structure");
            compare(Probe.rows(Session.project.experiments).length, 0, "The Create action starts without an experiment");
        } else {
            prepareLessonProject("fitting");
            Session.project.currentExperiment.backgroundEstimateMode = "manual";
        }
        finishPages();
        // Isolate the action being tested, then use only the real UI input to
        // satisfy it. No Next or controller advancement follows that input.
        panel.step = index;
        panel.show();
        settleTour();
        finishPages();
        const found = discoverStepControl(steps[index]);
        Ui.scrollIntoView(found.item);
        if (data.tutorial === "simulation") {
            Ui.click(test, Probe, app, data.target);
            compare(Probe.rows(Session.project.experiments).length, 1, "The actual Create button creates the tutorial's experiment");
        } else {
            const combo = Render.descendants(found.item).find(item => item.popup !== undefined && typeof item.textAt === "function");
            verify(combo !== undefined, "The action gate operates the real background mode combo box");
            let automatic = -1;
            for (let row = 0; row < combo.count; ++row)
                if (/automatic|^auto$/i.test(combo.textAt(row)))
                    automatic = row;
            verify(automatic >= 0, "The real background combo offers the tutorial's Automatic choice");
            tryVerify(() => {
                Ui.scrollIntoView(combo);
                return Ui.exposed(combo);
            }, 2000, "The actual combo finishes its group expansion and scrolls into view before input");
            const point = Ui.clickPoint(combo);
            verify(point !== null, "The real background combo has an exposed input point");
            mouseClick(combo, point.x, point.y);
            tryCompare(combo.popup, "opened", true, 2000, "The user's input opens the actual background choices");
            keyClick(Qt.Key_Home);
            for (let row = 0; row < automatic; ++row)
                keyClick(Qt.Key_Down);
            keyClick(Qt.Key_Return);
            tryCompare(Session.project.currentExperiment, "backgroundEstimateMode", "auto", 2000, "Selecting the actual Automatic choice changes the tutorial's model");
        }
        tryVerify(() => panel.step > index, 2000, "A tutorial action advances when the user's action establishes its expected state, without another Next click");
    }
    function test_explanation_waits_for_next_data() {
        return ["interface", "simulation", "fitting"].map(id => ({
                    tag: id,
                    tutorial: id
                }));
    }
    function test_explanation_waits_for_next(data) {
        start(data.tutorial);
        const steps = scripts().find(entry => entry.id === data.tutorial).steps;
        let index = 0;
        if (data.tutorial !== "interface") {
            index = steps.findIndex(step => step.target === "experimentType");
            if (index < 0)
                index = steps.findIndex(step => step.target === "workflow.project.mainContent" && /this tutorial/i.test(step.text));
            verify(index >= 0, "Each scientific tutorial includes an explanation of its already available project or experiment type");
            prepareLessonProject(data.tutorial);
            panel.step = index;
            panel.show();
            settleTour();
        }
        OnboardingProbe.startClock();
        clockTicks = 0;
        sentinel.start();
        OnboardingProbe.advanceClock(60000);
        verify(clockTicks > 0, "The explanation timing witness actually advances the injected QML clock");
        progress(index + 1, steps.length);
        sentinel.stop();
        OnboardingProbe.stopClock();
        next(index + 2, steps.length);
    }
    function test_simulation_reaches_analysis_and_report_data() {
        return [
            {
                tag: "edit",
                page: "analysis",
                targets: ["parameters.list"]
            },
            {
                tag: "filter",
                page: "analysis",
                targets: ["parameters.nameFilter", "parameters.category", "parameters.datablock"]
            },
            {
                tag: "slider",
                page: "analysis",
                targets: ["parameters.slider"]
            },
            {
                tag: "report",
                page: "report",
                targets: ["workflow.report.mainContent", "mainArea.report.tab.report"]
            }
        ];
    }
    function test_simulation_reaches_analysis_and_report(data) {
        const steps = scripts().find(entry => entry.id === "simulation").steps;
        const index = steps.findIndex(step => step.page === data.page && data.targets.includes(step.target));
        verify(index >= 0, "Simulation continues with a written, targeted Analysis or Report step: " + data.tag);
        isolateLessonStep({
            tutorial: "simulation",
            index: index
        });
        const item = target(steps[index].target);
        verify(Geometry.distance(Geometry.rect(panel.background, app.contentItem), Geometry.rect(item, app.contentItem)) <= 2 * one(panel, "tutorial.text").font.pixelSize, "The Simulation continuation callout sits beside the actual Analysis or Report control");
        if (data.tag === "edit") {
            const rows = Probe.rows(item.sourceModel);
            const row = rows.findIndex(entry => entry.parameter && entry.parameter.name === "length_a");
            verify(row >= 0, "The simulation parameter table includes its real cell length");
            item.positionViewAtIndex(row, ListView.Contain);
            verify(waitForPolish(item), "The tutorial's selected parameter row is laid out before editing");
            const cell = Render.cells(item.itemAtIndex(row))[2];
            verify(cell !== undefined, "The tutorial table exposes the actual value editor");
            const before = Session.project.currentStructure.cell.lengthA.value, after = before + 0.125;
            Ui.scrollIntoView(cell);
            const point = Ui.clickPoint(cell);
            verify(point !== null, "The tutorial's cell value is reachable by real pointer input");
            mouseClick(cell, point.x, point.y);
            verify(SettingsProof.type(cell, String(after)), "The simulation lesson edits the table value through keyboard input");
            verify(SettingsProof.key(cell, Qt.Key_Return), "The simulation table commits the entered value through Return");
            tryCompare(Session.project.currentStructure.cell.lengthA, "value", after, 2000, "Editing the tutorial's table updates the same structure parameter shown on Structure");
            tryVerify(() => panel.step > index, 2000, "The simulation table-edit action advances when its state is achieved");
        } else if (data.tag === "filter") {
            // A real search is independent of any filter option labels/order.
            const field = target("parameters.nameFilter");
            const table = target("parameters.list"), before = table.count;
            Ui.scrollIntoView(field);
            const point = Ui.clickPoint(field);
            verify(point !== null, "The tutorial filter is reachable for real input");
            mouseClick(field, point.x, point.y);
            verify(SettingsProof.type(field, "length_a"), "The tutorial's name filter receives actual keyboard text");
            tryVerify(() => table.count > 0 && table.count < before, 2000, "The simulation tutorial's filter actually narrows the parameter table");
            tryVerify(() => panel.step > index, 2000, "The simulation filter action advances when its state is achieved");
        } else {
            const page = data.page === "analysis" ? AppState.Page.Analysis : AppState.Page.Report;
            compare(app.appBarCentralTabs.currentIndex, page, "The explanation opens the actual simulation Analysis or Report page");
        }
    }
    function test_parameter_status_splits_only_measured_projects_data() {
        return [
            {
                tag: "simulation",
                example: "pd-neut-cwl_lbco_simulation",
                measured: false
            },
            {
                tag: "measured",
                example: "pd-neut-cwl_lbco-hrpt",
                measured: true
            }
        ];
    }
    function test_parameter_status_splits_only_measured_projects(data) {
        verify(Examples.bundled(test, Session, data.example), "The status count uses an independent bundled simulation or measured example");
        verify(waitForPolish(app), "The status bar publishes its count without waiting for unrelated workflow pages");
        compare(Session.project.fit.measured, data.measured, "The status witness has the intended presence or absence of measured data");
        const status = target("statusBar.parameters");
        const text = status.valueText;
        if (!data.measured) {
            verify(/^\d+$/.test(text), "Without measured data Parameters displays only its count, never the free/fixed split");
            verify(Number(text) > 0, "A populated simulation displays a nonzero parameter count");
            verify(!/free|fixed/i.test(Ui.text(status)), "The rendered simulation status has no hidden free/fixed suffix");
        } else {
            const counts = /^(\d+) \((\d+) free, (\d+) fixed\)$/.exec(text);
            verify(counts !== null, "With measured data Parameters retains its total, free and fixed counts");
            compare(Number(counts[1]), Number(counts[2]) + Number(counts[3]), "The measured status count equals its free and fixed parts");
            verify(Number(counts[1]) > 0, "The measured example displays a nonempty parameter census");
        }
    }
    function establishWrittenState(id, index, steps) {
        const step = steps[index];
        if (step.target === "home.start") {
            Ui.click(test, Probe, app, "home.start");
            return;
        }
        if (step.target === "project.create") {
            createLessonProject("progress_" + id);
            return;
        }

        if (id === "interface") {
            States.satisfy(test, app, id, index, Session, AppState, Probe, step);
            return;
        }
        // Match the independently authored scientific state by its control, not
        // its old ordinal: explicit opening steps may be inserted anywhere.
        const science = id === "simulation" ? ["appBar.tab.structure", "structures.create", "spaceGroup.nameHM", "cell.length_a", "atomSites.append", "experiments.create", "experimentType", "instrument.setup_wavelength", "linkedStructure.append", "workflow.experiment.mainContent"] : ["workflow.project.mainContent", "constraints.append", "background_estimate.mode", "background.estimate", "parameters.freeHeader", "statusBar.fit.button", "background.estimate", "statusBar.fit.button", "mainArea.analysis.tab.fitting"];
        const occurrence = steps.slice(0, index + 1).filter(item => item.target === step.target).length;
        const indices = science.map((name, n) => name === step.target ? n : -1).filter(n => n >= 0);
        if (indices.length) {
            States.satisfy(test, app, id, indices[Math.min(occurrence, indices.length) - 1], Session, AppState, Probe, null);
            return;
        }
        finishPages();
        const control = Ui.control(Probe, app, step.target);
        verify(control !== null, "Every added written step exposes its actual control before user action: " + step.target);
        if (step.target.startsWith("group.")) {
            if (control.collapsed)
                Ui.click(test, Probe, app, step.target);
            tryCompare(control, "collapsed", false, 2000, "The explicit opening step's group is open before continuation");
        } else if (step.target.includes(".tab.")) {
            if (!control.checked && control.enabled)
                Ui.click(test, Probe, app, step.target);
            verify(control.checked || !control.enabled, "An explicit tab step opens the available tab it names");
        } else if (id === "simulation" && step.target === "parameters.list") {
            const rows = Probe.rows(control.sourceModel), row = rows.findIndex(entry => entry.parameter && entry.parameter.name === "length_a");
            verify(row >= 0, "The continuation's table exposes the simulation cell length");
            const value = rows[row].parameter.value + 0.125;
            verify(control.sourceModel.setText(row, "value", String(value)), "The continuation state is established through the actual parameter table edit path");
            compare(Session.project.currentStructure.cell.lengthA.value, value, "The continuation's edited value reaches the actual structure");
        } else if (id === "simulation" && step.target === "parameters.nameFilter") {
            verify(SettingsProof.type(control, "length_a"), "The continuation state is established by typing into the real filter");
        } else {
            verify(id === "simulation" && (step.target === "parameters.slider" || step.page === "report"), "Every nonexplanatory added step needs an independently authored real state setup: " + step.target);
        }
    }
    function filterControls(root) {
        const fields = Probe.objectsWithProperty(root, "placeholderText").filter(item => Ui.rendered(item) && typeof item.selectAll === "function");
        const combos = Probe.objectsWithProperty(root, "popup").filter(item => Ui.rendered(item) && typeof item.textAt === "function").sort((a, b) => a.mapToItem(app.contentItem, 0, 0).x - b.mapToItem(app.contentItem, 0, 0).x);
        compare(fields.length, 1, "The shared filter bar exposes one visible search field");
        compare(combos.length, 2, "The shared filter bar exposes category and value comboboxes");
        let component = fields[0].parent;
        while (component && !combos.every(combo => Render.descendants(component).includes(combo)))
            component = component.parent;
        verify(component !== null, "Search and both facet controls belong to one filter-bar component");
        return {
            search: fields[0],
            category: combos[0],
            value: combos[1],
            component: component
        };
    }
    function openTutorialFilters() {
        const home = Probe.objectsWithProperty(app, "text").find(item => item.text === "Tutorials" && Ui.rendered(item) && typeof item.clicked === "function");
        verify(home !== undefined, "Filters are reached through the actual Home Tutorials link");
        press(home, "Tutorials filters");
        tryCompare(chooser, "opened", true, 2000, "The Tutorials chooser opens before filter input");
        return filterControls(chooser);
    }
    function chooseFilter(combo, index) {
        press(combo, "Open the real filter choice");
        tryCompare(combo.popup, "opened", true, 2000, "The actual filter options are visible before selection");
        const label = combo.textAt(index);
        const items = Render.descendants(combo.popup.contentItem).filter(item => item.text === label && typeof item.clicked === "function" && Ui.rendered(item));
        // Bring an off-screen value into the actual popup viewport, not directly
        // into the model's selected property.
        if (!items.length) {
            const lists = Probe.objectsWithProperty(combo.popup, "contentY").filter(item => typeof item.positionViewAtIndex === "function");
            verify(lists.length > 0, "A long filter popup exposes its real scrollable option list");
            lists[0].positionViewAtIndex(index, ListView.Contain);
            verify(waitForPolish(lists[0]), "The desired filter choice scrolls into view");
        }
        const delegates = Render.descendants(combo.popup.contentItem).filter(item => item.text === label && typeof item.clicked === "function" && Ui.rendered(item));
        compare(delegates.length, 1, "Each filter value is painted and selectable, including its count");
        press(delegates[0], "Choose " + label);
        tryCompare(combo.popup, "visible", false, 2000, "Selecting the actual choice closes its popup");
    }
    function tutorialInput() {
        // Manifest titles/descriptions/tags are the filter INPUT, never the
        // implementation's output list, predicate, or computed counts.
        const entries = scripts();
        verify(entries.every(entry => Array.isArray(entry.tags)), "Every tutorial supplies the tags displayed and filtered by its catalogue");
        return entries;
    }
    function filteredIds() {
        const table = one(chooser, "tutorials.list"), ids = [];
        for (let n = 0; n < table.count; ++n) {
            table.positionViewAtIndex(n, ListView.Contain);
            verify(waitForPolish(table), "Filtered tutorial rows are instantiated before their identity is read");
            const row = table.itemAtIndex(n);
            verify(row !== null && row.objectName.startsWith("tutorials.row."), "Every filtered row keeps its tutorial identity");
            ids.push(row.objectName.slice("tutorials.row.".length));
        }
        return ids.sort();
    }
    function wantedTutorials(entries, query, category = "", value = "") {
        const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
        return entries.filter(entry => {
            const text = [entry.title, entry.description].concat(entry.tags.map(tag => tag.slice(tag.indexOf(":") + 1))).join(" ").toLowerCase();
            const values = entry.tags.filter(tag => tag.startsWith(category + ":")).map(tag => tag.slice(category.length + 1));
            return terms.every(term => text.includes(term)) && (!value || (value === "__unknown__" ? !values.length : values.includes(value)));
        }).map(entry => entry.id).sort();
    }
    function liveTarget(name) {
        const candidates = objects(app).filter(item => item.objectName === name && Ui.rendered(Ui.target(item)));
        compare(candidates.length, 1, "The written step resolves one currently visible control, including dialog fields");
        return candidates[0];
    }
    function controlInstructionEnabled(step) {
        // Class: an instruction asks for an action after its control is locked.
        if (!/\b(set|choose|keep)\b/i.test(step.text))
            return;
        const control = liveTarget(step.target);
        verify(control.enabled && control.interactionEnabled !== false, "A step asking to set, choose or keep its control shows it enabled: " + step.target);
        const inputs = Render.descendants(control).filter(item => Ui.rendered(item) && (typeof item.selectAll === "function" || typeof item.textAt === "function"));
        for (const input of inputs)
            verify(input.enabled, "Every visible input described by the instruction is enabled when shown");
    }
    function aboveDialog(dialog) {
        // Class: a tutorial callout is occluded by a later-opened modal surface.
        verify(dialog && dialog.visible && panel.visible, "A tutorial dialog and its guiding callout are both visible");
        verify(panel.opacity > 0.99 && panel.contentItem.opacity > 0.99, "The dialog's callout is fully visible after injected settling");
        const roots = [dialog.contentItem].concat(Probe.objectsWithProperty(dialog, "contentItem").map(item => item.contentItem)).filter(item => item && Ui.rendered(item));
        verify(roots.length > 0, "The actual open dialog exposes its rendered surface for stack inspection");
        const chain = item => {
            const result = [];
            for (; item; item = item.parent)
                result.unshift(item);
            return result;
        };
        const guide = chain(panel.contentItem);
        for (const root of roots) {
            const modal = chain(root);
            let split = 0;
            while (split < guide.length && split < modal.length && guide[split] === modal[split])
                ++split;
            verify(split > 0 && split < guide.length && split < modal.length, "The callout and modal are independently stacked in the actual rendered scene");
            const a = guide[split], b = modal[split], siblings = Array.from(guide[split - 1].children);
            verify(a.z > b.z || (a.z === b.z && siblings.indexOf(a) > siblings.indexOf(b)), "The callout paints above each open dialog, not under its modal layer");
        }
        // Compare the composed window with the callout's own subtree. A higher-z
        // claim alone cannot conceal another opaque item covering the callout.
        const root = panel.contentItem.parent;
        verify(waitForRendering(root) && waitForRendering(app.contentItem), "The modal and callout are painted before their actual compositing is inspected");
        const local = grabImage(root), screen = grabImage(app.contentItem), at = Geometry.rect(root, app.contentItem);
        let matched = 0, sampled = 0;
        for (let y = 5; y < root.height - 5; y += 7)
            for (let x = 5; x < root.width - 5; x += 7) {
                const sx = Math.round((at.x + x) * screen.width / app.contentItem.width), sy = Math.round((at.y + y) * screen.height / app.contentItem.height);
                if (sx < 0 || sy < 0 || sx >= screen.width || sy >= screen.height)
                    continue;
                ++sampled;
                if (screen.pixel(sx, sy) === local.pixel(Math.round(x * local.width / root.width), Math.round(y * local.height / root.height)))
                    ++matched;
            }
        verify(sampled > 0 && matched / sampled > 0.9, "The composed window actually shows the callout instead of an occluding dialog");
    }
    function mainAreaStep(step) {
        return /^workflow\.[^.]+\.mainContent$/.test(step.target);
    }
    function pageAreaCallout(step) {
        liveTarget(step.target);
        const body = bodyBox(), window = app.contentItem;
        const centred = {
            x: (window.width - body.width) / 2,
            y: (window.height - body.height) / 2,
            width: body.width,
            height: body.height
        };
        const words = text => " " + String(text).replace(/<[^>]*>/g, " ").replace(/\.(?=\s|$)/g, " ").replace(/[^a-z0-9._-]+/gi, " ").trim().toLowerCase() + " ";
        const prose = words(step.text);
        const named = Render.descendants(Ui.page(app)).filter(item => {
            if (!Ui.rendered(item))
                return false;
            const label = String(item.text || item.title || "").trim();
            return label.length > 1 && !label.includes("\n") && prose.includes(words(label));
        }).map(item => Geometry.rect(Ui.target(item), window));
        verify(body.x >= 0 && body.y >= 0 && body.x + body.width <= window.width && body.y + body.height <= window.height, "A pointerless callout stays inside the application window");
        for (const item of named)
            compare(Geometry.overlap(body, item), 0, "A pointerless callout does not cover a visible item named by its step");
        if (!named.some(item => Geometry.overlap(centred, item) > 0)) {
            fuzzyCompare(body.x + body.width / 2, window.width / 2, 1, "A pointerless callout is centred horizontally in the app window unless it would cover a named item");
            fuzzyCompare(body.y + body.height / 2, window.height / 2, 1, "A pointerless callout is centred vertically in the app window unless it would cover a named item");
        } else {
            const xs = [centred.x, 0, window.width - body.width], ys = [centred.y, 0, window.height - body.height];
            for (const item of named) {
                xs.push(item.x - body.width, item.x + item.width);
                ys.push(item.y - body.height, item.y + item.height);
            }
            let nearest = Infinity;
            for (const x of xs)
                for (const y of ys) {
                    const candidate = {
                        x: x,
                        y: y,
                        width: body.width,
                        height: body.height
                    };
                    if (x >= 0 && y >= 0 && x + body.width <= window.width && y + body.height <= window.height && named.every(item => Geometry.overlap(candidate, item) === 0))
                        nearest = Math.min(nearest, Math.hypot(x - centred.x, y - centred.y));
                }
            verify(Number.isFinite(nearest), "The named-item exception has a free position inside the actual window");
            verify(Math.hypot(body.x - centred.x, body.y - centred.y) <= nearest + 1, "Only a named-item overlap permits moving to the nearest free position");
        }
        paintedPointer(true);
    }
    function test_pointerless_save_files_is_window_centred_data() {
        return [
            {
                tag: "default",
                width: 1200,
                height: 800
            },
            {
                tag: "small",
                width: 960,
                height: 640
            }
        ];
    }
    function test_pointerless_save_files_is_window_centred(data) {
        start("fitting");
        next(2, scripts().find(entry => entry.id === "fitting").steps.length);
        const steps = scripts().find(entry => entry.id === "fitting").steps;
        const index = steps.findIndex(step => step.files === true && mainAreaStep(step));
        verify(index >= 0, "The fitting lesson supplies its real pointerless Save the files instruction");
        app.width = Math.max(data.width, app.minimumWidth);
        app.height = Math.max(data.height, app.minimumHeight);
        panel.step = index;
        panel.show();
        settleTour();
        finishPages();
        app.update();
        verify(waitForRendering(app.contentItem), "The selected pointerless step renders before its window-centre measurement");
        tryVerify(() => {
            OnboardingProbe.advanceClock(16);
            OnboardingProbe.incubate(app);
            app.update();
            return panel.visible && panel.opacity > 0.99;
        }, 3000, "The geometry witness measures a fully visible actual callout after injected transition frames");
        pageAreaCallout(steps[index]);
    }
    function openLessonNameDialog(lesson) {
        start(lesson);
        Ui.click(test, Probe, app, "home.start");
        settleTour();
        Ui.click(test, Probe, app, "project.create");
        settleTour();
        const dialog = SettingsProof.creationDialog(app);
        verify(dialog !== null, "The learner opens the actual Create project dialog");
        tryCompare(dialog, "opened", true, 2000, "The name-step witness waits for the real creation dialog");
        const steps = scripts().find(item => item.id === lesson).steps;
        tryVerify(() => {
            settleTour();
            return steps[panel.step].target === "createProject.name";
        }, 2000, "Opening Create advances to the real name-field instruction");
        return dialog;
    }
    function test_manual_project_name_preserves_the_callout_and_context_data() {
        return ["simulation", "fitting"].map(lesson => ({
                    tag: lesson,
                    lesson: lesson
                }));
    }
    function test_manual_project_name_preserves_the_callout_and_context(data) {
        // Accident: the learner chooses dew instead of the suggested lbco, then
        // closes the modal that owned the callout's former target.
        const dialog = openLessonNameDialog(data.lesson), field = findChild(dialog, "createProject.name");
        const steps = scripts().find(item => item.id === data.lesson).steps, index = panel.step;
        verify(/name/i.test(steps[index].text) && /lbco/i.test(steps[index].text), "The name instruction offers lbco while allowing a user-entered name");
        aboveDialog(dialog);
        const pointer = paintedPointer(), box = Geometry.rect(field, app.contentItem), body = bodyBox();
        verify(Geometry.pointDistance(pointer.tip, box) <= 4, "The visible name-step pointer reaches the actual name field within the fixed small gap");
        const fields = Render.descendants(dialog.contentItem).filter(item => Ui.rendered(item) && (typeof item.selectAll === "function" || typeof item.textAt === "function"));
        fields.push(dialog.standardButton(Dialog.Ok));
        for (const item of fields)
            compare(Geometry.overlap(body, Geometry.rect(item, app.contentItem)), 0, "The callout never covers a creation field or the actual OK button");
        dialog.projectParentDirectory = String(SettingsProof.emptyDirectory());
        verify(SettingsProof.type(field, "dew"), "The learner enters a valid project name other than lbco");
        press(dialog.standardButton(Dialog.Ok), "Create dew manually");
        tryVerify(() => {
            settleTour();
            return Session.project && Session.project.name === "dew" && panel.step === index + 2;
        }, 3000, "Manual creation accepts dew and automatically advances beyond the closing name field");
        compare(dialog.visible, false, "The completed creation dialog closes");
        const step = steps[index + 2], current = liveTarget(step.target);
        verify(panel.visible && panel.opacity > 0.99, "The next callout remains visibly open after the target dialog closes");
        const sidebar = step.target.startsWith("sideBar.tab.") ? step.target : (String(step.via || "").startsWith("sideBar.tab.") ? step.via : "sideBar.tab.basic");
        verify(Ui.control(Probe, app, sidebar).checked, "The next instruction selects its named sidebar tab instead of retaining Extra");
        if (mainAreaStep(step))
            pageAreaCallout(step);
        else {
            const targetBox = Geometry.rect(Ui.target(current), app.contentItem);
            verify(Geometry.distance(bodyBox(), targetBox) <= 2 * one(panel, "tutorial.text").font.pixelSize, "The next visible callout attaches beside its own live target");
            verify(Geometry.pointDistance(paintedPointer().tip, targetBox) <= 4, "The next callout pointer reaches its live target after modal destruction");
        }
    }
    function test_save_files_link_advances_and_dialog_stays_below_callout() {
        const dialog = openLessonNameDialog("fitting");
        dialog.projectParentDirectory = String(SettingsProof.emptyDirectory());
        verify(SettingsProof.type(findChild(dialog, "createProject.name"), "dew"), "The file-saving lesson starts with a learner-named project");
        press(dialog.standardButton(Dialog.Ok), "Create the file-saving project");
        const steps = scripts().find(item => item.id === "fitting").steps;
        const index = steps.findIndex(step => /save.{0,60}(?:files|lbco\.cif)/i.test(step.text));
        verify(index >= 0, "The fitting lesson has its Save tutorial files instruction");
        panel.step = index;
        panel.show();
        settleTour();
        pageAreaCallout(steps[index]);
        const link = objects(panel).find(item => item.text === "Save tutorial files" && typeof item.clicked === "function" && Ui.rendered(item));
        verify(link !== undefined, "The actual callout offers the file-saving link");
        press(link, "Save tutorial files from its callout");
        let dialogs = [];
        tryVerify(() => {
            dialogs = SettingsProof.projectFileDialogs(app, true);
            return dialogs.length === 1;
        }, 2000, "The real file link opens its destination chooser");
        settleTour();
        aboveDialog(dialogs[0]);
        const destination = SettingsProof.emptyDirectory();
        verify(SettingsProof.chooseProjectLocation(dialogs[0], destination, true), "The injected folder supplies a real private save destination");
        for (const name of ["lbco.cif", "hrpt.xye"]) {
            const actual = SettingsProof.text(destination, name), source = OnboardingProbe.sourceText("app/tutorials/files/" + name);
            verify(source.length > 0 && actual === source, "The real Save tutorial files link writes the complete bundled input: " + name);
        }
        compare(SettingsProof.text(destination, "hrpt.xye"), OnboardingProbe.sourceText("tests/fixtures/background_estimate/meas-lbco-hrpt.xye"), "The saved measurement also matches the independently vendored HRPT source");
        tryVerify(() => {
            settleTour();
            return panel.step === index + 1;
        }, 3000, "Saving both files automatically advances the tutorial");
        verify(panel.visible && panel.opacity > 0.99, "The file dialog's completion leaves the next callout visible");
    }
    function test_live_lesson_instructions_and_staged_free_sets_data() {
        return ["simulation", "fitting"].map(lesson => ({
                    tag: lesson,
                    lesson: lesson
                }));
    }
    function test_live_lesson_instructions_and_staged_free_sets(data) {
        // Classes: action instructions on locked controls; bulk edits escaping
        // the filtered category; modal callouts hidden behind fit results.
        start(data.lesson);
        const steps = scripts().find(item => item.id === data.lesson).steps;
        let categories = 0, releases = 0, fits = 0;
        for (let index = 0; index < steps.length; ++index) {
            settleTour();
            finishPages();
            progress(index + 1, steps.length);
            const step = steps[index];
            controlInstructionEnabled(step);
            if (mainAreaStep(step))
                pageAreaCallout(step);
            const dialogs = Probe.visibleDialogs(app).filter(item => item !== panel && item.visible);
            for (const dialog of dialogs)
                aboveDialog(dialog);
            const results = dialogs.filter(item => item.objectName === "fit.results");
            if (data.lesson === "fitting" && step.target === "mainArea.analysis.tab.correlations" && Probe.rows(Session.project.analysis.constraints).length > 0) {
                const chart = liveTarget("correlations"), pair = correlationPair(chart);
                verify(pair === null || !Number.isFinite(pair.value), "The constrained La/Ba Biso pair has no independent matrix square");
            }
            if (step.page === "report")
                compare(results.length, 0, "Every Report step follows dismissal of the fit results window");
            if (results.length) {
                tutorialStrip();
                const ok = results[0].standardButton(Dialog.Ok), target = liveTarget(step.target);
                compare(target, ok, "The fit-result instruction targets the actual OK action");
                verify(/status/i.test(step.text) && /chi|χ/i.test(step.text) && /\bR/.test(step.text) && /dataset/i.test(step.text), "The result instruction explains overall status, reduced chi-square and per-dataset R values");
                ++fits;
            }
            let before = null, shown = null;
            if (step.target === "parameters.category")
                ++categories;
            if (step.target === "parameters.freeHeader") {
                const table = liveTarget("parameters.list");
                shown = Probe.rows(table.sourceModel).map(row => row.parameter).filter(Boolean);
                const all = Probe.rows(Session.project.parameters).map(row => row.parameter).filter(Boolean);
                verify(shown.length > 0 && shown.length < all.length, "The staged free-all witness has a nonempty proper category subset");
                before = all.map(parameter => ({
                            parameter: parameter,
                            free: parameter.free
                        }));
                ++releases;
            }
            if (index + 1 === steps.length)
                break;
            press(one(panel, "tutorial.next"), "Next performs the shown instruction");
            tryVerify(() => {
                OnboardingProbe.advanceClock(16);
                return panel.step === index + 1;
            }, 15000, "Next performs each real tutorial action and advances once");
            if (step.target === "parameters.clearFilters") {
                const model = liveTarget("parameters.list").sourceModel;
                compare(model.categoryFilter, "", "Next on Clear removes the staged category restriction");
                compare(model.nameFilter, "", "Next on Clear removes any staged name restriction");
            }
            for (const result of results)
                tryCompare(result, "visible", false, 2000, "Next on the results instruction presses OK before leaving the dialog");
            if (before)
                for (const row of before)
                    compare(row.parameter.free, shown.includes(row.parameter) ? true : row.free, "Free all affects exactly the filtered category and preserves every other free flag");
        }
        if (data.lesson === "fitting") {
            verify(categories >= 5 && releases >= 5, "Every required background, scale, cell, peak and displacement stage uses the real category and free-header controls");
            verify(fits > 0, "The fitting walk reaches a real results-window instruction");
        }
    }
    function mentionedParameters(step, project) {
        if (step.page !== "analysis" || step.check || /correlat/i.test(step.text) || /fit\.results|statusBar\./.test(step.target))
            return [];
        const text = step.text.toLowerCase(), rows = Probe.rows(project.parameters);
        return rows.filter(row => {
            const p = row.parameter;
            if (!p)
                return false;
            if (text.includes(p.uid.toLowerCase()))
                return true;
            if (/b[_ ]?iso|displacement/i.test(text) && p.name === "adp_iso")
                return new RegExp("\\b" + row.rowLabel + "(?:'s)?\\b", "i").test(step.text);
            return p.name.length > 3 && text.includes(p.name.toLowerCase()) && (!row.rowLabel || text.includes(String(row.rowLabel).toLowerCase()));
        }).sort((a, b) => {
            // Multiple named parameters follow their order in the prose, never
            // their incidental order in the model that the test will sort.
            const position = row => {
                const label = String(row.rowLabel || row.parameter.name).toLowerCase();
                const at = text.indexOf(label);
                return at < 0 ? text.indexOf(row.parameter.name.toLowerCase()) : at;
            };
            return position(a) - position(b);
        }).map(row => row.parameter);
    }
    function test_named_parameter_rows_survive_view_changes_data() {
        const rows = [];
        for (const lesson of ["interface", "simulation", "fitting"])
            for (const mode of ["all-ascending", "all-descending", "filtered-ascending", "filtered-descending"])
                rows.push({
                    tag: lesson + "-" + mode,
                    lesson: lesson,
                    mode: mode
                });
        return rows;
    }
    function test_named_parameter_rows_survive_view_changes(data) {
        // Enumerate parameter mentions from prose against the live parameter
        // inventory, independently of the tutorial's target resolver or row index.
        start(data.lesson);
        if (data.lesson !== "interface")
            prepareLessonProject(data.lesson);
        const project = Session.project, steps = scripts().find(item => item.id === data.lesson).steps;
        let checked = 0;
        for (let index = 0; index < steps.length; ++index) {
            const mentions = mentionedParameters(steps[index], project);
            if (!mentions.length)
                continue;
            // The explicit uncertainty decision names La's cell, with Ba below it.
            const wanted = /s\.u\.|uncertaint/i.test(steps[index].text) ? (mentions.find(p => /\.La\.adp_iso$/.test(p.uid)) || mentions[0]) : mentions[0];
            panel.step = index;
            panel.show();
            settleTour();
            const table = liveTarget("parameters.list"), model = table.sourceModel;
            model.clearFilters();
            if (data.mode.startsWith("filtered"))
                model.nameFilter = wanted.name;
            verify(OnboardingProbe.sortByRole(model, "path", data.mode.endsWith("descending")), "The named-row census sorts the actual filtered model by parameter path");
            const before = Probe.rows(model).map(row => row.parameter.uid);
            panel.show();
            settleTour();
            const rows = Probe.rows(model), at = rows.findIndex(row => row.parameter.uid === wanted.uid);
            verify(at >= 0, "The step's named parameter exists in the current filtered and sorted table");
            compare(rows.map(row => row.parameter.uid).join("|"), before.join("|"), "Resolving a named row preserves the user's current filter and sort");
            const delegate = table.itemAtIndex(at);
            verify(delegate !== null && Ui.rendered(delegate), "The tutorial exposes its named row without relying on a fixed index");
            verify(Geometry.pointDistance(paintedPointer().tip, Geometry.rect(delegate, app.contentItem)) <= 4, "Every named-parameter explanation points at that parameter's actual current row");
            ++checked;
        }
        if (data.lesson === "fitting")
            verify(checked > 0, "The general named-row census reaches the mandatory Biso explanation");
    }
    function fittedLesson() {
        start("fitting");
        prepareLessonProject("fitting");
        const p = Session.project, parameters = Probe.rows(p.parameters).map(row => row.parameter).filter(Boolean);
        verify(p.setParametersFree(parameters, false), "The named-target witness starts with a controlled real free set");
        const chosen = parameters.filter(item => /\.(La|Ba)\.adp_iso$/.test(item.uid));
        compare(chosen.length, 2, "The actual LBCO project contains both independently free La and Ba Biso parameters");
        verify(p.setParametersFree(chosen, true), "Both named displacements are free before the actual correlation fit");
        AppState.open(AppState.Page.Analysis);
        finishPages();
        tryCompare(p, "calculating", false, 15000, "The real LBCO calculation settles before fitting");
        Ui.click(test, Probe, app, "statusBar.fit.button");
        tryCompare(p.fit, "running", false, 15000, "The named-target witness completes an actual fit");
        verify(p.fit.canUndo && p.correlations.labels.length >= 2, "The actual fit supplies uncertainty and correlation results");
        for (const dialog of Probe.visibleDialogs(app).filter(item => item.objectName === "fit.results"))
            dialog.close();
        settleTour();
        return scripts().find(item => item.id === "fitting").steps;
    }
    function test_named_biso_target_survives_filtering_and_sorting_data() {
        return ["all-ascending", "all-descending", "filtered-ascending", "filtered-descending"].map(mode => ({
                    tag: mode,
                    mode: mode
                }));
    }
    function test_named_biso_target_survives_filtering_and_sorting(data) {
        // Class: positional row anchors drift away from the parameter named in prose.
        const steps = fittedLesson(), index = steps.findIndex(step => /La/.test(step.text) && /B[_ ]?iso/i.test(step.text) && /s\.u\.|uncertaint/i.test(step.text));
        verify(index >= 0, "Fitting contains its named La Biso uncertainty instruction");
        panel.step = index;
        panel.show();
        settleTour();
        const table = liveTarget("parameters.list"), model = table.sourceModel;
        const before = Probe.rows(model).map(row => row.parameter.uid).join("|");
        if (data.mode.startsWith("filtered")) {
            const search = liveTarget("parameters.nameFilter");
            verify(SettingsProof.type(search, "adp_iso"), "The accidental pre-existing filter is entered through the actual search field");
        }
        verify(OnboardingProbe.sortByRole(model, "path", data.mode.endsWith("descending")), "The actual proxy model sorts its public parameter-path role");
        settleTour();
        const rows = Probe.rows(model), expected = rows.findIndex(row => /\.La\.adp_iso$/.test(row.parameter.uid));
        verify(expected >= 0, "The name resolver finds La Biso in the currently filtered and sorted model");
        if (data.mode !== "all-ascending")
            verify(rows.map(row => row.parameter.uid).join("|") !== before, "The accident actually changes row membership or ordering");
        // Refresh the same instruction without assigning its target or an index.
        panel.show();
        settleTour();
        const row = table.itemAtIndex(expected);
        verify(row !== null && Ui.rendered(row), "The tutorial scrolls the named La row into view itself");
        const headers = Render.cells(table.headerItem), labels = headers.map(item => Ui.text(item).trim());
        const su = labels.findIndex(label => /^s\.?u\.?$/i.test(label) || /uncertainty/i.test(label));
        verify(su >= 0, "The actual table exposes its standard-uncertainty column by label");
        const cell = Render.cells(row)[su], rect = Geometry.rect(cell, app.contentItem), pointer = paintedPointer();
        verify(Geometry.pointDistance(pointer.tip, rect) <= 4, "The pointer reaches La Biso's actual s.u. cell, independent of row position");
        const column = Geometry.rect(headers[su], app.contentItem);
        column.height = table.height;
        compare(Geometry.overlap(bodyBox(), column), 0, "The uncertainty explanation never covers the s.u. column it asks the user to inspect");
    }
    function correlationPair(chart) {
        const labels = Array.from(chart.labels), la = labels.findIndex(label => /\bLa\b/.test(label) && /adp_iso|B[_ ]?iso/i.test(label)), ba = labels.findIndex(label => /\bBa\b/.test(label) && /adp_iso|B[_ ]?iso/i.test(label));
        if (la < 0 || ba < 0)
            return null;
        const row = Math.max(la, ba), column = Math.min(la, ba), cells = findChild(chart, "correlations.cells");
        verify(cells !== null, "The real correlation chart exposes its painted cell delegates");
        return cells.itemAt(row * labels.length + column);
    }
    function test_named_correlation_points_at_the_actual_matrix_pair() {
        // Class: a matrix explanation anchors a position instead of a parameter pair.
        const steps = fittedLesson(), index = steps.findIndex(step => /La/.test(step.text) && /Ba/.test(step.text) && /correlat/i.test(step.text));
        verify(index >= 0, "Fitting explains the La/Ba displacement correlation by name");
        panel.step = index;
        panel.show();
        settleTour();
        const chart = liveTarget("correlations"), pair = correlationPair(chart);
        verify(pair !== null && Number.isFinite(pair.value) && Ui.rendered(pair), "The named unconstrained La/Ba correlation has a visible real square");
        const box = Geometry.rect(pair, app.contentItem);
        verify(Geometry.pointDistance(paintedPointer().tip, box) <= 4, "The callout pointer reaches the matrix square resolved from both parameter names");
        compare(Geometry.overlap(bodyBox(), box), 0, "The correlation callout leaves its named matrix square unobscured");
    }
    function test_last_step_choices_name_the_actual_project_data() {
        const rows = [];
        for (const lesson of ["interface", "simulation", "fitting"])
            for (const prior of [false, true])
                for (const action of ["keep", "return", "stop"])
                    rows.push({
                        tag: lesson + "-" + prior + "-" + action,
                        lesson: lesson,
                        prior: prior,
                        action: action
                    });
        return rows;
    }
    function test_last_step_choices_name_the_actual_project(data) {
        let original = null, location = "", bytes = "";
        if (data.prior) {
            location = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"));
            verify(Session.openProject(location), "Completion ownership starts with an independently saved user project");
            original = Session.project;
            OnboardingProbe.rememberProject(original);
            original.description = "Unsaved user edit survives a tutorial";
            bytes = SettingsProof.text(location, "project.edi");
        }
        AppState.open(AppState.Page.Home);
        start(data.lesson);
        if (data.lesson !== "interface") {
            Ui.click(test, Probe, app, "home.start");
            settleTour();
            createLessonProject("dew");
        }
        const tutorial = Session.project, destination = Session.projectLocation, steps = scripts().find(item => item.id === data.lesson).steps;
        verify(tutorial !== null, "Each tutorial owns an actual project at its completion");
        const saved = destination ? SettingsProof.text(destination, "project.edi") : "";
        tutorial.description = "An unsaved tutorial edit";
        panel.step = steps.length - 1;
        panel.show();
        settleTour();
        const keepText = "Keep working on " + tutorial.name, returnText = data.prior ? "Return to my project" : "Close " + tutorial.name;
        const buttons = objects(panel).filter(item => typeof item.clicked === "function" && Ui.rendered(item));
        const keep = buttons.find(item => item.text === keepText), back = one(panel, "tutorial.back"), leave = buttons.find(item => item.text === returnText);
        verify(keep !== undefined && leave !== undefined, "The two final choices name exactly what happens to the actual tutorial project");
        const a = Geometry.rect(keep, app.contentItem), b = Geometry.rect(leave, app.contentItem), c = Geometry.rect(back, app.contentItem);
        verify(Math.abs(a.y - b.y) <= 1 && Geometry.overlap(a, b) === 0 && Math.max(a.x, b.x) - Math.min(a.x + a.width, b.x + b.width) > 0, "The two separate dialog-style choices share their own row with a clear gap");
        verify(c.y + c.height <= a.y || c.y >= a.y + a.height, "The Back icon stays on a separate row from the sentence choices");
        compare(Geometry.buttonComponent(keep), Geometry.buttonComponent(popupButton), "Keep uses the app's dialog button component");
        compare(Geometry.buttonComponent(leave), Geometry.buttonComponent(popupButton), "Return uses the app's dialog button component");
        press(data.action === "keep" ? keep : data.action === "return" ? leave : one(panel, "tutorial.stop"), "Finish the tutorial with the named choice");
        tryCompare(panel, "visible", false, 2000, "A completion choice or final Stop ends the tutorial");
        if (data.action === "keep") {
            compare(Session.project, tutorial, "Keep working leaves the tutorial's project open");
            compare(tutorial.description, "An unsaved tutorial edit", "Keep does not discard the ongoing tutorial work");
        } else if (data.prior) {
            verify(OnboardingProbe.isRemembered(Session.project), "Return and Stop reopen the exact user's earlier project");
            compare(Session.project.description, "Unsaved user edit survives a tutorial", "Return preserves the user's unsaved changes");
        } else
            compare(Session.project, null, "Closing or stopping without an earlier project leaves no project open");
        if (location)
            compare(SettingsProof.text(location, "project.edi"), bytes, "Tutorial completion never writes the earlier user's project");
        if (destination) {
            const after = SettingsProof.text(destination, "project.edi");
            verify(after === saved || (data.action !== "keep" && after === ""), "Completion never saves unsaved tutorial edits; discarded temporary files may be removed");
        }
    }
    function test_pointer_directions_have_one_size_and_never_enter_the_target() {
        // Class: direction-dependent pointer geometry, especially a long down arrow.
        start("interface");
        const steps = tourSteps(), seen = new Set();
        let dimensions = null, separation = null;
        const old = Preferences.sideBarSide;
        try {
            for (const side of ["Left", "Right"]) {
                Preferences.sideBarSide = side;
                for (let index = 0; index < steps.length; ++index) {
                    if (mainAreaStep(steps[index]))
                        continue;
                    panel.step = index;
                    panel.show();
                    settleTour();
                    finishPages();
                    const box = Geometry.rect(Ui.target(liveTarget(steps[index].target)), app.contentItem), body = bodyBox(), pointer = paintedPointer();
                    const center = Geometry.center(body), direction = Math.abs(pointer.tip.x - center.x) > body.width / 2 ? (pointer.tip.x < center.x ? "left" : "right") : (pointer.tip.y < center.y ? "up" : "down");
                    seen.add(direction);
                    const size = [pointer.box.width, pointer.box.height].sort((a, b) => a - b);
                    if (dimensions === null)
                        dimensions = size;
                    fuzzyCompare(size[0], dimensions[0], 1, "The pointer base is equal in all four directions");
                    fuzzyCompare(size[1], dimensions[1], 1, "The pointer length is equal in all four directions");
                    verify(!pointer.intersects(box), "No painted pointer pixels enter the target rectangle in any direction");
                    const gap = Geometry.pointDistance(pointer.tip, box);
                    verify(gap > 0 && gap <= 4, "The tip stops a small positive fixed gap short of its target");
                    if (separation === null)
                        separation = gap;
                    fuzzyCompare(gap, separation, 1, "All four pointer directions preserve the same small target gap");
                    if (steps[index].target === "statusBar.fit.button")
                        compare(direction, "down", "The Fit instruction exercises the down-pointing case");
                }
            }
        } finally {
            Preferences.sideBarSide = old;
        }
        compare(Array.from(seen).sort().join(","), "down,left,right,up", "The real layout witness exercises every pointer direction");
    }
    function createLessonProject(name) {
        compare(Session.project, null, "A scientific lesson waits for user creation instead of silently creating a project");
        Ui.click(test, Probe, app, "project.create");
        const dialog = SettingsProof.creationDialog(app);
        verify(dialog !== null, "The learner opens the real Create project dialog");
        tryCompare(dialog, "opened", true, 2000, "The project name is entered after the real dialog opens");
        dialog.projectParentDirectory = String(SettingsProof.emptyDirectory());
        const field = findChild(dialog, "createProject.name");
        verify(field !== null && SettingsProof.type(field, name), "The learner types the tutorial project's name into the real form");
        press(dialog.standardButton(Dialog.Ok), "Create the learner-named project");
        tryVerify(() => Session.project !== null && Session.project.name === name, 3000, "The actual Create action opens the project the learner named");
    }
    function test_scientific_lessons_begin_with_user_project_creation_data() {
        const rows = [];
        for (const lesson of ["simulation", "fitting"])
            for (const ending of ["stop", "last"])
                rows.push({
                    tag: lesson + "-" + ending,
                    lesson: lesson,
                    ending: ending
                });
        return rows;
    }
    function test_scientific_lessons_begin_with_user_project_creation(data) {
        verify(Examples.bundled(test, Session, "pd-neut-cwl_cosio-d20"), "The Project-first accident starts with a user's existing project");
        const original = Session.project, destination = Session.projectLocation;
        original.description = "unsaved before Project-first lesson";
        OnboardingProbe.rememberProject(original);
        AppState.open(AppState.Page.Home);
        start(data.lesson);
        compare(app.appBarCentralTabs.currentIndex, AppState.Page.Home, "Simulation and Fitting both start on Home");
        compare(Session.project, null, "The tutorial puts aside the user's project without creating one itself");
        const steps = scripts().find(entry => entry.id === data.lesson).steps;
        const create = steps.findIndex(step => step.target === "project.create");
        const structure = steps.findIndex(step => step.page === "structure");
        verify(create === 1 && steps[0].target === "home.start" && steps[0].page === "home" && structure > create, "Home Start precedes Project Create, before any Structure step");
        Ui.click(test, Probe, app, "home.start");
        tryCompare(panel, "step", create, 2000, "The Start action advances the lesson to project creation");
        createLessonProject("learner_named_" + data.lesson);
        verify(!OnboardingProbe.isRemembered(Session.project), "User creation makes a separate tutorial project");
        if (data.ending === "last") {
            // Completion ownership is orthogonal to scientific fitting; the
            // recipe actor covers those actions. Enter the real final control.
            panel.step = steps.length - 1;
            panel.show();
            settleTour();
            const discard = objects(panel).find(item => item.objectName === "tutorial.discard" && Ui.rendered(item));
            verify(discard !== undefined, "The final step offers its explicit return choice while Next is disabled");
            press(discard, "End the lesson and return to the user's project");
        } else {
            press(one(panel, "tutorial.stop"), "Stop the Project-first lesson");
        }
        tryCompare(panel, "visible", false, 2000, "Stopping or ending closes the scientific lesson");
        verify(OnboardingProbe.isRemembered(Session.project), "Stopping or ending restores the exact user's project");
        compare(Session.projectLocation, destination, "Project-first lessons preserve the user's original save destination");
        compare(Session.project.description, "unsaved before Project-first lesson", "The user's unsaved edits survive both tutorial endings");
    }
    function tutorialStrip() {
        const status = objects(app).filter(item => item.objectName.startsWith("statusBar") && Ui.rendered(item));
        const root = status.find(item => Render.texts(item).some(label => label.text === one(panel, "tutorial.progress").text));
        verify(root !== undefined, "The running tutorial has matching progress in the status bar");
        verify(!Render.texts(root).some(label => label.text === panel.title), "The status strip shows only progress, without the tutorial name");
        const actions = {};
        for (const action of ["stop", "back", "next"]) {
            const expected = action === "next" && panel.atEnd ? "Finish" : action[0].toUpperCase() + action.slice(1);
            const matches = Render.descendants(root).filter(item => typeof item.clicked === "function" && Ui.rendered(item) && (item.toolTip === expected || item.ToolTip.text === expected));
            compare(matches.length, 1, "The tutorial status strip has one real icon action with the matching tooltip: " + expected);
            actions[action] = matches[0];
        }
        const stop = Geometry.rect(actions.stop, app.contentItem), back = Geometry.rect(actions.back, app.contentItem), next = Geometry.rect(actions.next, app.contentItem), fit = Geometry.rect(one(app, "statusBar.fit.button"), app.contentItem);
        const a = back.x - stop.x - stop.width, b = next.x - back.x - back.width;
        verify(a >= 0 && b >= 0 && Math.abs(stop.y - next.y) <= 1, "The strip uses Stop/Back/Next order in one nonoverlapping row");
        fuzzyCompare(a, b, 1, "The status strip uses equal Stop/Back and Back/Next gaps");
        const popupStop = Geometry.rect(one(panel, "tutorial.stop"), app.contentItem), popupBack = Geometry.rect(one(panel, "tutorial.back"), app.contentItem), popupNext = Geometry.rect(one(panel, "tutorial.next"), app.contentItem);
        fuzzyCompare(a, popupBack.x - popupStop.x - popupStop.width, 1, "Strip and callout use the same equal navigation gap");
        fuzzyCompare(b, popupNext.x - popupBack.x - popupBack.width, 1, "Strip and callout use the same Back/Next gap");
        const fitItems = objects(app).filter(item => item.objectName.startsWith("statusBar.fit.") && Ui.rendered(item));
        if (Session.project && Session.project.fit.canUndo)
            verify(fitItems.some(item => item.objectName === "statusBar.fit.outcome"), "After a real fit the placement witness includes the visible fit-status items");
        const fitRight = Math.max(fit.x + fit.width, ...fitItems.map(item => {
            const box = Geometry.rect(item, app.contentItem);
            return box.x + box.width;
        }));
        verify(stop.x > fitRight, "The tutorial strip follows the complete fit group at the right of the status bar");
        const separators = Render.descendants(root).filter(item => Ui.rendered(item) && item.width > 0 && item.width <= 2 && item.height >= next.height / 2 && item.color !== undefined && item.color.a > 0);
        verify(separators.some(item => {
            const r = Geometry.rect(item, app.contentItem);
            return r.x > fitRight && r.x + r.width < stop.x;
        }), "A visible vertical separator divides the tutorial strip from Fit");
        verify(separators.some(item => {
            const r = Geometry.rect(item, app.contentItem), gap = stop.x - r.x - r.width;
            return gap >= 0 && gap <= 2 * one(panel, "tutorial.text").font.pixelSize;
        }), "The tutorial strip also retains the status bar's usual separator on its left");
        for (const action of Object.keys(actions)) {
            const button = actions[action], circles = Render.descendants(button.background).filter(item => item.color !== undefined && item.color.a > 0 && item.radius >= Math.min(item.width, item.height) / 2);
            verify(circles.length > 0, "Status-strip actions use the app's visible light circular icon background");
        }
        return actions;
    }
    function test_status_strip_stays_fixed_and_drives_the_same_tutorial_data() {
        const rows = [];
        for (const lesson of ["interface", "simulation", "fitting"])
            for (const ending of ["stop", "last"])
                rows.push({
                    tag: lesson + "-" + ending,
                    lesson: lesson,
                    ending: ending
                });
        return rows;
    }

    function test_status_strip_stays_fixed_and_drives_the_same_tutorial(data) {
        start(data.lesson);
        const steps = scripts().find(entry => entry.id === data.lesson).steps;
        if (data.lesson !== "interface") {
            Ui.click(test, Probe, app, "home.start");
            createLessonProject("strip_" + data.lesson);
        }
        const explain = steps.findIndex(step => !step.check);
        verify(explain >= 0 && explain + 1 < steps.length, "Every tutorial supplies an explanation for the strip's actual Next/Back witness");
        panel.step = explain;
        panel.show();
        settleTour();
        const buttons = tutorialStrip();
        const positions = ["stop", "back", "next"].map(action => Geometry.rect(buttons[action], app.contentItem));
        press(buttons.next, "Status-bar Next");
        progress(explain + 2, steps.length);
        press(tutorialStrip().back, "Status-bar Back");
        progress(explain + 1, steps.length);
        for (let index = 0; index < steps.length; ++index) {
            panel.step = index;
            panel.show();
            settleTour();
            const current = tutorialStrip();
            ["stop", "back", "next"].forEach((action, at) => {
                const box = Geometry.rect(current[action], app.contentItem);
                fuzzyCompare(box.x, positions[at].x, 1, "Status-strip buttons keep their horizontal screen position across all steps");
                fuzzyCompare(box.y, positions[at].y, 1, "Status-strip buttons keep their vertical screen position across all steps");
            });
        }
        const progressText = one(panel, "tutorial.progress").text;
        press(tutorialStrip()[data.ending === "stop" ? "stop" : "next"], "End from the fixed strip");
        tryCompare(panel, "visible", false, 2000, "The strip's Stop or final check ends the same tutorial as the callout");
        verify(!objects(app).some(item => item.objectName.startsWith("statusBar") && Ui.rendered(item) && Render.texts(item).some(label => label.text === progressText)), "The tutorial status strip disappears after Stop and after the last step");
    }
    function test_all_lesson_pointers_keep_one_size_and_touch_the_target_data() {
        return ["interface", "simulation", "fitting"].map(lesson => ({
                    tag: lesson,
                    lesson: lesson
                }));
    }
    function test_all_lesson_pointers_keep_one_size_and_touch_the_target(data) {
        start(data.lesson);
        // Geometry is independent of the learner's scientific input: a populated
        // temporary LBCO fixture exposes all named fields. Project-first behavior
        // and the real scientific actions have their separate acceptance actors.
        if (data.lesson !== "interface")
            prepareLessonProject(data.lesson);
        const steps = scripts().find(entry => entry.id === data.lesson).steps;
        let size = null, gap = null;
        for (let index = 0; index < steps.length; ++index) {
            panel.step = index;
            panel.show();
            settleTour();
            finishPages();
            const current = Ui.control(Probe, app, steps[index].target);
            verify(current !== null && Ui.rendered(Ui.target(current)), "Every lesson step resolves its actual visible target before pointer measurement");
            if (mainAreaStep(steps[index])) {
                pageAreaCallout(steps[index]);
                continue;
            }
            const target = Geometry.rect(Ui.target(current), app.contentItem), body = bodyBox(), pointer = paintedPointer();
            const dims = [pointer.box.width, pointer.box.height].sort((a, b) => a - b);
            if (size === null)
                size = dims;
            fuzzyCompare(dims[0], size[0], 1, "Every step keeps the same pointer thickness regardless of placement side");
            fuzzyCompare(dims[1], size[1], 1, "Every step keeps the same pointer length instead of stretching a wedge");
            verify(Geometry.pointDistance(pointer.tip, target) > 0 && Geometry.pointDistance(pointer.tip, target) <= 4, "The painted tip stops a small gap before the target edge");
            verify(!pointer.intersects(target), "The pointer never enters the target rectangle");
            compare(Geometry.overlap(body, target), 0, "A callout never overlaps the target it describes");
            verify(body.x >= 0 && body.y >= 0 && body.x + body.width <= app.contentItem.width && body.y + body.height <= app.contentItem.height, "The complete callout stays inside the application window");
            const distance = Geometry.distance(body, target);
            if (gap === null)
                gap = distance;
            verify(distance <= 2 * one(panel, "tutorial.text").font.pixelSize, "The callout uses a small gap beside its target");
            fuzzyCompare(distance, gap, 1, "The nearest callout edge uses one fixed gap across every lesson step");
        }
    }
    function selectedContext() {
        const page = Ui.page(app);
        return Render.descendants(page).filter(item => item.checked && (/^mainArea\..*\.tab\./.test(item.objectName) || item.objectName.startsWith("sideBar.tab."))).map(item => item.objectName).sort();
    }
    function proveStepContext(step) {
        finishPages();
        const pages = {
            home: AppState.Page.Home,
            project: AppState.Page.Project,
            structure: AppState.Page.Structure,
            experiment: AppState.Page.Experiment,
            analysis: AppState.Page.Analysis,
            report: AppState.Page.Report
        };
        compare(app.appBarCentralTabs.currentIndex, pages[step.page], "Each step establishes its own correct workflow page");
        const page = Ui.page(app), current = Ui.control(Probe, app, step.target);
        verify(current !== null && Ui.rendered(Ui.target(current)), "Each step resolves the visible target on the current page and tab, never a hidden copy");
        if (!current.enabled) {
            verify(step.target.includes(".tab.") && /^(Stacked|Map)$/.test(current.text), "Only the designed-disabled Stacked and Map tabs may be targeted in LBCO");
            verify(/scan/i.test(step.text) && /patterns|temperatures/i.test(step.text), "A designed-disabled target explains the multi-pattern experiment that enables it");
        } else if (step.target.includes(".tab.")) {
            verify(current.checked, "A described available tab is selected by its own step");
        }
        const groups = Render.descendants(page).filter(item => item.objectName.startsWith("group.") && Ui.inPane(Ui.target(item)));
        if (step.page !== "home")
            verify(groups.length > 0, "Tour context restoration never leaves a workflow sidebar empty");
        if (step.target.startsWith("group.")) {
            compare(current.collapsed, false, "Every group-target step unfolds its group without requiring a per-step flag");
            verify(Render.descendants(current.contentItem).some(item => item !== current.contentItem && Ui.rendered(item)), "An unfolded group exposes actual content in the current sidebar viewport");
        }
        controlInstructionEnabled(step);
        if (mainAreaStep(step)) {
            pageAreaCallout(step);
            return selectedContext();
        }
        const rect = Geometry.rect(Ui.target(current), app.contentItem);
        verify(Geometry.distance(bodyBox(), rect) <= 2 * one(panel, "tutorial.text").font.pixelSize, "The callout attaches to the current visible copy instead of floating in a corner");
        const pointer = paintedPointer();
        verify(Geometry.pointDistance(pointer.tip, rect) <= 2 * one(panel, "tutorial.text").font.pixelSize, "The painted tip reaches the current-tab target");
        return selectedContext();
    }
    function test_tour_table_lifecycle_emits_no_qml_runtime_errors() {
        // Class: detached delegate lifecycle warnings during table remeasurement.
        verify(OnboardingProbe.startHostLog().length > 0, "The tour warning census installs the actual run log with private storage and an injected clock");
        tourLogOpen = true;
        console.warn("tour-log-warning-control");
        start("interface");
        OnboardingProbe.startClock();
        const steps = tourSteps();
        let measured = 0;
        for (let index = 0; index < steps.length; ++index) {
            if (index)
                next(index + 1, steps.length);
            finishPages();
            for (const table of Render.descendants(Ui.page(app))) {
                if (!Ui.rendered(table) || typeof table.itemAtIndex !== "function" || table.columnWidths === undefined)
                    continue;
                const width = table.width;
                table.width = width + 1;
                OnboardingProbe.advanceClock(200);
                table.width = width;
                OnboardingProbe.advanceClock(200);
                verify(waitForPolish(table), "A real table remeasurement and delegate lifecycle finish under the tour");
                ++measured;
            }
            verify(!tourFitStarted, "Walking the tour's Fit instruction never starts a worker");
        }
        const text = OnboardingProbe.finishHostLog();
        tourLogOpen = false;
        verify(measured > 0 && text.includes("tour-log-warning-control"), "The witness reaches real table remeasurement and proves warnings enter the actual run log");
        verify(!/(TypeError|ReferenceError):/.test(text), "No QML TypeError or ReferenceError reaches the run log during the complete tour and table remeasurement");
    }
    function transitionState() {
        const page = Ui.page(app), groups = Render.descendants(page).filter(item => item.objectName.startsWith("group.") && Ui.inPane(Ui.target(item)));
        const scrolls = Render.descendants(page).filter(item => typeof item.contentY === "number" && Ui.inPane(item));
        const progressLabels = objects(app).filter(item => item.objectName.startsWith("statusBar") && Ui.rendered(item));
        const progress = [];
        for (const root of progressLabels)
            for (const label of Render.texts(root))
                if (/^Step \d+ of \d+$/.test(label.text) && !progress.includes(label.text))
                    progress.push(label.text);
        const at = bodyBox();
        return {
            context: JSON.stringify([app.appBarCentralTabs.currentIndex, selectedContext(), groups.map(item => [item.objectName, item.height]), scrolls.map(item => [item.objectName, item.contentY])]),
            opacity: panel.visible ? panel.opacity * panel.contentItem.opacity * panel.background.opacity : 0,
            x: at.x,
            y: at.y,
            progress: progress
        };
    }
    function test_each_step_fades_out_before_context_and_in_after_settling_data() {
        return targetRows();
    }
    function test_each_step_fades_out_before_context_and_in_after_settling(data) {
        // Class: revealing new context under a still-visible or moving old callout.
        start("interface");
        const steps = tourSteps(), previous = data.index ? data.index - 1 : steps.length - 1;
        panel.step = previous;
        panel.show();
        settleTour();
        finishPages();
        // All transition durations are private test inputs, never wall-clock sleeps.
        const animations = Probe.objectsWithProperty(app, "duration").filter(item => OnboardingProbe.inheritsType(item, "QQuickNumberAnimation"));
        verify(animations.length > 0, "The frame gate injects real UI animation durations");
        for (const animation of animations)
            animation.duration = 160;
        const destination = steps[data.index];
        if (destination.target.startsWith("group.")) {
            const groups = objects(app).filter(item => item.objectName === destination.target && typeof item.collapsed === "boolean");
            for (const group of groups)
                group.collapsed = true;
            settleTour();
        }
        const trace = [transitionState()];
        if (data.index) {
            const button = one(panel, "tutorial.next"), point = Ui.clickPoint(button);
            verify(point !== null && button.enabled, "A real Next click begins the observed step transition");
            mouseClick(button, point.x, point.y, Qt.LeftButton, Qt.NoModifier, 0);
        } else {
            panel.step = 0;
            panel.show();
        }
        for (let time = 0; time < 2000; time += 16) {
            OnboardingProbe.advanceClock(16);
            app.update();
            verify(waitForRendering(app.contentItem), "Each transition sample observes an actually rendered frame");
            trace.push(transitionState());
        }
        const final = trace[trace.length - 1], nextText = "Step " + (data.index + 1) + " of " + steps.length, oldText = "Step " + (previous + 1) + " of " + steps.length;
        verify(trace[0].opacity > 0.99 && final.opacity > 0.99 && final.progress.includes(nextText), "The trace spans a visible old callout through the visible settled new callout");
        const hidden = trace.findIndex(frame => frame.opacity <= 0.001);
        verify(hidden > 0, "Every step change hides the old callout completely before revealing new context");
        let appeared = false;
        for (let index = 1; index < trace.length; ++index) {
            const frame = trace[index], before = trace[index - 1];
            if (frame.context !== before.context)
                verify(before.opacity <= 0.001 && frame.opacity <= 0.001, "Page, tab, group-height and scroll changes happen only after the old callout reaches zero opacity");
            if (index > hidden && frame.opacity > 0.001) {
                appeared = true;
                compare(frame.context, final.context, "The new callout fades in only after all context movement has finished");
                fuzzyCompare(frame.x, final.x, 0.5, "Once visible the new callout never moves horizontally before the next step");
                fuzzyCompare(frame.y, final.y, 0.5, "Once visible the new callout never moves vertically before the next step");
                verify(frame.progress.includes(nextText), "The status step number changes together with the new callout's appearance");
            } else if (!appeared) {
                verify(frame.progress.includes(oldText), "The status strip retains the old step number throughout fade-out and context setup");
            }
        }
    }
    function test_tour_groups_and_tabs_follow_live_layout_order() {
        // Class: narration order diverges from the live layout after groups move.
        start("interface");
        const steps = tourSteps();
        let groupContext = "", previousGroup = "";
        const previousTabs = {};
        for (let index = 0; index < steps.length; ++index) {
            if (index)
                next(index + 1, steps.length);
            finishPages();
            const step = steps[index], current = liveTarget(step.target);
            if (step.target.startsWith("group.")) {
                const context = step.page + ":" + selectedContext().filter(name => name.startsWith("sideBar.tab.")).join(",");
                const groups = Render.descendants(Ui.page(app)).filter(item => item.objectName.startsWith("group.") && Ui.inPane(Ui.target(item))).sort((a, b) => Geometry.rect(Ui.target(a), app.contentItem).y - Geometry.rect(Ui.target(b), app.contentItem).y).map(item => item.objectName);
                verify(groups.includes(step.target), "The narrated group belongs to the running app's current sidebar layout");
                if (context === groupContext && previousGroup) {
                    verify(groups.includes(previousGroup), "Consecutive narrated groups remain in the same live sidebar census");
                    verify(groups.indexOf(step.target) > groups.indexOf(previousGroup), "Consecutive group instructions follow the live top-to-bottom order");
                }
                groupContext = context;
                previousGroup = step.target;
            }
            if (step.target.includes(".tab.")) {
                const family = step.target.startsWith("appBar.") ? "appBar" : step.page + ":" + (step.target.startsWith("sideBar.") ? "sideBar" : "mainArea");
                if (previousTabs[family] && previousTabs[family] !== current)
                    verify(Geometry.rect(current, app.contentItem).x > Geometry.rect(previousTabs[family], app.contentItem).x, "Consecutive tab instructions follow their actual left-to-right layout order");
                previousTabs[family] = current;
                if (step.target.startsWith("sideBar.")) {
                    groupContext = "";
                    previousGroup = "";
                }
            }
        }
    }
    function test_every_tour_step_restores_context_data() {
        return ["forward", "backward", "direct"].map(mode => ({
                    tag: mode,
                    mode: mode
                }));
    }
    function test_every_tour_step_restores_context(data) {
        // Class: history-dependent tour context, disabled targets and collapsed groups.
        // Accident: Back or a direct jump enters a group after another tab was open.
        start("interface");
        verify(Session.project && Session.project.currentStructure.name === "lbco" && Probe.rows(Session.project.experiments).length > 0, "The full walk uses the tour's loaded LBCO project with its experiment");
        const steps = tourSteps(), contexts = [];
        for (let index = 0; index < steps.length; ++index) {
            if (index)
                next(index + 1, steps.length);
            contexts.push(proveStepContext(steps[index]));
        }
        if (data.mode === "forward")
            return;
        const order = data.mode === "backward" ? steps.map((step, index) => index).reverse() : steps.map((step, index) => index).filter(index => index % 2).concat(steps.map((step, index) => index).filter(index => !(index % 2)));
        for (const index of order) {
            if (data.mode === "backward" && index < steps.length - 1)
                press(one(panel, "tutorial.back"), "Back through the complete tour");
            if (data.mode === "direct") {
                panel.step = index;
                panel.show();
                settleTour();
            }
            progress(index + 1, steps.length);
            compare(JSON.stringify(proveStepContext(steps[index])), JSON.stringify(contexts[index]), "Back and direct jumps reproduce the complete valid forward context as a round-trip invariant");
        }
    }
    function test_each_step_scrolls_only_to_the_nearest_visible_edge() {
        // Class: over-scrolling or selecting a hidden duplicate during context setup.
        start("interface");
        const steps = tourSteps();
        let scrollable = 0;
        for (let index = 0; index < steps.length; ++index) {
            if (index)
                next(index + 1, steps.length);
            proveStepContext(steps[index]);
            const control = Ui.target(Ui.control(Probe, app, steps[index].target));
            for (let viewport = control.parent; viewport; viewport = viewport.parent) {
                if (typeof viewport.contentY !== "number" || viewport.contentHeight <= viewport.height)
                    continue;
                ++scrollable;
                for (const offset of [0, viewport.height / 2, -viewport.height / 2]) {
                    const origin = viewport.originY || 0;
                    viewport.contentY = Math.max(origin, Math.min(origin + viewport.contentHeight - viewport.height, viewport.contentY + offset));
                    verify(waitForPolish(app), "The independent scroll accident settles before context is restored");
                    const before = viewport.contentY, rect = Geometry.rect(control, viewport);
                    if (rect.height > viewport.height)
                        continue;
                    const delta = rect.y < 0 ? rect.y : Math.max(0, rect.y + rect.height - viewport.height);
                    panel.show();
                    settleTour();
                    verify(waitForPolish(app), "The step's own reveal finishes before its scroll distance is measured");
                    fuzzyCompare(viewport.contentY - before, delta, 1, "A visible target does not scroll; an off-screen target moves only to its nearest viewport edge");
                    verify(Ui.control(Probe, app, steps[index].target) === control || Ui.target(Ui.control(Probe, app, steps[index].target)) === control, "Restoring the step still targets the same visible copy");
                }
            }
        }
        verify(scrollable > 0, "The complete tour reaches real overflowing sidebar content");
    }
    function test_every_live_sidebar_group_has_a_tour_step() {
        // Class: hand-maintained tour inventories omit new or less-used groups.
        verify(Examples.bundled(test, Session, "pd-neut-cwl_lbco-hrpt"), "The group census loads the independent bundled LBCO project");
        finishPages();
        const steps = tourSteps(), pages = ["home", "project", "structure", "experiment", "analysis", "report"];
        const seen = [];
        for (let pageIndex = 0; pageIndex < pages.length; ++pageIndex) {
            AppState.open(pageIndex);
            finishPages();
            const page = Ui.page(app), tabs = Render.descendants(page).filter(item => item.objectName.startsWith("sideBar.tab.") && item.enabled);
            for (const tab of tabs) {
                Ui.click(test, Probe, app, tab.objectName);
                const groups = Render.descendants(page).filter(item => item.objectName.startsWith("group.") && Ui.inPane(Ui.target(item)));
                for (const group of groups) {
                    const key = pages[pageIndex] + ":" + tab.objectName + ":" + group.objectName;
                    seen.push(key);
                    verify(steps.some(step => step.page === pages[pageIndex] && step.target === group.objectName), "Every group in the live page/tab census has a tour step: " + key);
                }
            }
        }
        verify(seen.some(key => key.startsWith("experiment:sideBar.tab.extras:") && /peak/.test(key)), "The live census includes the Experiment Extra Peak group containing peak cutoff");
    }
    function test_analysis_order_and_every_filter_control_are_explained() {
        verify(Examples.bundled(test, Session, "pd-neut-cwl_lbco-hrpt"), "The Analysis census loads actual LBCO parameter controls");
        AppState.open(AppState.Page.Analysis);
        finishPages();
        Ui.click(test, Probe, app, "sideBar.tab.basic");
        Ui.expandGroup(test, Probe, app, "group.parameters");
        const name = Ui.control(Probe, app, "parameters.nameFilter"), clear = Ui.control(Probe, app, "parameters.clearFilters");
        verify(name !== null && clear !== null, "The live parameters filter bar exposes search and clear controls");
        let bar = name.parent;
        while (bar && !Render.descendants(bar).includes(clear))
            bar = bar.parent;
        verify(bar !== null, "The live filter controls share the parameters filter bar");
        const controls = Render.descendants(bar).filter(item => item.objectName && (item === name || item === clear || typeof item.textAt === "function"));
        const steps = tourSteps().filter(step => step.page === "analysis"), targets = steps.map(step => step.target);
        const position = target => {
            const at = targets.indexOf(target);
            verify(at >= 0, "The Analysis tour includes its actual required control: " + target);
            return at;
        };
        const begin = position("appBar.tab.analysis"), main = position("sideBar.tab.basic"), table = position("parameters.list"), fit = position("statusBar.fit.button"), correlations = position("mainArea.analysis.tab.correlations"), stacked = position("mainArea.analysis.tab.stacked"), map = position("mainArea.analysis.tab.map"), extra = position("sideBar.tab.extras");
        const results = steps.findIndex(step => /fit\.results/.test(step.target));
        const pattern = targets.indexOf("mainArea.analysis.tab.fitting", fit + 1);
        verify(begin < main && main <= table && table < fit && results === fit + 1 && pattern === results + 1 && correlations === pattern + 1 && correlations < stacked && stacked < map && map < extra, "Analysis explains filters before Fit, then results, Pattern, populated Correlations and scan tabs");
        verify(controls.length > 2, "The independent filter census includes category choices, not only search and clear");
        for (const control of controls) {
            const at = position(control.objectName);
            verify(at > table && at < fit, "Every live parameter filter control has its own step between the table and Fit");
        }
        verify(/after.*fit|fit.*first/i.test(steps[correlations].text) && /depend|correlat/i.test(steps[correlations].text), "Correlations explains that a fit first populates parameter dependencies");
    }
    function test_tour_next_runs_fit_before_results_pattern_and_correlations() {
        // Accident: a learner follows Next and arrives at an empty matrix.
        start("interface");
        finishPages();
        const steps = tourSteps(), fit = steps.findIndex(step => step.target === "statusBar.fit.button");
        verify(fit >= 0 && fit + 3 < steps.length, "The tour contains Fit and its three follow-up explanations");
        verify(/fit\.results/.test(steps[fit + 1].target) && steps[fit + 2].target === "mainArea.analysis.tab.fitting" && steps[fit + 3].target === "mainArea.analysis.tab.correlations", "Fit is followed immediately by results, Pattern and Correlations");
        panel.step = fit;
        panel.show();
        settleTour();
        compare(tourFitStarted, false, "Entering the Fit explanation waits for an actual user action");
        press(one(panel, "tutorial.next"), "Next runs the described fit");
        tryVerify(() => tourFitStarted, 15000, "Next on the Fit step actually starts the real LBCO fit");
        tryVerify(() => {
            OnboardingProbe.advanceClock(16);
            return !Session.project.fit.running && panel.step === fit + 1;
        }, 15000, "The fit completes before the results explanation is shown");
        const results = Probe.visibleDialogs(app).filter(item => item.objectName === "fit.results");
        compare(results.length, 1, "The next callout explains the actual fit results window");
        aboveDialog(results[0]);
        next(fit + 3, steps.length);
        tryCompare(results[0], "visible", false, 2000, "Next accepts the results before showing the fitted Pattern");
        verify(liveTarget("mainArea.analysis.tab.fitting").checked, "The Pattern step selects the actual fitted-pattern view");
        next(fit + 4, steps.length);
        verify(liveTarget("mainArea.analysis.tab.correlations").checked, "The Correlations step selects its real matrix view");
        verify(Session.project.correlations.labels.length > 1, "A completed tour fit supplies a nonempty correlations matrix");
        const chart = liveTarget("correlations"), cells = findChild(chart, "correlations.cells");
        verify(cells !== null && cells.count > 0, "The Correlations step creates actual matrix cell delegates");
        let painted = 0;
        for (let index = 0; index < cells.count; ++index)
            if (cells.itemAt(index) && Ui.rendered(cells.itemAt(index)) && Number.isFinite(cells.itemAt(index).value))
                ++painted;
        verify(painted > 0, "The Correlations step visibly paints finite matrix values");
    }
    function test_last_step_keeps_next_visible_and_disabled_data() {
        return ["interface", "simulation", "fitting"].map(lesson => ({
                    tag: lesson,
                    lesson: lesson
                }));
    }
    function test_last_step_keeps_next_visible_and_disabled(data) {
        start(data.lesson);
        const steps = scripts().find(entry => entry.id === data.lesson).steps;
        panel.step = steps.length - 1;
        panel.show();
        settleTour();
        for (const name of ["tutorial.next", "statusBar.tutorial.next"]) {
            const button = one(app, name);
            verify(Ui.rendered(button), "Next stays visibly in its navigation row on every tutorial's last step: " + name);
            compare(button.enabled, false, "The last-step Next control is disabled rather than removed: " + name);
        }
    }
    function test_rightmost_strip_does_not_move_when_fit_status_appears() {
        start("interface");
        finishPages();
        const steps = tourSteps(), at = steps.findIndex(step => step.target === "statusBar.fit.button");
        verify(at >= 0, "The strip-position witness reaches the real Fit control");
        panel.step = at;
        panel.show();
        settleTour();
        const strip = one(app, "statusBar.tutorial"), fit = one(app, "statusBar.fit.button");
        const stripBox = Geometry.rect(strip, app.contentItem), fitBox = Geometry.rect(fit, app.contentItem);
        verify(stripBox.x > fitBox.x + fitBox.width, "The tutorial strip is after Fit at the rightmost status-bar position");
        const others = objects(app).filter(item => item.objectName.startsWith("statusBar.") && Ui.rendered(item) && !Render.descendants(strip).includes(item));
        verify(others.every(item => {
            const box = Geometry.rect(item, app.contentItem);
            return box.x <= stripBox.x || box.width > stripBox.width;
        }), "No other status-bar control group follows the tutorial strip");
        const separators = Render.descendants(strip).filter(item => Ui.rendered(item) && item.width > 0 && item.width <= 2 && item.height >= fit.height / 2 && item.color !== undefined && item.color.a > 0);
        verify(separators.some(item => Geometry.rect(item, app.contentItem).x > fitBox.x + fitBox.width), "A visible separator divides Fit from the rightmost tutorial strip");
        const actions = ["stop", "back", "next"].map(action => one(app, "statusBar.tutorial." + action));
        const before = actions.map(button => Geometry.rect(button, app.contentItem));
        verify(!Session.project.fit.canUndo, "The position witness starts before a fit adds its status");
        press(fit, "Run a real fit while the tutorial strip is visible");
        tryVerify(() => tourFitStarted, 15000, "The fit-position witness starts the actual fit worker");
        tryCompare(Session.project.fit, "running", false, 15000, "The actual fit completes before comparing strip positions");
        settleTour();
        verify(Ui.rendered(one(app, "statusBar.fit.outcome")), "The completed fit adds its visible status items for the position comparison");
        actions.forEach((button, index) => {
            const after = Geometry.rect(button, app.contentItem);
            fuzzyCompare(after.x, before[index].x, 0.01, "Fit status appearing never changes a tutorial button's horizontal screen position");
            fuzzyCompare(after.y, before[index].y, 0.01, "Fit status appearing never changes a tutorial button's vertical screen position");
        });
    }
    function test_project_name_next_preserves_input_then_targets_ok_data() {
        const rows = [];
        for (const lesson of ["simulation", "fitting"])
            for (const typed of ["", "dew"])
                rows.push({
                    tag: lesson + "-" + (typed || "empty"),
                    lesson: lesson,
                    typed: typed
                });
        return rows;
    }
    function test_project_name_next_preserves_input_then_targets_ok(data) {
        const dialog = openLessonNameDialog(data.lesson), field = findChild(dialog, "createProject.name");
        verify(field !== null, "The name action exposes the actual Create project input");
        dialog.projectParentDirectory = String(SettingsProof.emptyDirectory());
        verify(SettingsProof.type(field, data.typed), "The independent input witness leaves Name empty or types dew");
        const placeholders = Probe.objectsWithProperty(dialog, "placeholderText").map(item => item.placeholderText);
        for (const text of ["Enter project title here (optional)", "Enter authors here, separated by ; (optional)", "Enter project description here (optional)"])
            compare(placeholders.filter(value => value === text).length, 1, "Each optional Create project field has the exact recorded placeholder: " + text);
        const index = panel.step, steps = scripts().find(entry => entry.id === data.lesson).steps;
        press(one(panel, "tutorial.next"), "Next fills an empty Name or preserves the learner's name");
        progress(index + 2, steps.length);
        compare(field.text, data.typed || "lbco", "Next on Name fills lbco only when empty; typed names survive");
        verify(dialog.visible && Ui.rendered(field), "The entered name remains visibly in the open dialog during the OK instruction");
        compare(liveTarget(steps[index + 1].target), dialog.standardButton(Dialog.Ok), "The distinct step immediately after Name targets the actual OK button");
        press(one(panel, "tutorial.next"), "Next on OK creates the named project");
        tryVerify(() => Session.project !== null && !dialog.visible, 3000, "The OK action closes its dialog and creates the actual project");
        compare(Session.project.name, data.typed || "lbco", "The created project retains the name shown before OK");
    }
    function test_each_step_shows_its_short_heading_and_tutorial_identity_data() {
        return ["interface", "simulation", "fitting"].map(lesson => ({
                    tag: lesson,
                    lesson: lesson
                }));
    }
    function test_each_step_shows_its_short_heading_and_tutorial_identity(data) {
        start(data.lesson);
        const entry = scripts().find(item => item.id === data.lesson), steps = entry.steps;
        verify(steps[0].text.toLowerCase().includes(entry.title.toLowerCase()), "The first step names the tutorial in its text");
        const strip = one(app, "statusBar.tutorial");
        verify(String(strip.toolTip || strip.ToolTip.text || "").includes(entry.title), "The tutorial's name appears in the status-strip tooltip");
        for (let index = 0; index < steps.length; ++index) {
            const heading = String(steps[index].title || "").trim(), words = heading.split(/\s+/).filter(Boolean);
            verify(words.length >= 1 && words.length <= 3, "Every step declares its own one-to-three-word heading");
            panel.step = index;
            panel.show();
            settleTour();
            const progressLabel = one(panel, "tutorial.progress");
            const labels = Render.texts(panel.contentItem).filter(item => item.text === heading);
            verify(labels.some(item => Math.abs(Geometry.center(Geometry.rect(item, app.contentItem)).y - Geometry.center(Geometry.rect(progressLabel, app.contentItem)).y) <= 1), "The step's own short heading, rather than the tutorial name, is shown on the progress title row");
        }
    }
    function test_simulation_next_teaches_four_parameter_changes_in_order() {
        // Accident: a learner follows only Next and sees no parameter/filter effect.
        start("simulation");
        const steps = scripts().find(entry => entry.id === "simulation").steps;
        const expected = ["cell", "wavelength", "adp", "profile"], categories = ["Cell", "", "Atomic displacements", "Peak profile"];
        let changes = 0, cleared = true;
        for (let index = 0; index + 1 < steps.length; ++index) {
            finishPages();
            const project = Session.project, step = steps[index], analysis = step.page === "analysis" && project !== null;
            const before = analysis ? Probe.rows(project.parameters).filter(row => row.parameter).map(row => ({
                        uid: row.parameter.uid,
                        name: row.parameter.name,
                        value: row.parameter.value
                    })) : [];
            const pattern = analysis ? JSON.stringify(Probe.rows(project.currentExperiment.pattern).map(row => row.intensityCalc)) : "";
            const category = analysis ? liveTarget("parameters.category") : null, name = analysis ? liveTarget("parameters.nameFilter") : null;
            const selected = category ? category.textAt(category.currentIndex) : "", query = name ? name.text : "";
            press(one(panel, "tutorial.next"), "Next performs the Simulation example or filter instruction");
            tryVerify(() => {
                OnboardingProbe.advanceClock(16);
                return panel.step === index + 1 && (!Session.project || !Session.project.calculating);
            }, 15000, "Each Simulation action completes before inspecting its parameter and pattern effect");
            if (!analysis)
                continue;
            if (step.target === "parameters.clearFilters") {
                const model = liveTarget("parameters.list").sourceModel;
                verify(model.categoryFilter === "" && model.nameFilter === "", "The explicit clear step removes both category and name restrictions between examples");
                cleared = true;
            }
            const after = Probe.rows(project.parameters).filter(row => row.parameter).map(row => row.parameter);
            const altered = before.filter(row => after.some(parameter => parameter.uid === row.uid && !Object.is(parameter.value, row.value)));
            if (!altered.length)
                continue;
            compare(altered.length, 1, "Each parameter example changes exactly its named parameter and no other parameter");
            verify(changes < expected.length && cleared, "Each of the four ordered examples follows a cleared filter");
            const parameter = altered[0], kind = parameter.name === "length_a" ? "cell" : /wavelength/.test(parameter.name) ? "wavelength" : /adp_iso/.test(parameter.name) ? "adp" : /(^|_)w$/i.test(parameter.name) ? "profile" : "other";
            compare(kind, expected[changes], "Next changes cell a, wavelength, B iso and profile W in exactly that order");
            if (kind === "wavelength")
                compare(query, "wave", "The wavelength example uses the recorded wave name search");
            else
                verify(selected.replace(/\s*\(\d+\)$/, "") === categories[changes], "The example selects its recorded Cell, Atomic displacements or Peak profile category");
            const calculated = Probe.rows(project.currentExperiment.pattern).map(row => row.intensityCalc);
            verify(calculated.some(Number.isFinite) && JSON.stringify(calculated) !== pattern, "Each actual named parameter change updates the calculated pattern");
            ++changes;
            cleared = false;
        }
        compare(changes, 4, "Next reaches all four Simulation parameter examples, without extra parameter edits");
        verify(cleared, "The final parameter example also clears its filter before leaving Analysis");
    }
    function test_simulation_cell_length_reveals_and_selects_its_named_row() {
        // Accident: the learner scrolled past a before entering the cell-length
        // instruction. Class: a named-row callout misses its scrolled selection.
        start("simulation");
        prepareLessonProject("simulation");
        const steps = scripts().find(entry => entry.id === "simulation").steps;
        const index = steps.findIndex(step => step.page === "analysis" && /cell length a/i.test(step.text));
        verify(index >= 0, "Simulation contains the instruction to change cell length a in Analysis");
        Ui.click(test, Probe, app, "appBar.tab.analysis");
        finishPages();
        Ui.click(test, Probe, app, "sideBar.tab.basic");
        Ui.expandGroup(test, Probe, app, "group.parameters");
        const table = liveTarget("parameters.list"), model = table.sourceModel;
        model.clearFilters();
        const wanted = Session.project.currentStructure.cell.lengthA;
        const at = Probe.rows(model).findIndex(row => row.parameter && row.parameter.uid === wanted.uid);
        verify(at >= 0 && at < table.count - 1, "The real parameter inventory resolves a by name and has later rows for the scroll accident");
        table.currentIndex = table.count - 1;
        table.positionViewAtIndex(table.count - 1, ListView.End);
        table.forceLayout();
        const before = table.itemAtIndex(at);
        verify(before === null || !Ui.exposed(before), "The accident begins with the named a row genuinely outside the clipped table viewport");
        panel.step = index;
        panel.show();
        settleTour();
        const row = table.itemAtIndex(at);
        verify(row !== null && Ui.exposed(row), "The cell-length step brings its named row back into the visible table");
        const box = Geometry.rect(row, table);
        verify(box.y >= 0 && box.y + box.height <= table.height, "The entire a row, not only its header or a clipped edge, is visible");
        compare(table.currentIndex, at, "The cell-length step selects a's actual row rather than keeping the off-screen selection");
        const slider = liveTarget("parameters.slider");
        verify(slider.parent.selected && slider.parent.selected.uid === wanted.uid, "The visible slider is bound to a rather than the previously selected parameter");
        verify(slider.enabled && slider.from <= wanted.value && slider.to >= wanted.value, "The selected a slider displays an enabled range containing a's actual value");
        compare(slider.stepSize, wanted.sliderStep, "The slider step is a's own parameter range step");
        const target = Geometry.rect(row, app.contentItem);
        verify(Geometry.pointDistance(paintedPointer().tip, target) <= 4, "The pointer touches the revealed a row resolved by name");
        compare(Geometry.overlap(bodyBox(), target), 0, "The cell-length callout never covers its named row");
        compare(Geometry.overlap(bodyBox(), Geometry.rect(slider, app.contentItem)), 0, "The cell-length callout never covers a's slider");
    }
    function test_back_never_replays_an_already_satisfied_action_data() {
        return ["simulation", "fitting"].map(tutorial => ({
                    tag: tutorial,
                    tutorial: tutorial
                }));
    }
    function test_back_never_replays_an_already_satisfied_action(data) {
        // Class: arrival-triggered action replay sends Back immediately forward.
        start(data.tutorial);
        const steps = scripts().find(entry => entry.id === data.tutorial).steps;
        for (let index = 0; index + 1 < steps.length; ++index) {
            finishPages();
            press(one(panel, "tutorial.next"), "Establish the lesson's real action state before Back");
            tryVerify(() => {
                OnboardingProbe.advanceClock(16);
                return panel.step === index + 1 && (!Session.project || !Session.project.fit.running);
            }, 15000, "The actual Next action reaches the following step before the reverse walk");
        }
        for (let index = steps.length - 1; index > 0; --index) {
            press(one(panel, "tutorial.back"), "Back with earlier action states already satisfied");
            progress(index, steps.length);
            finishPages();
            for (let frame = 0; frame < 180; ++frame) {
                OnboardingProbe.advanceClock(16);
                compare(panel.step, index - 1, "Back stays on the previous step after layout and state notifications; arrival must not replay a satisfied action");
            }
            verify(waitForPolish(app), "The app settles at the previous step after Back");
            compare(panel.step, index - 1, "The previous step remains selected after the app settles");
        }
    }
    function test_callout_vertical_margins_measure_visible_ink_data() {
        return ["light", "dark"].map(theme => ({
                    tag: theme,
                    theme: theme
                }));
    }
    function test_callout_vertical_margins_measure_visible_ink(data) {
        const saved = Style.Colors.theme;
        try {
            Style.Colors.theme = data.theme === "light" ? Style.Colors.LightTheme : Style.Colors.DarkTheme;
            start("simulation");
            next(2, scripts().find(entry => entry.id === "simulation").steps.length);
            app.update();
            verify(waitForRendering(app.contentItem), "The callout paints its title and icons before measuring visible margins");
            const title = one(panel, "tutorial.title");
            verify(Ui.rendered(title), "The callout heading is visible before measuring its ink");
            chevronMetrics.font = title.font;
            const titleInk = chevronMetrics.tightBoundingRect(title.text);
            verify(titleInk.height > 0, "The actual title font supplies nonempty text-ink bounds");
            const top = title.mapToItem(app.contentItem, 0, title.baselineOffset + titleInk.y).y;
            let bottom = -Infinity;
            for (const name of ["tutorial.stop", "tutorial.back", "tutorial.next"]) {
                const labels = Render.texts(one(panel, name));
                const glyphs = labels.filter(item => !labels.some(other => other !== item && Render.descendants(item).includes(other)));
                compare(glyphs.length, 1, "Each navigation button supplies one actual icon glyph for bottom-padding measurement");
                const glyph = glyphs[0];
                verify(Ui.rendered(glyph), "Each navigation icon is visibly painted before measuring its bottom edge");
                chevronMetrics.font = glyph.font;
                const ink = chevronMetrics.tightBoundingRect(glyph.text);
                verify(ink.height > 0, "Navigation glyph ink bounds exclude the taller button hit area");
                bottom = Math.max(bottom, glyph.mapToItem(app.contentItem, 0, glyph.baselineOffset + ink.y + ink.height).y);
            }
            const box = bodyBox();
            const topGap = top - box.y, bottomGap = box.y + box.height - bottom;
            verify(topGap >= 0 && bottomGap >= 0, "Title and lowest glyph stay inside the callout body, excluding its pointer");
            verify(Math.abs(topGap - bottomGap) <= 1, "The title-ink top gap equals the lowest icon-ink bottom gap within one pixel: top=" + topGap + ", bottom=" + bottomGap);
        } finally {
            Style.Colors.theme = saved;
        }
    }
    function test_step_text_uses_unfolded_group_colour_data() {
        const rows = [];
        for (const theme of ["light", "dark"])
            for (const place of ["callout", "status"])
                rows.push({
                    tag: theme + "-" + place,
                    theme: theme,
                    place: place
                });
        return rows;
    }
    function test_step_text_uses_unfolded_group_colour(data) {
        const saved = Style.Colors.theme;
        try {
            Style.Colors.theme = data.theme === "light" ? Style.Colors.LightTheme : Style.Colors.DarkTheme;
            start("simulation");
            next(2, scripts().find(entry => entry.id === "simulation").steps.length);
            finishPages();
            app.update();
            verify(waitForRendering(app.contentItem), "Theme bindings and the unfolded group render before colour comparison");
            const groups = Render.descendants(Ui.page(app)).filter(item => item.objectName.startsWith("group.") && item.collapsed === false && item.title && item.titleArea && Ui.rendered(item.titleArea));
            verify(groups.length > 0, "The actual current sidebar supplies a visible unfolded group as the accent reference");
            const group = groups[0];
            const names = Render.texts(group.titleArea).filter(item => item.text === group.title && Ui.rendered(item));
            compare(names.length, 1, "The unfolded group's name is measured from its actual painted label");
            const progressLabel = one(panel, "tutorial.progress");
            const labels = data.place === "callout" ? [progressLabel] : Render.texts(one(app, "statusBar.tutorial")).filter(item => item.text === progressLabel.text && /^Step \d+ of \d+$/.test(item.text));
            compare(labels.length, 1, "Each tutorial surface paints one Step N of M label");
            verify(Ui.rendered(labels[0]) && labels[0].color !== undefined, "The measured tutorial step label is actually visible and painted");
            compare(labels[0].color, names[0].color, "Step N of M uses the unfolded group's accent colour in " + data.theme + " theme on the " + data.place);
        } finally {
            Style.Colors.theme = saved;
        }
    }
    function test_navigation_chevron_ink_is_centred_data() {
        return ["callout", "status"].map(place => ({
                    tag: place,
                    place: place
                }));
    }
    function test_navigation_chevron_ink_is_centred(data) {
        // The shared icon component needs no expensive measured example.
        start("simulation");
        next(2, scripts().find(entry => entry.id === "simulation").steps.length);
        const prefix = data.place === "status" ? "statusBar.tutorial." : "tutorial.";
        const buttons = {
            back: one(app, prefix + "back"),
            next: one(app, prefix + "next")
        };
        mouseMove(app.contentItem, 1, 1, 0);
        settleTour();
        for (const name of ["back", "next"]) {
            const button = buttons[name], labels = Render.texts(button);
            const glyphs = labels.filter(item => !labels.some(other => other !== item && Render.descendants(item).includes(other)));
            compare(glyphs.length, 1, "Each icon-only navigation button paints exactly one chevron label");
            const content = glyphs[0];
            verify(Ui.rendered(content), "The actual chevron glyph remains visible in its button");
            chevronMetrics.font = content.font;
            // Tight glyph bounds include the asymmetric bearings that an
            // advance-width or text-box centre misses. These are measured from
            // the rendered label's real font, independently of button padding.
            const ink = chevronMetrics.tightBoundingRect(content.text);
            const advance = chevronMetrics.advanceWidth(content.text);
            verify(ink.width > 0 && advance > 0, "The chevron's real font yields nonempty visible-ink metrics");
            const available = content.width - (content.leftPadding || 0) - (content.rightPadding || 0);
            const alignment = content.horizontalAlignment;
            const inset = alignment === Text.AlignHCenter ? (available - advance) / 2 : alignment === Text.AlignRight ? available - advance : 0;
            const origin = content.mapToItem(button, (content.leftPadding || 0) + inset, 0);
            const centre = origin.x + ink.x + ink.width / 2;
            verify(Math.abs(centre - button.width / 2) <= 1, "The chevron's visible ink is horizontally centred within one scene pixel: " + data.place + ":" + name);
        }
    }
    function test_project_text_apply_is_explained_exactly_once() {
        const steps = tourSteps(), applies = steps.map((step, index) => ({
                    step: step,
                    index: index
                })).filter(entry => entry.step.target === "text.apply");
        compare(applies.length, 1, "The tour explains the text apply button exactly once across all pages");
        const at = applies[0].index;
        verify(at > 0 && applies[0].step.page === "project" && steps[at - 1].page === "project" && steps[at - 1].target === "sideBar.tab.text", "The sole apply step immediately follows Project's Text tab step");
        verify(/Editable/.test(applies[0].step.text) && /Read.only/i.test(applies[0].step.text), "The apply instruction also names the adjacent Editable/Read-only choice");
        reach(at);
        const input = target("text.apply");
        verify(Geometry.distance(bodyBox(), Geometry.rect(input, app.contentItem)) <= 2 * one(panel, "tutorial.text").font.pixelSize, "The apply instruction is anchored beside the actual Project apply control");
    }
    function test_disabled_tabs_have_exact_text_and_enabled_tabs_are_specific() {
        start("interface");
        const steps = tourSteps(), enabled = [];
        let tabs = 0;
        for (let index = 0; index < steps.length; ++index) {
            if (index)
                next(index + 1, steps.length);
            finishPages();
            const step = steps[index];
            if (!step.target.includes(".tab."))
                continue;
            ++tabs;
            const tab = target(step.target), text = one(panel, "tutorial.text").text;
            if (!tab.enabled && /^(Stacked|Map)$/.test(tab.text)) {
                verify(/scan/i.test(text) && /patterns|temperatures/i.test(text), "A designed-disabled scan tab explains when it becomes available");
            } else if (!tab.enabled) {
                compare(text, tab.text + ": not used on this page yet.", "A disabled tab's callout contains only its exact availability explanation");
            } else {
                verify(!enabled.some(previous => previous.page !== step.page && previous.text === text), "An enabled tab never repeats the same generic explanation on another page");
                enabled.push({
                    page: step.page,
                    text: text
                });
            }
        }
        verify(tabs > 0 && enabled.length > 0, "The wording census reaches actual tabs in the tour's loaded project");
    }
    function test_tutorial_filters_reuse_examples_component() {
        AppState.open(AppState.Page.Project);
        finishPages();
        Ui.expandGroup(test, Probe, app, "group.examples");
        const reference = filterControls(Ui.control(Probe, app, "group.examples"));
        const type = Geometry.buttonComponent(reference.component);
        verify(!["Row", "GroupRow", "RowLayout", "Item"].includes(type), "The filters share a dedicated component rather than coincidentally sharing a generic layout");
        AppState.open(AppState.Page.Home);
        finishPages();
        const actual = openTutorialFilters();
        compare(Geometry.buttonComponent(actual.component), type, "Examples and Tutorials instantiate the same unchanged filter-bar component");
    }
    function test_tutorial_search_filters_text_tags_and_counts() {
        const controls = openTutorialFilters(), entries = tutorialInput();
        const queries = entries.map(entry => entry.title).concat([].concat(...entries.map(entry => entry.tags.map(tag => tag.slice(tag.indexOf(":") + 1)))), ["no-such-tutorial-unique-query", ""]);
        for (const query of queries) {
            verify(SettingsProof.type(controls.search, query), "Search is entered through the real filter text field");
            const expected = wantedTutorials(entries, query);
            tryCompare(one(chooser, "tutorials.list"), "count", expected.length, 2000, "Search updates the visible row count from tutorial text and tags");
            compare(JSON.stringify(filteredIds()), JSON.stringify(expected), "Search shows precisely the independent text/tag matches");
            const all = controls.value.textAt(0).match(/(\d+)\D*$/);
            verify(all !== null && Number(all[1]) === expected.length, "The all-values choice displays the current search count");
        }
    }
    function test_tutorial_every_category_value_filters_rows_and_counts() {
        const controls = openTutorialFilters(), entries = tutorialInput();
        const categories = Array.from(new Set([].concat(...entries.map(entry => entry.tags.map(tag => tag.slice(0, tag.indexOf(":")))))));
        verify(categories.length > 0, "The tutorial corpus exercises at least one real tag category");
        const covered = [];
        for (let category = 0; category < controls.category.count; ++category) {
            chooseFilter(controls.category, category);
            const key = controls.category.model.text(category, "value");
            covered.push(key);
            for (let option = 0; option < controls.value.count; ++option) {
                const value = controls.value.model.text(option, "value"), expected = wantedTutorials(entries, "", key, value);
                const label = controls.value.textAt(option), count = label.match(/(\d+)\D*$/);
                verify(count !== null && Number(count[1]) === expected.length, "Every category/value count equals independent tag membership: " + key + ":" + value);
                chooseFilter(controls.value, option);
                tryCompare(one(chooser, "tutorials.list"), "count", expected.length, 2000, "A selected facet narrows the actual tutorial table to the matching count");
                compare(JSON.stringify(filteredIds()), JSON.stringify(expected), "Every facet shows exactly the tutorials with its tag, without losing their row identities");
            }
            chooseFilter(controls.value, 0);
        }
        verify(categories.every(category => covered.includes(category)), "Every category used by a tutorial tag is offered in the filter bar");
    }
    function test_tutorial_rows_reuse_examples_and_table_actions_data() {
        const rows = [];
        for (const id of ["interface", "simulation", "fitting"])
            for (const fraction of [0.05, 0.5, 0.95])
                rows.push({
                    tag: id + "-" + fraction,
                    tutorial: id,
                    fraction: fraction
                });
        return rows;
    }
    function test_tutorial_rows_reuse_examples_and_table_actions(data) {
        const recent = RecentProjects.settings.recent.slice();
        try {
            RecentProjects.settings.recent = ["/missing/tutorial-row-style-reference"];
            RecentProjects.refresh();
            AppState.open(AppState.Page.Project);
            finishPages();
            Ui.expandGroup(test, Probe, app, "group.recentProjects");
            Ui.expandGroup(test, Probe, app, "group.examples");
            const examples = Ui.control(Probe, app, "examples.list");
            verify(examples !== null && examples.count > 0, "The tutorial row reference is the populated real Examples table");
            examples.positionViewAtBeginning();
            verify(waitForPolish(examples), "The independent Examples row finishes its actual table layout");
            const reference = examples.itemAtIndex(0);
            verify(reference !== null, "The independent Examples row is instantiated");
            const rowType = Geometry.buttonComponent(reference);
            hoverTreatment(reference);
            const chips = Render.descendants(reference).filter(item => item.radius > 0 && item.color !== undefined && item.color.a > 0 && item.color.a < 1 && Render.texts(item).length > 0);
            verify(chips.length > 0, "The Examples reference includes its actual coloured tag chips");
            const chipRadius = chips[0].radius, chipAlpha = chips[0].color.a;
            AppState.open(AppState.Page.Home);
            let links = [];
            tryVerify(() => {
                links = Probe.objectsWithProperty(app, "text").filter(item => item.text === "Tutorials" && Ui.rendered(item) && typeof item.clicked === "function");
                return links.length === 1;
            }, 2000, "The row-style test waits for the actual Home Tutorials link to enter the viewport");
            press(links[0], "Home Tutorials");
            tryCompare(chooser, "opened", true, 2000, "The Tutorials table is shown before its row is inspected");
            const row = one(chooser, "tutorials.row." + data.tutorial);
            compare(Geometry.buttonComponent(row), rowType, "Every tutorial uses the same row component as the real Examples table");
            // A transparent full-row input handler is the row action, not a
            // separate play button. Judge the painted affordance and rectangle.
            const plays = objects(row).filter(item => /play/.test(String(item.fontIcon || "")) || (item.objectName.startsWith("tutorials.open.") && (item.width < row.width - 1 || item.height < row.height - 1)));
            compare(plays.length, 0, "The Tutorials popup contains no separate play buttons");
            hoverTreatment(row);
            const tutorial = scripts().find(entry => entry.id === data.tutorial), ordinal = scripts().findIndex(entry => entry.id === data.tutorial) + 1;
            const labels = Render.texts(row);
            verify(labels.some(item => item.text === String(ordinal)), "A tutorial row includes its row number like Examples");
            verify(labels.some(item => item.text === tutorial.title), "The tutorial row paints its title");
            const description = labels.find(item => item.text === tutorial.description);
            verify(description !== undefined && description.lineCount === 1 && description.wrapMode === Text.NoWrap, "The tutorial row paints a single-line description like Examples");
            const badges = Render.descendants(row).filter(item => item.radius > 0 && item.color !== undefined && item.color.a > 0 && item.color.a < 1 && Render.texts(item).length > 0);
            verify(badges.length > 0, "Every tutorial row contains visible coloured tag chips");
            for (const badge of badges) {
                compare(badge.radius, chipRadius, "Tutorial chips use the Examples chip shape");
                fuzzyCompare(badge.color.a, chipAlpha, 1 / 255, "Tutorial chips use the Examples translucent colour treatment");
            }
            clickTutorialRow(row, data.fraction);
            tryCompare(panel, "opened", true, 2000, "Clicking the row's number, middle or trailing space starts its tutorial");
            compare(panel.tutorial.id, data.tutorial, "Each row starts its own tutorial, not another row's script");
        } finally {
            RecentProjects.settings.recent = recent;
            RecentProjects.refresh();
        }
    }
}
