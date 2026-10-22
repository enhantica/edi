// Tests-only owner allocator. Never throws from or charges host hooks.
#pragma once
#include "json.hpp"
#include <cstdint>
#include <new>
#include <stdexcept>
namespace independent_fault {
inline thread_local bool enabled=false,fired=false,length=false;
inline thread_local unsigned hook_depth=0;
inline thread_local std::uint64_t seen=0,target=0;
inline thread_local edi::json::Array milestones;
struct HostHook {
    HostHook() noexcept {++hook_depth;}
    ~HostHook() noexcept {--hook_depth;}
};
inline void allocation() {
    if(!enabled || hook_depth)return;
    ++seen;
    if(target && seen==target) {
        enabled=false;fired=true;
        if(length)throw std::length_error("private one-shot encoding exhaustion");
        throw std::bad_alloc();
    }
}
inline void event(const edi::json::Value& value) {
    if(!enabled)return;
    milestones.push_back(edi::json::Object{{"type",value.at("type")},
        {"allocation_count",static_cast<double>(seen)}});
}
struct Arm {
    Arm(std::uint64_t ordinal,bool as_length) {
        enabled=false;seen=0;target=ordinal;length=as_length;fired=false;milestones.clear();
        enabled=true;
    }
    ~Arm() noexcept {enabled=false;}
};
inline edi::json::Value observation() {
    return edi::json::Object{{"fired",fired},{"seen",static_cast<double>(seen)},
        {"target",static_cast<double>(target)},{"milestones",milestones}};
}
}
