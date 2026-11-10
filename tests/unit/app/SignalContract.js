.pragma library

// Same predicate for the production object and deliberately broad test doubles.
function violation(events, expected) {
    const names = Object.keys(events).sort();
    if (JSON.stringify(names) !== JSON.stringify(expected.slice().sort()))
        return "I3 unexpected signal set: " + names.join(",");
    for (let i = 0; i < names.length; ++i)
        if (events[names[i]].length !== 1)
            return "I3 signal emitted more than once: " + names[i];
    return "";
}
