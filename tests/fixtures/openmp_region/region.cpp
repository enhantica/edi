// SPDX-License-Identifier: BSD-3-Clause
#include <omp.h>

#include <cstdint>

#ifdef _WIN32
#define OBSERVER_EXPORT __declspec(dllexport)
#else
#define OBSERVER_EXPORT
#endif

extern "C" OBSERVER_EXPORT int edi_observed_team() {
    int team = 0;
#pragma omp parallel
    {
#pragma omp single
        team = omp_get_num_threads();
    }
    return team;
}

extern "C" OBSERVER_EXPORT std::uintptr_t edi_observed_runtime() {
    return reinterpret_cast<std::uintptr_t>(&omp_get_num_threads);
}
