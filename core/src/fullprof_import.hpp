// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_FULLPROF_IMPORT_HPP
#define EDI_FULLPROF_IMPORT_HPP

#include "edi/io.hpp"

namespace edi::detail {
std::optional<SpaceGroupSettingName> fullprof_default_space_group(const std::string& symbol);
Project import_fullprof_project(const std::string& path);
}

#endif
