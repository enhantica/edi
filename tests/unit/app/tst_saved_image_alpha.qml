import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render

Item {
    id: surface
    width: 1200
    height: 900
    Component {
        id: structureFactory
        StructureView {
            width: 1100
            height: 800
            shown: true
        }
    }
    Component {
        id: patternFactory
        PatternChart {
            width: 1100
            height: 800
            shown: true
            settingsPage: "pattern"
        }
    }
    Component {
        id: preferencesFactory
        AppPreferencesDialog {}
    }
    TestCase {
        id: test
        name: "SavedImageAlpha"
        when: windowShown
        property var figure
        property var preferences
        function cleanup() {
            if (preferences)
                preferences.destroy();
            if (figure)
                figure.destroy();
            preferences = null;
            figure = null;
            Session.closeProject();
        }
        function click(control) {
            verify(control !== null && control.visible && control.enabled, "The image action has a real visible enabled control");
            Ui.scrollIntoView(control);
            const point = Ui.clickPoint(control);
            verify(point !== null, "The real image action has an exposed pointer target");
            mouseClick(control, point.x, point.y);
            verify(waitForRendering(surface), "The actual saved-image control renders after input");
        }
        function chooseBackground(chart) {
            preferences = preferencesFactory.createObject(surface);
            verify(preferences !== null, "The image preference is the production Preferences dialog");
            preferences.open();
            tryCompare(preferences, "visible", true, 1000, "The real Preferences dialog opens");
            verify(waitForPolish(preferences.contentItem) && waitForRendering(preferences.contentItem), "Preferences finishes its actual tab layout before pointer input");
            click(findChild(preferences.contentItem, "preferences.tab.appearance"));
            const box = findChild(preferences.contentItem, "preferences.imageBackground");
            verify(box !== null && box.visible, "Appearance exposes the saved-image background preference");
            compare(box.currentText, "Transparent", "A fresh Preferences store defaults to transparent saved images");
            if (chart) {
                const index = Array.from({
                    length: box.count
                }, (_, i) => box.textAt(i)).findIndex(text => /chart/i.test(text));
                verify(index >= 0, "The image preference offers the chart's background colour");
                click(box);
                tryCompare(box.popup, "opened", true, 1000, "Real input opens the image-background choices");
                const list = box.popup.contentItem;
                list.positionViewAtIndex(index, ListView.Contain);
                tryVerify(() => list.itemAtIndex(index) && Ui.exposed(list.itemAtIndex(index)), 1000, "The chart-background choice is visible in the actual popup");
                const entry = list.itemAtIndex(index);
                mouseClick(entry, entry.width / 2, entry.height / 2);
                tryCompare(box, "currentIndex", index, 1000, "Actual preference input changes the saved-image background");
            }
            const ok = Render.descendants(preferences.footer).find(item => item.visible && typeof item.text === "string" && item.text.toUpperCase() === "OK" && typeof item.down === "boolean");
            verify(ok !== undefined, "The actual Preferences dialog exposes its OK button");
            click(ok);
            tryCompare(preferences, "visible", false, 1000, "The real OK button closes Preferences before saving the image");
        }
        function test_saved_png_background_follows_preferences_data() {
            const rows = [];
            for (const kind of ["structure", "pattern"])
                for (const background of ["default", "chart"])
                    rows.push({
                        tag: kind + "-" + background,
                        kind,
                        chart: background === "chart"
                    });
            return rows;
        }
        function test_saved_png_background_follows_preferences(data) {
            Preferences.resetToDefaults();
            const project = SettingsProof.copyProject(Qt.resolvedUrl("../../fixtures/legacy_structure_project/compact-project"));
            verify(Session.openProject(project), "The independent project opens for a real image export");
            tryCompare(Session.project, "calculating", false, 15000, "The image's actual scientific calculation finishes");
            if (data.kind === "structure") {
                figure = structureFactory.createObject(surface, {
                    structure: Session.project.currentStructure,
                    options: Session.project.structureViewOptions
                });
                verify(figure !== null, "The image actor instantiates the production Structure view");
                tryVerify(() => figure.has3D && figure.current && figure.atomCount > 0, 10000, "The real Structure view contains atoms under a supported graphics API");
            } else {
                figure = patternFactory.createObject(surface, {
                    experiment: Session.project.currentExperiment,
                    axisProject: Session.project
                });
                verify(figure !== null, "The image actor instantiates the production Pattern chart");
            }
            verify(waitForPolish(figure) && waitForRendering(figure), "The production figure has rendered before export");
            chooseBackground(data.chart);
            const directory = SettingsProof.emptyDirectory();
            const target = SettingsProof.childUrl(directory, "image.png");
            const button = findChild(figure, data.kind === "structure" ? "structure.toolbar.save.button" : "chart.toolbar.save.button");
            click(button);
            let dialogs;
            tryVerify(() => {
                dialogs = SettingsProof.projectFileDialogs(figure, false);
                return dialogs.length === 1;
            }, 5000, "The real camera control opens its actual Save image file chooser");
            verify(SettingsProof.chooseProjectLocation(dialogs[0], target, false), "The platform file chooser receives the test's external output filename");
            let facts;
            tryVerify(() => {
                facts = SettingsProof.savedImageFacts(target);
                return facts.valid;
            }, 5000, "The real Save image action writes a nonempty output file");
            console.log("SAVED_PNG_FACTS " + JSON.stringify(facts));
        }
    }
}
