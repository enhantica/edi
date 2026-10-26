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

function fixture(session, id) {
    const source = Qt.resolvedUrl("../../../docs/user/cli/" + id + "/project");
    return session.openProject(Acceptance.SettingsProof.copyProject(source));
}

function open(test, session, id, retained) {
    return retained ? fixture(session, id) : bundled(test, session, id);
}
