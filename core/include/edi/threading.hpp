// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_THREADING_HPP
#define EDI_THREADING_HPP

#include <memory>
#include <string>

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

// The engine's thread count for every fill, the Develop preference: 0 is Auto, the
// engine's policy unchanged; N >= 1 runs each fill on N threads, in place of OMP_NUM_THREADS. It never
// changes a result.
void set_engine_threads(int count) noexcept;
int engine_threads_setting() noexcept;

// How many files of a sequential or independent scan the engine fits at once, the "Parallel fits in a scan"
// preference: 1, the default, fits them one after another, each from the previous result; with more, each file of a
// group starts from where the previous group ended and runs on one thread. Below 1 is taken as 1. Unlike the thread
// count it can change a scan's results, so it is one value for the whole process, read when a scan starts.
void set_scan_workers(int count) noexcept;
int scan_workers_setting() noexcept;

// The app's one "Cores for fitting" preference: 0 is Auto, every core of the machine, N >= 1 that many. Every
// calculation runs on that many threads, and each fit spends them by its mode (apply_cores_for_mode). Until it is set,
// the two settings above are used as they are (the CLI and Python set them themselves).
void set_cores_for_fitting(int count) noexcept;
// The cores in effect, Auto resolved; 0 while the preference is unset.
int cores_for_fitting() noexcept;
// Before a fit of `mode`, once the preference is set: Independent fits that many files at once and Parametric that many
// points (ADR-0107 decision 11); Sequential, single and Joint fit one at a time, each calculation on that many threads.
void apply_cores_for_mode(const std::string& mode) noexcept;

// One fit's cores, taken from the preference and the fit's mode when the fit is asked for, so a preference or mode
// changed while it runs, or another fit's, does not change it. Zero fields: the preference is unset.
struct CoresBudget {
    int threads = 0;       // each calculation's threads
    int scan_workers = 0;  // the files or points of a scan fitted at once; 0 for a fit that is not a scan
};
CoresBudget cores_budget_for_mode(const std::string& mode) noexcept;

// Holds a budget for one fit on the calling thread: the calculation threads and the scan workers are both that thread's
// own, so another fit, here or on another thread, never changes them.
class ScopedCores {
   public:
    explicit ScopedCores(const CoresBudget& budget);
    ~ScopedCores();
    ScopedCores(const ScopedCores&) = delete;
    ScopedCores& operator=(const ScopedCores&) = delete;
    ScopedCores(ScopedCores&&) = delete;
    ScopedCores& operator=(ScopedCores&&) = delete;

   private:
    struct Held;
    std::unique_ptr<Held> held_;
};

}  // namespace edi

#endif  // EDI_THREADING_HPP
