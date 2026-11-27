// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest

import EasyApplication.Gui.Style as EaStyle
import edi.app

// The Evolution selector lists its parameters in groups: one per datablock in the Analysis table's order, then the
// derived values, then the fit quality. A group's title is drawn over its first entry, which is no row of its own; every
// line has its icons, its short name and its grey full name, cut at its start when it is long.
Item {
    id: root

    width: 900
    height: 700

    BlockSelector {
        id: selector

        readonly property EvolutionViewModel evolution: Session.project ? Session.project.evolution : null

        objectName: "selector"
        width: 320
        blocks: evolution ? evolution.parameters : null
        blocksTextRole: "label"
        groupRole: "group"
        blockKind: "parameter"
        blockIndex: evolution ? evolution.currentParameter : -1
        onBlockActivated: index => evolution.currentParameter = index
        lineFor: (index, text) => ParameterNames.pickerLine(evolution ? evolution.parameterItem(index) : null, text, evolution ? evolution.siblingItem(index) : null)
    }

    TestCase {
        id: test

        name: "EvolutionGroups"
        when: windowShown

        property var model: null
        readonly property EvolutionViewModel evolution: selector.evolution

        function initTestCase() {
            verify(Session.openProject(Qt.resolvedUrl("evolution_groups")), Session.lastError);
            model = evolution.parameters;
            tryVerify(() => model.count > 10, 5000);
        }
        function cleanupTestCase() {
            Session.closeProject();
        }
        function names() {
            const out = [];
            for (let i = 0; i < model.count; ++i)
                out.push(model.text(i, "name"));
            return out;
        }
        function groups() {
            const out = [];
            for (let i = 0; i < model.count; ++i)
                if (i === 0 || model.text(i, "group") !== model.text(i - 1, "group"))
                    out.push(model.text(i, "group"));
            return out;
        }
        function line(name) {
            return selector.lineFor(names().indexOf(name), model.text(names().indexOf(name), "label"));
        }

        function test_a_groups_in_order() {
            compare(groups(), ["cosio", "d20", "gone", "Derived values", "Fit quality"]);
            const list = names();
            const at = name => {
                verify(list.indexOf(name) >= 0, name);
                return list.indexOf(name);
            };
            verify(at("cosio.cell.length_a") < at("cosio.atom_site.Co1.occupancy"), "as the Analysis table lists them");
            verify(at("cosio.atom_site.Co1.occupancy") < at("cosio.atom_site.Co1.adp_iso"));
            compare(model.text(at("d20.linked_structure.cosio.weight_fraction"), "group"), "Derived values");
            compare(model.text(at("cosio.atom_site_moment.Co1.spherical_modulus"), "group"), "Derived values");
            compare(list[list.length - 1], "fit_result.r_bragg.cosio");
        }
        function test_b_the_index_is_the_selection() {
            const at = names().indexOf("cosio.atom_site.Co1.occupancy");
            evolution.currentParameter = at;
            compare(evolution.yTitle, "cosio.atom_site.Co1.occupancy");
            compare(selector.currentIndex, at);
            compare(selector.count, model.count);
        }
        function test_c_each_line_has_its_icons_and_grey_path() {
            for (const name of names()) {
                const pieces = line(name);
                verify(pieces[0].icon, name);
                const last = pieces[pieces.length - 1];
                verify(last.elides && last.color !== undefined, name);
                compare(pieces.filter(piece => piece.elides === true).length, 1, name);
                verify(last.text.endsWith(name.split(".").pop()), `${name}: ${last.text}`);
            }
            const offset = names().find(name => name.endsWith("twotheta_offset"));
            verify(evolution.parameterItem(names().indexOf(offset)) !== null, "a free instrument parameter is the table's");
        }
        function test_d_derived_values() {
            const fraction = line("d20.linked_structure.cosio.weight_fraction").map(piece => piece.text ?? "");
            verify(fraction.indexOf("cosio") >= 0 && fraction.indexOf(Session.label("linked_structure.weight_fraction")) >= 0, fraction);
            const item = evolution.parameterItem(names().indexOf("cosio.atom_site.Co1.adp_iso"));
            const pieces = ParameterNames.derivedLine(item, "cosio.atom_site_moment.Co1.spherical_modulus").map(piece => piece.text ?? "");
            verify(pieces.indexOf("Co1") >= 0, pieces);
            compare(pieces[pieces.length - 3], Session.label("atom_site_moment.spherical_modulus"));
            verify(pieces.indexOf(item.shortName) < 0, pieces);
            verify(model.text(names().indexOf("cosio.atom_site_moment.Co1.spherical_modulus"), "label").startsWith("Co1 " + Session.label("atom_site_moment.spherical_modulus")));
        }
        function test_e_titles_in_the_list() {
            evolution.currentParameter = 0;
            selector.popup.open();
            tryVerify(() => selector.popup.opened, 5000);
            const title = index => findChild(selector.popup.contentItem, `selector.group.${index}`);
            tryVerify(() => title(0) !== null, 5000);
            compare(title(0).text, "cosio");
            compare(title(1), null);
            // A click on a title chooses nothing.
            mouseClick(title(0), 20, title(0).height / 2);
            verify(selector.popup.opened);
            // A search keeps the title over the first entry it leaves.
            const search = findChild(selector.popup.contentItem, "comboBox.search");
            verify(search !== null);
            search.text = "occupancy";
            const at = names().indexOf("cosio.atom_site.Co1.occupancy");
            tryVerify(() => title(at) !== null && title(at).text === "cosio", 5000);
            selector.popup.close();
        }

        // A typed search, as typed: the entries are ranked within their group, the groups keep their order, and each
        // title sits over the first entry of its group the list shows.
        function fold(text) {
            return text.toLowerCase().replace(/\s+/g, "");
        }
        function rank(index, query) {
            const text = fold(model.text(index, "label"));
            return text === query ? 0 : text.startsWith(query) ? 1 : text.includes(query) ? 2 : 3;
        }
        function group(index) {
            return model.text(index, "group");
        }
        // The source rows in the order the list should show them for a query.
        function expected(query) {
            const order = [];
            const ranks = {};
            for (let i = 0; i < model.count; ++i) {
                const at = rank(i, query);
                if (at === 3)
                    continue;
                if (!(group(i) in ranks)) {
                    ranks[group(i)] = [[], [], []];
                    order.push(group(i));
                }
                ranks[group(i)][at].push(i);
            }
            return order.reduce((rows, name) => rows.concat(ranks[name][0], ranks[name][1], ranks[name][2]), []);
        }
        // Typed prefixes of each label that can be keyed in one by one.
        function queries() {
            const out = [];
            for (let i = 0; i < model.count; ++i) {
                const text = fold(model.text(i, "label"));
                for (let length = 2; length <= text.length && /^[a-z0-9]+$/.test(text.slice(0, length)); ++length)
                    out.push({
                        "query": text.slice(0, length),
                        "row": i
                    });
            }
            return out;
        }
        // A later row of a group starts with the query while an earlier one of the same group only holds it; the one with
        // the fewest matches, so every entry is drawn.
        function inversion() {
            let best = null;
            for (const each of queries())
                for (let early = 0; early < each.row; ++early)
                    if (group(early) === group(each.row) && rank(early, each.query) === 2 && (best === null || expected(each.query).length < expected(best.query).length))
                        best = {
                            "query": each.query,
                            "early": early,
                            "late": each.row
                        };
            return best;
        }
        // A query matching two groups, where an entry of the later group ranks above one of the earlier: a ranking
        // across the whole list would put them side by side. The one with the fewest matches.
        function acrossGroups() {
            let best = "";
            for (const each of queries()) {
                const rows = expected(each.query);
                if (best !== "" && rows.length >= expected(best).length)
                    continue;
                if (rows.some((first, at) => rows.slice(at + 1).some(second => group(first) !== group(second) && rank(second, each.query) < rank(first, each.query))))
                    best = each.query;
            }
            return best;
        }
        function box() {
            return findChild(selector, "selector.box");
        }
        function list() {
            return selector.popup.contentItem;
        }
        function shownEntries() {
            const entries = [];
            const all = list().contentItem.children;
            for (let i = 0; i < all.length; ++i)
                if (all[i].matching === true && all[i].height > 0 && all[i].visible)
                    entries.push(all[i]);
            return entries.sort((a, b) => a.y - b.y);
        }
        function title(index) {
            return findChild(list(), `selector.group.${index}`);
        }
        // Opens the list from a row the query leaves out, so a pick is seen to change it.
        function typeQuery(query) {
            const rows = expected(query);
            evolution.currentParameter = Math.max(0, Array.from({
                "length": model.count
            }, (_, row) => row).findIndex(row => rows.indexOf(row) < 0));
            mouseClick(box(), box().width - 10, box().height / 2);
            tryVerify(() => selector.popup.opened, 5000);
            tryVerify(() => findChild(list(), "comboBox.search")?.activeFocus === true, 5000);
            for (const letter of query)
                keyClick(letter);
        }
        // The list shows the rows in order, each group's title over its first shown entry and nowhere else.
        function laidOut(rows) {
            const entries = shownEntries();
            if (entries.map(entry => entry.index).join(",") !== rows.join(","))
                return false;
            return rows.every((row, at) => {
                const opens = at === 0 || group(rows[at - 1]) !== group(row);
                const heading = title(row);
                return opens ? heading !== null && heading.text === group(row) && entries[at].titleHeight > 0 : heading === null && entries[at].titleHeight === 0;
            });
        }
        // The list as tall as its shown entries and their groups' titles, and its search field, no more.
        function sized(rows) {
            const titles = rows.filter((row, at) => at === 0 || group(rows[at - 1]) !== group(row)).length;
            const wanted = (rows.length + titles) * EaStyle.Sizes.comboBoxHeight + list().headerItem.height + selector.popup.topPadding + selector.popup.bottomPadding;
            return Math.abs(selector.popup.height - wanted) < 0.5;
        }
        function pressAt(entry) {
            mouseClick(entry, entry.width / 2, entry.height - EaStyle.Sizes.comboBoxHeight / 2);
        }
        function cleanup() {
            selector.popup.close();
            tryVerify(() => !selector.popup.visible, 5000);
        }

        function test_f_typed_ranking_within_a_group() {
            const found = inversion();
            verify(found !== null, "the fixture has a group whose later row starts with a text an earlier row holds");
            const rows = expected(found.query);
            verify(rows.indexOf(found.late) < rows.indexOf(found.early), JSON.stringify(found));
            // Enter takes the top entry.
            typeQuery(found.query);
            tryVerify(() => laidOut(rows), 5000, `${found.query}: ${rows}`);
            keyClick(Qt.Key_Return);
            tryVerify(() => !selector.popup.visible, 5000);
            compare(evolution.currentParameter, rows[0]);
            // A click on either entry picks its own row.
            for (const row of [found.late, found.early]) {
                typeQuery(found.query);
                tryVerify(() => laidOut(rows), 5000, `${found.query}: ${rows}`);
                pressAt(shownEntries().find(entry => entry.index === row));
                tryVerify(() => !selector.popup.visible, 5000);
                compare(evolution.currentParameter, row);
            }
        }
        function test_g_typed_search_across_groups() {
            const query = acrossGroups();
            verify(query !== "", "the fixture has a text that ranks a later group's entry above an earlier group's");
            const rows = expected(query);
            typeQuery(query);
            tryVerify(() => laidOut(rows), 5000, `${query}: ${rows}`);
            tryVerify(() => sized(rows), 5000, `${query}: ${selector.popup.height}`);
            keyClick(Qt.Key_Return);
            tryVerify(() => !selector.popup.visible, 5000);
            compare(evolution.currentParameter, rows[0]);
            // The first entry of the second group, under its own title.
            const second = rows.find(row => group(row) !== group(rows[0]));
            typeQuery(query);
            tryVerify(() => laidOut(rows), 5000, `${query}: ${rows}`);
            const entry = shownEntries().find(each => each.index === second);
            verify(entry.y + entry.height <= list().contentY + list().height, "the entry is in view");
            pressAt(entry);
            tryVerify(() => !selector.popup.visible, 5000);
            compare(evolution.currentParameter, second);
        }
        function test_h_height_counts_the_shown_titles() {
            // A query that leaves some groups out, the shortest such list.
            let query = "";
            for (const each of queries()) {
                const rows = expected(each.query);
                const left = new Set(rows.map(row => group(row))).size;
                if (left < groups().length && (query === "" || rows.length < expected(query).length))
                    query = each.query;
            }
            verify(query !== "", "the fixture has a text that leaves a group out");
            const rows = expected(query);
            typeQuery(query);
            tryVerify(() => laidOut(rows), 5000, `${query}: ${rows}`);
            tryVerify(() => sized(rows), 5000, `${query}: ${selector.popup.height}`);
        }
    }
}
