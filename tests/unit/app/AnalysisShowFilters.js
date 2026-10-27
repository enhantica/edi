.pragma library
.import "UiInteraction.js" as Ui
.import "E04Review.js" as View

var titles = ["Not measured in this fit", "Fixed by symmetry", "Set by a constraint", "Setup values"];
var defaults = [true, false, false, true];

function controls(test, root) {
    return titles.map(title => {
        const matches = View.descendants(root).filter(item => typeof item.text === "string" &&
            item.text.replace(/\s*\(\d+\)$/, "") === title &&
            typeof item.checked === "boolean" && typeof item.clicked === "function");
        test.compare(matches.length, 1, "Analysis Settings exposes one actual show-checkbox for " + title);
        return matches[0];
    });
}

function choose(test, root, states) {
    const boxes = controls(test, root);
    expand(test, boxes);
    boxes.forEach((box, i) => {
        if (box.checked === states[i]) return;
        Ui.scrollIntoView(box);
        const hit = Ui.clickPoint(box);
        test.verify(hit !== null, "The actual Analysis show-checkbox has an exposed pointer target");
        test.mouseClick(box, hit.x, hit.y);
        test.tryCompare(box, "checked", states[i], 1000, "A pointer click changes the requested Analysis view group");
    });
    return boxes;
}

function expand(test, boxes) {
    for (let group = boxes[0].parent; group; group = group.parent) {
        if (group.collapsed !== true || !group.titleArea) continue;
        Ui.scrollIntoView(group.titleArea);
        test.tryVerify(() => Ui.clickPoint(group.titleArea) !== null, 2000,
            "The show-filter group's actual header finishes sliding into the Settings viewport");
        const hit = Ui.clickPoint(group.titleArea);
        test.verify(hit !== null, "The show-filter group's real header can be expanded by the user");
        test.mouseClick(group.titleArea, hit.x, hit.y);
        test.tryCompare(group, "collapsed", false, 1000, "The actual show-filter group opens after its header is clicked");
        test.tryVerify(() => Math.abs(group.height - (group.titleArea.height + group.spacing + group.contentHeight + group.bottomPadding)) < 0.01, 2000,
            "The actual show-filter group's expansion finishes before its checkboxes receive pointer input");
    }
    test.tryVerify(() => boxes.every(box => Ui.clickPoint(box) !== null), 1000,
        "All four show-checkboxes reach the visible Settings viewport after the group opens");
}

function key(row) {
    return [row.blockName, row.category, row.rowLabel, row.name].filter(x => x !== "").join(".");
}

function inventory(cubic, constrained) {
    const rows = [];
    function add(id, group) { rows.push({id: id, group: group}); }
    for (const name of ["length_a", "length_b", "length_c", "angle_alpha", "angle_beta", "angle_gamma"])
        add("phase.cell." + name, cubic && name !== "length_a" ? 1 : 0);
    for (const name of ["fract_x", "fract_y", "fract_z", "occupancy", "adp_iso"])
        add("phase.atom_site.Ni." + name, cubic && name.startsWith("fract_") ? 1 : constrained && name === "adp_iso" ? 2 : -1);
    add("bank.instrument.setup_wavelength", 0);
    add("bank.extinction.crystal_radius", 3);
    add("bank.extinction.domain_radius", -1);
    add("bank.linked_structure.phase.scale", -1);
    return rows;
}

function shown(expected, states, freeIds) {
    return expected.filter(row => row.group < 0 || states[row.group] || (freeIds || []).includes(row.id)).map(row => row.id).sort();
}
