// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_FULLPROF_HPP
#define EDI_FULLPROF_HPP

#include <string>

namespace edi {

class Project;

/// Write a FullProf PCR project and measurements into a fresh directory and return the PCR path.
/// Fixed exports evaluate native relations and write a project for forward calculation.
std::string export_fullprof_project(const Project& project, const std::string& directory, bool fixed = false);

}  // namespace edi

#endif
