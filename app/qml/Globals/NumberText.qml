// SPDX-License-Identifier: BSD-3-Clause
pragma Singleton

import QtQuick

import edi.app

// The one rule for a number shown in the app (the owner, 2026-11-09 and 2026-11-11): a decimal when
// 0.001 <= |x| < 1000 (zero is 0), else three significant digits times a power of ten with a superscript exponent
// (`8.40×10⁻⁵`). A value with an uncertainty is rounded by the project's rule for standard uncertainties, and outside
// that range both are written in the value's power of ten (`2.290×10⁷`, `0.010×10⁷`); an uncertainty beside a value
// inside the range follows the rule on its own (`2.5×10⁻⁴`). The text never depends on the cell's width or on whether
// the parameter is free; a field being edited shows the value in plain digits (`full`). The displayed texts come from
// edi::table_number and edi::table_value_su, which the report uses too.
QtObject {
    // Whether `value` is written in scientific notation.
    function scientific(value) {
        return ApplicationInfo.numberPresentation(ApplicationInfo.NumberScientific, value, undefined, undefined, undefined);
    }

    // The exponent `value` is written with in scientific notation, after rounding (9999600 is 1.000e7).
    function scientificExponent(value) {
        return ApplicationInfo.numberPresentation(ApplicationInfo.NumberScientificExponent, value, undefined, undefined, undefined);
    }

    // The exponent of a number written by toExponential.
    function exponentOf(text) {
        return ApplicationInfo.numberPresentation(ApplicationInfo.NumberExponentOf, text, undefined, undefined, undefined);
    }

    // The value as typed into a field to edit it: every digit it has.
    function full(value) {
        return ApplicationInfo.numberPresentation(ApplicationInfo.NumberFull, value, undefined, undefined, undefined);
    }

    // Every digit `value` holds, written plainly, never with an exponent: what hovering a cell that shows the number
    // shorter or in scientific notation reveals (the owner, 2026-10-22). 8.3e-9 is `0.0000000083`.
    function plainFull(value) {
        return ApplicationInfo.numberPresentation(ApplicationInfo.NumberPlainFull, value, undefined, undefined, undefined);
    }

    // A parameter's `value` with its uncertainty `error` (0 or absent: none), by the rule above. `digits` caps the
    // significant digits of a value without an uncertainty inside the decimal range (6 by default).
    function parameter(value, error, digits) {
        return ApplicationInfo.numberPresentation(ApplicationInfo.NumberParameter, value, error, digits, undefined);
    }

    // `value` and its uncertainty `error` rounded by the open project's rule: the `value`, `su` and `bracket`
    // texts, or null without a project or a usable uncertainty. Reading the rule redraws the cells it changes.
    function ruled(value, error) {
        return ApplicationInfo.numberPresentation(ApplicationInfo.NumberRuled, value, error, undefined, undefined);
    }

    // `value` rounded by its uncertainty `error` and to the cell, as the comment at the top says.
    function rounded(value, error, width, digits) {
        return ApplicationInfo.numberPresentation(ApplicationInfo.NumberRounded, value, error, width, digits);
    }

    // An uncertainty as the error column shows it, beside its `parameterValue`, by the rule above.
    function error(value, width, parameterValue) {
        return ApplicationInfo.numberPresentation(ApplicationInfo.NumberError, value, width, parameterValue, undefined);
    }

    // A positive `value` written in units of 10^power with three decimals, from its decimal digits: for an
    // uncertainty so far from its value that scaling the number overflows (1e-288 beside 1e-309) or writes
    // itself with an exponent (1e30 beside 1e6), which would leave or garble the value's exponent.
    function sharedExponent(value, power) {
        return ApplicationInfo.numberPresentation(ApplicationInfo.NumberSharedExponent, value, power, undefined, undefined);
    }

    // A number with no uncertainty (a range end, a reflection's position), rounded as a parameter without the
    // scientific notation.
    function plain(value, width) {
        return ApplicationInfo.numberPresentation(ApplicationInfo.NumberPlain, value, width, undefined, undefined);
    }

    // How an axis writes its ticks, each on its own by the rule above: a decimal when 0.001 <= |x| < 1000, else three
    // significant digits times a power of ten, trailing zeros dropped (500, 1×10³, 1.5×10³), with the fewest digits
    // that write every tick exactly, or else tell neighbours apart. `shared` is not used.
    function axisFormat(ticks, shared) {
        return ApplicationInfo.numberPresentation(ApplicationInfo.NumberAxisFormat, ticks, shared, undefined, undefined);
    }

    // One tick of an axis written by `format` (axisFormat).
    function axisTick(value, format) {
        return ApplicationInfo.numberPresentation(ApplicationInfo.NumberAxisTick, value, format, undefined, undefined);
    }

    // The round tick step for an axis from `low` to `high`, `pixels` long, whose labels in `font` leave a gap between
    // neighbours (their widths along a horizontal axis, their height along a vertical one), nearest `count` ticks.
    function axisStep(low, high, count, pixels, font, horizontal) {
        return ApplicationInfo.numberPresentation(ApplicationInfo.NumberAxisStep, [low, high, count], pixels, font, horizontal);
    }

    // A plain decimal text as its sign, its digits from the first significant one and that digit's power of ten, and
    // whether it is a whole number; null for a zero or a text that is not a plain decimal number.
    function decimal(text) {
        return ApplicationInfo.numberPresentation(ApplicationInfo.NumberDecimal, text, undefined, undefined, undefined);
    }

    // A number's text by the rule for numbers: a decimal when 0.001 <= |x| < 1000, else three significant digits times
    // a power of ten (`8.40×10⁻⁵`; the owner, 2026-11-09 and 2026-11-11). A text that is not a number is returned as
    // it is; `significant` is not used.
    function compact(text, significant) {
        return ApplicationInfo.numberPresentation(ApplicationInfo.NumberCompact, text, significant, undefined, undefined);
    }

    // The written value/SU pair, retaining its meaningful last digit and all
    // explicit exact digits when a control needs a scientific spelling.
    function writtenNarrow(text, su) {
        return ApplicationInfo.numberPresentation(ApplicationInfo.NumberWrittenNarrow, text, su, undefined, undefined);
    }

    // How many significant digits an s.u. the project's rule wrote has: two under iucr_99, and under iucr_19 from 10
    // to 19 (a first digit 1); one otherwise. A whole number's text alone cannot say (`200000` is 2e5 or 2.0e5).
    function suDigits(su) {
        return ApplicationInfo.numberPresentation(ApplicationInfo.NumberSuDigits, su, undefined, undefined, undefined);
    }

    // How many significant digits a value the rule rounded beside its s.u. has (both texts from ruled): down to the
    // s.u.'s last digit, or the s.u.'s own count for a value too small to reach that digit, which keeps as many of its
    // own.
    function ruledDigits(value, su) {
        return ApplicationInfo.numberPresentation(ApplicationInfo.NumberRuledDigits, value, su, undefined, undefined);
    }

    // The same text as parameter: a cell's width never changes how a number is written.
    function narrowParameter(value, error, digits) {
        return ApplicationInfo.numberPresentation(ApplicationInfo.NumberNarrowParameter, value, error, digits, undefined);
    }

    // The text as it is: a number is written the same whatever the cell's width (the owner, 2026-11-11). Kept for the
    // cells that call it.
    function fitted(text, room, metrics, narrow) {
        return ApplicationInfo.numberPresentation(ApplicationInfo.NumberFitted, text, room, metrics, narrow);
    }

    // The same text as error.
    function ownUncertainty(value, parameterValue) {
        return ApplicationInfo.numberPresentation(ApplicationInfo.NumberOwnUncertainty, value, parameterValue, undefined, undefined);
    }

    // `value` in exponent form with `digits` significant digits, without trailing zeros in its mantissa.
    function exponent(value, digits) {
        return ApplicationInfo.numberPresentation(ApplicationInfo.NumberExponent, value, digits, undefined, undefined);
    }
}
