// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_PARAMETER_WALK_HPP
#define EDI_PARAMETER_WALK_HPP

// Every parameter the pages show, in page order — the rows of the app's parameter table — each with its
// identity path in edi's path grammar (the one fit results are keyed by: `structure.cell.length_a`,
// `structure.atom_sites[<id>].<field>`, `experiment.<category>.<field>` for a one-experiment project,
// `experiments[<name>].<category>.<field>` for several).

#include <string>
#include <vector>

#include "edi/model.hpp"

namespace edi {

struct ParameterEntry {
    Parameter* parameter = nullptr;
    std::string path;        // the identity path
    std::string block_kind;  // "structure" or "experiment"
    std::string block_name;  // the datablock name
    std::string category;    // the `.edi` category id
    std::string row_label;   // an atom id or a row index for loop categories; empty otherwise
    std::string name;        // the `.edi` item name
    bool refinable = true;   // false: symmetry fixes or ties it (categories.hpp); shown, never fitted
    bool fittable = true;    // false: a fixed setting (categories.hpp); editable, never fitted
};

// Every shown parameter of the project (the union of the categories' shown fields, §2b (iv), I15)
// in page order: structures, then experiments. A listing of what a fit can vary (the app's
// Analysis table) takes the `refinable` entries; the pages show every entry. Paths come from the fit surface's own grammar
// functions (core/src/parameter_paths.cpp), so fit results map onto these rows by path.
std::vector<ParameterEntry> parameter_entries(Project& project);

// What a fit or an undo worked out on a copy, written onto the project it was copied from. Every
// parameter's value, uncertainty and fit start is written from `from` onto `to` where they differ — a
// value as an admitted write is. Both walks must name the same parameters in the same order: otherwise
// nothing is written and the answer is false.
bool copy_parameter_states(Project& to, Project& from);

}  // namespace edi

#endif  // EDI_PARAMETER_WALK_HPP
