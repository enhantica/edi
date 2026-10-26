// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <optional>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

// What a surface shows for a `.edi` item: its label, units, description and `.edi` name, a selector's
// option names, a category's title and icon, and a number rounded for display. Everything comes from
// crysta's dictionary; no surface keeps a label table or a rounding of its own. Engine-free like the
// rest of edi's public surface (ADR-0003); display.cpp calls crysta.
//
// An item is named by its uid, `category.name` (`cell.length_a`, `experiment_type.beam_mode`). A
// `variant` is the token of the value an item's label or rounding depends on: an atom site's ADP type
// for the ADP items, `doublet` for the first wavelength of an X-ray doublet.

namespace edi {

class Project;
struct Parameter;
struct ParameterSpec;
struct ExperimentBase;
struct Structure;

/// One value of a selector: the token the file holds, the name shown, a description.
struct DisplayOption {
    std::string token;
    std::string label;
    std::string description;
};

/// The uid of a parameter kind, `category.name`.
std::string uid_of(const ParameterSpec& spec);

/// Whether the dictionary has an item with this uid.
bool has_item(std::string_view uid);

/// The short label every surface shows for item `uid`. Each of these throws std::invalid_argument
/// for a uid the dictionary does not hold.
std::string label(std::string_view uid, std::string_view variant = {});
/// The item's units as shown ("Å", "deg"), empty when it has none.
std::string units_label(std::string_view uid, std::string_view variant = {});
/// The item's one-line description.
std::string description(std::string_view uid);
/// The `.edi` name the file holds, e.g. `_atom_site.wyckoff_letter`.
std::string edi_name(std::string_view uid);
/// The tooltip of a label: the label and the `.edi` item it names, `WP: _atom_site.wyckoff_letter`.
std::string tooltip(std::string_view uid, std::string_view variant = {});

/// A selector's values in dictionary order.
std::vector<DisplayOption> options(std::string_view uid);
/// The name shown for one value of a selector. Throws std::invalid_argument for a token that is
/// not one of its values.
std::string option_label(std::string_view uid, std::string_view token);
/// The tooltip of a selector: its `.edi` name and the current token, `_peak.type cwl-gaussian`.
std::string option_tooltip(std::string_view uid, std::string_view token);

/// A category's group title: a loop's title for its rows, else its title. Empty for an id the
/// dictionary does not hold.
std::string category_label(std::string_view id);
/// Whether a category's title carries its row count ("Measured data (N)").
bool category_counts_rows(std::string_view id);
/// A category's Font Awesome icon name; empty for an id the dictionary does not hold.
std::string category_icon(std::string_view id);
/// A category's description.
std::string category_description(std::string_view id);
/// A category's title and its `.edi` name, `Cell: _cell`, as a group's tooltip names the file's category.
std::string category_tooltip(std::string_view id);

/// What a surface shows for a parameter: a value the space group fixes as its exact fraction, a value
/// with a nonzero s.u. as `value(su)` by the project's rule (`iucr_19` or `iucr_99`), any other by its
/// dictionary format. Throws std::invalid_argument for a parameter without a spec.
std::string display_text(const Parameter& parameter, const std::string& su_rule,
                         std::string_view variant = {});
/// A value of a numeric item without an s.u., by the item's dictionary format.
std::string display_text(std::string_view uid, double value, std::string_view variant = {});
/// A single crystal's reflection as its chart's hover reads it (edi ADR-0049): its Miller indices, the measured value
/// with its s.u. by `su_rule` (alone, by its format, without one) and the calculated value by its format, each named by
/// its dictionary label, in F² (`squared`) or F. A value that is not finite is left out.
std::vector<std::string> reflection_hover_lines(int h, int k, int l, double meas, double su, double calc, bool squared,
                                                const std::string& su_rule);
/// One unit of the last digit a parameter shows: a slider's step.
double display_step(const Parameter& parameter, std::string_view variant = {});
/// The same for a value of a numeric item.
double display_step(std::string_view uid, double value, std::string_view variant = {});

/// A parameter's value and s.u. as the project file and the Text tab spell them under `su_rule`.
struct FileText {
    std::string value;  ///< the file's value without its bracket, e.g. "3.89087"
    std::string su;     ///< the bracket as a decimal, e.g. "0.00013"; empty without one, "0" for an engaged zero
};

/// What an input field, the slider and the Analysis table show for a parameter (edi ADR-0051): the
/// value exactly as a save writes it, the s.u. apart, so a field reads as the Text tab does. Throws
/// std::invalid_argument for a parameter without a spec.
FileText file_text(const Parameter& parameter, const std::string& su_rule, bool exact = false);
/// The same for a value of item `uid` without an s.u. (a setting, a range limit, a table cell): the value as a save
/// writes it. Throws std::invalid_argument for a uid the dictionary does not hold.
std::string file_text(std::string_view uid, double value);

/// A fitted value and its s.u. as a table shows them apart: the value rounded by its s.u. under `su_rule`, the s.u.
/// as a decimal (`3.89087` and `0.00013`), as file_text spells a free parameter.
FileText fitted_text(std::string_view uid, double value, double su, const std::string& su_rule);

/// The variant each parameter of `project` reads by: an atom site's ADP type for its isotropic ADP and for its
/// tensor's components, and `doublet` for the first wavelength while an X-ray doublet's second line has a positive
/// intensity ratio. A parameter without one is absent. The app, the report, the CLI and Python all take labels,
/// units and rounding by it.
std::unordered_map<const Parameter*, std::string> parameter_variants(const Project& project);
/// The same for one structure, in a project or not.
std::unordered_map<const Parameter*, std::string> parameter_variants(const Structure& structure);
/// The same for one experiment, in a project or not.
std::unordered_map<const Parameter*, std::string> parameter_variants(const ExperimentBase& experiment);

/// What a save of a project writes exactly (crysta's save_spelling): every value, or the cell of each named structure,
/// whose rounded values would not load. A field shows the value as the save writes it.
struct SaveSpelling {
    bool all_exact = false;
    std::vector<std::string> exact_cells;  ///< structure names
};
SaveSpelling save_spelling(const Project& project);
/// Whether `spelling` writes `parameter` of `project` exactly.
bool written_exactly(const SaveSpelling& spelling, const Project& project, const Parameter& parameter);

/// A number with `decimals` decimals, as `fixed N` shows one: for a table column that keeps one number of decimals
/// for every row, chosen from its values.
std::string fixed_text(double value, int decimals);

/// The exact fraction a value the space group fixes shows as (`1/3`), or nullopt.
std::optional<std::string> exact_fraction(double value);

}  // namespace edi
