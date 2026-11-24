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

    // A parameter in a picker (Evolution's selector, an alias's parameter): the parameter table's own coloured name, a
    // dot and the full name in the greyed text, which alone may be cut at its end (the owner, 2026-11-17). Without an
    // item, `fallback` alone.
    // A name no item stands for (a column of a fit's results the parameter list does not hold), drawn in the same form:
    // the block's icon (a structure's for a structure's category, else an experiment's), the category's, the last part as
    // the short name, then the full name (the owner, 2026-11-24).
    readonly property var structureCategories: ["cell", "space_group", "atom_site", "atom_sites", "atom_site_aniso", "atom_site_moment", "scattering_length", "geom"]
    function unlistedLine(text: string): list<var> {
        // A factor's label comes before its name ("R_Bragg, cosio (%) · fit_result.r_bragg.cosio").
        const at = text.indexOf(" · ");
        const full = at > 0 ? text.slice(at + 3) : text;
        const parts = full.split(".");
        if (parts.length < 3)
            return [
                {
                    "text": text,
                    "elides": true,
                    "factors": true
                }
            ];
        const kind = names.structureCategories.indexOf(parts[1]) >= 0 ? "structure" : "experiment";
        const minor = String(EaStyle.Colors.themeForegroundMinor);
        const line = [
            {
                "icon": names.blockIcon(kind),
                "color": String(AppColors.block(kind, 0))
            }
        ];
        const icon = Session.categoryIcon(parts[1]);
        if (icon !== "")
            line.push({
                "icon": icon,
                "color": minor
            });
        return line.concat([
            {
                "text": at > 0 ? text.slice(0, at) : parts[parts.length - 1],
                "factors": true
            },
            {
                "text": "·",
                "color": minor
            },
            {
                "text": full,
                "color": minor,
                "elides": true,
                "factors": true
            }
        ]);
    }
    function pickerLine(item, fallback: string): list<var> {
        if (!item)
            return names.unlistedLine(fallback);
        return names.segments(item).concat([
            {
                "text": "·",
                "color": String(EaStyle.Colors.themeForegroundMinor)
            },
            {
                "text": names.fullName(item),
                "color": String(EaStyle.Colors.themeForegroundMinor),
                "elides": true
            }
        ]);
    }
    // What a picker's search reads for a parameter: its short name and its full name, so either finds it.
    function pickerText(item, fallback: string): string {
        if (!item)
            return fallback;
        const row = item.rowLabel !== "" ? item.rowLabel + " " : "";
        return `${row}${item.shortName} · ${item.fullName}`;
    }
}
