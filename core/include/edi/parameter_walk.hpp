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

// One warning per anisotropic site whose tensor has a negative eigenvalue, by crysta's rule (a zero or
// semi-definite tensor is allowed): the site's tensor row and the message. A structure that does not
// convert gives none.
struct AdpDefinitenessWarning {
    const AtomSiteAniso* tensor = nullptr;
    std::string message;
};
std::vector<AdpDefinitenessWarning> adp_definiteness_warnings(const Project& project);

// The warnings that hold for the project's current values, one each: a value outside its admissible range,
// set or derived by a constraint (an anisotropic site's equivalent isotropic displacement), and an anisotropic
// tensor with a negative eigenvalue. Such values are kept, saved and loaded; the app posts these after a fit,
// and after a load those the loader does not report itself (`ranges` false: the tensors), and marks the values
// red; the user decides (the owner, 2026-10-23).
std::vector<std::string> standing_warnings(Project& project, bool ranges = true);

}  // namespace edi

#endif  // EDI_PARAMETER_WALK_HPP
