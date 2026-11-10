// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import EdiOnlineHttpFixture 1.0
import ReportAcceptance 1.0
import OnboardingAcceptance 1.0
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render

PopupContractSession {
    function check_precision() {
        resetProject();
        const answer = popupFixture("cod_publication.json");
        Object.assign(answer[0], {a:"5.1267", b:"7.2619", c:"8.9241", alpha:"81.24", beta:"109.26", gamma:"96.44"});
        openOnline({page:AppState.Page.Structure, group:"structures", action:"web"});
        verify(OnlineHttpFixture.attach(Session.onlineSearch), "Cell precision replaces only the COD transport");
        OnlineHttpFixture.clear();
        codAnswer(answer);
        Session.onlineSearch.search();
        tryCompare(Session.onlineSearch, "busy", false, 3000, "The nontrivial cell reaches the result view");
        const texts = Render.descendants(onlineControl("row.0")).filter(item => typeof item.text === "string").map(item => item.text);
        verify(texts.includes("5.13 7.26 8.92 81.2 109.3 96.4"), "Cell lengths round to two decimals and angles to one from independent nontrivial inputs");
    }
    function check_placeholders_data() { return ["structure", "experiment", "data"].map(tag => ({tag:tag})); }
    function check_placeholders(data) {
        resetProject();
        const search = searchDocument(data.tag, sourceDocument());
        onlineControl("source").activated(search.sources.indexOfKey("new-source"));
        settle();
        for (const pair of [["id","ID"], ["name","Name"], ["formula","Formula"], ["elements","Elements"]]) {
            verify(onlineControl("field." + pair[0]).placeholderText.startsWith(pair[1]), "Every text field carries its own title in the placeholder");
        }
        if (data.tag !== "structure") {
            for (const key of ["radiation", "technique"]) {
                const selector = onlineControl("choice." + key);
                verify(selector.count > 0 && /Any/i.test(selector.textAt(0)), "Radiation and Technique are selectors with an Any first choice");
            }
        }
    }
    function check_memory_data() { return ["structure", "experiment", "data"].map(tag => ({tag:tag})); }
    function check_memory(data) {
        resetProject();
        const search = searchDocument(data.tag, popupFixture("formula_index.json"), {name:"a", formula:"LaCoO3"});
        const before = Probe.rows(search.results).map(row => row.id);
        verify(before.length > 0, "Remembered search has real injected results");
        onlineControl("source").activated(search.sources.indexOfKey("new-source"));
        search.rememberSelection(0);
        onlineDialog.close();
        tryVerify(() => { settle(); return !onlineDialog.visible; }, 3000, "The search popup closes before it is reopened");
        const shape = {page:data.tag === "structure" ? AppState.Page.Structure : AppState.Page.Experiment,
                       group:data.tag === "structure" ? "structures" : "experiments",
                       action:data.tag === "structure" ? "web" : data.tag === "experiment" ? "experimentWeb" : "dataWeb"};
        openOnline(shape);
        compare(search.sourceId, "new-source", "Reopen keeps the chosen source for this kind");
        compare(search.field("name"), "a", "Reopen restores Name independently of Formula");
        compare(search.field("formula"), "LaCoO3", "Reopen restores Formula independently of Name");
        compare(Probe.rows(search.results).map(row => row.id), before, "Reopen restores the previous result identities");
        compare(search.rememberedSelection(), 0, "Reopen preserves the selected row within this session");
        search.clear();
        compare(search.results.count, 0, "Clear replaces the remembered results");
        compare(search.field("formula"), "", "Clear also replaces remembered input fields");
        verify(!search.recall(), "Cleared memory cannot revive the former search");
    }
    function codRows(first, count) {
        return Array.from({length:count}, (_, i) => ({file:String(9100000 + first + i), commonname:"fixture " + (first+i), formula:"- La Co O3 -", sg:"P 1"}));
    }
    function check_chunks_data() { return ["success", "retry"].map(tag => ({tag:tag})); }
    function check_chunks(data) {
        resetProject();
        openOnline({page:AppState.Page.Structure, group:"structures", action:"web"});
        const search = Session.onlineSearch;
        search.sourceId = "cod";
        verify(OnlineHttpFixture.attach(search), "Chunk loading uses only a scripted COD server");
        OnlineHttpFixture.clear();
        OnlineHttpFixture.enqueue(200, "250");
        OnlineHttpFixture.enqueue(200, Array.from({length:250}, (_, i) => String(9100000+i)).join("\n"));
        OnlineHttpFixture.enqueue(200, JSON.stringify(codRows(0,100)));
        search.setField("elements", "La");
        search.search();
        tryCompare(search.results, "count", 100, 3000, "The first chunk contains exactly one hundred of the independent 250 matches");
        compare(search.total, 250, "The server's match count is retained independently of loaded rows");
        verify(onlineControl("count").text.includes("250") && onlineControl("count").text.includes("100"), "The popup displays total and loaded entry counts");
        const requests = OnlineHttpFixture.requests().map(url => OnlineHttpFixture.query(url));
        compare(requests[0].format, "count", "COD asks for a count before loading details");
        compare(requests[1].format, "lst", "COD obtains stable matching identities for chunking");
        compare(requests[2].id.split(","), codRows(0,100).map(row => row.file), "The first detail request is exactly the first hundred comma-separated identities");
        if (data.tag === "retry") OnlineHttpFixture.enqueue(503, "unavailable");
        else OnlineHttpFixture.enqueue(200, JSON.stringify(codRows(100,100)));
        const table = onlineControl("results");
        table.contentY = Math.max(0, table.contentHeight - table.height);
        if (data.tag === "retry") {
            tryVerify(() => search.chunkError !== "", 3000, "A failed next chunk exposes a retry reason");
            compare(search.results.count, 100, "A failed chunk preserves every earlier row");
            verify(onlineControl("chunk").visible, "The failed chunk has a visible retry line in the table");
            OnlineHttpFixture.enqueue(200, JSON.stringify(codRows(100,100)));
            click(onlineControl("retry"));
        }
        tryCompare(search.results, "count", 200, 3000, "Scrolling near the end appends the next hundred rows");
        OnlineHttpFixture.enqueue(200, JSON.stringify(codRows(200,50)));
        table.contentY = Math.max(0, table.contentHeight - table.height);
        tryCompare(search.results, "count", 250, 3000, "The final chunk appends the remaining fifty rows");
        compare(Probe.rows(search.results).map(row => row.id), codRows(0,250).map(row => row.file), "Chunking preserves every identity exactly once and in server order");
        verify(!search.moreAvailable, "The exhausted identity list cannot request another chunk");
    }
    function check_empty_kind_data() { return check_placeholders_data(); }
    function check_empty_kind(data) {
        resetProject();
        const doc = popupFixture("formula_index.json");
        const search = searchDocument(data.tag, doc);
        compare(Probe.rows(search.results).map(row => row.id).sort(), doc.entries.filter(row => row.kind === data.tag).map(row => row.id).sort(), "An empty collection query lists every entry of its own kind");
        compare(search.total, doc.entries.filter(row => row.kind === data.tag).length, "Collection count equals the independent index inventory");
    }
    function check_case_formula_data() { return ["laCoO3", "LaCoO3", "la co o3"].map(tag => ({tag:tag})); }
    function check_case_formula(data) {
        resetProject();
        const search = searchDocument("structure", popupFixture("formula_index.json"), {formula:data.tag});
        compare(Probe.rows(search.results).map(row => row.id), ["structure-zzz-exact", "structure-aaa-substituted"], "Case-insensitive collection formula spelling retains exact-first composition matching");
    }
    function check_linked_structure_data() { return ["missing", "present"].map(tag => ({tag:tag})); }
    function check_linked_structure(data) {
        resetProject(false);
        const project = Session.project;
        verify(project.loadStructure(fixture({file:"easydiffraction/structures/lbco.cif"})), "The disk reference loads the independent linked structure");
        verify(project.loadExperiments([fixture({file:"easydiffraction/experiments/lbco_hrpt.edi"})]), "The disk reference loads the independent full experiment");
        const expected = {structure:project.currentStructure.text.inputText, experiment:project.currentExperiment.text.inputText};
        resetProject(false);
        if (data.tag === "present") {
            verify(Session.project.loadStructure(fixture({file:"easydiffraction/structures/lbco.cif"})), "The reuse control already holds the linked structure by name");
            Session.project.currentStructure.cell.lengthA.value = 3.93;
            settle();
            tryVerify(() => !Session.project.calculating, 5000, "The held reuse structure settles before its input snapshot");
            expected.structure = Session.project.currentStructure.text.inputText;
        }
        const before = Session.project.structures.count;
        const doc = sourceDocument();
        const entry = doc.entries.find(row => row.kind === "experiment");
        entry.structures = ["lbco"];
        entry.description = "Measured profile, background and displacement inputs";
        const search = searchDocument("experiment", doc, {id:entry.id});
        verify(headers().includes("Description"), "Full experiment results expose the index description as a column");
        compare(Probe.rows(search.results)[0].description, entry.description, "The result description comes from the independent index");
        // Both ordinary inputs are available whichever order the dependency fetches use.
        verify(OnlineHttpFixture.enqueueFile(200, fixture({file:"easydiffraction/structures/lbco.cif"})), "The dependency transport receives the independent saved CIF");
        verify(OnlineHttpFixture.enqueueFile(200, fixture({file:"easydiffraction/experiments/lbco_hrpt.edi"})), "The full experiment receives its saved input");
        onlineControl("results").selectWithModifiers(0, Qt.NoModifier);
        onlineDialog.loadSelected();
        tryCompare(Session.project.experiments, "count", 1, 3000, "A full experiment brings the structure it needs before adoption");
        compare(Session.project.structures.count, 1, "A present same-name structure is reused without duplication");
        if (data.tag === "present") compare(Session.project.currentStructure.cell.lengthA.value, 3.93, "Reusing a same-name structure preserves the independently chosen existing cell value");
        compare(Session.project.currentStructure.text.inputText, expected.structure, "Online structure equals the ordinary disk loader state");
        compare(Session.project.currentExperiment.text.inputText, expected.experiment, "Online full experiment equals the ordinary disk loader state");
        Session.project.undo();
        compare(Session.project.experiments.count, 0, "One Undo removes the full online experiment");
        compare(Session.project.structures.count, before, "The same Undo removes only structures added by that online load");
    }
}
