.pragma library
function reference(proof) {
    const palettes = JSON.parse(proof.repoText("tests/fixtures/approved_palettes/colours.json")).palettes;
    const tokens = ["ediNatural", "ediCoast", "ediGarden", "ediStudio", "ediContrast"];
    return {default: tokens[0], schemes: palettes.map((palette, index) => ({id: tokens[index], label: palette.name, palette}))};
}
function colours(proof, token, role, count, dark) {
    const rows = JSON.parse(proof.repoText("tests/fixtures/approved_palettes/assignments.json"));
    const row = rows.find(value => value.scheme === token && value.role === role && value.count === count && value.theme === (dark ? "dark" : "light"));
    if (!row) throw Error("The independent approved assignment fixture has no matching case");
    return row.colours.map(value => value.toLowerCase());
}
