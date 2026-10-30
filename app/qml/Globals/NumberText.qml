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
    function scientific(value) { return ApplicationInfo.numberPresentation(ApplicationInfo.NumberScientific, value, undefined, undefined, undefined); }

    // The exponent `value` is written with in scientific notation, after rounding (9999600 is 1.000e7).
    function scientificExponent(value) { return ApplicationInfo.numberPresentation(ApplicationInfo.NumberScientificExponent, value, undefined, undefined, undefined); }

    // The exponent of a number written by toExponential.
    function exponentOf(text) { return ApplicationInfo.numberPresentation(ApplicationInfo.NumberExponentOf, text, undefined, undefined, undefined); }

    // The value as typed into a field to edit it: every digit it has.
    function full(value) { return ApplicationInfo.numberPresentation(ApplicationInfo.NumberFull, value, undefined, undefined, undefined); }

    // Every digit `value` holds, written plainly, never with an exponent: what hovering a cell that shows the number
    // shorter or in scientific notation reveals (the owner, 2026-10-22). 8.3e-9 is `0.0000000083`.
    function plainFull(value) { return ApplicationInfo.numberPresentation(ApplicationInfo.NumberPlainFull, value, undefined, undefined, undefined); }

    // A parameter's `value` with its uncertainty `error` (0 or absent: none). `digits` caps the significant digits
    // of a value without an uncertainty (6 by default; the ADP table asks for 5, so a beta component fits its cell).
    function parameter(value, error, digits) { return ApplicationInfo.numberPresentation(ApplicationInfo.NumberParameter, value, error, digits, undefined); }

    // `value` and its uncertainty `error` rounded by the open project's rule: the `value`, `su` and `bracket`
    // texts, or null without a project or a usable uncertainty. Reading the rule redraws the cells it changes.
    function ruled(value, error) { return ApplicationInfo.numberPresentation(ApplicationInfo.NumberRuled, value, error, undefined, undefined); }

    // `value` rounded by its uncertainty `error` and to the cell, as the comment at the top says.
    function rounded(value, error, width, digits) { return ApplicationInfo.numberPresentation(ApplicationInfo.NumberRounded, value, error, width, digits); }

    // An uncertainty as the error column shows it: rounded up by the project's rule and written plainly (without a
    // project, one significant digit, plainly while it fits). Beside a `parameterValue` in scientific notation it
    // takes that value's exponent and three decimals.
    function error(value, width, parameterValue) { return ApplicationInfo.numberPresentation(ApplicationInfo.NumberError, value, width, parameterValue, undefined); }

    // A positive `value` written in units of 10^power with three decimals, from its decimal digits: for an
    // uncertainty so far from its value that scaling the number overflows (1e-288 beside 1e-309) or writes
    // itself with an exponent (1e30 beside 1e6), which would leave or garble the value's exponent.
    function sharedExponent(value, power) { return ApplicationInfo.numberPresentation(ApplicationInfo.NumberSharedExponent, value, power, undefined, undefined); }

    // A number with no uncertainty (a range end, a reflection's position), rounded as a parameter without the
    // scientific notation.
    function plain(value, width) { return ApplicationInfo.numberPresentation(ApplicationInfo.NumberPlain, value, width, undefined, undefined); }

    // How a chart's value axis writes its ticks (the owner, 2026-10-11): by the rule above, an axis whose largest
    // tick is at or above a million, or below 1e-4, writes every tick with that tick's exponent (`2.5e8`, `5.0e8`,
    // `7.5e8`), one exponent for the axis, and any other axis writes them plainly. Either way the ticks share the
    // fewest decimals that write each of them exactly, or else that tell them apart. On a logarithmic axis
    // (`shared` false) the ticks are decades apart and each is written on its own, as a parameter's value.
    function axisFormat(ticks, shared) { return ApplicationInfo.numberPresentation(ApplicationInfo.NumberAxisFormat, ticks, shared, undefined, undefined); }

    // One tick of an axis written by `format` (axisFormat).
    function axisTick(value, format) { return ApplicationInfo.numberPresentation(ApplicationInfo.NumberAxisTick, value, format, undefined, undefined); }

    // A plain decimal text as its sign, its digits from the first significant one and that digit's power of ten, and
    // whether it is a whole number; null for a zero or a text that is not a plain decimal number.
    function decimal(text) { return ApplicationInfo.numberPresentation(ApplicationInfo.NumberDecimal, text, undefined, undefined, undefined); }

    // A number's text as written for its cell, in scientific notation with the same significant digits, for a cell too
    // narrow to show it (the owner, 2026-10-22): `0.0000123` is `1.23e-5`, `0.0010` is `1.0e-3`, `1250000` is
    // `1.25e6`. `significant` is how many digits the text holds where its rounding says so (narrowParameter,
    // ownUncertainty): `120000` known to the units is `1.20000e5`. Without it a whole number's trailing zeros are not
    // counted, as for a number with no uncertainty. A text that is not a plain decimal number (already an exponent, a
    // word) is returned as it is.
    function compact(text, significant) { return ApplicationInfo.numberPresentation(ApplicationInfo.NumberCompact, text, significant, undefined, undefined); }

    // How many significant digits an s.u. the project's rule wrote has: two under iucr_99, and under iucr_19 from 10
    // to 19 (a first digit 1); one otherwise. A whole number's text alone cannot say (`200000` is 2e5 or 2.0e5).
    function suDigits(su) { return ApplicationInfo.numberPresentation(ApplicationInfo.NumberSuDigits, su, undefined, undefined, undefined); }

    // How many significant digits a value the rule rounded beside its s.u. has (both texts from ruled): down to the
    // s.u.'s last digit, or the s.u.'s own count for a value too small to reach that digit, which keeps as many of its
    // own.
    function ruledDigits(value, su) { return ApplicationInfo.numberPresentation(ApplicationInfo.NumberRuledDigits, value, su, undefined, undefined); }

    // A parameter's text (parameter) in scientific notation, for a cell too narrow for it, with the digits its
    // uncertainty leaves it.
    function narrowParameter(value, error, digits) { return ApplicationInfo.numberPresentation(ApplicationInfo.NumberNarrowParameter, value, error, digits, undefined); }

    // A number's text as a cell `room` pixels wide shows it, measured with `metrics` (a FontMetrics in the cell's
    // font): as it is when it fits, else in scientific notation with the same significant digits. `narrow` is that
    // form, compact(text) unless given.
    function fitted(text, room, metrics, narrow) { return ApplicationInfo.numberPresentation(ApplicationInfo.NumberFitted, text, room, metrics, narrow); }

    // An uncertainty in its own shortest scientific form, for an s.u. cell too narrow for the column's form (the
    // owner, 2026-10-22): the one or two significant digits the project's rule gives (one without a project), never
    // in its value's exponent, so `0.008e-6` beside 3.700e-6 is `8e-9`, and 0.0012 is `1.2e-3`.
    function ownUncertainty(value, parameterValue) { return ApplicationInfo.numberPresentation(ApplicationInfo.NumberOwnUncertainty, value, parameterValue, undefined, undefined); }

    // `value` in exponent form with `digits` significant digits, without trailing zeros in its mantissa.
    function exponent(value, digits) { return ApplicationInfo.numberPresentation(ApplicationInfo.NumberExponent, value, digits, undefined, undefined); }
}
