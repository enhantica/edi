// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_WINDOWS_SDK_HPP
#define EDI_WINDOWS_SDK_HPP

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
// GDI's ERROR macro must not replace the product fit-status token (ADR-0071).
#ifdef ERROR
#undef ERROR
#endif
#endif

#endif
