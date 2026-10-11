// SPDX-License-Identifier: BSD-3-Clause
pragma Singleton

import QtQuick

// The one rule for a number shown in a table cell or a field (owner, 2026-10-07): round it to what it is known
// to (the place of its uncertainty's first digit, or six significant digits without one) and to what the cell can
// show, never padding or clipping digits. A value that would not fit in `width` characters is written with an
// exponent instead, keeping the digits its uncertainty allows. The base library's own rounding padded a value
// smaller than its uncertainty with zeros (`000`) and broke on an exponent (`-4.2e-170000000000000`).
//
// A parameter is written whatever the width of its cell, which clips a long one at its edge, and edited in full
// (`full`). One at or above a million, or below 1e-4 and not zero, is written in scientific notation with four
// significant digits and its uncertainty in the same exponent (`2.290e7`, `0.010e7`), so a column of large
// intensities reads at a glance (the owner, 2026-10-10).
QtObject {
    // Whether `value` is written in scientific notation.
    function scientific(value) {
        return typeof value === "number" && isFinite(value) && value !== 0 && (Math.abs(value) >= 1e6 || Math.abs(value) < 1e-4);
    }

    // The exponent `value` is written with in scientific notation, after rounding (9999600 is 1.000e7).
    function scientificExponent(value) {
        const text = value.toExponential(3);
        return Number(text.slice(text.indexOf("e") + 1));
    }

    // The value as typed into a field to edit it: every digit it has.
    function full(value) {
        return String(value);
    }

    // A parameter's `value` with its uncertainty `error` (0 or absent: none).
    function parameter(value, error) {
        return scientific(value) ? value.toExponential(3).replace("e+", "e") : rounded(value, error, Infinity);
    }

    // `value` rounded by its uncertainty `error` and to the cell, as the comment at the top says.
    function rounded(value, error, width) {
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

    // An uncertainty as the error column shows it: one significant digit, written plainly while it fits. Beside
    // a `parameterValue` in scientific notation it takes that value's exponent and three decimals.
    function error(value, width, parameterValue) {
        if (typeof value !== "number" || !isFinite(value) || value <= 0)
            return "";
        if (scientific(parameterValue)) {
            const power = scientificExponent(parameterValue);
            return (value * Math.pow(10, -power)).toFixed(3) + "e" + power;
        }
        const room = width > 0 ? width : 6;
        const text = String(Number(value.toPrecision(1)));
        return text.length <= room ? text : exponent(value, 1);
    }

    // A number with no uncertainty (a range end, a reflection's position), rounded as a parameter without the
    // scientific notation.
    function plain(value, width) {
        return rounded(value, 0, width);
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
