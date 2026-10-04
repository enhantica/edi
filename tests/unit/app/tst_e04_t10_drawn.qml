import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import EdiChartReference 1.0
import EdiStructureReference 1.0
import "UiInteraction.js" as Ui
import "E04Review.js" as Review
import "../../../app/qml/Components" as Components

// Run by hand on app-test-3d. A VM run is correctness evidence only;
// StructureOracle records the actual graphics renderer and forbids a VM bank.
TestCase {
    id: test
    name: "E04T10StructureDrawn"
    when: windowShown
    property var appWindow
    property var view
    property bool drivingFrames: false
    property int frameSteps: 0
    property var editField: null
    Component {
        id: coordinateField
        Components.ParameterField {}
    }
    Connections {
        target: StructureOracle
        function onNextFrame() {
            if (test.drivingFrames && test.frameSteps < 56) {
                ++test.frameSteps;
                test.mouseMove(test.view, test.view.width * .4 + test.frameSteps, test.view.height * .5);
            }
        }
    }
    Component {
        id: application
        Main {}
    }
    function init() {
        Session.closeProject();
        appWindow = application.createObject(null);
        verify(appWindow !== null, " I16 drawn gates require the real app window");
        appWindow.requestActivate();
        // Cocoa may expose/render the production window without making it the
        // OS-active window. Pointer events already name their production item;
        // Return below names this window explicitly instead of focusWindow().
        tryCompare(appWindow, "visible", true, 2000, " O1 input reaches the visible production window");
        verify(waitForRendering(appWindow.contentItem), " O1 production window renders before real input");
    }
    function cleanup() {
        if (view && view.controller)
            tryCompare(view.controller, "animating", false, 5000, " animated view finishes before the next real app window is opened");
        view = null;
        drivingFrames = false;
        StructureOracle.disarm();
        if (editField) {
            editField.destroy();
            editField = null;
        }
        Session.closeProject();
        appWindow.destroy();
    }
    function open(path) {
        verify(Session.openProject(Probe.repoUrl(path || "docs/user/cli/pd-neut-tof_ncaf-wish-2bank_start-3/project")), " amended M1 project fixture opens through the real app: " + Session.lastError);
        if (path && path.indexOf("docs/user/cli/") < 0) {
            const experiments = Probe.rows(Session.project.experiments);
            compare(experiments.length, 1, " amended M1 saved fixture retains exactly one experiment");
            verify(Session.project.currentExperiment.calculationOnly, " amended M1 saved fixture retains a calculation-only grid");
        }
        Ui.click(test, Probe, appWindow, "appBar.tab.structure");
        tryVerify(() => Review.find(Ui.page(appWindow), "structure.view") !== null, 5000, " I16 selected page contains the actual Quick 3D view");
        view = Review.find(Ui.page(appWindow), "structure.view");
        tryCompare(Session.project, "calculating", false, 10000, " I12 initial project calculation completes before the drawn scenario");
        tryVerify(() => view.current, 10000, " I12 drawn view waits for actual current publication");
        settledView();
        // First-use style/font layout may finish after the scene's publication
        // and frame. Prove toolbar readiness here, before any camera input;
        // clickViewButton must remain immediate when it retargets a moving turn.
        verify(waitForPolish(view, 2000), " animated view toolbar layout finishes before the first production button input");
        tryVerify(() => ["projection", "a", "b", "c", "reset"].every(name => {
                    const button = Review.find(view, "structure.toolbar." + name) || ChartOracle.object(view, "structure.toolbar." + name);
                    return button !== null && button.enabled && Ui.exposed(button);
                }), 2000, " animated view camera toolbar is enabled and exposed before the first production button input");
    }
    function object(name) {
        const result = Review.find(view, name) || ChartOracle.object(view, name);
        verify(result !== null, " P5 drawn gate finds the declared object: " + name);
        return result;
    }
    // Completion is controller state followed by a rendered frame, never elapsed time.
    // This also keeps animation frames outside A1/A2's existing measured intervals.
    function settledView() {
        tryCompare(view.controller, "animating", false, 5000, " animated view reaches its final state before measurement or picking");
        verify(waitForRendering(view), " animated view final state reaches the real rendered frame");
    }
    function clickViewButton(name) {
        const button = object("structure.toolbar." + name);
        verify(button.enabled && Ui.exposed(button), " animated view input uses the exposed production toolbar button");
        // The geometry is already laid out; waitForPolish during an active turn
        // would wait for the very animation that the retarget input must interrupt.
        mouseClick(button, button.width / 2, button.height / 2);
    }
    function cameraState() {
        const controller = view.controller;
        const q = controller.cameraRotation;
        const p = controller.cameraPosition;
        const centre = controller.projectedCentre(0);
        return {
            rotation: [q.scalar, q.x, q.y, q.z],
            position: [p.x, p.y, p.z],
            centre: [centre.x, centre.y],
            zoom: controller.magnification,
            projection: controller.projection
        };
    }
    function rotationGap(a, b) {
        const dot = a.reduce((sum, value, index) => sum + value * b[index], 0);
        return 1 - Math.abs(dot); // q and -q describe the same orientation.
    }
    function verifyCamera(actual, expected) {
        verify(Math.abs(rotationGap(actual.rotation, expected.rotation)) < 1e-6, " animation endpoint orientation equals the instant view up to quaternion sign");
        actual.position.forEach((value, i) => verify(Math.abs(value - expected.position[i]) < .001, " animation endpoint camera position equals the instant fitted view"));
        actual.centre.forEach((value, i) => verify(Math.abs(value - expected.centre[i]) < .001, " animation endpoint restores the same independently chosen atom pixel and pan as the instant view"));
        verify(Math.abs(actual.zoom - expected.zoom) < 1e-9, " animation endpoint zoom equals the instant fitted view");
        compare(actual.projection, expected.projection, " animation preserves the selected camera projection");
    }
    function rotatedBasis(q, v) {
        const u = [q[1], q[2], q[3]];
        const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
        const uv = cross(u, v);
        const uuv = cross(u, uv);
        return v.map((value, i) => value + 2 * (q[0] * uv[i] + uuv[i]));
    }
    function verifyCubicTarget(name, state) {
        // Independent cubic P1 fixture: a=(10,0,0), b=(0,10,0), c=(0,0,10).
        // Diffraction-lib's equal-length tie order gives a rightward horizontal
        // axis and the remaining axis upward. Home uses seam rows 12 and 14.
        const length = Math.sqrt(.37 * .37 + .24 * .24 + .90 * .90);
        const home = [.37 / length, .24 / length, .90 / length];
        const homeUp = [-home[1] * home[0], 1 - home[1] * home[1], -home[1] * home[2]];
        const upLength = Math.sqrt(homeUp.reduce((sum, value) => sum + value * value, 0));
        const directions = {
            a: [1, 0, 0],
            b: [0, -1, 0],
            c: [0, 0, 1],
            reset: home
        };
        const ups = {
            a: [0, 0, 1],
            b: [0, 0, 1],
            c: [0, 1, 0],
            reset: homeUp.map(value => value / upLength)
        };
        rotatedBasis(state.rotation, [0, 0, 1]).forEach((value, i) => verify(Math.abs(value - directions[name][i]) < 1e-5, " I9/I13 animation target direction obeys the independent cubic-axis or diffraction-lib home formula"));
        rotatedBasis(state.rotation, [0, 1, 0]).forEach((value, i) => verify(Math.abs(value - ups[name][i]) < 1e-5, " I9/I13 animation target up vector obeys the independent cubic-axis or diffraction-lib home formula"));
        verify(Math.abs(state.zoom - .9) < 1e-9, " owner home zoom applies 0.9 to the fitted button target");
    }
    function disturbCamera() {
        view.controller.rotateBy(41, 23);
        view.controller.zoomAt(view.width * .45, view.height * .55, 120);
        view.controller.panBy(13, -17);
    }
    function test_animated_view_endpoint_data() {
        const rows = [];
        ["orthographic", "perspective"].forEach(projection => ["a", "b", "c", "reset"].forEach(button => rows.push({
                    tag: projection + "-" + button,
                    projection: projection,
                    button: button
                })));
        return rows;
    }
    function test_animated_view_endpoint(data) {
        open(StructureOracle.pickFixture(.2));
        const controller = view.controller;
        compare(controller.viewAnimationDuration, 1000, " owner animation uses the base's 1000 ms duration");
        if (data.projection === "perspective")
            clickViewButton("projection");
        compare(controller.projection, data.projection, " animated endpoint case reaches its requested projection");
        controller.viewAnimationDuration = 0;
        clickViewButton(data.button);
        compare(controller.animating, false, " zero-duration view button takes the instant path");
        const instant = cameraState();
        verifyCubicTarget(data.button, instant);
        disturbCamera();
        const start = cameraState();
        verify(rotationGap(start.rotation, instant.rotation) > .001, " animation begins from a nontrivially rotated view");
        verify(Math.abs(start.zoom - instant.zoom) > .01, " animation begins from a nontrivially zoomed view");
        controller.viewAnimationDuration = 1000;
        clickViewButton(data.button);
        verify(controller.animating, " positive-duration production button starts an actual animation");
        tryVerify(() => controller.animating && rotationGap(cameraState().rotation, start.rotation) > 1e-5 && rotationGap(cameraState().rotation, instant.rotation) > 1e-5, 5000, " animation renders an intermediate orientation rather than jumping to its endpoint");
        verify(waitForRendering(view), " animation intermediate state reaches the real view");
        settledView();
        const end = cameraState();
        verifyCamera(end, instant); // Invariant between paths, not a generated golden.
        verifyCubicTarget(data.button, end);
    }
    function test_animated_view_retarget_data() {
        return [
            {
                tag: "orthographic-a-to-b",
                first: "a",
                next: "b",
                projection: "orthographic"
            },
            {
                tag: "orthographic-home-to-c",
                first: "reset",
                next: "c",
                projection: "orthographic"
            },
            {
                tag: "perspective-b-to-home",
                first: "b",
                next: "reset",
                projection: "perspective"
            },
            {
                tag: "perspective-c-to-a",
                first: "c",
                next: "a",
                projection: "perspective"
            }
        ];
    }
    function test_animated_view_retarget(data) {
        open(StructureOracle.pickFixture(.2));
        const controller = view.controller;
        if (data.projection === "perspective")
            clickViewButton("projection");
        controller.viewAnimationDuration = 0;
        clickViewButton(data.next);
        const target = cameraState();
        verifyCubicTarget(data.next, target);
        clickViewButton(data.first);
        const abandoned = cameraState();
        disturbCamera();
        const start = cameraState();
        controller.viewAnimationDuration = 1000;
        clickViewButton(data.first);
        tryVerify(() => controller.animating && rotationGap(cameraState().rotation, start.rotation) > 1e-5 && rotationGap(cameraState().rotation, abandoned.rotation) > 1e-5, 5000, " retarget is issued during a genuinely moving unfinished turn");
        // Deliver input immediately, without a polish/render wait that finishes the turn.
        clickViewButton(data.next);
        verify(controller.animating, " mid-turn production button keeps the retarget animation active");
        settledView();
        const end = cameraState();
        verifyCamera(end, target);
        verifyCubicTarget(data.next, end);
        verify(rotationGap(end.rotation, abandoned.rotation) > .01, " mid-turn retarget finishes at the new target instead of the abandoned one");
    }
    function inputField(parameter) {
        editField = coordinateField.createObject(appWindow.contentItem, {
            item: parameter,
            x: 12,
            y: appWindow.contentItem.height - 80,
            width: 180
        });
        verify(editField !== null && editField.enabled, " A2 uses the production coordinate input bound to the real independent parameter");
    }
    function test_instance_readback_and_drag_retains_buffers() {
        open();
        const expected = StructureOracle.reference("docs/user/cli/pd-neut-tof_ncaf-wish-2bank_start-3/project");
        const spheres = object("structure.view.spheres");
        const actual = StructureOracle.instances(spheres);
        compare(actual.length, expected.length, " I16 C++ sphere buffer covers the independent engine positions");
        actual.forEach((row, i) => ["x", "y", "z"].forEach(key => compare(row[key], Math.fround(expected[i][key]), " seam 11 Qt's float readback is the nearest float to the engine coordinate")));
        verify(StructureOracle.watch(spheres), " I16 buffer signal is observable on the real table");
        mouseDrag(view, view.width * .4, view.height * .5, 24, 12);
        compare(StructureOracle.changes(), 0, " I16 a pointer drag never repacks the instance table");
        const colors = object("structure.toolbar.colors");
        mouseClick(colors, colors.width / 2, colors.height / 2);
        tryCompare(colors.popup, "opened", true, 2000, " I18 palette input opens its real popup");
        const list = colors.popup.contentItem;
        tryVerify(() => list.itemAtIndex(1) !== null, 2000, " I18 opened palette popup materialises VESTA");
        const vesta = list.itemAtIndex(1);
        compare(vesta.text, "vesta", " I18 input selects the independently named palette entry");
        mouseClick(vesta, vesta.width / 2, vesta.height / 2);
        tryCompare(colors, "currentIndex", 1, 2000, " O1 palette change reached the production control");
        tryVerify(() => StructureOracle.changes() === 1, 2000, " I16 one changed palette repacks each table exactly once");
    }
    function test_real_edit_to_synchronised_sphere_frame() {
        open();
        const parameter = Probe.rows(Session.project.currentStructure.atomSites)[0].fractX;
        verify(parameter !== undefined, " M2 real atom-site model exposes the first independent coordinate");
        const target = parameter.value + .001;
        inputField(parameter);
        const expected = StructureOracle.reference("docs/user/cli/pd-neut-tof_ncaf-wish-2bank_start-3/project", target)[0];
        verify(StructureOracle.arm(appWindow, view, expected), " O2 observer watches real synchronisation and swapped-frame signals");
        verify(StructureOracle.watchPublication(Session.project), " I12 actual publication signal is observed directly");
        mouseClick(editField, editField.width / 2, editField.height / 2);
        editField.forceActiveFocus();
        verify(editField.activeFocus, " O1 actual parameter field owns keyboard focus");
        editField.text = String(target);
        StructureOracle.start();
        verify(StructureOracle.returnKey(appWindow, editField), " O1 Return is delivered through the real production window to its focused parameter field");
        compare(parameter.value, target, " O1 Return committed the independently requested input");
        tryVerify(() => StructureOracle.result().complete, 10000, " M6 completion is the first swapped frame whose real instance has the independently requested position");
        const result = StructureOracle.result();
        verify(!result.superseded, " I12 a superseded current scene never reaches the synchronised frame");
        verify(StructureOracle.guiPublication(), " I12 publication signal originates on the GUI thread");
        verify(result.update_ms > 0, " O1 real frame completion follows the input-side monotonic clock");
        console.log(" real-update diagnostic " + JSON.stringify(result));
    }
    function test_shared_site_hover_uses_hit_surface_data() {
        return [
            {
                tag: "contained",
                near: .2,
                label: "La/Ba"
            },
            {
                tag: "in-front",
                near: .7,
                label: "H/He"
            }
        ];
    }
    function test_shared_site_hover_uses_hit_surface(data) {
        open(StructureOracle.pickFixture(data.near));
        const along = object("structure.toolbar.c");
        clickViewButton("c");
        settledView();
        tryVerify(() => Math.abs(view.controller.cameraPosition.x - 5) < .02, 2000, " I15 real c-axis input reaches the independently aligned camera");
        const top = along.mapToItem(view, 0, 0).y;
        const band = along.height + 2 * top;
        const x = view.width / 2 + 1;
        const y = view.height / 2 + band / (2 * (1 + band / view.height)) + 1;
        // P1 cell, positions at (5,5,5) and (5,5,5+near), view along c.
        // A's .4316-Angstrom surface encloses B for near=.2, although B's
        // centre is nearer that front surface. For .7 B is exposed in front.
        // A one-pixel offset avoids the shared mesh's pole and still passes
        // through both spheres under M1's independent radius/fit formulas.
        verify(waitForRendering(view), " I15 the selected c-axis camera reaches an actual rendered frame before picking");
        const hit = view.view3d.pick(x, y);
        verify(hit.objectHit !== null, " I15 independently placed hover ray reaches real rendered geometry");
        console.log(" pick diagnostic " + JSON.stringify({
            expected: data.label,
            point: [x, y],
            object: hit.objectHit.objectName,
            uv: [hit.uvPosition.x, hit.uvPosition.y],
            position: [hit.scenePosition.x, hit.scenePosition.y, hit.scenePosition.z]
        }));
        mouseMove(view, x, y);
        tryVerify(() => object("structure.view.hover").text.indexOf(data.label) >= 0, 3000, " I15 hover identity follows the actual hit triangle rather than the nearest centre; expected=" + data.label + "; actual=" + object("structure.view.hover").text);
    }
    function test_rotating_frame_measurement_data() {
        return StructureOracle.datasets();
    }
    function test_rotating_frame_measurement(data) {
        open(data.path);
        settledView();
        const expected = StructureOracle.reference(data.path)[0];
        verify(StructureOracle.arm(appWindow, view, expected), " A1 measures the real render window's swapped frames");
        frameSteps = 0;
        drivingFrames = true;
        mousePress(view, view.width * .4, view.height * .5);
        mouseMove(view, view.width * .4 + .5, view.height * .5);
        tryVerify(() => StructureOracle.result().frames_ms.length >= 55, 30000, " A1 every swapped frame drives the next real one-pixel drag without test polling in the measured interval");
        drivingFrames = false;
        mouseRelease(view, view.width * .4 + 56, view.height * .5);
        const result = StructureOracle.result();
        const samples = result.frames_ms.slice(5, 55).sort((a, b) => a - b);
        compare(samples.length, 50, " M2 frame metric has fifty samples after five warmups");
        verify(samples.every(value => value > 0 && isFinite(value)), " A1 observed swapped-frame intervals are finite positive measurements");
        console.log(JSON.stringify({
            dataset: data.tag,
            scenario: "A1",
            samples: 50,
            warmups: 5,
            frame: {
                median_ms: samples[24],
                p95_ms: samples[47]
            },
            renderer: result.renderer,
            performanceReference: result.performanceReference,
            bankAllowed: result.performanceReference
        }));
    }
    function test_update_frame_measurement_data() {
        return StructureOracle.datasets();
    }
    function test_update_frame_measurement(data) {
        open(data.path);
        const parameter = Probe.rows(Session.project.currentStructure.atomSites)[0].fractX;
        verify(parameter !== undefined, " A2 input reaches the first independent site coordinate");
        const base = parameter.value;
        inputField(parameter);
        const samples = [];
        let renderer = "";
        let gpu = false;
        for (let i = 0; i < 55; ++i) {
            const requested = base + .001 * (1 + i % 2);
            const expected = StructureOracle.reference(data.path, requested)[0];
            verify(StructureOracle.arm(appWindow, view, expected), " A2 completion watches the real requested sphere at synchronisation");
            mouseClick(editField, editField.width / 2, editField.height / 2);
            editField.forceActiveFocus();
            verify(editField.activeFocus, " O1 each actual parameter input owns keyboard focus");
            editField.text = String(requested);
            StructureOracle.start();
            verify(StructureOracle.returnKey(appWindow, editField), " O1 each Return is delivered through the real production window to its focused parameter field");
            compare(parameter.value, requested, " O1 each Return committed the independently requested input");
            tryVerify(() => StructureOracle.result().complete, 10000, " M6 each real update finishes only when its independently requested scene is swapped");
            const result = StructureOracle.result();
            verify(!result.superseded, " I12 no superseded current scene is counted as an update");
            if (i >= 5)
                samples.push(result.update_ms);
            renderer = result.renderer;
            gpu = result.performanceReference;
        }
        samples.sort((a, b) => a - b);
        compare(samples.length, 50, " M2 update metric has fifty samples after five discarded warmups");
        verify(samples.every(value => value > 0 && isFinite(value)), " A2 real input-to-swapped-frame times are positive measured intervals");
        console.log(JSON.stringify({
            dataset: data.tag,
            scenario: "A2",
            samples: 50,
            warmups: 5,
            update: {
                median_ms: samples[24],
                p95_ms: samples[47]
            },
            renderer: renderer,
            performanceReference: gpu,
            bankAllowed: gpu
        }));
    }
}
