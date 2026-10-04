// SPDX-License-Identifier: BSD-3-Clause
// The ThreadSanitizer tree's negative control — two threads write one plain int with no lock.
// tools/ci/tsan-worker.sh requires the sanitizer to report it.
#include <thread>

int main() {
    int shared = 0;
    std::thread first([&shared] {
        for (int i = 0; i < 100000; ++i) {
            ++shared;
        }
    });
    std::thread second([&shared] {
        for (int i = 0; i < 100000; ++i) {
            ++shared;
        }
    });
    first.join();
    second.join();
    return shared == 0 ? 1 : 0;
}
