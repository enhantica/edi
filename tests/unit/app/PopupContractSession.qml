// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import OnboardingAcceptance 1.0
import EdiOnlineHttpFixture 1.0
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render

CollectionBoundarySession {
    SignalSpy { id: delivered; target: Session.onlineSearch; signalName: "fileReady" }
    property int sourceSerial: 0

    function popupFixture(name) {
        const file = SettingsProof.fileObservation(Qt.resolvedUrl("../../fixtures/online_popup_contract/"), name);
        verify(file.exists, "Popup contracts read an independently authored fixture");
        return JSON.parse(file.text);
    }
    function codAnswer(answer) {
        OnlineHttpFixture.enqueue(200, String(answer.length));
        OnlineHttpFixture.enqueue(200, JSON.stringify(answer));
    }
    function sourceFor(kind, value) {
        const shape = {page:kind === "structure" ? AppState.Page.Structure : AppState.Page.Experiment,
                       group:kind === "structure" ? "structures" : "experiments",
                       action:kind === "structure" ? "web" : kind === "experiment" ? "experimentWeb" : "dataWeb"};
        openOnline(shape);
        verify(OnlineHttpFixture.attach(Session.onlineSearch), "Popup assertions replace only HTTP transport");
        OnlineHttpFixture.clear();
        Session.onlineSources.add();
        Session.onlineSources.setKinds("new-source", [kind]);
        Session.onlineSources.setUrl("new-source", "https://popup.invalid/" + (++sourceSerial));
        Session.onlineSearch.sourceId = "new-source";
        OnlineHttpFixture.enqueue(200, JSON.stringify(value));
        return Session.onlineSearch;
    }
    function searchDocument(kind, value, fields = {}) {
        const search = sourceFor(kind, value);
        for (const key of Object.keys(fields)) search.setField(key, fields[key]);
        search.search();
        tryCompare(search, "busy", false, 3000, "The fixture index finishes before its rendered result is inspected");
        return search;
    }
    function headers() {
        const table = onlineControl("results");
        const row = Array.from(table.headerItem.children).find(item => item.children.length === table.columnWidths.length);
        verify(row !== undefined, "The results header exposes one cell per rendered column");
        return Array.from(row.children).map(item => item.text);
    }
    function check_columns_data() { return ["cod", "collection"].map(tag => ({tag:tag})); }
    function check_columns(data) {
        resetProject();
        if (data.tag === "collection") searchDocument("structure", sourceDocument());
        else {
            openOnline({page:AppState.Page.Structure, group:"structures", action:"web"});
            verify(OnlineHttpFixture.attach(Session.onlineSearch), "COD columns use an injected answer");
            OnlineHttpFixture.clear();
            codAnswer(popupFixture("cod_publication.json"));
            Session.onlineSearch.search();
            tryCompare(Session.onlineSearch, "busy", false, 3000, "The COD result reaches the common table");
        }
        const titles = headers();
        compare(titles.filter(title => title !== "").length, 6, "Structure results have one index and six owner-declared columns");
        compare(titles.filter(title => title !== ""), ["ID", "Name", "Formula", "Space group", "Cell", "Reference"],
                "COD and collection expose the same structure columns without Kind");
        verify(!Render.descendants(onlineControl("results")).some(item => item.fontIcon === "download" && typeof item.clicked === "function"),
               "Result rows have no per-row download action");
    }
    function check_fields_data() {
        return ["cod", "collection", "experiment", "data"].map(tag => ({tag:tag}));
    }
    function check_fields(data) {
        resetProject();
        const kind = ["cod", "collection"].includes(data.tag) ? "structure" : data.tag;
        const search = sourceFor(kind, sourceDocument());
        if (data.tag === "cod") search.sourceId = "cod";
        const keys = Array.from({length:search.fields.count}, (_, index) => search.fields.keyAt(index));
        if (kind === "structure") compare(keys, ["id", "name", "formula", "elements", "space_group"],
                                         "Both structure sources offer the same complete ordered search fields");
        else for (const key of ["id", "name", "formula", "elements", "radiation", "technique", "instrument"])
            verify(keys.includes(key), "Experiment and measured-data searches retain their descriptive fields and add Formula and Elements");
        const hint = onlineControl("field.formula").placeholderText;
        verify(["LaCoO3", "La Co O3"].every(sample => hint.includes(sample)),
               "Formula guidance shows the owner's examples of arbitrary order and spacing");
    }
    function check_kind_data() { return ["structure", "experiment", "data"].map(tag => ({tag:tag})); }
    function check_kind(data) {
        resetProject();
        const search = searchDocument(data.tag, popupFixture("formula_index.json"));
        const entries = Probe.rows(search.results);
        compare(entries.length, 3, "The mixed fixture offers three entries of each popup's own kind");
        verify(entries.every(row => row.kind === data.tag), "A popup never lists another entry kind");
        verify(!headers().includes("Kind"), "A kind-specific popup has no redundant Kind column");
    }
    function check_formula_order_data() { return ["structure", "experiment", "data"].map(tag => ({tag:tag})); }
    function check_formula_order(data) {
        resetProject();
        const search = searchDocument(data.tag, popupFixture("formula_index.json"), {formula:"LaCoO3"});
        compare(Probe.rows(search.results).map(row => row.id), [data.tag + "-zzz-exact", data.tag + "-aaa-substituted"],
                "Collection formula search ignores amounts, excludes missing elements and ranks exact Hill matches first");
    }
    function check_cod_name_and_formula_data() {
        return ["commonname", "mineral", "chemname", "title"].map(tag => ({tag:tag}));
    }
    function check_cod_name_and_formula(data) {
        resetProject();
        openOnline({page:AppState.Page.Structure, group:"structures", action:"web"});
        const search = Session.onlineSearch;
        verify(OnlineHttpFixture.attach(search), "COD Name and Formula use an injected answer");
        OnlineHttpFixture.clear();
        const answer = popupFixture("cod_publication.json");
        const order = ["commonname", "mineral", "chemname", "title"];
        for (const key of order.slice(0, order.indexOf(data.tag))) delete answer[0][key];
        answer[0][data.tag] = "alpha oxide";
        codAnswer([answer[0]]);
        search.setField("name", "alpha");
        search.setField("formula", "LaCoO3");
        search.search();
        tryCompare(search, "busy", false, 3000, "COD Name filtering reaches its result state");
        compare(Probe.rows(search.results).map(row => row.id), ["9100001"], "COD Name is applied to its answer instead of being silently dropped");
        compare(Probe.rows(search.results)[0].name, "alpha oxide", "COD Name follows commonname, mineral, chemname and title priority");
        const query = OnlineHttpFixture.query(OnlineHttpFixture.requests()[0]);
        compare(query.text, "alpha", "COD receives Name as its metadata text query");
        compare(query.formula, "Co La O3", "COD retains its exact Hill formula query while collection matching ignores amounts");
    }
    function check_reference_data() { return ["multi", "single", "unknown"].map(tag => ({tag:tag})); }
    function check_reference(data) {
        resetProject();
        openOnline({page:AppState.Page.Structure, group:"structures", action:"web"});
        const search = Session.onlineSearch;
        verify(OnlineHttpFixture.attach(search), "Publication metadata comes from the injected COD answer");
        OnlineHttpFixture.clear();
        const answer = popupFixture("cod_publication.json");
        if (data.tag === "single") answer[0].authors = "Ng";
        if (data.tag === "unknown") answer[0].journal = "Unlisted Fixture Journal";
        codAnswer(answer);
        search.search();
        tryCompare(search, "busy", false, 3000, "The publication answer finishes before reference input");
        const expected = (data.tag === "single" ? "Ng" : "Smith et al.") + ", " + (data.tag === "unknown" ? "Unlisted Fixture Journal" : "Phys. Rev. B") + " 40, 34 (2026)";
        let reference;
        tryVerify(() => {
            reference = Render.descendants(onlineControl("row.0")).find(item => typeof item.text === "string" && item.text.replace(/<[^>]*>/g, "") === expected);
            return reference !== undefined;
        }, 3000, "The injected author list, journal, volume, first page and year form the exact short reference");
        OnboardingProbe.interceptUrls();
        try {
            click(reference);
            compare(OnboardingProbe.urls(), ["https://doi.org/10.5555/edi.fixture.2026.34"], "The actual reference opens the DOI URL from its COD answer");
        } finally { OnboardingProbe.releaseUrls(); }
    }
    function check_cell() {
        resetProject();
        openOnline({page:AppState.Page.Structure, group:"structures", action:"web"});
        verify(OnlineHttpFixture.attach(Session.onlineSearch), "Cell display uses the independent non-orthogonal COD answer");
        OnlineHttpFixture.clear();
        codAnswer(popupFixture("cod_publication.json"));
        Session.onlineSearch.search();
        tryCompare(Session.onlineSearch, "busy", false, 3000, "All six cell values reach the result view");
        const texts = Render.descendants(onlineControl("row.0")).filter(item => typeof item.text === "string" && Ui.exposed(item)).map(item => item.text);
        verify(texts.some(text => ["5.13", "7.26", "8.92", "81.2", "109.3", "96.4"].every(value => text.includes(value))),
               "The Cell column visibly carries a, b, c, alpha, beta and gamma rather than hiding them in another column's tooltip");
    }
    function check_fits_data() {
        const rows = [];
        for (const source of ["cod", "collection"])
            for (const width of ["minimum", "wide"]) rows.push({tag:source + "-" + width, source:source, width:width});
        return rows;
    }
    function check_fits(data) {
        resetProject();
        app.width = data.width === "minimum" ? AppSizes.minimumAppWidth : 1680;
        if (data.source === "collection") searchDocument("structure", sourceDocument());
        else {
            openOnline({page:AppState.Page.Structure, group:"structures", action:"web"});
            verify(OnlineHttpFixture.attach(Session.onlineSearch), "COD table geometry uses an injected publication and non-orthogonal cell");
            OnlineHttpFixture.clear();
            codAnswer(popupFixture("cod_publication.json"));
            Session.onlineSearch.search();
            tryCompare(Session.onlineSearch, "busy", false, 3000, "The COD geometry fixture reaches the result table");
        }
        const table = onlineControl("results");
        verify(waitForPolish(table), "The popup table finishes its real layout at the selected window width");
        app.update();
        const widths = Array.from(table.resolvedColumnWidths);
        compare(headers().filter(title => title !== "").length, 6, "The fit check includes the index, cell and reference columns");
        verify(widths.reduce((sum, width) => sum + width, 0) <= table.width + 1,
               "Every results column fits inside the table instead of cropping the trailing columns");
        const point = table.mapToItem(onlineDialog.contentItem, 0, 0);
        verify(point.x >= 0 && point.x + table.width <= onlineDialog.contentItem.width + 1,
               "The complete results table stays inside its popup at minimum and wide window sizes");
    }
    function check_load_data() { return [{tag:"row-click"}]; }
    function check_load(data) {
        resetProject();
        const before = Session.project.structures.count;
        const search = searchDocument("structure", sourceDocument(), {id:"lbco"});
        const actions = Probe.objectsWithProperty(onlineDialog, "text");
        verify(!actions.some(item => item.text === "Load" && typeof item.clicked === "function" && Ui.exposed(item)),
               "A single result loads by row click with no redundant bottom Load button");
        delivered.clear();
        verify(OnlineHttpFixture.enqueueFile(200, fixture({file:"easydiffraction/structures/lbco.cif"}), true), "Row-click loading receives the independent saved CIF");
        click(onlineControl("id.0"));
        verify(search.busy, "The row action starts its actual pending download");
        compare(OnlineHttpFixture.requests().length, 2, "A row click dispatches exactly one file request after the index");
        verify(OnlineHttpFixture.release(0), "The deferred row download reaches the ordinary callback");
        tryCompare(delivered, "count", 1, 3000, "A row click delivers exactly one ordinary loader input");
        tryCompare(Session.project.structures, "count", before + 1, 3000, "Row click adds the selected structure");
        Session.project.undo();
        compare(Session.project.structures.count, before, "One Undo removes the clicked structure");
    }
    function check_atomic_count_data() { return ["biso", "mixed"].map(tag => ({tag:tag})); }
    function atomicControls() {
        let group;
        tryVerify(() => { group = Ui.control(Probe, app, "group.atom_site_aniso"); return group !== null; }, 3000,
                  "The Structure page exposes its Atomic displacement category");
        if (group.collapsed) click(group.titleArea);
        settle();
        tryCompare(group, "collapsed", false, 3000, "The real Atomic displacement group expands before its row count is read");
        const table = Ui.find(group, "atomSiteAdps.list", true);
        verify(table !== null, "The Atomic displacement group owns its visible atom-site table");
        return {group:group, table:table};
    }
    function check_atomic_setup() {
        resetProject(false);
        verify(Session.project.loadStructure(fixture({file:"easydiffraction/structures/lbco.cif"})), "The count witness loads the independent four-site Biso structure");
        AppState.open(AppState.Page.Structure);
        settle();
        Ui.click(this, Probe, app, "sideBar.tab.basic");
        compare(atomicControls().table.count, 4, "The committed witness displays one displacement row for each of its four atom sites");
    }
    function check_atomic_count(data) {
        const structure = Session.project.currentStructure;
        verify(structure !== null, "The shared count fixture retains its independently loaded structure");
        for (let site = 0; site < 4; ++site) structure.atomSiteAdps.setType(site, "Biso");
        if (data.tag === "mixed") structure.atomSiteAdps.setType(0, "Uani");
        const observed = atomicControls();
        const group = observed.group, table = observed.table;
        compare(table.count, 4, "The count comparison starts from all four independently supplied atom-site rows");
        const count = group.title.match(/\((\d+)\)$/);
        verify(count !== null, "The Atomic displacement group title displays its row count");
        compare(Number(count[1]), table.count,
                "The Atomic displacement title count equals the rows shown, including Biso atoms");
        const actions = [
            {run:() => Session.project.currentStructure.atomSites.remove(3), count:3},
            {run:() => Session.project.undo(), count:4},
            {run:() => Session.project.currentStructure.atomSites.duplicate(0), count:5},
            {run:() => Session.project.undo(), count:4}
        ];
        for (const action of actions) {
            action.run();
            settle();
            const currentGroup = Ui.control(Probe, app, "group.atom_site_aniso");
            verify(currentGroup !== null, "Atom-site edits keep the displacement category available");
            if (currentGroup.collapsed) click(currentGroup.titleArea);
            settle();
            const currentTable = Ui.find(currentGroup, "atomSiteAdps.list", true);
            verify(currentTable !== null, "The displacement table remains visible after atom-site edits and Undo");
            tryCompare(currentTable, "count", action.count, 3000, "Removing, duplicating and undoing a site updates the displayed displacement rows");
            const currentCount = currentGroup.title.match(/\((\d+)\)$/);
            verify(currentCount !== null, "The displacement title keeps its count after edits and Undo");
            compare(Number(currentCount[1]), action.count, "The displacement title follows the actual atom-site rows through edits and Undo");
        }
    }
    function check_tooltips_data() {
        const rows = [];
        for (const kind of ["structure", "experiment", "data"])
            for (const area of ["menu", "popup"])
                for (const enabled of [false, true]) rows.push({tag:kind + "-" + area + "-" + enabled, kind:kind, area:area, enabled:enabled});
        return rows;
    }
    function check_tooltips(data) {
        resetProject();
        const before = Preferences.toolTips;
        Preferences.toolTips = data.enabled;
        try {
            const shape = {page:data.kind === "structure" ? AppState.Page.Structure : AppState.Page.Experiment,
                           group:data.kind === "structure" ? "structures" : "experiments",
                           action:data.kind === "structure" ? "web" : data.kind === "experiment" ? "experimentWeb" : "dataWeb"};
            let controls;
            if (data.area === "menu") {
                const action = menuAction(shape);
                const menu = renderedLoadMenu;
                verify(menu !== null, "The open Load menu remains available after popup reparenting");
                controls = Array.from({length:menu.count}, (_, index) => menu.itemAt(index)).filter(item => item.enabled && /^experiments\.load\.|^structures\.load\./.test(item.objectName) && !/Header$/.test(item.objectName) && item.objectName !== shape.group + ".load.menu");
                verify(controls.includes(action), "Tooltip checks include the real selected Load menu action");
            } else {
                openOnline(shape);
                controls = [onlineControl("source"), onlineControl("field.id"), onlineControl("field.formula"), onlineControl("field.elements"), onlineControl("search")];
            }
            for (const control of controls) {
                const explanation = control.toolTip || control.ToolTip.text;
                verify(typeof explanation === "string" && explanation !== "", "Each actual menu item and popup control declares its own explanatory tooltip: " + control.objectName);
                const tips = () => {
                    const found = Probe.objectsWithProperty(control, "enterAnimationDuration").filter(tip => tip.text === explanation);
                    const attached = control.ToolTip.toolTip;
                    if (attached && attached.parent === control && attached.text === explanation && !found.includes(attached)) found.push(attached);
                    return found;
                };
                const finishTransitions = () => {
                    for (const tip of tips()) {
                        tip.delay = 0;
                        tip.timeout = -1;
                        if (typeof tip.enterAnimationDuration === "number") tip.enterAnimationDuration = 0;
                        if (typeof tip.exitAnimationDuration === "number") tip.exitAnimationDuration = 0;
                    }
                    OnboardingProbe.advanceClock(100);
                };
                finishTransitions();
                mouseMove(app.contentItem, 1, 1);
                verify(waitForPolish(control), "Tooltip hover starts after the real control finishes layout");
                app.update();
                verify(waitForRendering(app.contentItem), "The real tooltip source renders before pointer hover");
                const point = Ui.clickPoint(control);
                verify(point !== null, "Each tooltip control exposes a real hover target");
                mouseMove(control, point.x, point.y);
                tryCompare(control, "hovered", true, 1000, "Pointer hover reaches the actual Load control");
                tryVerify(() => { finishTransitions(); return tips().length > 0; }, 1000,
                          "Each menu item and popup control carries a real explanatory tooltip");
                tryVerify(() => {
                    finishTransitions();
                    return data.enabled ? tips().some(tip => tip.visible && tip.opened) : tips().every(tip => !tip.visible && !tip.opened);
                }, 2000, "The real tooltip visibility follows the initial Preferences switch state");
                Preferences.toolTips = !data.enabled;
                tryVerify(() => {
                    finishTransitions();
                    return data.enabled ? tips().every(tip => !tip.visible && !tip.opened) : tips().some(tip => tip.visible && tip.opened);
                }, 2000, "Changing Preferences updates the real tooltip while its control remains hovered");
                Preferences.toolTips = data.enabled;
            }
        } finally { Preferences.toolTips = before; }
    }
}
