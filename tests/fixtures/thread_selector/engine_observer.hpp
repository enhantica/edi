#pragma once
#include <cstddef>
extern "C" unsigned thread_selector_fill(std::size_t items, std::size_t chunks);
extern "C" void thread_selector_worker(unsigned fill);
extern "C" void thread_selector_reset();
extern "C" const char* thread_selector_report();
extern "C" bool thread_selector_escape(const char* name);
