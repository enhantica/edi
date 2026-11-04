// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtCore
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Shapes
import QtQuick.Templates as T

import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// A running tutorial's written steps (ADR-0064), one at a time in a callout that leaves the page usable: the step's
// text and what should be seen after it, next to the control the step names (found by object name, ADR-0066) with a
// pointer toward it, and outlined. A tutorial with a scientific project works in a temporary one: the user's own
// project is set aside at the start and comes back on Stop or Discard; Keep goes on with the tutorial's project,
// unsaved until the user saves it.
Popup {
    id: panel

    property var tutorial: null
    property int step: 0
    // The last step offers the end's choices in place of Next.
    readonly property bool atEnd: steps.length > 0 && step === steps.length - 1
    property bool temporary: false
    // A temporary project the user may keep at the end (`completion` offers it), in every tutorial, the Interface tour's
    // LBCO example included.
    readonly property bool offersKeep: temporary && tutorial !== null && tutorial.completion.includes("keep")
    readonly property var steps: tutorial ? tutorial.steps : []
    readonly property var current: step < steps.length ? steps[step] : null
    // The running tutorial's title, as a dialog has one.
    readonly property string title: tutorial ? tutorial.title : ""
    // Next was pressed before the step's state held; cleared when the step changes.
    // The background estimates made since the tutorial started (a change of the background points of the experiment).
    property int backgroundEstimates: 0
    // Whether the step's state already held when it showed: such a step only explains and waits for Next.
    property bool heldAtStart: true
    // Reached by going on (Next, or a step done by itself), not by Back or the start.
    property bool arrivedForward: false
    // Whether the following step's state already held when this step showed: done before, not done ahead now.
    property bool followingHeld: true
    // The step's action was done while the step before it showed, the user a step ahead of the callout (Start, then
    // Create at once): it goes on as if done after it showed. A state that already held then, or one found on Back,
    // waits for Next.
    property bool doneAhead: false
    // The tutorial's files were saved (a step's "Save tutorial files" link).
    property bool filesSaved: false
    // The tutorial waiting for its example's project to open aside (start), if any.
    property var pendingStart: null
    // The tutorial's files staged from the collection, as a folder URL string; empty until staged.
    property string stagedFolder: ""
    // The step action to do again once the files are staged, if one waits for them.
    property string afterStaging: ""
    // The fits and background estimates made before the step showed: a step asking for one waits for one more.
    property int fitsAtStep: 0
    property int resultsAtStep: 0
    // The value of the parameter a `changed:` step changes, when the step showed.
    property var valueAtStep: null
    property int estimatesAtStep: 0
    // The fits finished since the tutorial started, for the steps that ask for a fit.
    property int fitsDone: 0
    // Where the callout sits against its control: "right", "left", "below" or "above" it with the pointer toward it,
    // "inside" a control too large to sit beside, or "" when the control is not on screen (the window's corner).
    property string side: ""
    // Along the callout's edge facing the control, where the pointer points from.
    property real pointerAt: 0
    readonly property real gap: EaStyle.Sizes.fontPixelSize * 0.9
    // The callout's colours (the owner, 2026-11-02): the dialog background with only a faint tint of the accent, fully
    // opaque; a 1 px border in a pale blue only a little darker than it; Step N of M in the app's accent, as unfolded
    // group names and selected tabs have it. The text keeps the theme's colours.
    readonly property color fill: Qt.tint(EaStyle.Colors.dialogBackground, Qt.rgba(EaStyle.Colors.themeAccent.r, EaStyle.Colors.themeAccent.g, EaStyle.Colors.themeAccent.b, 0.04))
    readonly property color edge: Qt.tint(EaStyle.Colors.dialogBackground, Qt.rgba(EaStyle.Colors.themeAccent.r, EaStyle.Colors.themeAccent.g, EaStyle.Colors.themeAccent.b, 0.18))
    readonly property color progressColor: EaStyle.Colors.themeForegroundHovered
    // The step's control as revealed, shown or not.
    property Item revealed: null
    // Whether the callout has its control to point at; without one it is not shown.
    property bool anchored: false
    // The step's control is in a dialog or popup, which can close under it.
    property bool revealedInPopup: false
    // The pointer's point stops this short of its control.
    readonly property real tipGap: 3
    // From a step's start until its reveal has run: the callout stays where it was meanwhile.
    property bool revealing: false
    // From Next or Back until the new step's page, tab, groups and list have stopped moving: the callout fades out,
    // the step's changes run, and it fades in at its final place with the new step, so it never moves with its control
    // (the owner, 2026-11-02).
    property bool settling: false
    // The step the callout and the status bar's strip show: the step until the callout fades in with it.
    property int shownStep: 0
    readonly property var shown: shownStep >= 0 && shownStep < steps.length ? steps[shownStep] : null
    // How often the reveal has waited for the step's page to be shown.
    property int revealTries: 0
    readonly property var pages: ({
            "home": AppState.Page.Home,
            "project": AppState.Page.Project,
            "structure": AppState.Page.Structure,
            "experiment": AppState.Page.Experiment,
            "analysis": AppState.Page.Analysis,
            "report": AppState.Page.Report
        })

    function start(chosen) {
        // One tutorial at a time: a second start would set aside the first tutorial's project in place of the user's.
        if (panel.tutorial !== null || Session.hasProjectSetAside)
            return;
        // An unapplied Text-tab edit joins the project before that project is set aside.
        if (AppState.textEdit !== null) {
            AppState.textEdit.settleEdit(() => panel.start(chosen));
            return;
        }
        const temporary = chosen.project === "temporary";
        // A scientific tutorial never works in the user's project: it is set aside, unsaved changes and all, and comes
        // back on Stop or Discard, or before anything else replaces the tutorial's project or quits
        // (AppState.afterChanges).
        if (temporary) {
            if (chosen.start !== "aside" && chosen.start !== "new") {
                // The example's project downloads first; the tutorial begins once it has opened aside.
                if (Session.openExampleAside(String(chosen.start).replace(/^example:/, "")))
                    panel.pendingStart = chosen;
                return;
            }
            const started = chosen.start === "aside" ? Session.setProjectAside() : Session.createProjectAside("tutorial", chosen.title);
            if (!started)
                return;
        }
        panel.begin(chosen, temporary);
    }
    // The tutorial chosen, with its project in place.
    function begin(chosen, temporary) {
        RunLog.note(`tutorial started: ${chosen.id}`);
        panel.temporary = temporary;
        panel.tutorial = chosen;
        panel.step = 0;
        panel.shownStep = 0;
        panel.fitsDone = 0;
        panel.filesSaved = false;
        panel.backgroundEstimates = 0;
        AppState.tutorialRunning = true;
        panel.open();
        panel.show();
    }
    // Back to the user's own project, as it was before the tutorial.
    function restoreUserProject() {
        if (panel.temporary && Session.hasProjectSetAside)
            Session.restoreProjectSetAside();
    }
    function stop() {
        RunLog.note(panel.atEnd ? "tutorial finished" : `tutorial stopped at step ${panel.step + 1}`);
        panel.restoreUserProject();
        panel.close();
    }
    // Whether the callout shows Stop: a temporary project's last step asks Keep or Discard there instead.
    readonly property bool canGoOn: !(atEnd && offersKeep)
    // Next: what the callout's forward button, the right arrow key and the status bar's strip do. The last step has no
    // Next (its button is off); Stop, or Keep and Discard, end the tutorial there.
    function forward() {
        if (!panel.atEnd)
            panel.next();
    }
    // Goes on. On a step asking for an action not done yet, Next does it first (the owner, 2026-11-02): one done at
    // once goes on at once; one that takes time (a fit, a folder to choose) goes on by itself once it is done.
    function next() {
        if (panel.current && !panel.holds(panel.current.check)) {
            panel.perform(panel.current.check);
            if (!panel.holds(panel.current.check))
                return;
        }
        if (panel.step + 1 < panel.steps.length) {
            ++panel.step;
            panel.arrivedForward = true;
            panel.show();
        }
    }
    // The tutorial's files, fetched from the collection into a temporary folder of their own, for Next on a step that
    // saves or loads them: on the disk, or in the browser's memory where its file chooser puts the files it opens, so
    // Next loads them as a chosen file is loaded. The folder's URL, empty until Session.stageTutorialFiles has brought
    // it (tutorialFilesStaged).
    function tutorialFolder() {
        return panel.stagedFolder;
    }
    // Whether a step action reads the staged files, so it waits for them.
    function needsFiles(name) {
        if (name === "files-saved")
            return !WebFiles.available;
        if (name === "structure")
            return panel.current.target === "structures.load";
        return name === "data";
    }
    // A parameter path with its keys as dotted parts, as a step names it: atom_sites[La].adp_iso is atom_sites.La.adp_iso.
    function dotted(path) {
        return String(path).replace(/\[([^\]]*)\]/g, ".$1");
    }
    // The parameter whose path ends with `suffix` ("cell.length_a", "La.adp_iso"), from the project's parameter list.
    function parameterNamed(suffix) {
        const parameters = Session.project ? Session.project.parameters : null;
        if (parameters === null || !suffix)
            return null;
        for (let row = 0; row < parameters.rowCount(); ++row) {
            if (panel.dotted(parameters.text(row, "path")).endsWith(suffix))
                return parameters.item(row, "parameter") as ParameterItem;
        }
        return null;
    }
    // Whether the fit's results window is closed, and closing it as its OK does.
    function resultsClosed() {
        return !AppState.fitResultsOpen;
    }
    function closeResults() {
        const window = Overlay.overlay ? Overlay.overlay.Window.window : null;
        (window ? ItemLocator.find(window, "fit.results.ok") as T.AbstractButton : null)?.click();
    }
    // A tutorial file's URL in that folder, empty if it could not be written.
    function tutorialFile(name) {
        const folder = panel.tutorialFolder();
        return folder !== "" ? `${folder}/${name}` : "";
    }
    // Does what a step's `check` asks, as the step's own control would: the counterpart of `holds`.
    function perform(check) {
        if (!check)
            return;
        if (check.includes(";")) {
            for (const part of check.split(";"))
                panel.perform(part.trim());
            return;
        }
        const colon = check.indexOf(":");
        const name = colon < 0 ? check : check.slice(0, colon);
        const argument = colon < 0 ? "" : check.slice(colon + 1);
        // The files come from the collection: staged once, the action goes on when they have arrived.
        if (panel.needsFiles(name) && panel.stagedFolder === "") {
            panel.afterStaging = check;
            Session.stageTutorialFiles();
            return;
        }
        const project = Session.project;
        const structure = project ? project.currentStructure : null;
        const experiment = project ? project.currentExperiment : null;
        switch (name) {
        case "page":
            AppState.open(panel.pages[argument]);
            return;
        // The creation goes through the page's own Create button and the dialog's own OK: what the
        // user typed in the form, name, title, authors and description, is what the project gets.
        case "creating":
            (panel.locate("project.create") as T.AbstractButton)?.click();
            return;
        case "project":
            {
                const accept = panel.locate("createProject.accept") as T.AbstractButton;
                if (accept === null || !accept.visible) {
                    panel.perform("creating");
                    return;
                }
                // A name first, as the name step gives one, when the field is still empty.
                panel.perform("text:createProject.name=" + (argument !== "" ? argument : "lbco"));
                accept.click();
            }
            return;
        case "files-saved":
            // No folder to choose: a temporary one, which the later steps load from.
            if (WebFiles.available)
                panel.saveFiles("");
            else
                panel.filesSaved = panel.tutorialFolder() !== "" || panel.filesSaved;
            return;
        case "structures":
            while (project !== null && project.structures.rowCount() < Number(argument) && project.createStructure()) {}
            return;
        case "structure":
            if (panel.current.target === "structures.load") {
                const file = panel.tutorialFile(`${argument}.cif`);
                if (project !== null && file !== "")
                    project.loadStructure(file);
            } else if (structure !== null) {
                structure.name = argument;
            }
            return;
        case "space-group":
            if (structure !== null)
                structure.spaceGroup.itNumber = Number(argument);
            return;
        case "cell-a":
        case "cell-a-not":
            if (structure !== null && structure.cell.lengthA !== null)
                structure.cell.lengthA.value = Number(argument) + (name === "cell-a-not" ? 0.01 : 0);
            return;
        case "sites":
            if (structure !== null)
                panel.placeSites(structure.atomSites, argument);
            return;
        case "experiment":
            if (project !== null)
                project.createExperiment();
            return;
        case "data":
            {
                const file = panel.tutorialFile("hrpt.xye");
                if (project !== null && file !== "")
                    project.loadData(0, file);
                return;
            }
        case "param":
            {
                const [path, value] = argument.split("=");
                const [list, item] = path.split(".");
                const parameters = experiment !== null ? (list === "peak" ? experiment.peak : experiment.instrument) : null;
                const parameter = parameters !== null ? parameters.parameterNamed(item) : null;
                if (parameter !== null)
                    parameter.value = Number(value);
                return;
            }
        case "scale":
            {
                const scale = experiment !== null && experiment.linkedStructures.rowCount() > 0 ? experiment.linkedStructures.item(0, "scale") as ParameterItem : null;
                if (scale !== null)
                    scale.value = Number(argument);
                return;
            }
        case "background-estimated":
            if (project !== null)
                project.estimateBackground();
            return;
        case "background-named":
            if (project !== null)
                project.namePointsByPosition();
            return;
        case "free":
            {
                // The free column's Free · all, as the step asks: it frees the rows the filters show, and only them.
                // Rows the filters hide stay as they are, so a stage filtered wrongly does not hold.
                const header = panel.locate("parameters.freeHeader");
                const menu = header !== null ? header.menu as FreeHeaderMenu : null;
                if (menu !== null && header.interactionEnabled)
                    menu.apply(true);
                return;
            }
        case "results-closed":
            panel.closeResults();
            return;
        case "selected":
            {
                const table = panel.locate("group.parameters");
                const found = panel.parameterNamed(argument);
                if (table !== null && found !== null)
                    table.selected = found;
                return;
            }
        case "changed":
            {
                const [path, value] = argument.split("=");
                const found = panel.parameterNamed(path);
                if (found !== null)
                    found.value = Number(value);
                return;
            }
        case "category":
            {
                const box = panel.locate("parameters.category") as T.ComboBox;
                if (box === null)
                    return;
                for (let i = 0; i < box.count; ++i) {
                    if (box.textAt(i).startsWith(argument)) {
                        box.activated(i);
                        return;
                    }
                }
                return;
            }
        case "name-filter":
            {
                const field = panel.locate("parameters.nameFilter") as TextInput;
                // Typed as a user types, so the field keeps showing the filter (an assignment would cut it loose).
                if (field !== null) {
                    field.remove(0, field.length);
                    field.insert(0, argument);
                    field.textEdited();
                }
                return;
            }
        case "filters-clear":
            (panel.locate("parameters.clearFilters") as T.AbstractButton)?.click();
            return;
        case "fit-done":
        case "fitted":
            // Fitted already: a step that wants the results closed has Next close them; one that leaves them open for
            // the step after it, about the results, has nothing more to do.
            if (panel.fitsDone > panel.fitsAtStep) {
                if (name === "fitted")
                    panel.closeResults();
                return;
            }
            // A fit asked for while the project still recalculates is refused; it is asked again until it runs.
            if (project !== null && !project.fit.running) {
                project.fit.start();
                if (!project.fit.running) {
                    fitAgain.tries = 0;
                    fitAgain.start();
                }
            }
            return;
        case "aliases":
            if (project !== null)
                panel.addAliases(project.analysis.aliases, argument);
            return;
        case "constraint":
            if (project !== null) {
                const constraints = project.analysis.constraints;
                constraints.append();
                constraints.setText(constraints.rowCount() - 1, "expression", argument);
            }
            return;
        case "text":
            {
                // Typed into the field, where the user sees it, and only into an empty one: a name typed stays.
                const [name, value] = argument.split("=");
                const field = panel.locate(name) as TextInput;
                if (field !== null && field.text === "") {
                    field.insert(0, value ?? "");
                    field.forceActiveFocus();
                }
                return;
            }
        case "open":
            {
                const item = panel.locate(argument);
                if ((item as EaElements.GroupBox) !== null)
                    item.collapsed = false;
                else
                    (item as T.AbstractButton)?.click();
                return;
            }
        }
    }
    // The atom sites as `sites` wants them, "La 0 0 0,Ba 0 0 0,...": as many rows, each element at its position; two
    // sites sharing a position share it half and half.
    function placeSites(sites, wanted) {
        const specs = wanted.split(",").map(spec => spec.trim().split(/\s+/));
        while (sites.rowCount() < specs.length)
            sites.append();
        while (sites.rowCount() > specs.length)
            sites.remove(sites.rowCount() - 1);
        const set = (row, role, value) => {
            const item = sites.item(row, role) as ParameterItem;
            if (item !== null)
                item.value = value;
        };
        specs.forEach(([element, x, y, z], row) => {
            const shared = specs.filter(other => other[1] === x && other[2] === y && other[3] === z).length;
            sites.setText(row, "label", element);
            sites.setText(row, "typeSymbol", element);
            set(row, "fractX", Number(x));
            set(row, "fractY", Number(y));
            set(row, "fractZ", Number(z));
            set(row, "occupancy", 1 / shared);
        });
    }
    // Aliases as `wanted` names them, "biso_La=La.adp_iso,...": each name for the parameter ending in that path; a bare
    // count adds as many unnamed ones.
    // An alias that already has the name is given the right parameter, as the user would correct it.
    function addAliases(aliases, wanted) {
        const entries = wanted.includes("=") ? wanted.split(",").map(entry => entry.trim().split("=")) : [];
        const count = entries.length > 0 ? entries.length : Number(wanted);
        for (let i = 0; i < count; ++i) {
            if (entries.length === 0) {
                aliases.append();
                continue;
            }
            let row = panel.aliasRow(aliases, entries[i][0]);
            if (row < 0) {
                aliases.append();
                row = aliases.rowCount() - 1;
                aliases.setText(row, "id", entries[i][0]);
            }
            const parameter = aliases.parameterNames.find(candidate => panel.dotted(candidate).endsWith(entries[i][1]));
            if (parameter && aliases.text(row, "parameter") !== parameter)
                aliases.setText(row, "parameter", parameter);
        }
    }
    // The row of the alias named `id`, -1 if there is none.
    function aliasRow(aliases, id) {
        for (let row = 0; row < aliases.rowCount(); ++row) {
            if (aliases.text(row, "id") === id)
                return row;
        }
        return -1;
    }
    // Whether a step's `check` holds in the open project (app/tutorials/manifest.json); a step without one has
    // nothing to wait for.
    function holds(check) {
        if (!check)
            return true;
        if (check.includes(";"))
            return check.split(";").every(part => panel.holds(part.trim()));
        const colon = check.indexOf(":");
        const name = colon < 0 ? check : check.slice(0, colon);
        const argument = colon < 0 ? "" : check.slice(colon + 1);
        const project = Session.project;
        const structure = project ? project.currentStructure : null;
        const experiment = project ? project.currentExperiment : null;
        const near = (item, value) => item !== null && Math.abs(item.value - Number(value)) < 0.0005;
        switch (name) {
        case "files-saved":
            return panel.filesSaved;
        case "page":
            return EaGlobals.Vars.appBarCurrentIndex === panel.pages[argument];
        case "creating":
            // The new project's dialog is open, or the project is made.
            return EaGlobals.Vars.showProjectDescriptionDialog || project !== null;
        case "project":
            // Any name: the step suggests one, the user may give another.
            return project !== null && (argument === "" || project.name.toLowerCase() === argument);
        case "structures":
            return project !== null && project.structures.rowCount() >= Number(argument);
        case "structure":
            return structure !== null && structure.name.toLowerCase() === argument;
        case "space-group":
            return structure !== null && structure.spaceGroup.itNumber === Number(argument);
        case "cell-a":
            return structure !== null && near(structure.cell.lengthA, argument);
        case "cell-a-not":
            return structure !== null && structure.cell.lengthA !== null && !near(structure.cell.lengthA, argument);
        case "sites":
            return structure !== null && panel.sitesAre(structure.atomSites, argument);
        case "experiment":
            return project !== null && project.experiments.rowCount() >= 1;
        case "data":
            return project !== null && project.fit.measured;
        case "param":
            {
                // "instrument.calib_twotheta_offset=0.3": a value of the experiment's instrument or peak.
                const [path, value] = argument.split("=");
                const [list, item] = path.split(".");
                const parameters = experiment !== null ? (list === "peak" ? experiment.peak : experiment.instrument) : null;
                return parameters !== null && near(parameters.parameterNamed(item), value);
            }
        case "scale":
            return experiment !== null && experiment.linkedStructures.rowCount() > 0 && near(experiment.linkedStructures.item(0, "scale") as ParameterItem, argument);
        case "background-estimated":
            return panel.backgroundEstimates > panel.estimatesAtStep;
        case "background-named":
            return experiment !== null && panel.pointsNamedByPosition(experiment.background);
        case "free":
            return project !== null && argument.split(",").every(spec => panel.allFree(project.parameters, spec));
        case "fit-done":
            // Fitted, its results window open when the preferences show it.
            return panel.fitsDone > panel.fitsAtStep && (!Preferences.showFitResults || AppState.fitResultsShown > panel.resultsAtStep);
        case "fitted":
            // Fitted, and its results read and closed.
            return panel.fitsDone > panel.fitsAtStep && (!Preferences.showFitResults || AppState.fitResultsShown > panel.resultsAtStep) && panel.resultsClosed();
        case "results-closed":
            return panel.resultsClosed();
        case "selected":
            {
                const table = panel.locate("group.parameters");
                const found = panel.parameterNamed(argument);
                return table !== null && found !== null && table.selected === found;
            }
        case "changed":
            {
                // "cell.length_a=3.95": changed from its value when the step showed (Next sets the value given).
                const found = panel.parameterNamed(argument.split("=")[0]);
                return found !== null && panel.valueAtStep !== null && Math.abs(found.value - panel.valueAtStep) > 1e-9;
            }
        case "category":
            {
                const box = panel.locate("parameters.category") as T.ComboBox;
                return box !== null && box.displayText.startsWith(argument);
            }
        case "name-filter":
            {
                const field = panel.locate("parameters.nameFilter") as TextInput;
                return field !== null && field.text === argument;
            }
        case "filters-clear":
            {
                const box = panel.locate("parameters.category") as T.ComboBox;
                const field = panel.locate("parameters.nameFilter") as TextInput;
                return box !== null && field !== null && box.currentIndex <= 0 && field.text === "";
            }
        case "aliases":
            {
                const aliases = project !== null ? project.analysis.aliases : null;
                if (aliases === null)
                    return false;
                if (!argument.includes("="))
                    return aliases.rowCount() >= Number(argument);
                // Each alias names the parameter it is for, not only its id.
                return argument.split(",").every(entry => {
                    const [id, target] = entry.trim().split("=");
                    const row = panel.aliasRow(aliases, id);
                    return row >= 0 && panel.dotted(aliases.text(row, "parameter")).endsWith(target);
                });
            }
        case "constraint":
            return project !== null && panel.hasConstraint(project.analysis.constraints, argument);
        case "text":
            {
                // "createProject.name=lbco": the field holds a text, the user's or the one Next types.
                const field = panel.locate(argument.split("=")[0]) as TextInput;
                return field !== null && field.text !== "";
            }
        case "open":
            {
                // A group unfolded, or a tab chosen.
                const item = panel.locate(argument);
                const group = item as EaElements.GroupBox;
                const tab = item as T.AbstractButton;
                return (group !== null && !group.collapsed) || (tab !== null && (tab.checked || (tab.TabBar.tabBar !== null && tab.TabBar.tabBar.currentIndex === tab.TabBar.index)));
            }
        }
        console.warn(`Tutorial check '${check}' is not known`);
        return true;
    }
    // The atom sites are exactly the ones given, "La 0 0 0,Ba 0 0 0,...": each element at its fractional position, in
    // any order, and with the occupancy placeSites gives it: sites sharing a position share it equally (La and Ba half
    // each), any other site is full.
    function sitesAre(sites, wanted) {
        const specs = wanted.split(",").map(spec => spec.trim().split(/\s+/));
        if (sites.rowCount() !== specs.length)
            return false;
        const at = (row, role, value) => {
            const item = sites.item(row, role) as ParameterItem;
            return item !== null && Math.abs(item.value - Number(value)) < 0.0005;
        };
        const used = [];
        for (const [element, x, y, z] of specs) {
            const shared = specs.filter(other => other[1] === x && other[2] === y && other[3] === z).length;
            let found = -1;
            for (let row = 0; row < sites.rowCount() && found < 0; ++row) {
                if (!used.includes(row) && sites.text(row, "typeSymbol").toLowerCase() === element.toLowerCase() && at(row, "fractX", x) && at(row, "fractY", y) && at(row, "fractZ", z) && at(row, "occupancy", 1 / shared))
                    found = row;
            }
            if (found < 0)
                return false;
            used.push(found);
        }
        return true;
    }
    // Every parameter of `spec` ("category.name") a fit can vary is free, and there is at least one.
    function allFree(parameters, spec) {
        const [category, name] = spec.split(".");
        let found = false;
        for (let row = 0; row < parameters.rowCount(); ++row) {
            const parameter = parameters.item(row, "parameter") as ParameterItem;
            if (parameter === null || !parameter.fittable || parameter.category !== category || parameter.name !== name)
                continue;
            if (!parameter.free)
                return false;
            found = true;
        }
        return found;
    }
    // Every background point is named by its position, rounded (Id from position).
    function pointsNamedByPosition(points) {
        if (points.rowCount() === 0)
            return false;
        // A point's position is a plain number, not a parameter: read as text.
        for (let row = 0; row < points.rowCount(); ++row) {
            // The core rounds a half to even (146.5 is "146"), so any whole number within half of the position.
            const position = Number(points.text(row, "position"));
            const id = points.text(row, "id");
            if (!isFinite(position) || !/^-?\d+$/.test(id) || Math.abs(Number(id) - position) > 0.5)
                return false;
        }
        return true;
    }
    // A constraint reads `expression`, spaces aside.
    function hasConstraint(constraints, expression) {
        const wanted = expression.replace(/\s+/g, "");
        for (let row = 0; row < constraints.rowCount(); ++row) {
            if (constraints.text(row, "expression").replace(/\s+/g, "") === wanted)
                return true;
        }
        return false;
    }
    // Saves the tutorial's files where the user chose, or downloads them in the browser.
    function saveFiles(folder) {
        Session.saveTutorialFiles(folder);
    }
    // The callout's outline, `w` by `h` with rounded corners, with the pointer on the side facing the control, as an
    // SVG path. Drawn on half pixels, so its 1 px border is sharp.
    function outline(w, h) {
        const r = 4;
        const x0 = 0.5, y0 = 0.5, x1 = w - 0.5, y1 = h - 0.5;
        const b = EaStyle.Sizes.fontPixelSize * 0.6;
        const reach = panel.gap - panel.tipGap;
        const p = panel.pointerAt;
        const side = ["right", "left", "below", "above"].includes(panel.side) ? panel.side : "";
        let d = `M ${x0 + r} ${y0}`;
        if (side === "below")
            d += ` L ${p - b} ${y0} L ${p} ${y0 - reach} L ${p + b} ${y0}`;
        d += ` L ${x1 - r} ${y0} A ${r} ${r} 0 0 1 ${x1} ${y0 + r}`;
        if (side === "left")
            d += ` L ${x1} ${p - b} L ${x1 + reach} ${p} L ${x1} ${p + b}`;
        d += ` L ${x1} ${y1 - r} A ${r} ${r} 0 0 1 ${x1 - r} ${y1}`;
        if (side === "above")
            d += ` L ${p + b} ${y1} L ${p} ${y1 + reach} L ${p - b} ${y1}`;
        d += ` L ${x0 + r} ${y1} A ${r} ${r} 0 0 1 ${x0} ${y1 - r}`;
        if (side === "right")
            d += ` L ${x0} ${p + b} L ${x0 - reach} ${p} L ${x0} ${p - b}`;
        d += ` L ${x0} ${y0 + r} A ${r} ${r} 0 0 1 ${x0 + r} ${y0} Z`;
        return d;
    }

    function back() {
        if (panel.step > 0) {
            --panel.step;
            panel.show();
        }
    }
    // Opens the step's page, then reveals its control and places the callout once the page is laid out.
    function show() {
        panel.revealTries = 0;
        // What the step counts from, read as it becomes the step: Next may be pressed before its callout has faded in.
        panel.fitsAtStep = panel.fitsDone;
        panel.resultsAtStep = AppState.fitResultsShown;
        const changing = panel.current && panel.current.check && panel.current.check.startsWith("changed:") ? panel.parameterNamed(panel.current.check.slice(8).split("=")[0]) : null;
        panel.valueAtStep = changing !== null ? changing.value : null;
        panel.estimatesAtStep = panel.backgroundEstimates;
        // An action step goes on only for what is done after it shows, never because it already held on arrival
        // (Back to a done step stays there), unless it was done ahead: read now, before the fade gives the timer a
        // chance.
        const holdsNow = panel.current ? panel.holds(panel.current.check) : false;
        panel.doneAhead = holdsNow && panel.arrivedForward && !panel.followingHeld;
        panel.heldAtStart = holdsNow && !panel.doneAhead;
        const following = panel.steps[panel.step + 1];
        panel.followingHeld = following ? panel.holds(following.check) : true;
        panel.arrivedForward = false;
        panel.settling = true;
        settled.stop();
        // The last step's control is not this one's: nothing to point at until the reveal has found it.
        panel.revealed = null;
        panel.revealing = true;
        fadedOut.restart();
    }
    // Once the callout has faded out: the step's page, then its control revealed.
    function change() {
        if (panel.current && panel.current.page in panel.pages)
            AppState.open(panel.pages[panel.current.page]);
        Qt.callLater(panel.reveal);
    }
    // A step that asks for an action goes on by itself once the action is done (the owner, 2026-11-02); one that only
    // explains, and the Interface tour, wait for Next.
    function advanceWhenDone() {
        if (panel.revealing || panel.settling)
            return;
        if (panel.revealedInPopup && !panel.revealing && !panel.settling && (panel.revealed === null || !panel.revealed.visible)) {
            panel.revealedInPopup = false;
            if (panel.current && !panel.holds(panel.current.check)) {
                // Its dialog done another way (OK pressed on the name step): on past the step that follows, which holds.
                const following = panel.steps[panel.step + 1];
                if (following && following.check && panel.holds(following.check) && panel.step + 2 < panel.steps.length) {
                    panel.step += 2;
                    panel.arrivedForward = true;
                    panel.show();
                } else {
                    panel.back();
                }
                return;
            }
        }
        if (panel.current && panel.current.check && !panel.heldAtStart && panel.holds(panel.current.check))
            panel.next();
    }
    // Sets up the step's whole context, the same on Next, Back or a jump (ADR-0064): the step's page, the copy of its
    // control on that page that has content (pages and tabs share names: each category has a group on Main and one on
    // Extra), that copy's sidebar or main-view tab current, every folded group around it unfolded, a group step's own
    // group unfolded too, and scrolled to. A control on a sidebar tab not built yet is looked for on each tab in turn.
    // A step that describes a tab (`open`) opens it. Other controls are left as they are: a step asking to open a group
    // or a tab is the user's to do.
    function reveal() {
        const window = Overlay.overlay ? Overlay.overlay.Window.window : null;
        if (!panel.opened || !panel.current || !window)
            return;
        // A page is built in the background the first time it opens and shows only once it is ready; until then
        // nothing of it can be revealed, and the page still shown must not be touched.
        if (!ItemLocator.find(window, `workflow.${panel.current.page}.mainContent`)) {
            if (++panel.revealTries < 40) {
                revealLater.restart();
            } else {
                panel.revealing = false;
                settled.since = Date.now();
                settled.last = "";
                settled.start();
            }
            return;
        }
        panel.revealTries = 0;
        // Read again only for what the step's own setup may have made true, its page or a group it unfolded: anything
        // else that came true since the step began, during the fade, the user did, and it counts as done.
        if (/(^|;)\s*(page|open):/.test(panel.current.check))
            panel.heldAtStart = panel.holds(panel.current.check) && !panel.doneAhead;
        const name = panel.current.target;
        let item = panel.locate(name);
        // A control on the step's sidebar tab not built yet: that tab opened. Never the tabs in turn: a control not on
        // the page (a dialog's field, gone once it closed) left the sidebar on whichever tab was tried last.
        for (const tab of panel.current.tab ? [`sideBar.tab.${panel.current.tab}`] : []) {
            if (item)
                break;
            const button = ItemLocator.find(window, tab) as T.AbstractButton;
            if (button) {
                button.click();
                item = panel.locate(name);
            }
        }
        if (item) {
            for (const ancestor of panel.ancestors(item.parent)) {
                // A tab that is not the current one. A sidebar tab through its tab button, so the tab bar and its view
                // stay bound to each other (a view's index set directly would come loose from them); a main-view tab
                // through its page, which sets its tab bar.
                if (ancestor.SwipeView.view && !ancestor.SwipeView.isCurrentItem) {
                    if (panel.inSidebar(ancestor.SwipeView.view))
                        (ItemLocator.find(window, panel.sidebarTabs[ancestor.SwipeView.index]) as T.AbstractButton)?.click();
                    else
                        panel.pageOf(ancestor)?.showMainTab(ancestor.SwipeView.index);
                }
                if (ancestor.collapsible === true && ancestor.collapsed === true)
                    ancestor.collapsed = false;
            }
            // A step on a group shows what the group holds, unless opening it is what the step asks.
            if (item.collapsible === true && item.collapsed === true && panel.current.check !== `open:${name}`)
                item.collapsed = false;
            if (panel.current.open && ItemLocator.shown(item))
                (item as T.AbstractButton)?.click();
        }
        panel.revealed = item;
        panel.revealedInPopup = item !== null && panel.popupOf(item) !== null;
        panel.revealing = false;
        panel.scrollTo(item);
        // Shown once everything has stopped moving (unfolded groups take their height as the base animates it).
        settled.since = Date.now();
        settled.last = "";
        settled.start();
        panel.place();
    }
    // The sidebar's tabs, in their order.
    readonly property var sidebarTabs: ["sideBar.tab.basic", "sideBar.tab.extras", "sideBar.tab.text", "sideBar.tab.settings"]
    // Whether `view` is a page's sidebar (inside its `workflow.<page>.sidebarHost`).
    function inSidebar(view) {
        for (let ancestor = view; ancestor !== null; ancestor = ancestor.parent) {
            if (ancestor.objectName.endsWith(".sidebarHost"))
                return true;
        }
        return false;
    }
    // The step's control by name. On the step's page and its sidebar tab: among its copies with content (a copy a tier
    // leaves empty is hidden), the one on the tabs already current, else the first; a copy on a tab beside the current one also counts
    // as shown, so being shown does not choose. Outside the page (the app bar, the status bar): the one shown.
    function locate(name) {
        const window = Overlay.overlay ? Overlay.overlay.Window.window : null;
        if (!window || !name)
            return null;
        if (name.includes("@"))
            return panel.locateByParameter(window, name);
        const host = panel.current ? ItemLocator.findAnywhere(window, `workflow.${panel.current.page}.sidebarHost`) : null;
        if (host && host.parent) {
            // On the step's sidebar tab when it has one (Peak and Background are on Main and on Extra).
            const tab = panel.current.tab ? panel.sidebarTabs.indexOf(`sideBar.tab.${panel.current.tab}`) : -1;
            const copies = panel.named(host.parent, name).filter(item => item.visible && (tab < 0 || [-1, tab].includes(panel.sidebarTabOf(item))));
            const current = copies.find(item => panel.onCurrentTabs(item));
            if (current || copies.length > 0)
                return current ?? copies[0];
        }
        return ItemLocator.find(window, name) ?? (host && host.parent ? ItemLocator.findUnder(host.parent, name) : ItemLocator.findAnywhere(window, name));
    }
    // The dialog or popup `item` is in (the item under the overlay holding it), or null; never the callout itself.
    function popupOf(item) {
        for (let ancestor = item; ancestor !== null; ancestor = ancestor.parent) {
            if (ancestor.parent === Overlay.overlay)
                return ancestor === panel.contentItem.parent ? null : ancestor;
        }
        return null;
    }
    // The controls of the dialog or popup holding `target` other than `target`: what the callout keeps clear of.
    function dialogControls(target) {
        const popup = panel.popupOf(target);
        const found = [];
        if (popup === null)
            return found;
        const walk = item => {
            if (!item.visible)
                return;
            if (item !== target && ((item as T.AbstractButton) !== null || item instanceof TextInput || item instanceof TextEdit || (item as T.ComboBox) !== null) && ItemLocator.shown(item)) {
                found.push(ItemLocator.visibleRect(item));
                return;
            }
            for (const child of item.children)
                walk(child);
        };
        walk(popup);
        return found;
    }
    // A control found by the parameters it is about, never by its row (the owner, 2026-11-02): `<cell>@<path>` is that
    // cell of the parameters table's row whose path ends with `<path>` ("parameters.su@La.adp_iso"), and
    // `correlations.cell@<path>|<path>` the Correlations square of the two.
    function locateByParameter(window, spec) {
        const [base, wanted] = spec.split("@");
        if (base === "correlations.cell") {
            const chart = ItemLocator.find(window, "correlations");
            if (!chart)
                return null;
            const [first, second] = wanted.split("|");
            const i = chart.labels.findIndex(label => panel.dotted(label).endsWith(first));
            const j = chart.labels.findIndex(label => panel.dotted(label).endsWith(second));
            if (i < 0 || j < 0)
                return null;
            const cells = [panel.named(chart, `correlations.cell.${i}.${j}`)[0], panel.named(chart, `correlations.cell.${j}.${i}`)[0]];
            return cells.find(cell => cell && !isNaN(cell.value)) ?? cells[0] ?? null;
        }
        const host = panel.current ? ItemLocator.findAnywhere(window, `workflow.${panel.current.page}.sidebarHost`) : null;
        const rows = [];
        const walk = item => {
            if (item.objectName.startsWith("parameters.row.") && item.visible && typeof item.path === "string" && panel.dotted(item.path).endsWith(wanted))
                rows.push(item);
            for (const child of item.children)
                walk(child);
        };
        walk(host ? host.parent : window.contentItem);
        let built = null;
        for (const row of rows) {
            const cell = panel.named(row, `${base}.${row.objectName.split(".").pop()}`)[0];
            if (cell && ItemLocator.shown(cell))
                return cell;
            built = built ?? cell ?? null;
        }
        // Its row is not built, the table making rows only as they come into view (DataTable), or it is built but
        // scrolled out of sight. Found by the parameter itself in the rows the filters show, the table is scrolled
        // just enough to show it, and the cell then looked for again. A row the filters hide stays hidden: no header
        // or other row stands in for it.
        const table = panel.locate("parameters.list");
        const parameter = table !== null ? panel.parameterNamed(wanted) : null;
        const shown = parameter !== null && table.sourceModel ? table.sourceModel.rowOf(parameter) : -1;
        if (shown < 0)
            return built;
        table.positionViewAtIndex(shown, ListView.Contain);
        table.forceLayout();
        rows.length = 0;
        walk(host ? host.parent : window.contentItem);
        for (const row of rows) {
            const cell = panel.named(row, `${base}.${row.objectName.split(".").pop()}`)[0];
            if (cell)
                return cell;
        }
        return built;
    }
    // Every item named `name` under `root`, in the order they are drawn.
    function named(root, name) {
        const found = [];
        const walk = item => {
            if (item.objectName === name)
                found.push(item);
            for (const child of item.children)
                walk(child);
        };
        walk(root);
        return found;
    }
    // The index of the sidebar tab holding `item`, -1 outside the sidebar.
    function sidebarTabOf(item) {
        for (let ancestor = item; ancestor !== null; ancestor = ancestor.parent) {
            if (ancestor.SwipeView.view && panel.inSidebar(ancestor.SwipeView.view))
                return ancestor.SwipeView.index;
        }
        return -1;
    }
    // Whether every tab holding `item` is its view's current one.
    function onCurrentTabs(item) {
        for (let ancestor = item; ancestor !== null; ancestor = ancestor.parent) {
            if (ancestor.SwipeView.view && !ancestor.SwipeView.isCurrentItem)
                return false;
        }
        return true;
    }
    function isWithin(item, root) {
        for (let ancestor = item; ancestor !== null; ancestor = ancestor.parent) {
            if (ancestor === root)
                return true;
        }
        return false;
    }
    // The workflow page holding `item`, which shows its main-view tabs.
    function pageOf(item) {
        for (let ancestor = item; ancestor !== null; ancestor = ancestor.parent) {
            if (typeof ancestor.showMainTab === "function")
                return ancestor;
        }
        return null;
    }
    // The item and its ancestors, from the outside in.
    function ancestors(item) {
        const chain = [];
        for (let ancestor = item; ancestor !== null; ancestor = ancestor.parent)
            chain.unshift(ancestor);
        return chain;
    }
    // Scrolls every list or page holding `item` so that it is in view.
    // Whether it moved a list.
    function scrollTo(item) {
        let moved = false;
        if (!item)
            return moved;
        const margin = EaStyle.Sizes.fontPixelSize;
        for (const ancestor of panel.ancestors(item)) {
            if (!(ancestor instanceof Flickable) || ancestor === item)
                continue;
            const flickable = ancestor as Flickable;
            // Only a list that scrolls up and down, and only when it has to move. A tab view's own list scrolls
            // sideways; setting its position while it slides to a new tab stopped the slide half way, leaving the
            // previous tab's place, emptied, on screen under the new tab's name.
            if (flickable.contentHeight <= flickable.height)
                continue;
            const rect = item.mapToItem(flickable.contentItem, 0, 0, item.width, item.height);
            const top = flickable.contentY;
            let wanted = top;
            if (rect.y + rect.height > top + flickable.height)
                wanted = rect.y + rect.height - flickable.height + margin;
            if (rect.y < wanted)
                wanted = rect.y - margin;
            const clamped = Math.max(0, Math.min(Math.max(0, flickable.contentHeight - flickable.height), wanted));
            if (clamped !== flickable.contentY) {
                flickable.contentY = clamped;
                moved = true;
            }
        }
        return moved;
    }
    // What the callout points at: the step's control when it can be seen, else the nearest group holding it that can
    // (its header), else the step's `via` control.
    function anchorItem(window) {
        const target = panel.revealed && ItemLocator.shown(panel.revealed) && panel.onCurrentTabs(panel.revealed) ? panel.revealed : null;
        if (target)
            return target;
        // The step's control was let go of while the step shows (a table's row scrolled away and destroyed), or a named
        // parameter's cell scrolled out of sight: found again by what the step names, not by the item it had.
        if (!panel.revealing && !panel.settling && (panel.revealed === null || panel.current.target.includes("@"))) {
            const again = panel.locate(panel.current.target);
            if (again !== null && ItemLocator.shown(again) && panel.onCurrentTabs(again)) {
                panel.revealed = again;
                return again;
            }
        }
        if (panel.revealed) {
            for (let ancestor = panel.revealed.parent; ancestor !== null; ancestor = ancestor.parent) {
                if ((ancestor as EaElements.GroupBox) !== null && ItemLocator.shown(ancestor))
                    return ancestor;
            }
        }
        return panel.current.via ? ItemLocator.find(window, panel.current.via) : null;
    }
    // The input a labelled control holds (its text field or combo box), which the pointer aims at; the control itself
    // when it holds none.
    // The box a field or combo box draws (its background), when it has one shown; else null.
    function boxOf(control) {
        const box = control && control.background !== undefined ? control.background : null;
        return box !== null && box.visible && box.height > 0 && ItemLocator.shown(box) ? box : null;
    }
    function inputOf(item) {
        if (item instanceof TextInput || item instanceof T.ComboBox)
            return item;
        for (let i = 0; i < item.children.length; ++i) {
            const child = item.children[i];
            if (!child.visible)
                continue;
            const input = panel.inputOf(child);
            if (input !== child || child instanceof TextInput || child instanceof T.ComboBox)
                return input;
        }
        return item;
    }
    // Puts the callout beside the step's control at the small fixed gap (the owner, 2026-11-02), on the first side with
    // room: right, left, below, above, sliding along that side to stay in the window and never covering the control.
    // The pointer is always the same size and reaches across the gap to the control, which is outlined. A control too
    // large for any side has the callout inside it, without a pointer. With nothing to point at, no callout shows.
    function place() {
        if (!panel.opened || !Overlay.overlay || !panel.current)
            return;
        const window = Overlay.overlay.Window.window;
        const item = window ? panel.anchorItem(window) : null;
        const margin = EaStyle.Sizes.fontPixelSize;
        const width = Overlay.overlay.width;
        const height = Overlay.overlay.height;
        const clampX = value => Math.max(margin, Math.min(width - panel.width - margin, value));
        const clampY = value => Math.max(margin, Math.min(height - panel.height - margin, value));
        // Never a callout without its control: hidden until the control is found and shown, which the reveal and the
        // timer below keep trying.
        if (!item && panel.revealing)
            return;
        panel.anchored = item !== null;
        if (!item) {
            outlineBox.visible = false;
            panel.side = "";
            return;
        }
        // A field's input, not a group, a button or a whole area: those are pointed at as they are.
        const whole = (item as EaElements.GroupBox) !== null || (item as T.AbstractButton) !== null || panel.current.target.startsWith("workflow.");
        const input = item.objectName === panel.current.target && !whole ? panel.inputOf(item) : item;
        // A field or combo box by its own box: one with a title above it holds the title too (the owner, 2026-11-02).
        const box = input !== item || input instanceof TextInput || (input as T.ComboBox) !== null ? panel.boxOf(input) : null;
        let rect = ItemLocator.visibleRect(box !== null ? box : ItemLocator.shown(input) ? input : item);
        // A group pointed at in place of a control it holds: its header.
        if (item.objectName !== panel.current.target && item.collapsible !== undefined)
            rect = Qt.rect(rect.x, rect.y, rect.width, Math.min(rect.height, margin * 2.5));
        outlineBox.x = rect.x - 3;
        outlineBox.y = rect.y - 3;
        outlineBox.width = rect.width + 6;
        outlineBox.height = rect.height + 6;
        outlineBox.visible = true;
        const middleX = rect.x + rect.width / 2;
        const middleY = rect.y + rect.height / 2;
        // A step about a whole area (a page's main view) has nothing to point at: the callout sits in the middle of the
        // window, as a dialog does (the owner, 2026-11-02). Only when that would cover what the step names, the area
        // itself unless the step names nothing in it (`coversTarget`), or the status bar's strip, does it move to the
        // nearest place clear of them.
        if (panel.current.target.startsWith("workflow.")) {
            outlineBox.visible = false;
            panel.side = "";
            const stripItem = ItemLocator.find(window, "statusBar.tutorial");
            const keepClear = (stripItem ? [ItemLocator.visibleRect(stripItem)] : []).concat(panel.current.coversTarget ? [] : [rect]);
            const centreX = clampX((width - panel.width) / 2);
            const centreY = clampY((height - panel.height) / 2);
            const covers = (x, y) => keepClear.some(r => x < r.x + r.width && r.x < x + panel.width && y < r.y + r.height && r.y < y + panel.height);
            const fits = (x, y) => x >= margin && y >= margin && x + panel.width <= width - margin && y + panel.height <= height - margin;
            // The centre, else beside each thing to keep clear on each of its sides, the nearest that clears them all.
            const candidates = [[centreX, centreY]];
            for (const r of keepClear) {
                candidates.push([r.x + r.width + margin, centreY], [r.x - panel.width - margin, centreY], [centreX, r.y + r.height + margin], [centreX, r.y - panel.height - margin]);
            }
            const free = candidates.filter(([x, y]) => fits(x, y) && !covers(x, y));
            free.sort((p, q) => Math.hypot(p[0] - centreX, p[1] - centreY) - Math.hypot(q[0] - centreX, q[1] - centreY));
            const [x, y] = free.length > 0 ? free[0] : [centreX, centreY];
            panel.x = x;
            panel.y = y;
            return;
        }
        // Nor does it cover the status bar's strip of the same tutorial, whose buttons stay usable, or, for a control
        // in a dialog, the dialog's other fields and buttons.
        const strip = ItemLocator.find(window, "statusBar.tutorial");
        const obstacles = (strip ? [ItemLocator.visibleRect(strip)] : []).concat(panel.dialogControls(item));
        // A cell of the parameters table: its row and the slider under the table stay clear, as the step is about them.
        for (let ancestor = item; ancestor !== null; ancestor = ancestor.parent) {
            if (ancestor.objectName.startsWith("parameters.row.")) {
                obstacles.push(ItemLocator.visibleRect(ancestor));
                const slider = ItemLocator.find(window, "parameters.slider");
                if (slider)
                    obstacles.push(ItemLocator.visibleRect(slider));
                break;
            }
        }
        // A control in the main view: the sidebar beside it stays clear, as the table it explains may be there.
        const mainView = ItemLocator.find(window, `workflow.${panel.current.page}.mainContent`);
        const sidebar = ItemLocator.find(window, `workflow.${panel.current.page}.sidebarHost`);
        if (mainView && sidebar && panel.isWithin(item, mainView))
            obstacles.push(ItemLocator.visibleRect(sidebar));
        const free = (x, y) => obstacles.every(o => o.width <= 0 || x >= o.x + o.width || x + panel.width <= o.x || y >= o.y + o.height || y + panel.height <= o.y);
        const besideY = clampY(middleY - panel.height / 2);
        const alongX = clampX(middleX - panel.width / 2);
        if (rect.x + rect.width + panel.gap + panel.width + margin <= width && free(rect.x + rect.width + panel.gap, besideY)) {
            panel.side = "right";
            panel.x = rect.x + rect.width + panel.gap;
            panel.y = besideY;
        } else if (rect.x - panel.gap - panel.width >= margin && free(rect.x - panel.gap - panel.width, besideY)) {
            panel.side = "left";
            panel.x = rect.x - panel.gap - panel.width;
            panel.y = besideY;
        } else if (rect.y + rect.height + panel.gap + panel.height + margin <= height && free(alongX, rect.y + rect.height + panel.gap)) {
            panel.side = "below";
            panel.x = alongX;
            panel.y = rect.y + rect.height + panel.gap;
        } else if (rect.y - panel.gap - panel.height >= margin && free(alongX, rect.y - panel.gap - panel.height)) {
            panel.side = "above";
            panel.x = alongX;
            panel.y = rect.y - panel.gap - panel.height;
        } else {
            panel.side = "inside";
            panel.x = clampX(rect.x + rect.width - panel.width - margin);
            panel.y = clampY(rect.y + margin);
        }
        const along = panel.side === "right" || panel.side === "left" ? middleY - panel.y : middleX - panel.x;
        const length = panel.side === "right" || panel.side === "left" ? panel.height : panel.width;
        panel.pointerAt = Math.max(margin, Math.min(length - margin, along));
    }

    objectName: "tutorial"
    // Above every dialog and popup a step may point into (the owner, 2026-11-02).
    z: 1000
    opacity: anchored && !settling ? 1 : 0
    Behavior on opacity {
        NumberAnimation {
            duration: 150
        }
    }
    // In the window's coordinates, as the control's rectangle is.
    parent: Overlay.overlay
    modal: false
    closePolicy: Popup.NoAutoClose
    width: EaStyle.Sizes.fontPixelSize * 26
    padding: EaStyle.Sizes.fontPixelSize
    // The same space on every side, measured from what shows (the owner, 2026-11-02): from the top of the heading's
    // letters and from the bottom of the icons' glyphs, not from the line boxes and buttons around them.
    topPadding: Math.max(0, padding - headingInk.inkTop)
    bottomPadding: Math.max(0, padding - calloutControls.inkBottomInset)

    onOpened: Qt.callLater(panel.reveal)
    onHeightChanged: Qt.callLater(panel.place)

    // A window closed during a tutorial does not leave one running for the next window.
    Component.onDestruction: {
        if (panel.tutorial !== null)
            AppState.tutorialRunning = false;
    }
    onClosed: {
        outlineBox.visible = false;
        panel.tutorial = null;
        panel.temporary = false;
        AppState.tutorialRunning = false;
    }
    // A replacement or a quit ended the tutorial and brought the user's project back.
    Connections {
        target: AppState
        function onTutorialEnded() {
            panel.close();
        }
    }
    // The example a tutorial starts from has opened aside, or not; the files a step needs have arrived, or not.
    Connections {
        target: Session
        function onExampleOpenFinished(exampleId, opened) {
            const chosen = panel.pendingStart;
            if (chosen === null)
                return;
            panel.pendingStart = null;
            if (opened && Session.hasProjectSetAside)
                panel.begin(chosen, true);
            else
                RunLog.note(`tutorial not started: ${chosen.id}, its example did not open`);
        }
        function onTutorialFilesStaged(folder) {
            panel.stagedFolder = folder.toString();
            const again = panel.afterStaging;
            panel.afterStaging = "";
            if (again !== "")
                panel.perform(again);
        }
        function onTutorialFilesSaved() {
            panel.filesSaved = true;
        }
        function onTutorialFilesFailed(message) {
            panel.afterStaging = "";
            RunLog.note(`tutorial files not available: ${message}`);
        }
    }

    // A fit of the tutorial's project finished: counted once it has stopped and has its outcome, which a project's
    // first fit gets only after it has stopped.
    property bool fitRunning: false
    // A fit counts once it has succeeded: one that failed, was stopped or ran out of iterations is no stage done, and
    // the step asks for the fit again. Every fit of the tutorials ends in success, the unconstrained
    // B_iso one with its large uncertainties included.
    function countFit() {
        const fit = Session.project ? Session.project.fit : null;
        if (panel.fitRunning && fit !== null && !fit.running && fit.outcome !== "") {
            panel.fitRunning = false;
            if (fit.outcome === "success")
                ++panel.fitsDone;
        }
    }
    Connections {
        target: Session.project ? Session.project.fit : null
        enabled: panel.tutorial !== null
        function onRunningChanged() {
            if (Session.project.fit.running)
                panel.fitRunning = true;
            panel.countFit();
        }
        function onOutcomeChanged() {
            panel.countFit();
        }
    }
    // The background points were estimated: the list replaced or its points moved.
    Connections {
        target: Session.project && Session.project.currentExperiment ? Session.project.currentExperiment.background : null
        enabled: panel.tutorial !== null
        function onModelReset() {
            ++panel.backgroundEstimates;
        }
        function onRowsInserted() {
            ++panel.backgroundEstimates;
        }
    }
    // The window resized: the control may have moved.
    Connections {
        target: Overlay.overlay
        function onWidthChanged() {
            Qt.callLater(panel.place);
        }
        function onHeightChanged() {
            Qt.callLater(panel.place);
        }
    }
    // The reveal again, while the step's page is still being built.
    Timer {
        id: revealLater

        interval: 250
        onTriggered: panel.reveal()
    }
    // Unfolding a group animates its height; the control is scrolled to again once it has its place.
    // Next's fit, asked again while the project recalculates: up to a minute, while the step still wants it.
    Timer {
        id: fitAgain

        property int tries: 0

        interval: 250
        repeat: true
        onTriggered: {
            const fit = Session.project ? Session.project.fit : null;
            if (fit === null || fit.running || ++tries > 240 || !panel.current || !["fitted", "fit-done"].includes(panel.current.check) || panel.fitsDone > panel.fitsAtStep) {
                stop();
                return;
            }
            fit.start();
        }
    }
    Timer {
        id: fadedOut

        interval: 150
        onTriggered: panel.change()
    }
    // Watches the step's control until it stays put: twice in the same place, at least a quarter of a second after
    // the reveal, so a group that has just started unfolding counts as moving; at most three seconds.
    Timer {
        id: settled

        property real since: 0
        property string last: ""

        interval: 100
        repeat: true
        onTriggered: {
            const item = panel.revealed;
            const r = item ? ItemLocator.sceneRect(item) : null;
            const now = r ? `${Math.round(r.x)},${Math.round(r.y)},${Math.round(r.width)},${Math.round(r.height)}` : "none";
            const elapsed = Date.now() - since;
            if ((now !== last || elapsed < 250) && elapsed < 3000) {
                last = now;
                return;
            }
            // A group that has unfolded may want the list moved again.
            if (panel.scrollTo(item) && elapsed < 3000) {
                last = "";
                return;
            }
            stop();
            if (panel.shownStep !== panel.step && panel.tutorial !== null)
                RunLog.note(`tutorial ${panel.tutorial.id}: step ${panel.step + 1} of ${panel.steps.length}`);
            panel.shownStep = panel.step;
            panel.settling = false;
            panel.place();
        }
    }
    // The step's control can appear, move or scroll away after the step shows: after a page change has slid it into
    // place, once the user has done what the step asks, or when a list scrolls. The callout follows it.
    Timer {
        interval: 250
        repeat: true
        running: panel.opened
        onTriggered: {
            panel.advanceWhenDone();
            panel.place();
        }
    }

    FolderDialog {
        id: filesFolder

        title: qsTr("Save the tutorial files to")
        onAccepted: panel.saveFiles(selectedFolder)
    }

    // The outline drawn around the step's control, over the page.
    Rectangle {
        id: outlineBox

        parent: Overlay.overlay
        visible: false
        color: "transparent"
        radius: 3
        border.width: 2
        border.color: EaStyle.Colors.themeAccent
    }

    // The callout and its pointer as one outline, one fill and one border, drawn by the curve renderer: no seam where
    // the pointer meets the box and smooth edges at any scale (the owner, 2026-11-02).
    background: Item {
        Shape {
            anchors.fill: parent
            preferredRendererType: Shape.CurveRenderer

            ShapePath {
                fillColor: panel.fill
                strokeColor: panel.edge
                strokeWidth: 1

                PathSvg {
                    path: panel.outline(pointer.parent.width, pointer.parent.height)
                }
            }
        }
        // Where the pointer is: from the callout's edge facing the control to its point toward it.
        Item {
            id: pointer

            // Across the edge, and how far the point reaches out from it.
            readonly property real base: EaStyle.Sizes.fontPixelSize * 1.2
            readonly property real reach: panel.gap - panel.tipGap
            readonly property bool across: panel.side === "right" || panel.side === "left"

            objectName: "tutorial.pointer"
            visible: ["right", "left", "below", "above"].includes(panel.side)
            width: across ? reach : base
            height: across ? base : reach
            x: panel.side === "right" ? -width : panel.side === "left" ? parent.width : panel.pointerAt - width / 2
            y: panel.side === "below" ? -height : panel.side === "above" ? parent.height : panel.pointerAt - height / 2
        }
    }

    contentItem: Column {
        spacing: EaStyle.Sizes.fontPixelSize * 0.75

        // The step's title, and Step N of M at the right of the same line.
        Item {
            id: headingInk

            // How far below the line's top the letters of either label begin.
            readonly property real inkTop: Math.max(0, Math.min(titleLine.ascent + titleInk.tightBoundingRect.y, progressLine.ascent + progressInk.tightBoundingRect.y))

            width: parent.width
            height: Math.max(title.implicitHeight, progress.implicitHeight)

            EaElements.Label {
                id: title

                objectName: "tutorial.title"
                width: parent.width - progress.implicitWidth - EaStyle.Sizes.fontPixelSize
                elide: Text.ElideRight
                font.bold: true
                // The step's own title (the owner, 2026-11-02); the tutorial's name is in its first step and the strip.
                text: panel.shown && panel.shown.title !== "" ? panel.shown.title : panel.tutorial ? panel.tutorial.title : ""
            }
            FontMetrics {
                id: titleLine
                font: title.font
            }
            TextMetrics {
                id: titleInk
                font: title.font
                text: title.text
            }
            FontMetrics {
                id: progressLine
                font: progress.font
            }
            TextMetrics {
                id: progressInk
                font: progress.font
                text: progress.text
            }
            EaElements.Label {
                id: progress

                objectName: "tutorial.progress"
                anchors.right: parent.right
                color: panel.progressColor
                text: qsTr("Step %1 of %2").arg(panel.shownStep + 1).arg(panel.steps.length)
            }
        }
        EaElements.Label {
            objectName: "tutorial.text"
            width: parent.width
            wrapMode: Text.WordWrap
            text: panel.shown ? panel.shown.text : ""
        }
        // The tutorial's own files, for a step that works with them.
        IconLink {
            objectName: "tutorial.saveFiles"
            visible: panel.shown !== null && panel.shown.files
            fontIcon: "download"
            text: qsTr("Save tutorial files")
            onClicked: WebFiles.available ? panel.saveFiles("") : filesFolder.open()
        }
        // The last step's two ways on, each in one sentence, named from the real projects (the owner, 2026-11-02).
        EaElements.Label {
            objectName: "tutorial.end"
            visible: panel.atEnd && panel.offersKeep
            width: parent.width
            wrapMode: Text.WordWrap
            text: {
                const name = Session.project ? Session.project.name : "";
                const own = Session.projectSetAsideName;
                const keep = qsTr("Keep working on %1: it stays open, unsaved until you save it.").arg(name);
                const back = own !== "" ? qsTr("Return to my project: %1 is closed and %2 comes back as it was.").arg(name).arg(own) : qsTr("Close %1: it is closed without saving.").arg(name);
                const unsaved = Session.projectSetAsideModified ? " " + qsTr("Keeping it closes %1 without saving its changes.").arg(own) : "";
                return `${keep} ${back}${unsaved}`;
            }
        }
        Row {
            objectName: "tutorial.endChoices"
            visible: panel.atEnd && panel.offersKeep
            anchors.right: parent.right
            spacing: EaStyle.Sizes.fontPixelSize

            EaElements.Button {
                objectName: "tutorial.discard"
                text: Session.projectSetAsideName !== "" ? qsTr("Return to my project") : qsTr("Close %1").arg(Session.project ? Session.project.name : "")
                onClicked: panel.stop()
            }
            EaElements.Button {
                objectName: "tutorial.keep"
                highlighted: true
                text: qsTr("Keep working on %1").arg(Session.project ? Session.project.name : "")
                // The tutorial's project stays open as the user's, unsaved until they save it.
                onClicked: {
                    RunLog.note("tutorial finished, its project kept");
                    Session.dropProjectSetAside();
                    panel.temporary = false;
                    panel.close();
                }
            }
        }
        // The actions at the bottom right: Stop, Back and Next as the status bar's strip has them (TutorialControls), Next
        // off on the last step, where the end choices stand in for Stop. The arrow keys
        // step back and on and Escape stops, while no text field, list or other control that takes those keys has the
        // focus.
        Item {
            id: controls

            readonly property Item focused: Window.activeFocusItem
            readonly property bool keysFree: focused === null || (focused.cursorPosition === undefined && focused.currentIndex === undefined && focused.value === undefined)

            width: parent.width
            height: actions.height

            Shortcut {
                sequence: "Left"
                enabled: panel.opened && controls.keysFree && panel.step > 0
                onActivated: panel.back()
            }
            Shortcut {
                sequence: "Right"
                enabled: panel.opened && controls.keysFree && !panel.atEnd
                onActivated: panel.forward()
            }
            Shortcut {
                sequence: "Escape"
                enabled: panel.opened && controls.keysFree
                onActivated: panel.stop()
            }

            Row {
                id: actions

                anchors.right: parent.right
                spacing: EaStyle.Sizes.fontPixelSize * 0.5

                TutorialControls {
                    id: calloutControls

                    anchors.verticalCenter: parent.verticalCenter
                    tutorial: panel
                    stopShown: panel.canGoOn
                }
            }
        }
    }
}
