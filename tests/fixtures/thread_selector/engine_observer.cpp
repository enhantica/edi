#include "engine_observer.hpp"

#include <cstdlib>
#include <cstring>
#include <map>
#include <mutex>
#include <set>
#include <sstream>
#include <string>
#include <thread>
namespace {
struct Fill {
    std::size_t items, chunks;
    std::set<std::thread::id> workers;
};
std::mutex mutex;
std::map<unsigned, Fill> fills;
bool enabled = false;
unsigned sequence = 0;
std::string report;
std::thread::id owner;
}  // namespace
extern "C" unsigned thread_selector_fill(std::size_t items, std::size_t chunks) {
    std::lock_guard lock(mutex);
    if (!enabled || std::this_thread::get_id() != owner) return 0;
    const auto id = ++sequence;
    fills.emplace(id, Fill{items, chunks, {}});
    return id;
}
extern "C" void thread_selector_worker(unsigned id) {
    if (!id) return;
    std::lock_guard lock(mutex);
    fills.at(id).workers.insert(std::this_thread::get_id());
}
extern "C" void thread_selector_reset() {
    std::lock_guard lock(mutex);
    fills.clear();
    owner = std::this_thread::get_id();
    enabled = true;
}
extern "C" const char* thread_selector_report() {
    std::lock_guard lock(mutex);
    enabled = false;
    std::ostringstream out;
    out << '[';
    bool first = true;
    for (const auto& [id, fill] : fills) {
        if (!first) out << ',';
        first = false;
        out << "{\"id\":" << id << ",\"items\":" << fill.items << ",\"chunks\":" << fill.chunks
            << ",\"workers\":" << fill.workers.size() << '}';
    }
    out << ']';
    report = out.str();
    return report.c_str();
}

extern "C" bool thread_selector_escape(const char* name) {
    const char* value = std::getenv("THREAD_SELECTOR_ESCAPE");
    return value && std::strcmp(value, name) == 0;
}
