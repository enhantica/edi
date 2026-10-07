// SPDX-License-Identifier: BSD-3-Clause
pragma Singleton

import QtQuick

// The one rule for a number shown in a table cell or a field (owner, 2026-10-07): round it to what it is known
// to (the place of its uncertainty's first digit, or six significant digits without one) and to what the cell can
// show, never padding or clipping digits. A value that would not fit in `width` characters is written with an
// exponent instead, keeping the digits its uncertainty allows. The base library's own rounding padded a value
// smaller than its uncertainty with zeros (`000`) and broke on an exponent (`-4.2e-170000000000000`).
QtObject {
    // `value` with its uncertainty `error` (0 or absent: none), for a cell `width` characters wide.
    function parameter(value, error, width) {
        if (typeof value !== "number")
            return String(value);
        if (!isFinite(value))
            return String(value);
        const room = width > 0 ? width : 8;
        const known = typeof error === "number" && isFinite(error) && error > 0;
        let text;
        let significant = 6;
        if (known) {
            // The place of the uncertainty's first digit, after rounding it to that one digit.
            const place = Math.floor(Math.log10(Number(error.toPrecision(1))));
            text = place >= 0 ? String(Math.round(value / Math.pow(10, place)) * Math.pow(10, place) + 0) : value.toFixed(Math.min(-place, 100));
            significant = value === 0 ? 1 : Math.max(1, Math.floor(Math.log10(Math.abs(value))) - place + 1);
        } else {
            text = String(Number(value.toPrecision(6)));
        }
        if (text.length <= room)
            return text;
        return exponent(value, Math.min(significant, Math.max(1, room - 5)));
    }

    // An uncertainty as the error column shows it: one significant digit, written plainly while it fits.
    function error(value, width) {
        if (typeof value !== "number" || !isFinite(value) || value <= 0)
            return "";
        const room = width > 0 ? width : 6;
        const text = String(Number(value.toPrecision(1)));
        return text.length <= room ? text : exponent(value, 1);
    }

    // A number with no uncertainty (a range end, a reflection's position), as `parameter` writes it.
    function plain(value, width) {
        return parameter(value, 0, width);
    }

    // `value` in exponent form with `digits` significant digits, without trailing zeros in its mantissa.
    function exponent(value, digits) {
        const text = value.toExponential(Math.max(0, digits - 1));
        const at = text.indexOf("e");
        let mantissa = text.slice(0, at);
        if (mantissa.indexOf(".") >= 0)
            mantissa = mantissa.replace(/0+$/, "").replace(/\.$/, "");
        return mantissa + text.slice(at);
    }
}
