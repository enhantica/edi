.pragma library
.import ReportAcceptance 1.0 as Acceptance

function bundled(test, session, id) {
    const model = session.examples;
    const search = model.searchText, filter = model.filterValue;
    model.searchText = "";
    model.filterValue = "";
    let present = false;
    for (let row = 0; row < model.count; ++row)
        present = present || model.text(row, "exampleId") === id;
    model.searchText = search;
    model.filterValue = filter;
    test.verify(present, "Example precondition: the requested id is bundled: " + id);
    return present && session.openExample(id);
}

function waitForOpen(test, session, id) {
    test.tryCompare(session, "openingExample", false, 10000, "ADR-0068: the accepted example request finishes before its project is used: " + id);
    test.verify(session.project !== null && session.openedExample === id, "ADR-0068: completion opens the requested example, with a non-null project rather than a stale or refused request: " + id + "; actual " + session.openedExample + "; error " + session.lastError);
}

function fixture(session, id) {
    const source = Qt.resolvedUrl("../../../docs/user/cli/" + id + "/project");
    return session.openProject(Acceptance.SettingsProof.copyProject(source));
}

function open(test, session, id, retained) {
    return retained ? fixture(session, id) : bundled(test, session, id);
}
