.pragma library
function reference(proof) {
    const palettes = JSON.parse(typeof proof.repoText === "function" ? proof.repoText("tests/fixtures/approved_palettes/colours.json") : proof.readFile("tests/fixtures/approved_palettes/colours.json")).palettes;
    const tokens = ["ediNatural", "ediCoast", "ediGarden", "ediStudio", "ediContrast"];
    return {default: tokens[0], schemes: palettes.map((palette, index) => ({id: tokens[index], label: palette.name, palette}))};
}
function colours(proof, token, role, count, dark) {
    const rows = JSON.parse(typeof proof.repoText === "function" ? proof.repoText("tests/fixtures/approved_palettes/assignments.json") : proof.readFile("tests/fixtures/approved_palettes/assignments.json"));
    const row = rows.find(value => value.scheme === token && value.role === role && value.count === count && value.theme === (dark ? "dark" : "light"));
    if (!row) throw Error("The independent approved assignment fixture has no matching case");
    return row.colours.map(value => value.toLowerCase());
}
function getSchemes(preferences) {
    if(typeof preferences.structureColours!=="string"||typeof preferences.patternColours!=="string")
        throw Error("The palette fixture requires the independent Structures and Patterns preferences");
    return {structures:preferences.structureColours,patterns:preferences.patternColours,
            rawStructures:preferences.structureColourScheme,rawPatterns:preferences.patternColourScheme};
}
function setSchemes(preferences,requested) {
    if(typeof preferences.structureColourScheme!=="string"||typeof preferences.patternColourScheme!=="string")
        throw Error("The palette fixture requires writable independent Structures and Patterns preferences");
    preferences.structureColourScheme=typeof requested==="string"?requested:requested.rawStructures!==undefined?requested.rawStructures:requested.structures;
    preferences.patternColourScheme=typeof requested==="string"?requested:requested.rawPatterns!==undefined?requested.rawPatterns:requested.patterns;
}
function freshSchemesCode() {
    return 'import QtQuick; import edi.app; QtObject { property string schemes:JSON.stringify([Preferences.structureColours,Preferences.patternColours]); property string libraries:Preferences.newReportLibraries }';
}
