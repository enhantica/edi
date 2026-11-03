.pragma library
.import "../../fixtures/scan_views/oklab.js" as Oklab
function owner(proof) {
    return JSON.parse(typeof proof.repoText === "function" ? proof.repoText("tests/fixtures/chart_controls/owner.json") : proof.readFile("tests/fixtures/chart_controls/owner.json"));
}
function reference(proof) {
    const recorded = owner(proof), tokens = ["earth", "classic", "soft", "natural", "colourBlindSafe"];
    const previous = JSON.parse(typeof proof.repoText === "function" ? proof.repoText("tests/fixtures/approved_palettes/colours.json") : proof.readFile("tests/fixtures/approved_palettes/colours.json")).palettes[0];
    return {default: tokens[0], schemes: recorded.palettes.map((row, index) => {
        const palette = {name: row.name};
        for (const theme of ["light", "dark"])
            palette[theme] = {measured: row[theme], structures: row[theme].slice(index === 0 ? 2 : 1), total_calculation: recorded.calc[theme], background: previous[theme].background, difference: previous[theme].difference};
        return {id: tokens[index], label: row.name, palette};
    })};
}
function colours(proof, token, role, count, dark, layout) {
    const names = ["earth", "classic", "soft", "natural", "colourBlindSafe"], index = names.indexOf(token);
    if (index < 0) throw Error("The independent figure reference requires an approved palette token");
    const palette = owner(proof).palettes[index][dark ? "dark" : "light"];
    const context = layout || {}, experiments = context.experiments === undefined ? 1 : context.experiments, structures = context.structures === undefined ? 1 : context.structures;
    const firstStructure = context.structureStart === undefined ? (context.scan ? 2 : Math.max(experiments, index === 0 ? 2 : 0)) : context.structureStart;
    const positions = [];
    if (role === "structures") {
        for (let i = 0; i < count; ++i) positions.push(firstStructure + i);
    } else if (context.scan) {
        for (let p = 0; positions.length < count; ++p)
            if (p < firstStructure || p >= firstStructure + structures) positions.push(p);
    } else {
        for (let i = 0; i < count; ++i) positions.push(i);
    }
    const size = Math.max(firstStructure + structures, positions.length ? positions[positions.length - 1] + 1 : 0);
    return positions.map((p, i) => context.scan && count > 11 ? Oklab.gradient(palette[0], palette[1], i / (count - 1)) : p < 11 ? palette[p].toLowerCase() : Oklab.gradient(palette[0], palette[1], (p - 10) / (size - 10)));
}
function getScheme(preferences) {
    if (typeof preferences.colourScheme !== "string") throw Error("The shared figure palette preference must exist");
    return preferences.colourScheme;
}
function setScheme(preferences, requested) { preferences.colourScheme = requested; }
function freshSchemeCode() {
    return 'import QtQuick; import edi.app; QtObject { property string scheme:Preferences.colourScheme; property string libraries:Preferences.newReportLibraries }';
}
