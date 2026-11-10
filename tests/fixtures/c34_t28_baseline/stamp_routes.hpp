#pragma once

#include "holder_routes.hpp"

// The route vehicle is public; expected flags come only from the pre-move executable.
#include <array>
#include <functional>
#include <map>
#include <string>
#include <utility>
#include <vector>

#include "edi/model.hpp"

namespace c34_t28_baseline {
using Flags = std::array<bool, 3>;
inline std::map<std::string, Flags> capture(bool dependants = true) {
    using P = edi::Parameter;
    std::map<std::string, Flags> rows;
    const std::vector<std::pair<std::string, std::function<void(P&)>>> writes{
        {"value-equal", [](P& p) { p.value = p.value; }},
        {"value-changed", [](P& p) { p.value = 4.125; }},
        {"free-equal", [](P& p) { p.free = p.free; }},
        {"free-changed", [](P& p) { p.free = true; }},
        {"su-absent", [](P& p) { p.uncertainty = std::nullopt; }},
        {"su-zero", [](P& p) { p.uncertainty = 0.0; }},
        {"su-nonzero", [](P& p) { p.uncertainty = 0.031; }},
        {"fit-start",
         [](P& p) {
             p.start_value = 0.0;
             p.start_uncertainty = 0.0;
         }},
        {"fit-clear",
         [](P& p) {
             p.start_value.reset();
             p.start_uncertainty.reset();
         }},
        {"copy-assign",
         [](P& p) {
             P other(4.5);
             p = other;
         }},
        {"self-assign",
         [](P& p) {
             const auto& same = p;
             p = same;
         }},
        {"move-assign",
         [](P& p) {
             P other(4.5);
             p = std::move(other);
         }},
        {"self-move",
         [](P& p) {
             auto& same = p;
             p = std::move(same);
         }},
        {"swap",
         [](P& p) {
             P other(4.5);
             using std::swap;
             swap(p, other);
         }},
    };
    for (const auto& [name, write] : writes) {
        P p(3.25);
        const auto v = p.value.written(), e = p.epoch.value();
        write(p);
        rows[name] = {p.value.written() != v, p.epoch.value() != e, false};
    }
    P p(3.25);
    P copied(p);
    rows["copy-renews"] = {copied.value.written() != p.value.written(),
                           copied.epoch.value() != p.epoch.value(), false};
    capture_holders(rows, dependants);
    return rows;
}
}  // namespace c34_t28_baseline
