// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_EDITS_HPP
#define EDI_EDITS_HPP

// The rules the app applies when a user sets a value, one function per rule, each the same rule the
// library applies — the Python attribute setters in lib/src/bindings.cpp or, for analysis settings,
// the loader. The bindings keep their own spelling unchanged (owner, 2026-09-27); parity tests hold
// the two equal. A field the library assigns without a rule (a name, a string, a plain number) needs
// no function here; a parameter value goes through assign_value (model.hpp, beside Parameter).

#include <stdexcept>
#include <string>

#include "edi/model.hpp"

namespace edi {

// A project name, the library's rule (the Python `ProjectMetadata.name` setter and named constructor,
// lib/src/bindings.cpp `validated_project_name`, whose message this reproduces; the binding keeps its
// own spelling unchanged — owner, 2026-09-27): a name lands in filesystem paths at save, so a path
// separator refuses at the boundary.
inline bool project_name_has_separator(const std::string& name) {
    return name.find('/') != std::string::npos || name.find('\\') != std::string::npos;
}
inline const std::string& validated_project_name(const std::string& name) {
    if (project_name_has_separator(name)) {
        throw std::invalid_argument("project name '" + name + "' must not contain a path separator ('/' or '\\')");
    }
    return name;
}

// Renaming an entry of a keyed collection: a rename onto a key the collection already holds is
// refused, so it never merges two entries or silently replaces one. Nothing changes on a
// refusal. An experiment's rename is io.hpp's rename_experiment, beside the adder whose rule it
// shares.
//
// A scattering length is declared once per type symbol — the loader's rule (io.cpp, a duplicate
// `_scattering_length.type_symbol` fails closed rather than letting the last row win).
inline void rename_scattering_length(Structure& structure, const std::string& from, const std::string& to) {
    const std::map<std::string, double>& lengths = structure.scattering_lengths_fm;
    const auto found = lengths.find(from);
    if (found == lengths.end()) {
        throw std::invalid_argument("the structure declares no scattering length for '" + from + "'");
    }
    if (from == to) {
        return;
    }
    if (to.empty()) {
        throw std::invalid_argument("a scattering length needs a type symbol");
    }
    if (lengths.count(to) != 0) {
        throw std::invalid_argument("a scattering length for '" + detail::printable_id(to) +
                                    "' is already declared");
    }
    const double length = found->second;
    structure.scattering_lengths_fm.modify([&from, &to, length](std::map<std::string, double>& rows) {
        rows.erase(from);
        rows.emplace(to, length);
    });
}
// An atom site's label keys it: a parameter identity path names the site by it
// (`structure.atom_sites[Ca].fract_x`, model.hpp), so two sites under one label make a path ambiguous.
inline void rename_atom_site(Structure& structure, AtomSite& site, const std::string& id) {
    if (id == site.id) {
        return;
    }
    for (const auto& other : structure.atom_sites) {
        if (other->id == id) {
            throw std::invalid_argument("an atom site labelled '" + detail::printable_id(id) +
                                        "' is already in the structure");
        }
    }
    // An anisotropic site's tensor row is keyed by the site id; the site's collection renames it
    // along (KeyedBase::holder).
    site.id = id;
}

// One component of a texture axis (the Python `PrefOrient.index_h/k/l` setters): an integer within
// the loader's bound, and never the axis [0 0 0].
inline void set_texture_axis_component(PrefOrient& row, detail::Written<int> PrefOrient::*component,
                                       int value) {
    if (value > kPreferredOrientationAxisBound || value < -kPreferredOrientationAxisBound) {
        throw std::invalid_argument("a texture axis component exceeds the bound " +
                                    std::to_string(kPreferredOrientationAxisBound));
    }
    // The axis the write would leave, checked before it: a component records its writes (ADR-0018), so a
    // write undone on refusal would still be two writes (edi ADR-0020 §8).
    const auto after = [&row, component, value](detail::Written<int> PrefOrient::*axis) {
        return axis == component ? value : static_cast<int>(row.*axis);
    };
    if (after(&PrefOrient::index_h) == 0 && after(&PrefOrient::index_k) == 0 && after(&PrefOrient::index_l) == 0) {
        throw std::invalid_argument("the texture axis [0 0 0] has no direction");
    }
    row.*component = value;
}

// The declared iteration bound (the loader's rule for `_minimizer.max_iterations`: a positive
// integer).
inline void set_minimizer_max_iterations(Project& project, int bound) {
    if (bound <= 0) {
        throw std::invalid_argument("_minimizer.max_iterations must be a positive integer");
    }
    project.minimizer_max_iterations = bound;
}

// The declared chi-square tolerance (the loader's rule for `_minimizer.chi_square_tolerance`: a
// positive number).
inline void set_minimizer_chi_square_tolerance(Project& project, double tolerance) {
    if (!(tolerance > 0.0)) {
        throw std::invalid_argument("_minimizer.chi_square_tolerance must be a positive number");
    }
    project.minimizer_chi_square_tolerance = tolerance;
}

}  // namespace edi

#endif  // EDI_EDITS_HPP
