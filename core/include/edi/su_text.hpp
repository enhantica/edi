// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <string>

// Values with a standard uncertainty as a project writes them: crysta's IUCr rule, one
// implementation for the files, the screen and the report. Engine-free like the rest of edi's
// public surface (ADR-0003); su_text.cpp calls crysta.

namespace edi {

/// A value and its standard uncertainty rounded by a project's `_su_format.rule`.
struct SuText {
    std::string value;    ///< the value rounded to the s.u.'s last digit, e.g. "2.164"
    std::string su;       ///< the s.u. rounded up, as a decimal, e.g. "0.005"
    std::string bracket;  ///< the bracket's digits, in units of the value's last digit, e.g. "5"
};

/// Rounds a finite value and a finite, nonzero s.u. by `rule` ("iucr_19" or "iucr_99").
/// Throws std::invalid_argument for any other input.
SuText su_text(double value, double su, const std::string& rule);

/// "value(bracket)", e.g. "2.164(5)", under the same conditions as su_text.
std::string value_su_text(double value, double su, const std::string& rule);

/// A correlation coefficient with two significant figures, three from a magnitude of 0.95.
/// Throws std::invalid_argument for a non-finite coefficient.
std::string correlation_text(double coefficient);

}  // namespace edi
