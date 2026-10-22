// SPDX-License-Identifier: BSD-3-Clause
pragma Singleton

import QtQuick

// Agreement factors written with their subscripts (edi ADR-0045; the owner, 2026-10-21): Rp, Rwp, Rexp, cRp, cRwp,
// R_Bragg and R_F in a plain text become R<sub>p</sub> and so on, through Qt's rich text. The rest of the text is
// escaped, so a name with `<` or `&` shows as written.
QtObject {
    readonly property var pattern: /\b(c?)R_?(wp|p|exp|Bragg|F)\b/g

    // Whether `text` names an agreement factor.
    function has(text) {
        return /\b(c?)R_?(wp|p|exp|Bragg|F)\b/.test(String(text ?? ""));
    }

    // `text` as rich text with every factor subscripted.
    function rich(text) {
        const escaped = String(text ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        return escaped.replace(pattern, "$1R<sub>$2</sub>");
    }
}
