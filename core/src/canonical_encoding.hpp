// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_CANONICAL_ENCODING_HPP
#define EDI_CANONICAL_ENCODING_HPP

// The canonical source encoding: an INJECTIVE byte encoding of everything in a Project that can
// affect the built engine graph, the parameter index, a calculation or a refinement — the
// stale-source guard, compared VERBATIM (never hashed). Pure edi value types, so it sits on edi's
// side of the ADR-0003 line and is unit-testable without the engine. core/src-private (never
// installed): the encoding is an engine-facing cache policy, not product surface. Adding a field to
// edi::Project REQUIRES extending it.

#include <string>
#include <cstddef>
#include <vector>

#include "edi/model.hpp"

namespace edi::detail {

std::string canonical_encoding(const Project& project);

// The same injective encoding narrowed to what one experiment's calculation reads — every
// structure of its project, the experiment's calculation inputs (a parameter's value, never its
// uncertainty or free flag; crysta's computed-input table), its data
// node (grid and measured columns) and the identity of every object among them (detail::Epoch).
// Equal encodings mean the experiment's computed categories still describe it.
std::string calculation_inputs(const ItemVec<Structure>& structures,
                               const ExperimentBase& experiment);

// The same encoding narrowed to what a structure's computed geometry reads — its cell, space group
// and atom sites (values, never an uncertainty or a free flag), `geom`, and the identity of every
// object among them. Equal encodings mean the structure's stored geometry still describes it. It
// is wider than crysta's own input set by the Wyckoff letter, the name and the scattering lengths,
// which is the conservative direction.
std::string geometry_inputs(const Structure& structure);

// Refill an existing encoding buffer. Publication reserves its complete unchanged-shape width before
// scalar writes; values and write identities have fixed encoded widths, so refilling cannot grow it.
void calculation_inputs_into(std::string& out, const ItemVec<Structure>& structures,
                             const ExperimentBase& experiment);
void geometry_inputs_into(std::string& out, const Structure& structure);

// The declared relations (edi ADR-0024): every alias and constraint row with the identity of each
// field's last write, and each collection's generation. A declaration sets dependents' values, so it
// is an input of every computed category and of the geometry; equal encodings mean no declaration
// was written, an equal rewrite included.
std::string relation_inputs(const ItemVec<ParameterAlias>& aliases,
                            const ItemVec<ParameterConstraint>& constraints);

// Preparation resolves aliases and records only the fixed-width value/write-ID
// slots. The owning declarations/shape must remain unchanged until commit.
struct RelationValueSlot {
    const Parameter* parameter;
    std::size_t offset;
};
std::string relation_inputs(const ItemVec<ParameterAlias>& aliases,
                            const ItemVec<ParameterConstraint>& constraints,
                            std::vector<RelationValueSlot>* values);
// The same original byte traversal with a nonallocating count sink. Relation
// lookup retains its original naming scratch; the caller admits that role before
// calling its count/writer. These source-private entrances never notify callers.
std::size_t geometry_inputs_size(const Structure&, std::size_t limit);
std::size_t calculation_inputs_size(const ItemVec<Structure>&, const ExperimentBase&, std::size_t limit);
std::size_t relation_inputs_size(const ItemVec<ParameterAlias>&, const ItemVec<ParameterConstraint>&, std::size_t limit);

// Slots were checked against this exact complete encoding before live writes.
// No name joining, resizing, allocation or declaration traversal occurs here.
void refresh_relation_values(std::string& encoding,
                              const std::vector<RelationValueSlot>& values) noexcept;


}  // namespace edi::detail

#endif  // EDI_CANONICAL_ENCODING_HPP
