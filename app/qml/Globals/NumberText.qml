// SPDX-License-Identifier: BSD-3-Clause
pragma Singleton

import QtQuick

import edi.app

// The one rule for a number shown in a table cell or a field (owner, 2026-10-07): round it to what it is known
// to (the place of its uncertainty's first digit, or six significant digits without one) and to what the cell can
// show, never padding or clipping digits. A value that would not fit in `width` characters is written with an
// exponent instead, keeping the digits its uncertainty allows. The base library's own rounding padded a value
// smaller than its uncertainty with zeros (`000`) and broke on an exponent (`-4.2e-170000000000000`).
//
// A parameter with an uncertainty is rounded as the project writes it, by its rule for standard uncertainties: the
// uncertainty rounded up to one or two digits and the value to the same digit. A parameter is written whatever the
// width of its cell, which clips a long one at its edge, and edited in full (`full`). One at or above a million, or
// below 1e-4 and not zero, is written in scientific notation with four significant digits and its uncertainty in the
// same exponent (`2.290e7`, `0.010e7`), so a column of large intensities reads at a glance (the owner, 2026-10-10).
QtObject {
    // Whether `value` is written in scientific notation.
    function scientific(value) {
        return typeof value === "number" && isFinite(value) && value !== 0 && (Math.abs(value) >= 1e6 || Math.abs(value) < 1e-4);
    }

    // The exponent `value` is written with in scientific notation, after rounding (9999600 is 1.000e7).
    function scientificExponent(value) {
        return exponentOf(value.toExponential(3));
    }

    // The exponent of a number written by toExponential.
    function exponentOf(text) {
        return Number(text.slice(text.indexOf("e") + 1));
    }

    // The value as typed into a field to edit it: every digit it has.
    function full(value) {
        return String(value);
    }

    // A parameter's `value` with its uncertainty `error` (0 or absent: none). `digits` caps the significant digits
    // of a value without an uncertainty (6 by default; the ADP table asks for 5, so a beta component fits its cell).
    function parameter(value, error, digits) {
        if (scientific(value))
            return value.toExponential(3).replace("e+", "e");
        const text = ruled(value, error);
        return text ? text.value : rounded(value, error, Infinity, digits);
    }

    // `value` and its uncertainty `error` rounded by the open project's rule: the `value`, `su` and `bracket`
    // texts, or null without a project or a usable uncertainty. Reading the rule redraws the cells it changes.
    function ruled(value, error) {
        const project = Session.project;
        if (!project || project.suRule === "" || typeof value !== "number" || !isFinite(value) || typeof error !== "number" || !isFinite(error) || error <= 0)
            return null;
        const text = project.suText(value, error);
        return text.value !== "" ? text : null;
    }

    // `value` rounded by its uncertainty `error` and to the cell, as the comment at the top says.
    function rounded(value, error, width, digits) {
        if (typeof value !== "number")
            return String(value);
        if (!isFinite(value))
            return String(value);
        const room = width > 0 ? width : 8;
        const known = typeof error === "number" && isFinite(error) && error > 0;
        let text;
        const most = digits > 0 ? digits : 6;
        let significant = most;
        if (known) {
            // The place of the uncertainty's first digit, after rounding it to that one digit. Read from the text, as
            // the rounded digit can lie past the largest number (an uncertainty near 1.8e308 rounds to 2e308).
            const place = exponentOf(error.toExponential(0));
            // A rounded whole number is written as its digits and zeros, never multiplied back: that could overflow.
            const digits = Math.round(value / Math.pow(10, place));
            significant = value === 0 ? 1 : Math.max(1, Math.floor(Math.log10(Math.abs(value))) - place + 1);
            if (place < 0)
                text = value.toFixed(Math.min(-place, 100));
            else if (Math.abs(digits) < 1e21)
                text = digits === 0 ? "0" : String(digits) + "0".repeat(place);
            else
                text = exponent(value, significant);
        } else {
            text = String(Number(value.toPrecision(most)));
        }
        if (text.length <= room)
            return text;
        return exponent(value, Math.min(significant, Math.max(1, room - 5)));
    }

    // An uncertainty as the error column shows it: rounded up by the project's rule and written plainly (without a
    // project, one significant digit, plainly while it fits). Beside a `parameterValue` in scientific notation it
    // takes that value's exponent and three decimals.
    function error(value, width, parameterValue) {
        if (typeof value !== "number" || !isFinite(value) || value <= 0)
            return "";
        if (scientific(parameterValue)) {
            const power = scientificExponent(parameterValue);
            const mantissa = value * Math.pow(10, -power);
            if (isFinite(mantissa) && mantissa < 1e21)
                return mantissa.toFixed(3) + "e" + power;
            return sharedExponent(value, power) + "e" + power;
        }
        const room = width > 0 ? width : 6;
        // By the project's rule the uncertainty is written plainly at its place, as the value beside it is.
        const text = ruled(parameterValue, value);
        if (text)
            return text.su;
        const plain = String(Number(value.toPrecision(1)));
        return plain.length <= room ? plain : exponent(value, 1);
    }

    // A positive `value` written in units of 10^power with three decimals, from its decimal digits: for an
    // uncertainty so far from its value that scaling the number overflows (1e-288 beside 1e-309) or writes
    // itself with an exponent (1e30 beside 1e6), which would leave or garble the value's exponent.
    function sharedExponent(value, power) {
        // The number of thousandths of 10^power the value rounds to, as digits.
        const shift = exponentOf(value.toExponential()) - power;
        let thousandths;
        if (shift + 3 < 0) {
            thousandths = String(Math.round(Number(value.toExponential().split("e")[0]) * Math.pow(10, shift + 3)));
        } else {
            // At most the 15 significant digits a number keeps exactly; the rest are zeros.
            const text = value.toExponential(Math.min(shift + 3, 14));
            const digits = text.slice(0, text.indexOf("e")).replace(".", "");
            thousandths = digits + "0".repeat(Math.max(0, exponentOf(text) - (power - 3) - (digits.length - 1)));
        }
        const padded = thousandths.padStart(4, "0");
        return padded.slice(0, -3) + "." + padded.slice(-3);
    }

    // A number with no uncertainty (a range end, a reflection's position), rounded as a parameter without the
    // scientific notation.
    function plain(value, width) {
        return rounded(value, 0, width);
    }

    // How a chart's value axis writes its ticks (the owner, 2026-10-11): by the rule above, an axis whose largest
    // tick is at or above a million, or below 1e-4, writes every tick with that tick's exponent (`2.5e8`, `5.0e8`,
    // `7.5e8`), one exponent for the axis, and any other axis writes them plainly. Either way the ticks share the
    // fewest decimals that write each of them exactly, or else that tell them apart. On a logarithmic axis
    // (`shared` false) the ticks are decades apart and each is written on its own, as a parameter's value.
    function axisFormat(ticks, shared) {
        let largest = 0;
        for (const tick of ticks) {
            if (isFinite(tick))
                largest = Math.max(largest, Math.abs(tick));
        }
        const power = shared && scientific(largest) ? scientificExponent(largest) : 0;
        const format = {
            "shared": shared,
            "power": power,
            "decimals": 0
        };
        if (!shared)
            return format;
        const most = power !== 0 ? 3 : 6;
        const exact = decimals => ticks.every(tick => {
                const mantissa = tick / Math.pow(10, power);
                return !isFinite(mantissa) || Math.abs(mantissa - Number(mantissa.toFixed(decimals))) <= 1e-9 * Math.max(1, Math.abs(mantissa));
            });
        const distinct = decimals => new Set(ticks.map(tick => (tick / Math.pow(10, power)).toFixed(decimals))).size === ticks.length;
        for (format.decimals = 0; format.decimals < most && !exact(format.decimals); ++format.decimals) {}
        while (format.decimals < 12 && !distinct(format.decimals))
            ++format.decimals;
        return format;
    }

    // One tick of an axis written by `format` (axisFormat).
    function axisTick(value, format) {
        if (typeof value !== "number" || !isFinite(value))
            return String(value);
        if (!format.shared)
            return scientific(value) ? exponent(value, 4).replace("e+", "e") : String(Number(value.toPrecision(6)));
        const text = (value / Math.pow(10, format.power)).toFixed(format.decimals);
        if (Number(text) === 0)
            return format.power !== 0 ? "0" : (0).toFixed(format.decimals);
        return format.power !== 0 ? text + "e" + format.power : text;
    }

    // A number's text as written for its cell, in scientific notation with the same significant digits, for a cell too
    // narrow to show it (the owner, 2026-10-22): `0.0000123` is `1.23e-5`, `0.0010` is `1.0e-3`, `1250000` is
    // `1.25e6`. A whole number's trailing zeros are not counted as significant. A text that is not a plain decimal
    // number (already an exponent, a word) is returned as it is.
    function compact(text) {
        const parts = /^([+-]?)(\d*)(?:\.(\d*))?$/.exec(String(text));
        if (!parts || (parts[2] === "" && (parts[3] ?? "") === ""))
            return String(text);
        const whole = parts[2].replace(/^0+/, "");
        const fraction = parts[3] ?? "";
        let digits;
        let power;
        if (whole !== "") {
            digits = whole + fraction;
            power = whole.length - 1;
            if (parts[3] === undefined)
                digits = digits.replace(/0+$/, "") || "0";
        } else {
            const first = fraction.search(/[1-9]/);
            if (first < 0)
                return String(text);
            digits = fraction.slice(first);
            power = -(first + 1);
        }
        return parts[1] + digits[0] + (digits.length > 1 ? "." + digits.slice(1) : "") + "e" + power;
    }

    // A number's text as a cell `room` pixels wide shows it, measured with `metrics` (a FontMetrics in the cell's
    // font): as it is when it fits, else in scientific notation (compact) when that is narrower, so no number is cut.
    // `narrow` is the form to fall back to, compact(text) unless given.
    function fitted(text, room, metrics, narrow) {
        if (!(room > 0) || metrics.advanceWidth(text) <= room)
            return text;
        const short = narrow ?? compact(text);
        return metrics.advanceWidth(short) < metrics.advanceWidth(text) ? short : text;
    }

    // An uncertainty in its own shortest scientific form, for an s.u. cell too narrow for the column's form (the
    // owner, 2026-10-22): the one or two significant digits the project's rule gives (one without a project), never
    // in its value's exponent, so `0.008e-6` beside 3.700e-6 is `8e-9`, and 0.0012 is `1.2e-3`.
    function ownUncertainty(value, parameterValue) {
        if (typeof value !== "number" || !isFinite(value) || value <= 0)
            return "";
        const text = ruled(parameterValue, value);
        const written = text ? text.su : String(Number(value.toPrecision(1)));
        return /e/.test(written) ? written.replace("e+", "e") : compact(written);
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
