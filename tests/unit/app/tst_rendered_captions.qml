import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import ProjectTextAcceptance 1.0
import OnboardingAcceptance 1.0
import EasyApplication.Gui.Style as Style
import EasyApplication.Gui.Elements as Elements
import "CaptionCapitalisation.js" as CaseRule
import "NativeTurn.js" as Turn
import "RenderedTable.js" as Render
import "UiInteraction.js" as Ui
import "RenderedCaptions.js" as Captions

TestCase {
    id: test
    name: "RenderedCaptions"
    when: windowShown
    property var app
    property string gateTurnSelector: ""
    property var experimentIndices: ({measured: 0})
    ProjectTextProof { id: proof }
    Component { id: application; Main {} }
    Component {
        id: probeControl
        Elements.GroupBox {
            id: control
            objectName: "unlisted.group"
            width: 620
            height: 430
            x: 100
            y: 100
            z: 1000
            title: control.groupCaption
            collapsed: false
            property string fieldCaption: "Future axis"
            property string groupCaption: "Calculation range"
            property string headerCaption: "d spacing"
            property alias selector: selector
            readonly property var headerLabel: table.headerItem ? table.headerItem.children[0] : null
            Column {
                width: parent.width
                spacing: 20
                SelectorField {
                    id: selector
                    objectName: "unlisted.dynamic.selector"
                    uid: ""
                    options: null
                    label: control.fieldCaption
                    width: 250
                }
                ValueField {
                    objectName: "unlisted.dynamic.value"
                    uid: ""
                    label: "Reference field"
                    fieldValue: "lowercase field value"
                    width: 250
                }
                ListView {
                    id: table
                    objectName: "unlisted.table"
                    width: 300
                    height: 100
                    model: ["lowercase row content"]
                    header: Row {
                        width: 300
                        height: 30
                        HeaderLabel { id: headerTitle; uid: ""; text: control.headerCaption; width: 300; height: 30 }
                    }
                    delegate: Label { required property string modelData; text: modelData; width: 300; height: 30 }
                }
            }
        }
    }
    function settle() {
        OnboardingProbe.advanceClock(1000);
        OnboardingProbe.incubate(app);
        verify(waitForPolish(app), "Caption census observes completed layout in the actual application");
    }
    function initTestCase() {
        Session.closeProject();
        verify(Session.openProject(proof.project()), "Rendered captions use the independent retained project");
        for (const kind of ["cwl", "tof", "single"]) {
            verify(Session.project.createExperiment(), "Shared caption setup creates each real calculation-only experiment once");
            const index = Session.project.currentExperimentIndex;
            experimentIndices[kind] = index;
            if (kind === "tof")
                verify(Session.project.setExperimentType(index, "beamMode", "time-of-flight"), "Shared caption setup prepares the actual time-of-flight model");
            if (kind === "single")
                verify(Session.project.setExperimentType(index, "sampleForm", "single crystal"), "Shared caption setup prepares the actual single-crystal model");
        }
        Session.project.currentExperimentIndex = 0;
        app = application.createObject(null, {width: 1300, height: 1000, visible: true});
        verify(app !== null, "Rendered caption gates instantiate the real application");
        OnboardingProbe.startClock();
        tryVerify(() => {
            settle();
            return app.pagesBuilt > 0 && app.pagesBuilt === app.pagesWanted;
        }, 10000, "Caption census waits for the real asynchronous workflow pages");
    }
    function init() {
        gateTurnSelector = Turn.begin(test, Probe);
    }
    function cleanup() {
        Turn.end(gateTurnSelector);
    }
    function cleanupTestCase() {
        OnboardingProbe.stopClock();
        Session.closeProject();
        if (app) app.destroy();
    }
    function click(name) {
        Ui.click(test, Probe, app, name, true, () => settle());
        settle();
    }
    function census(root = null, part = 0, parts = 1) {
        const page = root || Ui.page(app), rows = [];
        const groups = Render.descendants(page).filter(item => item.titleArea &&
            typeof item.title === "string" && item.visible && Ui.inPane(item));
        const selected = groups.filter((group, index) => index % parts === part);
        verify(selected.length > 0, "Every census partition reaches actual caption-bearing groups");
        for (const group of selected) {
            group.collapsed = false;
            Ui.scrollIntoView(group.titleArea.width > 0 ? group.titleArea : group);
            settle();
            app.update();
            verify(waitForRendering(app.contentItem), "The group title is painted before its caption is sampled");
            if (group.title !== "" || (typeof group.categoryId === "string" && group.categoryId !== ""))
                rows.push(...Captions.group(group, OnboardingProbe, Style.Fonts.iconsFamily));
            const fields = Render.descendants(group).filter(item => Captions.field(item) && item.visible);
            for (const field of fields) {
                if (!Captions.titleItems(field, OnboardingProbe, Style.Fonts.iconsFamily).length) {
                    Ui.scrollIntoView(field);
                    settle();
                    app.update();
                    verify(waitForRendering(app.contentItem), "The scrolled field title is painted before its caption is sampled");
                }
                rows.push(...Captions.fields(field, OnboardingProbe, Style.Fonts.iconsFamily));
            }
            for (const table of Render.descendants(group).filter(item => item.headerItem && item.headerItem.visible && item.visible)) {
                if (!Ui.rendered(table.headerItem)) {
                    Ui.scrollIntoView(table.headerItem);
                    settle();
                    app.update();
                    verify(waitForRendering(app.contentItem), "The scrolled table header is painted before its caption is sampled");
                }
                rows.push(...Captions.headers(table, OnboardingProbe, Style.Fonts.iconsFamily));
            }
        }
        verify(rows.length > 0, "Rendered caption discovery reaches actual caption-bearing controls");
        return rows;
    }
    function test_context_data() {
        return JSON.parse(OnboardingProbe.sourceText("tests/fixtures/captions/contexts.json"));
    }
    function test_context(data) {
        Session.project.currentExperimentIndex = experimentIndices[data.experiment];
        compare(Session.project.currentExperimentIndex, experimentIndices[data.experiment], "The actual page shows the selected independent caption model");
        click("appBar.tab." + data.page);
        click("sideBar.tab." + data.tab);
        console.info("RENDERED_CAPTIONS " + JSON.stringify({context: data.tag, rows: census(null, data.part || 0, data.parts || 1)}));
    }
    function test_probe_controls() {
        const control = probeControl.createObject(app.contentItem);
        verify(control !== null, "The census probe instantiates original field, group and header components");
        const frames = [];
        function capture(name) {
            settle();
            app.update();
            verify(waitForRendering(control), "Every caption-probe state is actually rendered");
            frames.push({name: name, backing: control.selector.label, rows: census(control)});
        }
        capture("positive");
        control.fieldCaption = "future axis";
        capture("dynamic-lowercase");
        control.fieldCaption = "Future axis";
        settle();
        let labels = Captions.titleItems(control.selector, OnboardingProbe, Style.Fonts.iconsFamily);
        compare(labels.length, 1, "The caption probe identifies one actual selector title independently of its text");
        labels[0].text = "painted lowercase";
        capture("painted-only-lowercase");
        labels[0].text = Qt.binding(() => control.selector.shortPrettyName);
        settle();
        verify(control.selector.indicator && Ui.rendered(control.selector.indicator), "The hidden-title escape retains a real visible combo indicator");
        labels[0].visible = false;
        capture("missing-painted-title");
        labels[0].visible = true;
        control.groupCaption = "calculation range";
        capture("group-lowercase");
        control.groupCaption = "Calculation range";
        control.headerCaption = "new column";
        capture("header-lowercase");
        control.headerCaption = "d spacing";
        control.headerLabel.visible = false;
        capture("missing-painted-header");
        control.headerLabel.visible = true;
        control.fieldCaption = "α₀";
        capture("scientific-symbol");
        compare(CaseRule.expected("α₀"), "α₀", "Indexed scientific symbols retain their case in the preexisting dictionary rule too");
        compare(CaseRule.expected("dimensionality"), "Dimensionality", "Prose beginning with a symbol letter is not a scientific exception");
        console.info("CAPTION_PROBE_CONTROLS " + JSON.stringify(frames));
        control.destroy();
    }

}
