// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_FULLPROF_PROJECT_IO_HPP
#define EDI_FULLPROF_PROJECT_IO_HPP

#include "edi/io.hpp"

namespace edi::detail {
std::optional<SpaceGroupSettingName> fullprof_default_space_group(const std::string& symbol);
Project import_fullprof_project(const std::string& path);
double fullprof_range_tolerance(double value);
double fullprof_powder_scale_in_native_units(const Structure& structure);

struct FullProfRelationDirection {
    const Parameter* target;
    const Parameter* source;
    double slope;
    std::string name;
};
std::vector<FullProfRelationDirection> fullprof_relation_directions(Project& model);
std::optional<double> fullprof_default_neutron_length(const std::string& type);
std::string fullprof_scattering_type(const std::string& type);
std::optional<crysta::MagneticRadialCoefficients> fullprof_magnetic_radial(const std::string& label);
std::string fullprof_signed_operator(const std::string& spatial, const std::string& moment);
std::string fullprof_inverted_operator(const std::string& operation);
struct FullProfSiteGeometry {
    std::string letter;
    std::array<double, 3> representative;
    std::array<int, 9> rotation;
    int general_multiplicity;
    int site_multiplicity;
};
FullProfSiteGeometry fullprof_site_geometry(const Structure& structure, const AtomSite& site);
std::array<double, 6> fullprof_rotated_beta(const std::array<double, 6>& beta, const std::array<int, 9>& rotation);
struct FullProfEnumeratedMoment {
    std::string ion;
    std::array<double, 3> position;
    std::array<double, 3> moment;
    std::array<double, 3> codes;
    double occupancy;
    double b_iso;
    double b_iso_code;
};
std::optional<MagneticDescription> fullprof_magnetic_overlay_group(
    const Structure& structure, const std::vector<FullProfEnumeratedMoment>& moments);
struct FullProfMagneticOperators {
    std::vector<std::string> operators;
    std::vector<std::array<double, 3>> centerings;
    std::vector<std::array<double, 3>> anti_centerings;
    bool centrosymmetric = false;
};
FullProfMagneticOperators fullprof_magnetic_operators(const Structure& structure);
crysta::MagneticGroupName fullprof_magnetic_group(const std::string& bns);
}

#endif
