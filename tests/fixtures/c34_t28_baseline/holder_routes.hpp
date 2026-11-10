#pragma once

// Public measurement vehicle. Expected bits are captured from the pre-move build,
// never computed by the live implementation during a test.
#include <array>
#include <cstdint>
#include <functional>
#include <map>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace c34_t28_baseline {
using Ticks = std::array<std::uint64_t, 3>;
using Measurements = std::map<std::string, std::array<bool, 3>>;
inline void difference(Measurements& out, const std::string& name, Ticks before, Ticks after) {
    out[name] = {before[0] != after[0], before[1] != after[1], before[2] != after[2]};
}
template <typename Make, typename Read>
void holder_routes(
    Measurements& out, const std::string& family, Make make, Read read,
    const std::vector<std::pair<std::string, std::function<void(decltype(make())&)>>>& writes) {
    using T = decltype(make());
    for (std::size_t index = 0; index < writes.size(); ++index) {
        const auto& [name, write] = writes[index];
        T value = make();
        const auto before = read(value);
        write(value);
        difference(out, family + "/" + name, before, read(value));
    }
    T value = make();
    const auto before = read(value);
    T copied(value);
    difference(out, family + "/copy-differs", before, read(copied));
    difference(out, family + "/copy-source", before, read(value));
    if constexpr (std::is_move_constructible_v<T>) {
        T moved(std::move(value));
        difference(out, family + "/move-differs", before, read(moved));
        difference(out, family + "/move-source", before, read(value));
    }
}
}  // namespace c34_t28_baseline

#include "edi/model.hpp"
#include "plain_dependants.hpp"

