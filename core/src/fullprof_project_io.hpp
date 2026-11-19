// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_FULLPROF_PROJECT_IO_HPP
#define EDI_FULLPROF_PROJECT_IO_HPP

#include "edi/io.hpp"

namespace edi::detail {
std::optional<SpaceGroupSettingName> fullprof_default_space_group(const std::string& symbol);
Project import_fullprof_project(const std::string& path);

struct FullProfRelationDirection {
    const Parameter* target;
    const Parameter* source;
    double slope;
    std::string name;
};
std::vector<FullProfRelationDirection> fullprof_relation_directions(Project& model);
std::optional<double> fullprof_default_neutron_length(const std::string& type);
std::string fullprof_scattering_type(const std::string& type);
std::string fullprof_signed_operator(const std::string& spatial, const std::string& moment);
std::string fullprof_inverted_operator(const std::string& operation);
struct FullProfMagneticOperators {
    std::vector<std::string> operators;
    bool centrosymmetric = false;
};
FullProfMagneticOperators fullprof_magnetic_operators(const Structure& structure);
crysta::MagneticGroupName fullprof_magnetic_group(const std::string& bns);
}

#endif
