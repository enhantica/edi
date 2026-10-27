import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import ProjectTextAcceptance 1.0
import EasyApplication.Gui.Style as Style
import "RenderedTable.js" as Render
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "ProjectCategoryTables"
    when: windowShown
    property var appWindow
    property int oldTheme
    ProjectTextProof {
        id: proof
    }
    Component {
        id: application
        Main {}
    }
    function init() {
        oldTheme = Style.Colors.theme;
        Session.closeProject();
        verify(Session.openProject(proof.project()), "The category and geometry witness opens an independent project");
        appWindow = application.createObject(null, {
            width: 1300,
            height: 1000,
            visible: true
        });
        verify(appWindow !== null, "The category gates use the production application window");
    }
    function cleanup() {
        Session.closeProject();
        if (appWindow)
            appWindow.destroy();
        appWindow = null;
        Style.Colors.theme = oldTheme;
    }
    function click(name) {
        Ui.click(test, Probe, appWindow, name);
    }
    function group(id) {
        let result;
        tryVerify(() => {
            result = Render.descendants(Ui.page(appWindow)).find(item => item.categoryId === id && item.shown);
            return result !== undefined;
        }, 2000, "Every declared category has a group on its actual page: " + id);
        result.collapsed = false;
        Ui.scrollIntoView(result);
        verify(waitForPolish(result), "The actual category completes layout before geometry is observed");
        return result;
    }
    function test_generated_single_row_and_loop_groups() {
        click("appBar.tab.experiment");
        click("sideBar.tab.extras");
        const settings = group("background_estimate");
        compare(settings.title, "Background estimation", "The generated single-row title is the independent dictionary title");
        const fields = Render.descendants(settings).filter(item => item.uid && item.uid.startsWith("background_estimate."));
        verify(fields.length > 0, "A generated single-row category exposes its actual dictionary fields");
        const reference = proof.dictionary();
        verify(reference.items && reference.items.length > 0, "Generated-field labels come from an independent SDK YAML read");
        for (const field of fields) {
            const expected = reference.items.find(row => row.uid === field.uid);
            verify(expected !== undefined, "Every generated field belongs to the selected dictionary");
            compare(field.label, expected.display_name, "Generated fields use the dictionary label");
            if (field.unit !== undefined)
                compare(field.unit, expected.display_units ?? "", "Generated numeric fields show the dictionary units");
        }
        for (const uid of ["background_estimate.mode", "background_estimate.method", "background_estimate.use_model"]) {
            const selector = fields.find(item => item.uid === uid && typeof item.textAt === "function");
            verify(selector !== undefined, "Every generated selector is a real combobox for its dictionary item");
        }
        click("appBar.tab.structure");
        click("sideBar.tab.extras");
        const operators = group("space_group_symop");
        verify(operators.title.startsWith("Symmetry operators"), "A generated loop uses the dictionary's plural title");
        const table = Render.descendants(operators).find(item => item.sourceModel !== undefined && typeof item.itemAtIndex === "function");
        verify(table !== undefined && table.count > 0, "A generated loop uses the shared populated DataTable");
        const editors = Render.descendants(table).filter(item => "readOnly" in item && "cursorPosition" in item);
        verify(editors.every(item => item.readOnly || !item.enabled), "A generated output group cannot edit computed values");
    }
    function checkTable(table, category) {
        table.forceLayout();
        const head = Render.cells(table.headerItem).filter(item => item.visible && item.width > 1);
        verify(head.length > 0, "Every reached table has real laid-out header cells");
        const equal = ["atom_site", "atom_site_aniso"].includes(category);
        const scientific = head.filter(item => item.text && !["No.", "Fit"].includes(item.text));
        if (equal && scientific.length > 1) {
            const widths = scientific.map(item => item.width);
            verify(Math.max.apply(null, widths) - Math.min.apply(null, widths) < 1, "Atom-site and displacement tables retain equal-width scientific columns");
        }
        if (!table.count)
            return;
        const row = table.itemAtIndex(0);
        verify(row !== null, "The populated table creates an actual row for geometry comparison");
        const body = Render.cells(row).filter(item => item.visible && item.width > 1);
        compare(body.length, head.length, "Every shown header column corresponds to a real row cell");
        for (let i = 0; i < head.length; ++i) {
            const headerX = head[i].mapToItem(table, 0, 0).x, valueX = body[i].mapToItem(table, 0, 0).x;
            verify(Math.abs(headerX - valueX) < 1, "A header and its value share one column origin");
            const combo = Render.descendants(body[i]).find(item => typeof item.textAt === "function" && item.contentItem);
            if (combo) {
                const valueInk = combo.contentItem.mapToItem(table, combo.contentItem.leftPadding ?? 0, 0).x;
                const headerInk = headerX + (head[i].leftPadding ?? 0);
                verify(Math.abs(valueInk - headerInk) < 1, "A combobox's shown value aligns with its header rather than its padded popup");
                verify(combo.popup && combo.popup.padding > 0, "The combobox popup retains its own list padding");
            }
        }
        if (!equal) {
            const textColumns = body.map((cell, index) => ({
                        cell: cell,
                        index: index
                    })).filter(row => row.cell.text !== undefined && row.cell.text !== "" && !/^\d+$/.test(row.cell.text) || Render.descendants(row.cell).some(item => typeof item.textAt === "function"));
            if (textColumns.length) {
                const last = textColumns[textColumns.length - 1].index;
                const edge = body[last].mapToItem(table, body[last].width, 0).x;
                const right = last + 1 < body.length ? body[last + 1].mapToItem(table, 0, 0).x : table.width;
                verify(Math.abs(edge - right) <= AppSizes.fieldSpacing + 1, "The last text or combobox column fills the row up to its trailing controls");
                for (let index = last + 1; index < body.length; ++index) {
                    const controls = Render.descendants(body[index]).filter(item => typeof item.clicked === "function");
                    verify(controls.length > 0, "Only row controls may occupy space after the last text or combobox column");
                }
            }
        }
    }
    function test_tables_use_one_layout_rule_in_both_themes() {
        let reached = 0;
        for (const theme of [Style.Colors.LightTheme, Style.Colors.DarkTheme]) {
            Style.Colors.theme = theme;
            for (const page of ["structure", "experiment", "analysis"]) {
                click("appBar.tab." + page);
                for (const tier of ["basic", "extras"]) {
                    click("sideBar.tab." + tier);
                    const groups = Render.descendants(Ui.page(appWindow)).filter(item => item.objectName.startsWith("group.") && item.visible);
                    for (const current of groups) {
                        if ("collapsed" in current)
                            current.collapsed = false;
                        Ui.scrollIntoView(current);
                        verify(waitForPolish(current), "The real category is laid out in the selected theme");
                        for (const table of Render.descendants(current).filter(item => item.sourceModel !== undefined && typeof item.itemAtIndex === "function")) {
                            checkTable(table, current.categoryId ?? current.objectName.slice(6));
                            ++reached;
                        }
                    }
                }
            }
        }
        verify(reached > 0, "Both-theme geometry checks reach populated production table groups");
    }
    function test_file_categories_and_sidebar_order_follow_sdk_dictionary() {
        const reference = proof.dictionary();
        verify(reference.categories && reference.categories.length > 0, "The category reference reads the selected SDK YAML independently of the display bridge");
        const rows = {};
        reference.categories.forEach((row, index) => {
            const numbers = Object.keys(row).filter(key => typeof row[key] === "number");
            compare(numbers.length, 1, "Each SDK category declares one presentation order");
            rows[row.id] = {
                data: row,
                order: row[numbers[0]],
                declaration: index
            };
        });
        verify(Session.save(), "The category census uses the real saved files of its loaded project");
        const pages = [
            {
                page: "project",
                file: "project.edi"
            },
            {
                page: "structure",
                file: "structures/structure.edi"
            },
            {
                page: "experiment",
                file: "experiments/experiment.edi"
            },
            {
                page: "analysis",
                file: "analysis/analysis.edi"
            },
            {
                page: "report",
                file: "reports/report.edi"
            }
        ];
        for (const entry of pages) {
            click("appBar.tab." + entry.page);
            const found = new Set();
            for (const tier of ["basic", "extras"]) {
                const button = Ui.find(Ui.page(appWindow), "sideBar.tab." + tier);
                if (!button || !button.enabled)
                    continue;
                click("sideBar.tab." + tier);
                tryVerify(() => !Ui.moving(Ui.page(appWindow)), 2000, "The selected sidebar pane finishes moving before its group order is observed");
                const groups = Render.descendants(Ui.page(appWindow)).filter(item => item.objectName.startsWith("group.") && Ui.inPane(item) && item.titleArea);
                const observed = [];
                for (const group of groups) {
                    const id = group.categoryId ?? group.objectName.slice(6);
                    if (!rows[id])
                        continue;
                    found.add(id);
                    observed.push({
                        id: id,
                        y: group.mapToItem(Ui.page(appWindow), 0, 0).y
                    });
                    const title = rows[id].data.loop ? rows[id].data.loop_title : rows[id].data.title;
                    verify(group.title === title || group.title.startsWith(title + " ("), "Each category group uses the independently read dictionary title");
                }
                const actual = observed.sort((a, b) => a.y - b.y).map(row => row.id);
                const expected = actual.slice().sort((a, b) => rows[a].order - rows[b].order || rows[a].declaration - rows[b].declaration);
                compare(JSON.stringify(actual), JSON.stringify(expected), "The actual sidebar group sequence follows SDK presentation order with declaration-order ties");
            }
            const text = SettingsProof.text(proof.project(), entry.file);
            verify(text.length > 0, "The every-category census reaches the saved file for each page");
            const carried = new Set((text.match(/^_[A-Za-z0-9_]+\./gm) ?? []).map(tag => tag.slice(1, -1)));
            for (const id of carried)
                if (id !== "geom")
                    verify(found.has(id), "Every saved category has a real group on its page, except the deferred bond settings: " + id);
        }
    }
    function test_text_controls_and_generated_groups_fit_at_minimum() {
        appWindow.width = appWindow.minimumWidth;
        appWindow.height = appWindow.minimumHeight;
        for (const page of ["project", "structure", "experiment", "analysis", "report"]) {
            click("appBar.tab." + page);
            click("sideBar.tab.text");
            verify(waitForPolish(appWindow.contentItem) && waitForRendering(appWindow.contentItem), "Every Text tab completes a frame at the supported minimum size");
            const current = Ui.page(appWindow);
            const editor = findChild(current, "text.view");
            verify(editor !== null && Ui.inPane(editor), "Every page has a reachable Text editor at the supported minimum");
            const controls = Render.descendants(current).filter(item => Ui.inPane(item) && ((typeof item.textAt === "function" && item.count === 2 && item.textAt(0) === "Editable") || (typeof item.clicked === "function" && /^check(?:-circle)?$/.test(item.fontIcon ?? ""))));
            verify(controls.length >= 2, "The Show and Apply controls are both present at minimum size");
            for (const control of controls) {
                const at = control.mapToItem(appWindow.contentItem, 0, 0);
                verify(at.x >= 0 && at.x + control.width <= appWindow.width && at.y >= 0 && at.y + control.height <= appWindow.height, "The minimum-size Text-tab controls stay wholly within the native window");
            }
        }
    }
    function test_dirty_text_navigation_data() {
        return [
            {
                tag: "page",
                boundary: "page"
            },
            {
                tag: "block",
                boundary: "block"
            },
            {
                tag: "show",
                boundary: "show"
            }
        ];
    }
    function test_dirty_text_navigation(data) {
        click("appBar.tab.structure");
        click("sideBar.tab.text");
        const pageIndex = appWindow.appBarCentralTabs.currentIndex;
        const blockIndex = Session.project.currentStructureIndex;
        const page = Ui.page(appWindow), editor = findChild(page, "text.view");
        verify(editor !== null && !editor.readOnly, "Navigation starts from the real editable Text tab");
        editor.text += "\n# pending text edit\n";
        const pending = editor.text;
        const show = Render.descendants(page).find(item => typeof item.textAt === "function" && item.count === 2 && item.textAt(0) === "Editable");
        verify(show !== undefined, "The dirty-show witness reaches the actual category selector");
        function leave() {
            if (data.boundary === "page")
                click("appBar.tab.experiment");
            else if (data.boundary === "block")
                click("mainArea.blocks.down");
            else {
                show.currentIndex = 1;
                show.activated(1);
            }
        }
        function prompt() {
            let dialog;
            tryVerify(() => {
                dialog = Probe.visibleDialogs(appWindow).find(item => /Discard changes\?/i.test([item.title].concat(Render.descendants(item.contentItem).map(child => child.text ?? "")).join(" ")));
                return dialog !== undefined;
            }, 2000, "Leaving a block, page or Show choice with dirty text asks Discard changes");
            return dialog;
        }
        leave();
        let dialog = prompt();
        const cancel = dialog.standardButton(Dialog.Cancel) ?? dialog.standardButton(Dialog.No);
        verify(cancel !== null, "The discard prompt offers a way to keep editing");
        mouseClick(cancel, cancel.width / 2, cancel.height / 2);
        compare(editor.text, pending, "Cancelling navigation retains the unapplied text");
        compare(Session.project.currentStructureIndex, blockIndex, "Cancelling navigation keeps the original block selected");
        compare(appWindow.appBarCentralTabs.currentIndex, pageIndex, "Cancelling navigation keeps the original page selected");
        compare(show.currentIndex, 0, "Cancelling navigation keeps Editable selected");
        leave();
        dialog = prompt();
        const discard = dialog.standardButton(Dialog.Discard) ?? dialog.standardButton(Dialog.Yes);
        verify(discard !== null, "The discard prompt offers an explicit discard action");
        mouseClick(discard, discard.width / 2, discard.height / 2);
        if (data.boundary === "page")
            tryVerify(() => appWindow.appBarCentralTabs.currentIndex !== pageIndex, 1000, "Confirming discard completes the requested page change");
        else if (data.boundary === "block")
            tryVerify(() => Session.project.currentStructureIndex !== blockIndex, 1000, "Confirming discard completes the requested block change");
        else
            tryCompare(show, "currentIndex", 1, 1000, "Confirming discard completes the requested Show change");
    }
    function test_constraints_disable_every_visible_parameter_editor() {
        const item = Session.project.currentStructure.atomSiteAdps.item(1, "adpIso");
        verify(item !== null, "The declared atom-displacement constraint reaches its real parameter");
        compare(item.value, 1.8, "The dependent displacement shows the hand-authored constraint's implied value");
        for (const page of ["structure", "analysis"]) {
            click("appBar.tab." + page);
            let reached = 0;
            for (const tier of ["basic", "extras"]) {
                const button = Ui.find(Ui.page(appWindow), "sideBar.tab." + tier);
                if (!button || !button.enabled)
                    continue;
                click("sideBar.tab." + tier);
                for (const group of Render.descendants(Ui.page(appWindow)).filter(object => object.titleArea && Ui.inPane(object))) {
                    if ("collapsed" in group)
                        group.collapsed = false;
                    Ui.scrollIntoView(group);
                    verify(waitForPolish(group), "Constrained-parameter rows complete layout before their editability is checked");
                    for (const editor of Render.descendants(group).filter(object => object.item && object.item.path === item.path && "cursorPosition" in object)) {
                        verify(!editor.enabled, "Every table and field disables a declared constrained parameter");
                        compare(editor.item.value, 1.8, "Every disabled constrained cell retains the implied value");
                        ++reached;
                    }
                }
            }
            verify(reached > 0, "Each relevant page actually shows the constrained value instead of silently omitting it");
        }
    }
    function test_reference_projects_expose_every_carried_category_data() {
        return [
            {
                tag: "lbco",
                project: "pd-neut-cwl_lbco-hrpt"
            },
            {
                tag: "wish-five-banks",
                project: "pd-neut-tof_ncaf-wish-5bank_start-5"
            },
            {
                tag: "scan",
                project: "pd-neut-cwl_cosio-d20_scan-3f"
            },
            {
                tag: "taurine",
                project: "sc-neut-tof_taurine_fit"
            },
            {
                tag: "two-structures",
                project: "pd-neut-tof_ferrite-austenite-beer"
            }
        ];
    }
    function test_reference_projects_expose_every_carried_category(data) {
        Session.closeProject();
        verify(Session.openProject(Probe.repoUrl("docs/user/cli/" + data.project + "/project")), "Each required reference project opens through the production application: " + Session.lastError);
        for (const page of ["project", "structure", "experiment", "analysis", "report"]) {
            click("appBar.tab." + page);
            const count = page === "structure" ? Session.project.structures.count : page === "experiment" ? Session.project.experiments.count : 1;
            verify(count > 0, "Every reference page reaches at least one actual datablock");
            for (let index = 0; index < count; ++index) {
                if (page === "structure")
                    Session.project.currentStructureIndex = index;
                if (page === "experiment")
                    Session.project.currentExperimentIndex = index;
                click("sideBar.tab.text");
                const current = Ui.page(appWindow);
                const editor = findChild(current, "text.view");
                verify(editor !== null, "Each reference datablock has a real Text editor");
                const show = Render.descendants(current).find(item => typeof item.textAt === "function" && item.count === 2 && item.textAt(0) === "Editable");
                verify(show !== undefined, "Each reference Text tab offers the declared category filter");
                show.currentIndex = 1;
                show.activated(1);
                tryCompare(editor, "readOnly", true, 1000, "Reference category discovery uses the complete read-only view");
                const carried = new Set((editor.text.match(/^_[A-Za-z0-9_]+\./gm) ?? []).map(tag => tag.slice(1, -1)));
                verify(carried.size > 0, "Every reference block contributes actual categories to the app census");
                const found = new Set();
                for (const tier of ["basic", "extras"]) {
                    const button = Ui.find(current, "sideBar.tab." + tier);
                    if (!button || !button.enabled)
                        continue;
                    click("sideBar.tab." + tier);
                    tryVerify(() => !Ui.moving(current), 2000, "The real reference sidebar reaches its selected pane");
                    for (const group of Render.descendants(current).filter(item => item.objectName.startsWith("group.") && item.titleArea && Ui.inPane(item)))
                        found.add(group.categoryId ?? group.objectName.slice(6));
                }
                for (const id of carried)
                    if (id !== "geom")
                        verify(found.has(id), "Every category carried by every reference block has a group on its page: " + id);
            }
        }
    }
}
