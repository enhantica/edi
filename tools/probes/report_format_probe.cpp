// SPDX-License-Identifier: BSD-3-Clause
// Direct, constructed-value coverage of edi::core's presentation contract.
//
// Why this exists as a probe rather than as assertions on a live fit: the percent-change rule (seam
// S18) has edge cases a real refinement will essentially never produce — a zero start value, a
// non-finite operand, a move sitting either side of the 0.05 % blanking threshold. Before the rule
// lived in a Python example and was pinned directly; moved it into edi::core and the replacement
// coverage checked a single natural-fit string, so a regression to a current-value denominator, an
// infinity, or a wrong threshold would have gone unnoticed. Feeding the formatter constructed values
// is the only way to keep those cases genuinely discriminating.
//
// This is a NON-HIDDEN probe owned by the implementation lane: it exercises production behaviour
// through edi::core's public surface and asserts the contract that surface documents.
//
// Build:  pixi run core-build   (target `report_format_probe`)
// Run:    build/ci/core/report_format_probe   -> exits 0 and prints "report-format-probe: OK"

#include <cmath>
#include <cstdio>
#include <limits>
#include <string>
#include <vector>

#include "edi/report.hpp"

namespace {

int failures = 0;

void check(bool condition, const std::string& what) {
    if (!condition) {
        std::fprintf(stderr, "  FAIL: %s\n", what.c_str());
        ++failures;
    }
}

void check_change(double current, double previous, const std::string& expected,
                  const std::string& what) {
    const std::string actual = edi::format_change(current, previous);
    if (actual != expected) {
        std::fprintf(stderr, "  FAIL: %s — format_change(%g, %g) = \"%s\", expected \"%s\"\n",
                     what.c_str(), current, previous, actual.c_str(), expected.c_str());
        ++failures;
    }
}

const char* kUp = "↑";
const char* kDown = "↓";

void probe_change_format() {
    const double inf = std::numeric_limits<double>::infinity();
    const double nan = std::numeric_limits<double>::quiet_NaN();

    // --- the denominator is the START value, never the refined one ----------------------------
    // 1.0 -> 2.0 is +100 % of the start. Against the CURRENT value it would be 50 %, so this single
    // case discriminates the two definitions.
    check_change(2.0, 1.0, std::string("100.0% ") + kUp, "start-value denominator (up)");
    // 2.0 -> 1.0 is -50 % of the start; against the current value it would be 100 %.
    check_change(1.0, 2.0, std::string("50.0% ") + kDown, "start-value denominator (down)");

    // --- the arrow follows the SIGN, not the magnitude -----------------------------------------
    check_change(1.5, 1.0, std::string("50.0% ") + kUp, "increase renders the up arrow");
    check_change(0.5, 1.0, std::string("50.0% ") + kDown, "decrease renders the down arrow");
    // A negative start: the magnitude uses |previous|, and the direction is still the sign of the
    // difference, so moving from -1 to -2 is a DECREASE.
    check_change(-2.0, -1.0, std::string("100.0% ") + kDown, "negative start keeps sign semantics");

    // --- previous == 0 is blank (a percentage of zero is undefined, not infinite) ---------------
    check_change(1.0, 0.0, "", "zero start blanks rather than rendering infinity");
    check_change(0.0, 0.0, "", "zero start with no movement blanks");
    check_change(-1.0, 0.0, "", "zero start blanks for a negative current too");

    // --- non-finite operands blank -------------------------------------------------------------
    check_change(inf, 1.0, "", "infinite current blanks");
    check_change(1.0, inf, "", "infinite start blanks");
    check_change(-inf, 1.0, "", "negative-infinite current blanks");
    check_change(nan, 1.0, "", "NaN current blanks");
    check_change(1.0, nan, "", "NaN start blanks");

    // --- BOTH sides of the 0.05 % blanking threshold -------------------------------------------
    // These two are the whole point: a wrong threshold passes a test that only checks one side.
    check_change(1.00049, 1.0, "", "0.049 % is immaterial and blanks");
    check_change(1.00051, 1.0, std::string("0.1% ") + kUp, "0.051 % is material and renders");
    check_change(0.99949, 1.0, std::string("0.1% ") + kDown, "-0.051 % is material and renders");
    check_change(0.99951, 1.0, "", "-0.049 % is immaterial and blanks");
    // Deliberately NOT pinned: a value intended to land exactly ON 0.05 %. (1.0005 - 1.0) / 1.0
    // evaluates to 0.049999999999994 in IEEE double, so such a case tests which side of the
    // threshold the FPU happens to land on, not the contract. The four bracketing cases above
    // already discriminate the threshold, and they do so robustly.

    // --- an unmoved parameter shows nothing ----------------------------------------------------
    check_change(1.0, 1.0, "", "an unmoved value blanks");
}

void probe_iteration_line() {
    // The streaming progress line and the `full` table share the change rule, so a per-iteration
    // line must blank on the first iteration, where there is no previous reduced chi-square.
    edi::IterationRecord first;
    first.iteration = 1;
    first.rwp = 0.1032;
    first.reduced_chi_square = 7.1638;
    first.elapsed_ms = 660.0;
    const std::string opening = edi::iteration_line(first, 0.0);
    check(opening.find("7.1638") != std::string::npos, "iteration line carries reduced chi-square");
    check(opening.find(kUp) == std::string::npos && opening.find(kDown) == std::string::npos,
          "the first iteration has no previous value, so it renders no arrow");

    edi::IterationRecord second;
    second.iteration = 2;
    second.rwp = 0.1011;
    second.reduced_chi_square = 6.8675;
    second.elapsed_ms = 1070.0;
    const std::string improving = edi::iteration_line(second, first.reduced_chi_square);
    check(improving.find(kDown) != std::string::npos,
          "a falling reduced chi-square renders the down arrow");
}

void probe_error_report() {
    // The failure record carries no numeric rows, ever, and `off` renders nothing at all.
    check(edi::error_report(edi::VerbosityEnum::OFF).empty(), "error report is empty at verbosity off");
    const std::string record = edi::error_report(edi::VerbosityEnum::COMPACT);
    check(record == "schema=1\nrecord=error\nstatus=error\n",
          "error report is exactly the three-row failure shape, got: " + record);
}

}  // namespace

int main() {
    probe_change_format();
    probe_iteration_line();
    probe_error_report();
    if (failures != 0) {
        std::fprintf(stderr, "report-format-probe: %d FAILURE(S)\n", failures);
        return 1;
    }
    std::printf("report-format-probe: OK\n");
    return 0;
}
