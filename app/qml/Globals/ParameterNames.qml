// SPDX-License-Identifier: BSD-3-Clause
pragma Singleton

import QtQuick

import EasyApplication.Gui.Style as EaStyle

import edi.app

// A parameter's iconified name on the Analysis page, as easydiffractionbeta's shortest name with icons and
// pretty labels (Globals/Proxies.qml paramName; ADR-0017 §8), as the pieces of one
// IconLine (§10): the block's icon in the block's colour; the category's icon, for an atom site in its element's
// colour; the row (an atom's label, a loop row's number) in the category icon's colour; the parameter's icon;
// then its short name, never bold.
QtObject {
    id: names

    // A block kind's icon, as the block tables show it.
    function blockIcon(kind) {
        return ApplicationInfo.nameBlockIcon(kind);
    }

    // easydiffractionbeta's parameter icons (Logic/Calculators.py), by `.edi` item name or its prefix; none
    // for a parameter the original had no icon for.
    function parameterIcon(name) {
        return ApplicationInfo.nameParameterIcon(name);
    }

    // A parameter's full name, qualified by its datablock and, in a loop, its row: d20.peak.broad_gauss_v,
    // lbco.atom_site.La.fract_x (the owner, 2026-11-14).
    function fullName(item): string {
        if (!item)
            return "";
        return item.fullName;
    }

    // A ParameterItem's name as IconLine pieces (§10).
    function segments(item) {
        return ApplicationInfo.nameSegments(item);
    }

    // A picker's line: the name's pieces, a dot and the full name in the greyed text, which alone may be cut. The pieces
    // keep their width: a row label that gave way instead left the full name to run past the line's end.
    function withFullName(pieces, full: string): list<var> {
        const minor = String(EaStyle.Colors.themeForegroundMinor);
        return pieces.map(piece => Object.assign({}, piece, {
                "elides": false
            })).concat([
            {
                "text": "·",
                "color": minor
            },
            {
                "text": full,
                "color": minor,
                "elides": true
            }
        ]);
    }
    // A name no item stands for (a column of a fit's results the parameter list does not hold), drawn in the same form:
    // the block's icon (a structure's for a structure's category, else an experiment's), the category's, the last part as
    // the short name, then the full name (the owner, 2026-11-24). A name without a datablock (a fit's χ² and factors, a
    // column every bank has) has its category's icon alone.
    readonly property var structureCategories: ["cell", "space_group", "atom_site", "atom_sites", "atom_site_aniso", "atom_site_moment", "scattering_length", "geom"]
    function unlistedLine(text: string): list<var> {
        // A factor's label comes before its name ("R_Bragg, cosio (%) · fit_result.r_bragg.cosio").
        const at = text.indexOf(" · ");
        const full = at > 0 ? text.slice(at + 3) : text;
        const parts = full.split(".");
        if (parts.length < 2)
            return [
                {
                    "text": text,
                    "elides": true,
                    "factors": true
                }
            ];
        const inBlock = parts.length > 2 && parts[0] !== "fit_result" && Session.categoryIcon(parts[1]) !== "";
        const line = [];
        if (inBlock) {
            const kind = names.structureCategories.indexOf(parts[1]) >= 0 ? "structure" : "experiment";
            line.push({
                "icon": names.blockIcon(kind),
                "color": String(AppColors.block(kind, 0))
            });
        }
        const icon = Session.categoryIcon(parts[inBlock ? 1 : 0]);
        if (icon !== "")
            line.push({
                "icon": icon,
                "color": String(EaStyle.Colors.themeForegroundMinor)
            });
        line.push({
            "text": at > 0 ? text.slice(0, at) : names.unlistedName(parts, inBlock ? 1 : 0),
            "factors": true
        });
        return names.withFullName(line, full);
    }
    // A name's item in words, from the label registry (`category.item`: "|M|", "Weight fraction"), after its row where
    // the name has one (`category.row.item`: "Co1 |M|"); the raw item only for a name the registry lacks.
    function unlistedName(parts: list<string>, category: int): string {
        const item = parts[parts.length - 1];
        const forms = Session.labelForms(`${parts[category]}.${item}`);
        if (!forms.long)
            return item;
        return parts.length - category === 3 ? `${parts[category + 1]} ${forms.long}` : forms.long;
    }
    // A value crysta derives from the fit (a moment's |M|, a weight fraction), by `sibling`, a parameter of the same row:
    // its block, category and row, then the value's own symbol, as its table's header has it.
    function derivedLine(sibling, full: string): list<var> {
        const parts = full.split(".");
        const name = parts[parts.length - 1];
        // The sibling's own name ends its line: its icon, when it has one, and its short name.
        const line = names.segments(sibling).slice(0, names.parameterIcon(sibling.name) !== "" ? -2 : -1);
        return names.withFullName(line.concat([
            {
                "text": Session.labelForms(`${parts[parts.length - 3]}.${name}`).long ?? name
            }
        ]), full);
    }
    // A parameter in a picker (Evolution's selector, an alias's parameter): the parameter table's own coloured name, a
    // dot and the full name in the greyed text, which alone may be cut (the owner, 2026-11-17). Without an item, a
    // derived value by its `sibling`, else `fallback` alone.
    function pickerLine(item, fallback: string, sibling = null): list<var> {
        if (item)
            return names.withFullName(names.segments(item), names.fullName(item));
        if (sibling)
            return names.derivedLine(sibling, fallback.slice(fallback.indexOf(" · ") + 3));
        return names.unlistedLine(fallback);
    }
    // What a picker's search reads for a parameter: its short name and its full name, so either finds it.
    function pickerText(item, fallback: string): string {
        if (!item)
            return fallback;
        const row = item.rowLabel !== "" ? item.rowLabel + " " : "";
        return `${row}${item.shortName} · ${item.fullName}`;
    }
}
