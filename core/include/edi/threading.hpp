// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_THREADING_HPP
#define EDI_THREADING_HPP

namespace edi {

// Forward to the engine's shipped threading applier. The effective seam for an edi process is
// edi's package preamble (lib/edi/__init__.py), which plants OMP_WAIT_POLICY=passive and
// OMP_NUM_THREADS=max(1, visible cores - 2) as ENVIRONMENT before the compiled extension (and
// libgomp) load. Presence of any caller wait variable — any value, empty included — stands the
// whole policy down (wait AND team); a caller OMP_NUM_THREADS wins over the max-2 rule. This call,
// from the `_edi` module init, is a defensive no-op once the preamble has planted the environment;
// it is implemented in adapter.cpp, the one TU allowed to hold a crysta call (ADR-0003). See
// crysta/threading.hpp for the matrix.
void apply_engine_thread_defaults() noexcept;

// The engine's parallel fill as built, for the Develop diagnostics view: its backend ("OpenMP",
// "std::thread pool" or "serial"), the threads it runs on (the pool starts on the first call) and
// whether the engine was compiled with WebAssembly SIMD. A configuration report, not proof that a
// fill ran in parallel.
struct EngineThreading {
    const char* backend;
    int workers;
    bool wasm_simd;
};
EngineThreading engine_threading() noexcept;

// The engine's thread count for every fill, the Develop preference (crysta ADR-0063): 0 is Auto, the
// engine's policy unchanged; N >= 1 runs each fill on N threads, in place of OMP_NUM_THREADS. It never
// changes a result.
void set_engine_threads(int count) noexcept;
int engine_threads_setting() noexcept;

}  // namespace edi

#endif  // EDI_THREADING_HPP
