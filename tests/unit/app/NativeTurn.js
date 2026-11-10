.pragma library

function begin(test, probe, report) {
    const args = Qt.application.arguments;
    const index = args.indexOf("-o");
    if (index < 0 || !args[index + 1].endsWith("/native-owner-stream.txt,txt"))
        return "";
    const permit = args[index + 1].slice(0, -4) + ".permit";
    const selected = test.name + "::" + test.qtest_results.functionName + (test.qtest_results.dataTag ? ":" + test.qtest_results.dataTag : "");
    if (report)
        report("NATIVE_OWNER_READY " + selected);
    else
        console.log("NATIVE_OWNER_READY " + selected);
    test.tryVerify(() => probe.readFile(permit).trim() === selected, 20000, "ADR-0076: the shared native host waits for this row's explicit pytest request before its setup or assertions");
    return selected;
}

function end(selected, report) {
    if (selected !== "") {
        if (report)
            report("NATIVE_OWNER_DONE " + selected);
        else
            console.log("NATIVE_OWNER_DONE " + selected);
    }
}
