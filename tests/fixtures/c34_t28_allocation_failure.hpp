#pragma once

#include <cstddef>
#include <new>

// Both fault suites use the one global allocator in test_c13_t12_ownership.cpp.
// This independent countdown is armed only around a first-admission operation;
// the older ownership suite retains its own counting and persistent-failure mode.
namespace c34_t28_fault {
inline thread_local std::ptrdiff_t remaining = -1;
inline thread_local bool observing = false;
inline thread_local std::size_t largest_allocation = 0;
inline void before_allocation(std::size_t size = 0) {
    if (observing && size > largest_allocation) largest_allocation = size;
    if (remaining == 0) {
        remaining = -1;
        throw std::bad_alloc();
    }
    if (remaining > 0) --remaining;
}
}  // namespace c34_t28_fault
