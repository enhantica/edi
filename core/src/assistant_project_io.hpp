// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include "edi/io.hpp"

namespace edi::detail {
// Core-private admission for the host's already bounded, sealed native snapshot.
// Uses the actual loader; rejects generated grids BEFORE allocation, plus
// external scan/report declarations BEFORE external materialization.
Project load_assistant_project(const std::string& directory);

std::size_t relation_name_preparation_bytes(const Project&,std::size_t limit);
}