namespace c34_t28_baseline {
inline void capture_holders(Measurements& out, bool dependants = true) {
    if (dependants) capture_plain_dependants(out);
    // R5 preserves the old plain-member boundary. These rows observe the old
    // epochs, including equal writes and optional engagement, without inferring
    // an epoch renewal from a changed value or strengthening that contract.
    holder_routes(
        out, "plain-peak", [] { return edi::PeakBase(); },
        [](const auto& p) { return Ticks{p.epoch.value(), 0, 0}; },
        {
            {"cutoff-equal",
             [](auto& p) {
                 double& held = p.cutoff_fwhm;
                 held = 20.0;
             }},
            {"cutoff-changed", [](auto& p) { p.cutoff_fwhm = 27.5; }},
            {"selector-engage", [](auto& p) { p.type = "cwl-tch-pseudo-voigt"; }},
            {"parameter-engage", [](auto& p) { p.broad_gauss_u = edi::Parameter(0.137); }},
        });
    holder_routes(
        out, "plain-spacegroup", [] { return edi::SpaceGroup(); },
        [](const auto& p) { return Ticks{p.epoch.value(), 0, 0}; },
        {
            {"number-engage", [](auto& p) { p.it_number = 19; }},
            {"number-disengaged-equal", [](auto& p) { p.it_number.reset(); }},
        });
    holder_routes(
        out, "plain-experiment-type", [] { return edi::ExperimentType(); },
        [](const auto& p) { return Ticks{p.epoch.value(), 0, 0}; },
        {
            {"axis-engage", [](auto& p) { p.beam_mode = edi::BeamModeEnum::CONSTANT_WAVELENGTH; }},
            {"axis-disengaged-equal", [](auto& p) { p.beam_mode.reset(); }},
        });
    holder_routes(
        out, "plain-linked-structure", [] { return edi::LinkedStructure(); },
        [](const auto& p) { return Ticks{p.epoch.value(), 0, 0}; },
        {
            {"key-equal", [](auto& p) { p.structure_id = p.structure_id.value(); }},
            {"key-changed", [](auto& p) { p.structure_id = "another-structure"; }},
        });
    holder_routes(
        out, "plain-absorption", [] { return edi::AbsorptionBase(); },
        [](const auto& p) { return Ticks{p.epoch.value(), 0, 0}; },
        {
            {"selector-engage", [](auto& p) { p.type = "cylinder-hewat"; }},
            {"parameter-engage", [](auto& p) { p.mu_r = edi::Parameter(0.137); }},
        });
    holder_routes(
        out, "plain-instrument", [] { return edi::InstrumentBase(); },
        [](const auto& p) { return Ticks{p.epoch.value(), 0, 0}; },
        {
            {"wavelength-engage", [](auto& p) { p.setup_wavelength = edi::Parameter(1.54); }},
            {"wavelength-disengaged-equal", [](auto& p) { p.setup_wavelength.reset(); }},
        });
    using W = edi::detail::Written<double>;
    holder_routes(
        out, "written-number", [] { return W(3.25); },
        [](const W& value) { return Ticks{value.written(), 0, 0}; },
        {
            {"equal", [](W& p) { p = 3.25; }},
            {"changed", [](W& p) { p = 4.125; }},
            {"compound-equal", [](W& p) { p += 0.0; }},
            {"plus", [](W& p) { p += 0.125; }},
            {"minus", [](W& p) { p -= 0.125; }},
            {"multiply", [](W& p) { p *= 2.5; }},
            {"divide", [](W& p) { p /= 2.5; }},
            {"copy-assign",
             [](W& p) {
                 const W other(4.125);
                 p = other;
             }},
            {"self-assign",
             [](W& p) {
                 const auto& same = p;
                 p = same;
             }},
            {"move-assign",
             [](W& p) {
                 W other(4.125);
                 p = std::move(other);
             }},
            {"self-move",
             [](W& p) {
                 auto& same = p;
                 p = std::move(same);
             }},
            {"swap",
             [](W& p) {
                 W other(4.125);
                 using std::swap;
                 swap(p, other);
             }},
        });
    using T = edi::detail::WrittenText;
    holder_routes(
        out, "written-text", [] { return T("start"); },
        [](const T& value) { return Ticks{value.written(), 0, 0}; },
        {
            {"equal", [](T& p) { p = "start"; }},
            {"changed", [](T& p) { p = std::string("after"); }},
            {"copy-assign",
             [](T& p) {
                 const T other("after");
                 p = other;
             }},
            {"self-assign",
             [](T& p) {
                 const auto& same = p;
                 p = same;
             }},
            {"move-assign",
             [](T& p) {
                 T other("after");
                 p = std::move(other);
             }},
            {"self-move",
             [](T& p) {
                 auto& same = p;
                 p = std::move(same);
             }},
            {"swap",
             [](T& p) {
                 T other("after");
                 using std::swap;
                 swap(p, other);
             }},
        });
    using O = edi::detail::Written<std::optional<double>>;
    holder_routes(
        out, "written-optional", [] { return O(std::optional<double>(3.25)); },
        [](const O& value) { return Ticks{value.written(), 0, 0}; },
        {
            {"equal", [](O& p) { p = std::optional<double>(3.25); }},
            {"disengage", [](O& p) { p = std::optional<double>(); }},
            {"zero", [](O& p) { p = std::optional<double>(0.0); }},
            {"self-assign",
             [](O& p) {
                 const auto& same = p;
                 p = same;
             }},
        });
    using E = edi::detail::Epoch;
    holder_routes(
        out, "epoch", [] { return E(); },
        [](const E& value) { return Ticks{value.value(), 0, 0}; },
        {
            {"assign",
             [](E& p) {
                 const E other;
                 p = other;
             }},
            {"self-assign",
             [](E& p) {
                 const auto& same = p;
                 p = same;
             }},
            {"swap",
             [](E& p) {
                 E other;
                 using std::swap;
                 swap(p, other);
             }},
        });
    using K = edi::ItemVec<edi::AtomSite>;
    const auto site = [](const std::string& id) {
        auto value = std::make_shared<edi::AtomSite>();
        value->id = id;
        return value;
    };
    holder_routes(
        out, "items", [&] { return K(std::vector<K::Ptr>{site("a")}); },
        [](const K& value) {
            return Ticks{value.generation(), value.empty() ? 0 : value[0]->id.written(),
                         value.empty() ? 0 : value[0]->occupancy.value.written()};
        },
        {
            {"rename-equal", [](K& p) { p[0]->id = "a"; }},
            {"rename-changed", [](K& p) { p[0]->id = "b"; }},
            {"field-equal", [](K& p) { p[0]->occupancy.value = 1.0; }},
            {"insert", [&](K& p) { p.push_back(site("b")); }},
            {"assign-equal", [](K& p) { p.assign({p[0]}); }},
            {"replace-equal", [](K& p) { p.replace_at(0, p[0]); }},
            {"replace-changed", [&](K& p) { p.replace_at(0, site("b")); }},
            {"erase", [](K& p) { p.erase_at(0); }},
            {"clear", [](K& p) { p.clear(); }},
            {"copy-assign",
             [&](K& p) {
                 const K other(std::vector<K::Ptr>{site("b")});
                 p = other;
             }},
            {"self-assign",
             [](K& p) {
                 const auto& same = p;
                 p = same;
             }},
            {"move-assign",
             [&](K& p) {
                 K other(std::vector<K::Ptr>{site("b")});
                 p = std::move(other);
             }},
            {"self-move",
             [](K& p) {
                 auto& same = p;
                 p = std::move(same);
             }},
            {"swap",
             [&](K& p) {
                 K other(std::vector<K::Ptr>{site("b")});
                 using std::swap;
                 swap(p, other);
             }},
        });
}
}  // namespace c34_t28_baseline
