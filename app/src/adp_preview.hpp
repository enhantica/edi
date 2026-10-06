// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_ADP_PREVIEW_HPP
#define EDI_APP_ADP_PREVIEW_HPP

#include <array>
#include <string>

namespace edi_app {

// The Atomic displacement group's draft: the five ADP types the group offers before
// crysta computes with any but Biso. A site whose type is not Biso keeps its type and, for an anisotropic type,
// its six components here, in the app only: never saved and never used by the calculation, which goes on with the
// site's stored Biso. The conversions follow the CIF conventions (U and B tensors on the reciprocal-length-scaled
// axes, beta dimensionless) through the cell metric.

// The six components in CIF order: 11, 22, 33, 12, 13, 23.
using AdpTensor = std::array<double, 6>;

struct AdpPreview {
    std::string type;  // "Uiso", "Bani", "Uani" or "beta"
    AdpTensor ani{};   // anisotropic types only
};

// One cell, in Angstrom and degrees.
struct AdpCell {
    double a = 1.0, b = 1.0, c = 1.0, alpha = 90.0, beta = 90.0, gamma = 90.0;
};

bool is_anisotropic(const std::string& type);
// The tensor of `type` describing the isotropic displacement `b_iso` (Angstrom squared, B).
AdpTensor tensor_from_b_iso(const std::string& type, double b_iso, const AdpCell& cell);
// The tensor converted from one anisotropic type to another.
AdpTensor convert_tensor(const AdpTensor& tensor, const std::string& from, const std::string& to, const AdpCell& cell);
// The equivalent isotropic B of a tensor of `type` (Fischer and Tillmanns, 1988).
double b_equivalent(const AdpTensor& tensor, const std::string& type, const AdpCell& cell);
// The tensor as a Cartesian U matrix (row-major 3 x 3) in the frame of `cartn_matrix`, which takes fractional
// coordinates to Cartesian ones (row-major).
std::array<double, 9> cartesian_u(const AdpTensor& tensor, const std::string& type, const AdpCell& cell,
                                  const std::array<double, 9>& cartn_matrix);

}  // namespace edi_app

#endif  // EDI_APP_ADP_PREVIEW_HPP
