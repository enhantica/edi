// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_VERSION_HPP
#define EDI_VERSION_HPP

#include <string>

namespace edi {

// Returns the edi product-core version string. Trivial scaffold symbol (E01): it gives the
// core library a real translation unit to compile and the CLI something to call. The
// user-facing model, .edi/CIF I/O, and the crysta adapter arrive with the core in E02
// (ADR-0009); no product logic lives here yet.
std::string core_version();

// The git commit the artifact was built from: embedded at build time by
// cmake/build_commit.cmake, so a runtime witness can bind what it measured to a source sha.
// Mirrors crysta's `build_commit()`.
const char* build_commit() noexcept;

}  // namespace edi

#endif  // EDI_VERSION_HPP
