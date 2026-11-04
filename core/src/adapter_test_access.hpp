// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_ADAPTER_TEST_ACCESS_HPP
#define EDI_ADAPTER_TEST_ACCESS_HPP

// Test-only seam: exposes the adapter's edi -> crysta conversion helpers so the
// `e02_adapter_probe` C++ test can inspect the mapped crysta objects (cell / atom sites / experiment
// value·esd·free at non-trivial values) WITHOUT any public API. This header lives in core/src and is
// NEVER placed under core/include or installed; only the probe target gets core/src on its private
// include path. It is not part of edi's shipped surface (ADR-0009 keeps engine storage order private).

#include <vector>

#include "crysta/model.hpp"
#include "edi/model.hpp"

namespace edi::detail {

// Map the edi cell / atom sites / experiment to their crysta equivalents (the same functions the
// adapter uses internally). Cell + atom-site conversion is space-group-free, so a probe can drive a
// non-cubic conversion model (non-90° angle, a≠b≠c) that crysta MVP1 cannot resolve a space group for.
crysta::Cell to_crysta_cell(const Cell& cell);
std::vector<crysta::AtomSite> to_crysta_atom_sites(const ItemVec<AtomSite>& atoms);
std::vector<crysta::AtomSiteAniso> to_crysta_atom_site_aniso(const Structure& s);
crysta::BraggPdExperiment to_crysta_experiment(const ExperimentBase& experiment);

}  // namespace edi::detail

#endif  // EDI_ADAPTER_TEST_ACCESS_HPP
