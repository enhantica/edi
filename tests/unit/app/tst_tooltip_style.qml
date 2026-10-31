import QtQuick
import QtQuick.Controls
import QtQuick.Templates as T
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import EasyApplication.Gui.Elements as Elements
import EasyApplication.Gui.Components as Components
import EasyApplication.Gui.Globals as Globals
import EasyApplication.Gui.Style as Style
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render

TestCase {
    id: test
    name: "ToolTipStyle"
    when: windowShown
    property var app
    property bool savedAutoCollapse
    property bool savedPreference
    Component {
        id: factory
        Main {}
    }
    Component {
        id: styled
        Elements.ToolTip {
            text: "Independent style reference"
        }
    }
    Component {
        id: warningStyle
        WarningToolTip {}
    }
    Component {
        id: fontMeasure
        FontMetrics {}
    }
    Component {
        id: lazyLabel
        Components.ListViewLabel {
            width: 16
            height: 24
            text: "An independently authored long table description must render the application's lazy tooltip delegate"
        }
    }
    Component {
        id: anchorFactory
        Item {
            width: 40
            height: 30
            x: 300
            y: 300
        }
    }
    Component {
        id: plain
        ToolTip {
            text: "Qt default counterexample"
            property bool appStyled: true
        }
    }
    function inheritedStyle(tip) {
        if (!(tip instanceof Elements.ToolTip) || !tip.background)
            return false;
        const body = Render.descendants(tip.background);
        return body.some(item => item.rotation === 45 && item.width > 0 && item.height > 0) && body.some(item => item.radius > 0 && item.width > 0 && item.height > 0);
    }
    function objects() {
        return Probe.objectsWithProperty(app, "visible");
    }
    function tips() {
        return SettingsProof.tooltipObjects(app).filter(item => item instanceof T.ToolTip);
    }
    function fast(tip) {
        tip.delay = 0;
        tip.timeout = -1;
        if (typeof tip.enterAnimationDuration === "number")
            tip.enterAnimationDuration = 0;
        if (typeof tip.exitAnimationDuration === "number")
            tip.exitAnimationDuration = 0;
    }
    function click(name) {
        let item;
        tryVerify(() => {
            item = Ui.control(Probe, app, name);
            return item !== null && item.enabled && Ui.clickPoint(item) !== null && !Ui.moving(app.contentItem);
        }, 4000, "The tooltip route exposes its actual settled control: " + name);
        verify(waitForPolish(item), "The tooltip route control finishes its own layout before input");
        const point = Ui.clickPoint(item);
        mouseClick(item, point.x, point.y);
        app.update();
        verify(waitForRendering(app.contentItem), "The tooltip route input reaches an actual rendered frame");
    }
    function init() {
        savedPreference = Globals.Vars.showToolTips;
        savedAutoCollapse = Globals.Vars.autoCollapseSideBarGroups;
        Globals.Vars.autoCollapseSideBarGroups = false;
        Globals.Vars.showToolTips = true;
    }
    function cleanup() {
        SettingsProof.endAnimationClock();
        if (app) {
            app.close();
            app.destroy();
        }
        app = null;
        Session.closeProject();
        Globals.Vars.showToolTips = savedPreference;
        Globals.Vars.autoCollapseSideBarGroups = savedAutoCollapse;
    }
    function test_counterexamples() {
        verify(!isBalanced({
            lines: 2,
            last: "is",
            lastWidth: 10,
            widestWidth: 100
        }), "A short orphan final word fails the balance reference");
        verify(isBalanced({
            lines: 2,
            last: "calibration",
            lastWidth: 25,
            widestWidth: 100
        }), "A long unsplittable final word is not mistaken for a short orphan");
        const good = styled.createObject(test), bad = plain.createObject(test);
        good.parent = test;
        bad.parent = test;
        fast(good);
        fast(bad);
        good.open();
        bad.open();
        tryCompare(good, "opened", true, 2000, "The positive style reference is a real opened tooltip");
        tryCompare(bad, "opened", true, 2000, "The Qt default counterexample is a real opened tooltip");
        verify(inheritedStyle(good), "The app's actual tooltip type and arrow background are accepted");
        verify(!inheritedStyle(bad), "A plain Qt tooltip cannot impersonate the app style with a marker property");
        bad.close();
        good.close();
        bad.destroy();
        good.destroy();
    }
    function textLabel(tip) {
        return Render.descendants(tip.contentItem).find(item => typeof item.lineCount === "number" && item.text === tip.text);
    }
    function widthFacts(tip) {
        const label = textLabel(tip), metrics = fontMeasure.createObject(test, {
            font: tip.font
        });
        verify(label !== undefined, "A rendered tooltip exposes its actual text item for wrapping measurements");
        const scene = tip.contentItem.mapToItem(app.contentItem, 0, 0, tip.contentItem.width, tip.contentItem.height);
        const facts = {
            width: tip.width,
            textWidth: label.width,
            characters: label.width / metrics.averageCharacterWidth,
            lines: label.lineCount,
            wrap: label.wrapMode,
            window: app.width,
            left: scene.x - tip.leftPadding,
            right: scene.x + scene.width + tip.rightPadding
        };
        metrics.destroy();
        return facts;
    }
    function popupRect(tip) {
        return tip.background.mapToItem(app.contentItem, 0, 0, tip.background.width, tip.background.height);
    }
    function sourceRect(source) {
        return source.mapToItem(app.contentItem, 0, 0, source.width, source.height);
    }
    function intersects(a, b) {
        return a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height;
    }
    function placementErrors(tip, source, modal) {
        const popup = popupRect(tip), control = sourceRect(source), issues = [];
        const below = popup.y >= control.y + control.height, above = popup.y + popup.height <= control.y;
        if (intersects(popup, control))
            issues.push("covers its source");
        if (app.height - control.y - control.height >= popup.height + tip.margins * 2) {
            if (!below)
                issues.push("not below despite available room");
        } else if (!above)
            issues.push("does not move above when below has no room");
        if (modal) {
            const choices = Render.descendants(modal.contentItem).filter(item => /^(?:saveAs|open)\.(?:folder|zip|copy)$/.test(item.objectName));
            const others = choices.filter(item => item !== source && item.visible).map(sourceRect);
            const bottom = Math.max(control.y + control.height, ...others.map(rect => rect.y + rect.height));
            if (app.height - bottom >= popup.height + tip.margins * 2 && others.some(rect => intersects(popup, rect)))
                issues.push("covers another dialog choice despite room below the choices");
        }
        return issues;
    }
    function lineFacts(tip) {
        const label = textLabel(tip), lines = SettingsProof.tooltipTextLines(label, label.wrapMode === Text.WordWrap || label.wrapMode === Text.Wrap, label.wrapMode === Text.WrapAnywhere || label.wrapMode === Text.Wrap);
        if (lines.length !== label.lineCount)
            console.log("TOOLTIP_LAYOUT_MISMATCH " + JSON.stringify({
                text: label.text,
                actual: label.lineCount,
                observed: lines,
                width: label.width,
                wrap: label.wrapMode
            }));
        verify(lines.length === label.lineCount, "Public Qt line layout must match the actual rendered tooltip line count before its last line is examined");
        return {
            alignment: label.horizontalAlignment,
            lines: label.lineCount,
            last: lines.length ? lines[lines.length - 1].text : "",
            lastWidth: lines.length ? lines[lines.length - 1].width : 0,
            widestWidth: Math.max(0, ...lines.map(line => line.width))
        };
    }
    function isBalanced(facts) {
        const words = facts.last.match(/[A-Za-z0-9]+/g) || [];
        // The qualitative record forbids a short orphan word, not a long word
        // such as "calibration". Qualify short words by both length and rendered width.
        return facts.lines <= 1 || words.length !== 1 || words[0].length > 5 || facts.lastWidth >= facts.widestWidth / 3;
    }
    function test_balanced_placement() {
        app = factory.createObject(null, {
            width: 1280,
            height: 720,
            visible: true
        });
        verify(app !== null, "Tooltip placement uses an actual application window");
        app.requestActivate();
        const anchor = anchorFactory.createObject(app.contentItem), receipts = [];
        for (const component of [styled, warningStyle]) {
            for (const text of ["Write the project there and keep working where it is", "Site Fe2: its Uani tensor has a negative eigenvalue; its Debye-Waller factor grows with the reflection instead of falling. Fix or reset its U values."]) {
                for (const bottom of [false, true]) {
                    anchor.y = bottom ? app.height - anchor.height - 3 : 30;
                    const tip = component.createObject(anchor, {
                        text
                    });
                    tip.parent = anchor;
                    fast(tip);
                    tip.open();
                    tryCompare(tip, "opened", true, 2000, "The tooltip is open at the chosen actual source position");
                    app.update();
                    verify(waitForRendering(app.contentItem), "Tooltip line breaks and placement are measured from a rendered frame");
                    receipts.push({
                        lines: lineFacts(tip),
                        placement: placementErrors(tip, anchor, null),
                        popup: popupRect(tip),
                        source: sourceRect(anchor)
                    });
                    tip.close();
                    tip.destroy();
                }
            }
        }
        console.log("TOOLTIP_BALANCE_PLACEMENT " + JSON.stringify(receipts));
        for (const row of receipts) {
            verify(row.lines.lines > 1, "The balance witnesses actually render several lines");
            compare(row.lines.alignment, Text.AlignLeft, "Wrapped tooltip text aligns left");
            verify(isBalanced(row.lines), "Wrapped text has no single short word alone on its actual last line");
            compare(row.placement.length, 0, "A tooltip is below its control, or above only when below lacks room: " + row.placement.join("; "));
        }
        anchor.y = 30;
        const short = styled.createObject(anchor, {
            text: "A short hint"
        });
        short.parent = anchor;
        fast(short);
        short.open();
        tryCompare(short, "opened", true, 2000, "The one-line prior-art tooltip is actually open");
        const single = lineFacts(short);
        compare(single.lines, 1, "The one-line prior-art tooltip keeps one line");
        compare(single.alignment, Text.AlignHCenter, "One-line tooltips retain the prior app alignment");
        short.close();
        short.destroy();
        anchor.destroy();
    }
    function disabledVisuals(control) {
        return JSON.stringify(Render.descendants(control.indicator).filter(item => item.visible).map(item => ({
                    visible: item.visible,
                    color: typeof item.color !== "undefined" ? String(item.color) : null,
                    border: typeof item.border !== "undefined" ? String(item.border.color) : null
                })));
    }
    function test_disabled_choice_class() {
        app = SettingsProof.tooltipPlatformMain(test, true, false);
        verify(app !== null, "The disabled-choice gate uses actual fallback app QML");
        app.requestActivate();
        tryCompare(app, "active", true, 2000, "The actual disabled controls receive trusted hover and press input");
        const dialog = findChild(app, "saveAs.choice");
        dialog.open();
        tryCompare(dialog, "opened", true, 2000, "The unsupported Folder choice is visible in the actual Save-as dialog");
        const folder = findChild(dialog.contentItem, "saveAs.folder");
        verify(folder && !folder.enabled, "A browser without disk access fully disables the actual Folder choice");
        for (const tip of tips())
            fast(tip);
        for (const checked of [false, true]) {
            folder.checked = checked;
            tryCompare(folder.contentItem, "color", Style.Colors.themeForegroundDisabled, 2000, "The disabled choice label uses the app disabled colour");
            tryCompare(folder.indicator.border, "color", Style.Colors.themeForegroundDisabled, 2000, "The disabled radio indicator uses the same disabled colour whether checked or unchecked");
            const before = disabledVisuals(folder);
            for (const x of [folder.indicator.x + folder.indicator.width / 2, folder.width - 2]) {
                mouseMove(folder, x, folder.height / 2, 0);
                app.update();
                verify(waitForRendering(app.contentItem), "Disabled hover feedback is inspected after an actual rendered frame");
                compare(disabledVisuals(folder), before, "Neither indicator nor label area adds hover feedback to a disabled choice");
                mousePress(folder, x, folder.height / 2);
                app.update();
                verify(waitForRendering(app.contentItem), "Disabled press feedback is inspected while the real pointer is held down");
                compare(disabledVisuals(folder), before, "A disabled choice has no press feedback");
                verify(!folder.down, "A disabled radio cannot enter its pressed state");
                mouseRelease(folder, x, folder.height / 2);
                compare(folder.checked, checked, "Pressing a disabled choice never changes its selected state");
            }
        }
        const shown = tips().filter(tip => tip.visible && /folder/i.test(tip.text));
        verify(shown.length > 0 && shown.every(inheritedStyle), "The disabled Folder explanation is a rendered app-style tooltip");
        verify(shown.some(tip => /Chrome/.test(tip.text) && /Edge/.test(tip.text)), "The actual disabled choice tooltip names why this browser cannot write a folder");
        dialog.close();
    }
    function test_shared_wrap_width() {
        app = factory.createObject(null, {
            width: 1280,
            height: 720,
            visible: true
        });
        verify(app !== null, "Tooltip wrapping is measured in an actual application window");
        app.requestActivate();
        const anchor = anchorFactory.createObject(app.contentItem);
        const longText = "Site Fe2: its anisotropic U tensor is not positive semi-definite because it has a negative eigenvalue; its Debye-Waller factor grows with the reflection instead of falling. Fix or reset its U values before fitting.";
        const facts = [];
        for (const width of [1280, 320]) {
            app.width = width;
            anchor.x = Math.min(300, width / 2);
            for (const component of [styled, warningStyle]) {
                const tip = component.createObject(anchor, {
                    text: longText
                });
                tip.parent = anchor;
                fast(tip);
                tip.open();
                tryCompare(tip, "opened", true, 2000, "The long ordinary or warning tooltip is actually opened");
                app.update();
                verify(waitForRendering(app.contentItem), "Long tooltip width and lines come from a rendered frame");
                const row = widthFacts(tip);
                facts.push(row);
                console.log("TOOLTIP_WRAP " + JSON.stringify(row));
                tip.close();
                tip.destroy();
            }
        }
        for (const row of facts) {
            verify(row.characters <= 50.5 && (row.window < 600 || row.characters >= 39.5), "The common tooltip text limit spans about 40-50 average app-font characters, bounded by its window");
            verify(row.lines > 1 && row.wrap !== Text.NoWrap, "A long tooltip actually wraps onto several rendered lines");
            verify(row.width <= row.window && row.left >= 0 && row.right <= row.window, "A wrapped tooltip stays inside its actual window");
        }
        compare(facts[0].textWidth, facts[1].textWidth, "Ordinary and warning tooltips share one actual maximum text width");
        compare(facts[2].textWidth, facts[3].textWidth, "Ordinary and warning tooltips share their window-constrained maximum width");
        const label = lazyLabel.createObject(app.contentItem, {
            x: 120,
            y: 120
        });
        verify(label !== null, "The lazy-tooltip control is the pinned app table-label type");
        mouseMove(label, label.width / 2, label.height / 2);
        tryVerify(() => tips().some(tip => tip.visible && tip.text === label.text), 2000, "Truncating and hovering the actual table label instantiates its real tooltip");
        verify(tips().filter(tip => tip.visible && tip.text === label.text).every(inheritedStyle), "A lazily instantiated table tooltip uses the same actual app delegate");
        label.destroy();
        anchor.destroy();
    }
    function test_live_tree_data() {
        return ["project", "structure", "experiment", "analysis", "report", "preparing", "save-native", "save-web-disk", "save-web-fallback", "web-open", "browser-warning"].map(scope => ({
                    tag: scope,
                    scope
                }));
    }
    function test_live_tree(data) {
        const web = data.scope.startsWith("save-web") || data.scope === "web-open" || data.scope === "browser-warning";
        app = web ? SettingsProof.tooltipPlatformMain(test, true, data.scope === "save-web-disk") : factory.createObject(null, {
            width: 1280,
            height: 720,
            visible: true
        });
        verify(app !== null, "The tooltip census uses actual app QML with only capability operands selected");
        app.requestActivate();
        tryCompare(app, "active", true, 2000, "Actual hover input goes to the observed app window");
        if (Ui.control(Probe, app, "home.start"))
            click("home.start");
        if (data.scope === "preparing") {
            const tip = findChild(app, "appBar.preparingToolTip");
            const report = Ui.control(Probe, app, "appBar.tab.report");
            verify(tip && report, "The live tree exposes the real preparing tooltip and its disabled tab");
            fast(tip);
            verify(Session.openProject(SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"))), "Preparing-tooltip coverage starts an actual project opening");
            mouseMove(report, report.width / 2, report.height / 2);
            tryVerify(() => tip.visible, 2000, "Hovering the real preparing tab renders its actual tooltip before loading finishes");
            app.update();
            verify(waitForRendering(app.contentItem), "The preparing tooltip reaches an actual rendered frame");
            verify(tip.visible && inheritedStyle(tip), "Preparing this page uses the actual app tooltip delegate while the tab is still loading");
            compare(placementErrors(tip, report, null).length, 0, "The preparing tooltip sits clear of its real disabled tab");
            console.log("TOOLTIP_STYLE_CENSUS " + JSON.stringify({
                scope: data.scope,
                declared: tips().length,
                sources: 1,
                hovered: 1,
                rendered: 1,
                openedOwned: 0,
                defects: [],
                unreachable: [],
                unrendered: []
            }));
            return;
        }
        verify(Session.openProject(SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"))), "The tooltip census opens an independently authored real project");
        click("appBar.tab.project");
        const page = ["project", "structure", "experiment", "analysis", "report"].includes(data.scope) ? data.scope : "project";
        click("appBar.tab." + page);
        let modal = null;
        if (data.scope.startsWith("save-")) {
            modal = findChild(app, "saveAs.choice");
            verify(modal !== null, "The live census includes the actual Save-as dialog");
            modal.open();
        } else if (data.scope === "web-open") {
            modal = findChild(app, "open.choice");
            verify(modal !== null, "The live census includes the actual web Open dialog");
            modal.open();
        } else if (data.scope === "browser-warning") {
            modal = (findChild(app, "webStorageWarning") || findChild(app, "browserSaved"));
            verify(modal !== null, "The live census includes the actual browser-storage warning popup");
            modal.open();
        }
        if (modal)
            tryCompare(modal, "opened", true, 2000, "The dialog is actually open before its tooltip sources are walked");
        Globals.Vars.autoCollapseSideBarGroups = false;
        verify(SettingsProof.beginAnimationClock(), "Tooltip inventory controls only the UI transition clock");
        for (const object of Render.descendants(app.contentItem)) {
            if (!modal && object.visible && typeof object.collapsed === "boolean" && object.collapsible !== false)
                object.collapsed = false;
        }
        app.update();
        verify(waitForRendering(app.contentItem), "Expanded tooltip groups start their actual layout transitions");
        verify(SettingsProof.stepAnimationClock(500), "The pinned group transition duration finishes before inventory");
        app.update();
        verify(waitForRendering(app.contentItem), "Expanded tooltip groups finish drawing before source discovery");
        SettingsProof.endAnimationClock();
        // Keep table delegates resident while the census scrolls between their
        // controls. This changes only the test's view cache, not any tooltip.
        for (const item of Render.descendants(app.contentItem)) {
            if (typeof item.cacheBuffer === "number" && typeof item.contentHeight === "number")
                item.cacheBuffer = Math.max(item.cacheBuffer, item.contentHeight + app.height);
        }
        app.update();
        verify(waitForRendering(app.contentItem), "The census retains real table delegates before collecting their tooltip sources");
        const declared = tips();
        verify(declared.length > 0, "The actual QML tree contains app tooltip delegates to inspect");
        const defects = [];
        for (const tip of declared) {
            fast(tip);
            if (tip.visible && !inheritedStyle(tip))
                defects.push("rendered initially: " + String(tip));
        }
        const root = modal ? modal.contentItem : app.contentItem;
        const sources = Render.descendants(root).filter(item => item.visible && Ui.inPane(item) && item.width > 0 && item.height > 0 && item.ToolTip && String(item.ToolTip.text) !== "");
        for (const tip of declared) {
            const source = tip.parent;
            if (source && source.visible && Ui.inPane(source) && source.width > 0 && source.height > 0 && typeof source.mapToItem === "function" && tip.text !== "" && !sources.includes(source)) {
                if (!modal || Render.descendants(modal.contentItem).includes(source))
                    sources.push(source);
            }
        }
        let hovered = 0, rendered = 0, openedOwned = 0;
        const unreachable = [];
        const unrendered = [];
        const inactiveDescriptions = [];
        const inventory = sources.map(source => ({
                    item: source,
                    name: source.objectName,
                    type: String(source),
                    text: String(source.ToolTip.text)
                }));
        for (const record of inventory) {
            const source = record.item;
            Ui.scrollIntoView(source);
            app.update();
            verify(waitForRendering(app.contentItem), "A tooltip source reaches its scrolled viewport before hover input");
            const point = Ui.clickPoint(source);
            if (!point) {
                unreachable.push({
                    name: record.name,
                    type: record.type,
                    text: record.text,
                    visible: source.visible,
                    width: source.width,
                    height: source.height,
                    inPane: Ui.inPane(source)
                });
                continue;
            }
            source.ToolTip.delay = 0;
            source.ToolTip.timeout = -1;
            mouseMove(source, point.x, point.y);
            app.update();
            verify(waitForRendering(app.contentItem), "The hovered source and its real tooltip reach a rendered frame");
            ++hovered;
            // A disabled control may not receive hover. Open its already instantiated
            // application delegate directly, as we open the actual dialogs above; never
            // open an attached Qt fallback on behalf of the app.
            const current = tips();
            const owned = current.filter(tip => SettingsProof.tooltipOwnedBy(tip, source) && tip.text !== "");
            for (const tip of owned)
                fast(tip);
            const expected = String(source.ToolTip.text) || (owned.length ? owned[0].text : "");
            let visible = current.filter(tip => tip.visible && (owned.includes(tip) || tip.text === expected));
            // Qt's shared attached popup can live outside the app's QObject tree.
            const attached = source.ToolTip.toolTip;
            if (attached && attached.visible && !visible.includes(attached))
                visible.push(attached);
            if (visible.length === 0 && owned.length === 0) {
                // Attached text alone does not create a tooltip. Record this as
                // metadata without a live delegate, never as rendered coverage.
                inactiveDescriptions.push({
                    name: record.name,
                    text: expected,
                    type: record.type
                });
                continue;
            }
            if (visible.length === 0 && owned.length > 0) {
                for (const tip of owned)
                    tip.open();
                app.update();
                verify(waitForRendering(app.contentItem), "A disabled source's actual app tooltip is rendered before its style is inspected");
                visible = owned.filter(tip => tip.visible);
                if (visible.length > 0)
                    ++openedOwned;
            }
            if (visible.length === 0)
                unrendered.push({
                    name: source.objectName,
                    text: expected,
                    type: String(source)
                });
            for (const tip of visible) {
                ++rendered;
                if (!inheritedStyle(tip))
                    defects.push("rendered: " + String(tip) + " from " + source.objectName + " / " + source.ToolTip.text);
                const label = textLabel(tip);
                if (label) {
                    const lines = lineFacts(tip);
                    if (lines.lines > 1 && (lines.alignment !== Text.AlignLeft || !isBalanced(lines)))
                        defects.push("alignment/balance: " + String(tip) + " / " + record.name + " / " + tip.text + " / " + JSON.stringify(lines));
                    for (const issue of placementErrors(tip, tip.parent, modal))
                        defects.push("placement: " + issue + " / " + String(tip) + " / " + record.name + " / " + tip.text);
                    const width = widthFacts(tip);
                    if (width.characters > 50.5 || width.width > app.width || width.left < 0 || width.right > app.width)
                        defects.push("width/window: " + String(tip));
                }
                tip.close();
            }
        }
        console.log("TOOLTIP_STYLE_CENSUS " + JSON.stringify({
            scope: data.scope,
            declared: declared.length,
            sources: sources.length,
            hovered,
            rendered,
            openedOwned,
            defects,
            unreachable,
            unrendered,
            inactiveDescriptions
        }));
        compare(defects.length, 0, "Every actually rendered live tooltip uses the app type and arrow background: " + defects.join("; "));
        if (modal)
            modal.close();
    }
}
