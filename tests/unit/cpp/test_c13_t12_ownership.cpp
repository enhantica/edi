#include <doctest/doctest.h>

#include <algorithm>
#include <functional>
#include <memory>
#include <sstream>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

#include "edi/model.hpp"

// Test-only bounded failure seam. Production never sets this thread-local state.
// All allocations outside the single operation under examination behave normally.
#include <cstdlib>
#include <new>
#include <ranges>

#include "../../fixtures/c34_t28_allocation_failure.hpp"
namespace c13_t12_fault {
thread_local long remaining = -1;
thread_local unsigned calls = 0;
thread_local bool persistent = false;
thread_local unsigned faults = 0;
void before_allocation() {
    if (remaining < 0) return;
    ++calls;
    if (remaining == 0) {
        ++faults;
        if (!persistent) remaining = -1;
        throw std::bad_alloc();
    }
    --remaining;
}
}  // namespace c13_t12_fault
void* operator new(std::size_t size) {
    c34_t28_fault::before_allocation();
    c13_t12_fault::before_allocation();
    if (void* p = std::malloc(size ? size : 1)) return p;
    throw std::bad_alloc();
}
void* operator new[](std::size_t size) { return ::operator new(size); }
void operator delete(void* p) noexcept { std::free(p); }
void operator delete[](void* p) noexcept { std::free(p); }
void operator delete(void* p, std::size_t) noexcept { std::free(p); }
void operator delete[](void* p, std::size_t) noexcept { std::free(p); }

namespace {
template <class T>
T& object(T& value) {
    return value;
}
template <class T>
T& object(const std::shared_ptr<T>& value) {
    return *value;
}
template <class T>
T& object(std::shared_ptr<T>& value) {
    return *value;
}

template <class Action>
void collision(Action action, const std::string& identity) {
    bool refused = false;
    try {
        action();
    } catch (const std::exception& error) {
        refused = true;
        CHECK_MESSAGE(std::string(error.what()).find(identity) != std::string::npos,
                      " admission refusal must name the colliding identity");
    }
    CHECK_MESSAGE(refused, " duplicate identity must refuse at its native entry");
}

//  F1: previously only ids/scalars were observed; now every populated
// movable field and both nested siblings are observed after each refused operation.
template <class P>
double number(const P& p) {
    if constexpr (requires { p.value(); })
        return p.value();
    else
        return p.value;
}
template <class P>
void set_number(P& p, double value) {
    if constexpr (requires { p.set_value(value); })
        p.set_value(value);
    else
        p.value = value;
}
template <class T>
void seed_payload(T& value, double scalar) {
    if constexpr (requires { value.target; }) {
        value.target = std::string(64, 't') + std::to_string(scalar);
        value.pattern = std::string(64, 'p') + std::to_string(scalar);
        value.required = scalar < 0.5;
    } else if constexpr (requires { value.occupancy; }) {
        set_number(value.occupancy, scalar);
        value.type_symbol = std::string(64, 's') + std::to_string(scalar);
        value.wyckoff_letter = "letter-" + std::to_string(scalar);
        value.adp_type = "type-" + std::to_string(scalar);
    } else if constexpr (requires { value.dataset_weight; }) {
        value.dataset_weight = scalar;
        value.excluded_regions =
            edi::excluded_region_rows({{scalar, scalar + 1}, {scalar + 2, scalar + 3}});
        value.excluded_regions[0]->id = "low-" + std::to_string(scalar);
        value.excluded_regions[1]->id = "high-" + std::to_string(scalar);
        if constexpr (requires { value.peak.push_back(value.scale); }) {
            value.peak.push_back(value.scale);
            value.instrument.push_back(value.scale);
            set_number(value.peak.back(), scalar);
            set_number(value.instrument.back(), scalar + 1);
            value.background.push_back({scalar, value.scale});
            value.preferred_orientation = {value.scale, value.scale};
            value.linked_structure_id = std::string(64, 'l');
            value.preferred_orientation_structure_id = std::string(64, 'o');
            value.data.grid = {scalar, scalar + 1};
            value.data.intensity = {scalar + 2, scalar + 3};
            value.data.sigma = {1, 2};
        } else {
            using Row = typename std::remove_reference_t<
                decltype(value.preferred_orientation)>::Ptr::element_type;
            Row a, b;
            a.structure_id = "child-a";
            b.structure_id = "child-b";
            set_number(a.march_r, scalar);
            set_number(b.march_r, scalar + 1);
            value.preferred_orientation.push_back(a);
            value.preferred_orientation.push_back(b);
            using Anchor =
                typename std::remove_reference_t<decltype(value.background)>::Ptr::element_type;
            Anchor anchor;
            anchor.position = scalar;
            set_number(anchor.intensity, scalar + 1);
            value.background.push_back(anchor);
            value.data.emplace();
            value.data->two_theta = std::vector<double>{scalar, scalar + 1};
            value.data->intensity_meas = {scalar + 2, scalar + 3};
            value.data->intensity_meas_su = {1, 2};
        }
    } else if constexpr (requires { value.march_r; }) {
        set_number(value.march_r, scalar);
        set_number(value.march_random_fract, scalar / 2);
        value.index_h = 2;
        value.index_k = -3;
        value.index_l = 4;
    } else {
        set_number(value.cell.length_a, scalar);
        using Site =
            typename std::remove_reference_t<decltype(value.atom_sites)>::Ptr::element_type;
        Site a, b;
        a.id = "child-a";
        b.id = "child-b";
        seed_payload(a, scalar);
        seed_payload(b, scalar + 1);
        value.atom_sites.push_back(a);
        value.atom_sites.push_back(b);
        value.scattering_lengths_fm = {{"O", scalar}, {"Ca", scalar + 1}};
    }
}
template <class T>
std::string payload(T& value) {
    std::ostringstream out;
    out << std::hexfloat;
    if constexpr (requires { value.target; }) {
        out << value.target << '|' << value.pattern << '|' << value.required;
    } else if constexpr (requires { value.occupancy; }) {
        out << number(value.occupancy) << '|' << value.type_symbol << '|' << value.wyckoff_letter
            << '|' << value.adp_type;
    } else if constexpr (requires { value.dataset_weight; }) {
        out << value.dataset_weight << '|';
        for (const auto& row : value.excluded_regions)
            out << row->id.value() << ':' << row->first.get() << ':' << row->second.get() << '|';
        if constexpr (requires { value.peak.begin(); }) {
            for (auto& p : value.peak) out << number(p) << '|';
            for (auto& p : value.instrument) out << number(p) << '|';
            for (auto& p : value.background)
                out << p.position << ':' << number(p.intensity) << '|';
            for (auto& p : value.preferred_orientation) out << number(p) << '|';
            out << value.linked_structure_id << '|' << value.preferred_orientation_structure_id
                << '|';
            for (auto v : value.data.grid) out << v << '|';
            for (auto v : value.data.intensity) out << v << '|';
            for (auto v : value.data.sigma) out << v << '|';
        } else {
            for (auto& p : value.background)
                out << p->position << ':' << number(p->intensity) << '|';
            for (auto& p : value.preferred_orientation)
                out << p->structure_id << ':' << payload(*p) << '|';
            out << value.data.has_value() << '|';
            if (value.data) {
                for (auto v : *value.data->two_theta) out << v << '|';
                for (auto v : value.data->intensity_meas) out << v << '|';
                for (auto v : value.data->intensity_meas_su) out << v << '|';
            }
        }
    } else if constexpr (requires { value.march_r; }) {
        out << number(value.march_r) << '|' << number(value.march_random_fract) << '|'
            << value.index_h << '|' << value.index_k << '|' << value.index_l;
    } else {
        out << number(value.cell.length_a) << '|';
        for (auto& site : value.atom_sites) out << site->id << ':' << payload(*site) << '|';
        for (auto& [key, v] : value.scattering_lengths_fm) out << key << ':' << v << '|';
    }
    return out.str();
}
template <class T>
std::vector<const void*> child_addresses(T& value) {
    std::vector<const void*> result;
    if constexpr (requires { value.atom_sites; })
        for (auto& item : value.atom_sites) result.push_back(&object(item));
    else if constexpr (requires { value.preferred_orientation[0]->structure_id; })
        for (auto& item : value.preferred_orientation) result.push_back(&object(item));
    return result;
}
template <class T>
void child_membership(T& value) {
    if constexpr (requires { value.atom_sites; }) {
        REQUIRE_MESSAGE(value.atom_sites.size() == 2,
                        " refused mutation preserves populated child storage");
        collision([&] { value.atom_sites[1]->id = "child-a"; }, "child-a");
        CHECK_MESSAGE(value.atom_sites[1]->id == "child-b",
                      " refused child rename preserves nested membership");
    } else if constexpr (requires { value.preferred_orientation[0]->structure_id; }) {
        REQUIRE_MESSAGE(value.preferred_orientation.size() == 2,
                        " refused mutation preserves nested texture rows");
        collision([&] { value.preferred_orientation[1]->structure_id = "child-a"; }, "child-a");
        CHECK_MESSAGE(value.preferred_orientation[1]->structure_id == "child-b",
                      " nested texture membership survives refusal");
    }
}

template <class Collection, class Key>
void ownership(Collection initial, Key key) {
    Collection items = initial;
    seed_payload(object(items[0]), 0.17);
    seed_payload(object(items[1]), 0.93);
    const auto original_payload = payload(object(items[0]));
    auto names = [&]() {
        std::vector<std::string> result;
        for (auto& stored : items) result.emplace_back(key(object(stored)));
        return result;
    };
    const auto before = names();
    REQUIRE_MESSAGE(before.size() == 2, " native witness needs two distinct keyed members");
    SUBCASE("string assignment") {
        collision([&] { key(object(items[1])) = before[0]; }, before[0]);
        CHECK_MESSAGE(names() == before, " refused direct key write is atomic");
        key(object(items[1])) = "unique-control";
        CHECK_MESSAGE(std::string(key(object(items[1]))) == "unique-control",
                      " attached unique rename must remain available");
    }
    SUBCASE("whole item copy before scalar payload") {
        collision([&] { object(items[0]) = object(items[1]); }, before[1]);
        CHECK_MESSAGE(names() == before, " refused whole-item assignment preserves both keys");
        CHECK_MESSAGE(payload(object(items[0])) == original_payload,
                      " refused whole-item assignment changes no scalar payload");
    }
    SUBCASE("bulk assignment and old membership") {
        auto first = items[0];
        collision([&] { items.assign({first, first}); }, before[0]);
        CHECK_MESSAGE(names() == before, " failed bulk admission preserves original storage");
        collision([&] { key(object(items[1])) = before[0]; }, before[0]);
        CHECK_MESSAGE(names() == before, " failed bulk admission retains original membership");
    }
    SUBCASE("deep collection copy") {
        Collection copy(items);
        key(object(items[0])) = "source-only";
        CHECK_MESSAGE(std::string(key(object(copy[0]))) == before[0],
                      " collection copies own independent item identities");
        collision([&] { key(object(copy[1])) = before[0]; }, before[0]);
    }
    SUBCASE("collection move retargets membership") {
        Collection moved(std::move(items));
        collision([&] { key(object(moved[1])) = before[0]; }, before[0]);
        items = std::move(moved);
        collision([&] { key(object(items[1])) = before[0]; }, before[0]);
    }
    SUBCASE("moving attached item retains source membership") {
        auto detached(std::move(object(items[0])));
        CHECK_MESSAGE(names() == before, " moving an attached item leaves its source key intact");
        key(detached) = before[1];
        collision([&] { key(object(items[0])) = before[1]; }, before[1]);
    }
}

template <class Collection, class Key>
void refused_moves(Collection items, Key key) {
    seed_payload(object(items[0]), 0.17);
    seed_payload(object(items[1]), 0.93);
    const std::vector<std::string> before{std::string(key(object(items[0]))),
                                          std::string(key(object(items[1])))};
    const auto original_payload = payload(object(items[0]));
    const auto sibling_payload = payload(object(items[1]));
    const auto first_children = child_addresses(object(items[0]));
    const auto second_children = child_addresses(object(items[1]));
    // Before: swap asserted ids only. After: all refused move entries preserve
    // both populated payloads, parent membership, and nested keyed memberships.
    SUBCASE("swap siblings is checked and atomic") {
        collision([&] { std::swap(object(items[0]), object(items[1])); }, before[1]);
    }
    SUBCASE("iter swap exposed sibling objects is atomic") {
        auto* first = &object(items[0]);
        auto* second = &object(items[1]);
        collision([&] { std::iter_swap(first, second); }, before[1]);
    }
    SUBCASE("move based algorithm refuses before draining a sibling") {
        auto* first = &object(items[0]);
        auto* second = &object(items[1]);
        collision([&] { std::move(first, first + 1, second); }, before[0]);
    }
    SUBCASE("rotate exposed objects refuses atomically") {
        auto values =
            items | std::views::transform([](auto& item) -> auto& { return object(item); });
        collision([&] { std::rotate(values.begin(), values.begin() + 1, values.end()); },
                  before[1]);
    }
    SUBCASE("sort exposed objects refuses atomically") {
        auto values =
            items | std::views::transform([](auto& item) -> auto& { return object(item); });
        collision(
            [&] {
                std::sort(values.begin(), values.end(), [&](auto& a, auto& b) {
                    return std::string(key(a)) > std::string(key(b));
                });
            },
            before[0]);
    }
    SUBCASE("append moved sibling refuses without draining its argument") {
        collision([&] { items.push_back(std::move(object(items[0]))); }, before[0]);
    }

    REQUIRE_MESSAGE(items.size() == 2, " refused move preserves collection size");
    CHECK_MESSAGE((std::string(key(object(items[0]))) == before[0] &&
                   std::string(key(object(items[1]))) == before[1]),
                  " refused move preserves both identities");
    CHECK_MESSAGE((payload(object(items[0])) == original_payload &&
                   payload(object(items[1])) == sibling_payload),
                  " refused move preserves every populated string vector and nested payload");
    collision([&] { key(object(items[1])) = before[0]; }, before[0]);
    CHECK_MESSAGE(std::string(key(object(items[1]))) == before[1],
                  " refused move retains parent membership");
    CHECK_MESSAGE((child_addresses(object(items[0])) == first_children &&
                   child_addresses(object(items[1])) == second_children),
                  " refused move preserves the identities of already held nested children");
    child_membership(object(items[0]));
    child_membership(object(items[1]));
}

template <class Stored>
auto detached_value(const Stored& stored) {
    if constexpr (requires { typename Stored::element_type; })
        return std::make_shared<typename Stored::element_type>(*stored);
    else
        return stored;
}
template <class Collection, class Key>
auto contents(Collection& items, Key key) {
    std::vector<std::pair<std::string, std::string>> result;
    for (auto& item : items)
        result.emplace_back(std::string(key(object(item))), payload(object(item)));
    return result;
}
template <class Collection, class Key>
void checked_members(Collection& items, Key key) {
    for (std::size_t i = 0; i < items.size(); ++i) {
        CHECK_MESSAGE(key(object(items[i])).attached(),
                      " allocation refusal leaves no stored item detached");
        if (items.size() > 1) {
            const auto original = std::string(key(object(items[i])));
            const auto sibling = std::string(key(object(items[(i + 1) % items.size()])));
            collision([&] { key(object(items[i])) = sibling; }, sibling);
            CHECK_MESSAGE(std::string(key(object(items[i]))) == original,
                          " post-allocation-failure sibling rename remains checked and atomic");
        }
        child_membership(object(items[i]));
    }
}
template <class Collection, class Key>
void allocation_commit_points(Collection initial, Key key, int first, int last) {
    for (auto& item : initial) seed_payload(object(item), 0.37);
    // Before: only duplicate-id failures. After: fail every allocation reached by
    // insertion into fresh/moved-from/populated targets, bulk admission and owner copy.
    for (int mode = first; mode != last; ++mode) {
        INFO("allocation commit entry ", mode);
        bool completed = false;
        unsigned failures = 0;
        for (long fail_at = 0; fail_at < 512; ++fail_at) {
            Collection target;
            Collection moved_storage;
            if (mode == 2 || mode == 5 || mode == 7) {
                target = initial;
                moved_storage = std::move(target);
            } else if (mode == 3 || mode == 6 || mode == 8)
                target = initial;
            Collection source(initial);
            // Force element-reusing owner copy to allocate after admission too:
            // equal-size source/target strings would never reach that commit edge.
            key(object(source[0])) = std::string(256, 'a');
            key(object(source[1])) = std::string(256, 'b');
            using Stored = std::remove_cvref_t<decltype(source[0])>;
            std::vector<Stored> incoming;
            for (auto& item : source) incoming.push_back(detached_value(item));
            key(object(incoming[0])) = "incoming-a";
            key(object(incoming[1])) = "incoming-b";
            const auto before = contents(target, key);
            std::vector<const void*> old_addresses;
            for (auto& item : target) old_addresses.push_back(&object(item));
            const auto source_before = contents(source, key);
            const auto moved_before = contents(moved_storage, key);
            std::vector<Stored> held;
            if constexpr (requires { typename Stored::element_type; })
                for (auto& item : target) held.push_back(item);
            bool failed = false;
            c13_t12_fault::remaining = fail_at;
            c13_t12_fault::calls = 0;
            try {
                if (mode == 0 || mode >= 7)
                    target.push_back(incoming[0]);
                else if (mode <= 3)
                    target.assign(incoming);
                else
                    target = source;
            } catch (const std::bad_alloc&) {
                failed = true;
            } catch (...) {
                c13_t12_fault::remaining = -1;
                throw;
            }
            c13_t12_fault::remaining = -1;
            if (failed) {
                ++failures;
                std::vector<const void*> remaining_addresses;
                for (auto& item : target) remaining_addresses.push_back(&object(item));
                CHECK_MESSAGE(remaining_addresses == old_addresses,
                              " allocation rollback preserves existing stored object "
                              "lifetimes and addresses");
                CHECK_MESSAGE(
                    contents(target, key) == before,
                    " each allocation failure preserves complete previous target storage");
                for (auto& old : held)
                    CHECK_MESSAGE(key(object(old)).attached(),
                                  " allocation refusal preserves retained old-item ownership");
            } else
                completed = true;
            CHECK_MESSAGE(contents(source, key) == source_before,
                          " owner-copy allocation failure cannot change the source");
            CHECK_MESSAGE(contents(moved_storage, key) == moved_before,
                          " moved-from admission cannot alter the new owner");
            checked_members(target, key);
            checked_members(source, key);
            checked_members(moved_storage, key);
            if (completed) break;
        }
        CHECK_MESSAGE(failures > 0, " each allocation witness actually injects a failure");
        CHECK_MESSAGE(completed, " bounded allocation sweep reaches the successful control");
    }
}

// Review-6 F1 before: a single fault made recovery infallible and erase was absent.
// After: every allocation from the chosen point fails, including restoration;
// old keys exceed small-string storage and ORIGINAL objects/held refs must survive.
template <class Collection, class Key>
void persistent_recovery(Collection initial, Key key, bool erase) {
    for (std::size_t i = 0; i < initial.size(); ++i) {
        key(object(initial[i])) = std::string(128, static_cast<char>('a' + i));
        seed_payload(object(initial[i]), 0.37 + i);
    }
    bool completed = false;
    unsigned failed_operations = 0;
    for (long fail_at = 0; fail_at < 1024; ++fail_at) {
        INFO("persistent allocation point ", fail_at, " erase=", erase);
        Collection target(initial), source(initial);
        for (std::size_t i = 0; i < source.size(); ++i) {
            key(object(source[i])) = std::string(512, static_cast<char>('x' + i));
        }
        const auto before = contents(target, key);
        const auto source_before = contents(source, key);
        using Value = std::remove_reference_t<decltype(object(target[0]))>;
        std::vector<std::reference_wrapper<Value>> held;
        std::vector<const void*> old_addresses;
        for (auto& item : target) {
            held.emplace_back(object(item));
            old_addresses.push_back(&object(item));
        }
        bool failed = false;
        c13_t12_fault::persistent = true;
        c13_t12_fault::faults = 0;
        c13_t12_fault::calls = 0;
        c13_t12_fault::remaining = fail_at;
        try {
            if (erase) {
                if constexpr (requires { target.erase_at(0); })
                    target.erase_at(0);
                else
                    target.erase(target.begin());
            } else
                target = source;
        } catch (const std::bad_alloc&) {
            failed = true;
        } catch (...) {
            c13_t12_fault::remaining = -1;
            c13_t12_fault::persistent = false;
            throw;
        }
        // Observations may allocate; they begin only AFTER injection is disarmed.
        c13_t12_fault::remaining = -1;
        c13_t12_fault::persistent = false;
        if (failed) {
            ++failed_operations;
            CHECK_MESSAGE(c13_t12_fault::faults > 0,
                          " persistent refusal reaches the allocation vehicle");
            std::vector<const void*> addresses;
            for (auto& item : target) addresses.push_back(&object(item));
            CHECK_MESSAGE(addresses == old_addresses,
                          " persistent copy or erase failure preserves ORIGINAL object lifetimes");
            CHECK_MESSAGE(contents(target, key) == before,
                          " persistent copy or erase failure preserves complete old payload");
            // A failed lifetime assertion must not dereference a dangling witness.
            if (addresses == old_addresses) {
                for (std::size_t i = 0; i < held.size(); ++i) {
                    CHECK_MESSAGE(std::string(key(held[i].get())) == before[i].first,
                                  " held reference still reads its original long identity "
                                  "after persistent failure");
                    CHECK_MESSAGE(payload(held[i].get()) == before[i].second,
                                  " held reference still reads its populated payload after "
                                  "persistent failure");
                    CHECK_MESSAGE(key(held[i].get()).attached(),
                                  " held reference retains checked owner membership after "
                                  "persistent failure");
                }
                checked_members(target, key);
            }
        } else {
            completed = true;
            auto expected = erase ? before : source_before;
            if (erase) expected.erase(expected.begin());
            CHECK_MESSAGE(contents(target, key) == expected,
                          " successful persistent-fault control performs the complete "
                          "requested copy or erase");
        }
        CHECK_MESSAGE(contents(source, key) == source_before,
                      " persistent failure cannot alter the copied source owner");
        if (completed) break;
    }
    // Before: crysta erase had to allocate/fail. After: a no-allocation erase
    // is a valid stronger repair; its complete success state is checked above.
    // Populated copy must still exercise faults, and every actual failure keeps
    // the original lifetime/payload/reference assertions unchanged.
    if (!erase) {
        CHECK_MESSAGE(failed_operations > 0,
                      " populated owner copy executes injected persistent failures");
    } else if (failed_operations == 0) {
        CHECK_MESSAGE(c13_t12_fault::calls == 0,
                      " erase without an injected failure must prove no allocation was attempted");
    }
    CHECK_MESSAGE(completed, " persistent sweep also reaches a successful operation control");
}

// Review-6 F2 before: named-refusal witnesses used ordinary ASCII identities.
// After: NUL, controls and UTF-8 remain legal in memory and are named printably.
std::vector<std::pair<std::string, std::string>> diagnostic_ids() {
    return {{std::string("\0tail", 5), "\\x00tail"},
            {"head\x01tail", "head\\x01tail"},
            {"line\nend", "line\\x0Aend"},
            {"b\xc3\xa4\tend", "b\xc3\xa4\\x09end"},
            {"del\x7f"
             "end",
             "del\\x7Fend"}};
}
template <class Action>
void printable_collision(Action action, const std::string& expected) {
    bool refused = false;
    try {
        action();
    } catch (const std::exception& error) {
        refused = true;
        const std::string message(error.what());
        CHECK_MESSAGE(message.find(expected) != std::string::npos,
                      " arbitrary identity refusal preserves the complete printable id "
                      "including suffix");
        CHECK_MESSAGE(std::none_of(message.begin(), message.end(),
                                   [](unsigned char ch) { return ch < 32 || ch == 127; }),
                      " identity refusal contains no raw control bytes");
    }
    CHECK_MESSAGE(refused, " arbitrary in-memory duplicate still refuses at the chosen entry");
}
template <class Collection, class Key>
void arbitrary_id_entries(Collection initial, Key key) {
    for (auto& item : initial) seed_payload(object(item), 0.37);
    for (const auto& [id, expected] : diagnostic_ids()) {
        Collection items(initial);
        key(object(items[0])) = id;
        const auto before = contents(items, key);
        CHECK_MESSAGE(std::string(key(object(items[0]))) == id,
                      " unique arbitrary bytes remain accepted unchanged in memory");
        auto distinct = detached_value(items[0]);
        printable_collision([&] { items.push_back(distinct); }, expected);
        printable_collision([&] { key(object(items[1])) = id; }, expected);
        using Stored = std::remove_cvref_t<decltype(items[0])>;
        std::vector<Stored> duplicates{detached_value(items[0]), detached_value(items[0])};
        printable_collision([&] { items.assign(duplicates); }, expected);
        if constexpr (requires { typename Stored::element_type; }) {
            printable_collision([&] { items.push_back(items[0]); }, expected);
            printable_collision([&] { items.assign({items[0], items[0]}); }, expected);
            Collection foreign;
            printable_collision([&] { foreign.push_back(items[0]); }, expected);
            CHECK_MESSAGE(foreign.empty(),
                          " named foreign-owner refusal preserves the empty destination");
        }
        CHECK_MESSAGE(contents(items, key) == before,
                      " all arbitrary-id refusal entries preserve original ids and payload");
        CHECK_MESSAGE((key(object(items[0])).attached() && key(object(items[1])).attached()),
                      " arbitrary-id refusal retains both original memberships");
    }
}

template <class K>
constexpr bool mutable_character = requires(K& key) { key[0] = 'Z'; };
template <class C>
constexpr bool reseatable_slot =
    requires(C& items, typename C::Ptr pointer) { items[0] = pointer; };
template <class C>
constexpr bool reseatable_iterator =
    requires(C& items, typename C::Ptr pointer) { *items.begin() = pointer; };
template <class K>
void no_raw_key_escape() {
    CHECK_MESSAGE((!std::is_convertible_v<K&, std::string&>),
                  " no mutable string reference may escape a key");
    CHECK_MESSAGE(!mutable_character<K>, " character writes cannot bypass collection admission");
}
}  // namespace

namespace {
template <class T, class Key>
edi::ItemVec<T> pair(Key key) {
    edi::ItemVec<T> result;
    T a, b;
    key(a) = "first";
    key(b) = "second";
    result.push_back(a);
    result.push_back(b);
    return result;
}
template <class T, class Key>
void lifecycle(Key key) {
    auto items = pair<T>(key);
    auto held = items[0];
    auto sibling = items[1];
    SUBCASE("shared live ownership refused") {
        edi::ItemVec<T> other;
        collision([&] { other.push_back(held); }, "first");
        CHECK_MESSAGE(other.empty(), " failed shared admission cannot partially attach storage");
    }
    SUBCASE("erase detaches") {
        items.erase_at(0);
        key(*held) = "second";
    }
    SUBCASE("clear detaches") {
        items.clear();
        key(*held) = "second";
    }
    SUBCASE("destroy owner detaches") {
        {
            auto owner = pair<T>(key);
            held = owner[0];
        }
        key(*held) = "second";
    }
    SUBCASE("failed bulk retains all links") {
        collision([&] { items.assign({held, held}); }, "first");
        collision([&] { key(*sibling) = "first"; }, "first");
    }
    CHECK_MESSAGE((!std::is_constructible_v<edi::ItemVec<T>, std::size_t>),
                  " keyed counted construction must be unspellable");
    CHECK_MESSAGE(!reseatable_slot<edi::ItemVec<T>>,
                  " a shared pointer slot cannot bypass storage admission");
    CHECK_MESSAGE(!reseatable_iterator<edi::ItemVec<T>>,
                  " a pointer iterator cannot reseat keyed storage");
    no_raw_key_escape<std::remove_reference_t<decltype(key(*held))>>();
}
}  // namespace
#define C13_KEYED_CASE(TYPE, KEY, LABEL)                           \
    TEST_CASE("C13-T12 native " LABEL " admission and lifetime") { \
        auto key = [](auto& item) -> auto& { return item.KEY; };   \
        ownership(pair<TYPE>(key), key);                           \
        refused_moves(pair<TYPE>(key), key);                       \
        lifecycle<TYPE>(key);                                      \
    }
C13_KEYED_CASE(edi::AtomSite, id, "atom sites")
C13_KEYED_CASE(edi::Structure, name, "structures")
C13_KEYED_CASE(edi::BraggPdExperiment, name, "experiments")
C13_KEYED_CASE(edi::PrefOrient, structure_id, "preferred orientation")
C13_KEYED_CASE(edi::SequentialExtractRule, id, "extract rules")
#undef C13_KEYED_CASE

TEST_CASE("C13-T12 actual model members use the checked keyed storage") {
    CHECK_MESSAGE((std::is_same_v<decltype(std::declval<edi::Structure&>().atom_sites),
                                  edi::ItemVec<edi::AtomSite>>),
                  " actual atom-site storage must use the checked collection");
    CHECK_MESSAGE((std::is_same_v<decltype(std::declval<edi::Project&>().structures),
                                  edi::ItemVec<edi::Structure>>),
                  " actual structure storage must use the checked collection");
    CHECK_MESSAGE((std::is_same_v<decltype(std::declval<edi::Project&>().experiments),
                                  edi::ItemVec<edi::BraggPdExperiment>>),
                  " actual experiment storage must use the checked collection");
    CHECK_MESSAGE(
        (std::is_same_v<decltype(std::declval<edi::BraggPdExperiment&>().preferred_orientation),
                        edi::ItemVec<edi::PrefOrient>>),
        " actual orientation storage must use the checked collection");
    CHECK_MESSAGE((std::is_same_v<decltype(std::declval<edi::SequentialFitConfig&>().extract),
                                  edi::ItemVec<edi::SequentialExtractRule>>),
                  " actual extract-rule storage must use the checked collection");
}

TEST_CASE("C13-T12 native Project and Structure copies reattach every keyed member") {
    edi::Project source;
    source.structures = pair<edi::Structure>([](auto& value) -> auto& { return value.name; });
    source.experiments =
        pair<edi::BraggPdExperiment>([](auto& value) -> auto& { return value.name; });
    source.structures.front()->atom_sites =
        pair<edi::AtomSite>([](auto& value) -> auto& { return value.id; });
    edi::Project copy(source);
    source.structures.front()->atom_sites[0]->id = "source-only";
    CHECK_MESSAGE(std::string(copy.structures.front()->atom_sites[0]->id) == "first",
                  " copied Project retains independent site identities");
    collision([&] { copy.structures.front()->atom_sites[1]->id = "first"; }, "first");
    collision([&] { copy.structures[1]->name = "first"; }, "first");
    collision([&] { copy.experiments[1]->name = "first"; }, "first");
    edi::Structure structure(*copy.structures.front());
    collision([&] { structure.atom_sites[1]->id = "first"; }, "first");
    edi::Project assigned;
    assigned = source;
    collision([&] { assigned.structures.front()->atom_sites[1]->id = "source-only"; },
              "source-only");
    edi::Project moved(std::move(assigned));
    collision([&] { moved.experiments[1]->name = "first"; }, "first");
}

#include <chrono>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <map>

#include "edi/io.hpp"

TEST_CASE("C13-T12 native edi extract ids cross the delegated save domain seam") {
    namespace fs = std::filesystem;
    const auto root =
        fs::temp_directory_path() /
        ("-edi-extract-" +
         std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    struct Cleanup {
        fs::path path;
        ~Cleanup() {
            std::error_code ignored;
            fs::remove_all(path, ignored);
        }
    } cleanup{root};
    const auto fixture = fs::path(__FILE__).parent_path().parent_path().parent_path() /
                         "fixtures/c13_t4_march/model.edi";
    std::ifstream input(fixture);
    REQUIRE_MESSAGE(input.good(), " edi native save requires its committed vehicle");
    const std::string text((std::istreambuf_iterator<char>(input)), {});
    const auto at = text.find("data_experiment");
    fs::create_directories(root / "input/structures");
    fs::create_directories(root / "input/experiments");
    fs::create_directories(root / "input/scan");
    std::ofstream(root / "input/structures/structure.edi") << text.substr(0, at);
    std::ofstream(root / "input/experiments/experiment.edi")
        << text.substr(at)
        << "\nloop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n45 2 1\n46 3 "
           "1\n";
    std::ofstream(root / "input/scan/point.txt") << "TEMP 123\n";
    auto project = edi::load_project((root / "input").string());
    project.sequential_fit.data_dir = "scan";
    edi::SequentialExtractRule rule;
    rule.id = "valid-rule";
    rule.target = "temperature";
    rule.pattern = "(.*)";
    project.sequential_fit.extract.push_back(rule);
    edi::save_project(project, (root / "control").string());
    const auto snapshot = [&]() {
        std::map<std::string, std::string> result;
        for (const auto& entry : fs::recursive_directory_iterator(root)) {
            if (!entry.is_regular_file()) continue;
            std::ifstream stream(entry.path(), std::ios::binary);
            result.emplace(fs::relative(entry.path(), root).string(),
                           std::string((std::istreambuf_iterator<char>(stream)), {}));
        }
        return result;
    };
    const auto before = snapshot();
    // Before: required raw control bytes in what(). After: require their
    // literal escaped identity spelling, while preserving the no-publication check.
    for (const auto& [bad, named_id] :
         std::vector<std::pair<std::string, std::string>>{{"bad\nid", "bad\\x0Aid"},
                                                          {"bad\rid", "bad\\x0Did"},
                                                          {"bad\x01id", "bad\\x01id"},
                                                          {"bad\x7f"
                                                           "id",
                                                           "bad\\x7Fid"},
                                                          {"b\xc3\xa4"
                                                           "d",
                                                           "b\xc3\xa4"
                                                           "d"},
                                                          {"a' b\" c", "a' b\" c"}}) {
        object(project.sequential_fit.extract[0]).id = bad;
        collision([&] { edi::save_project(project, (root / "control").string()); }, named_id);
        CHECK_MESSAGE(snapshot() == before,
                      " edi adapter must refuse invalid extract ids before publishing any bytes");
    }
}

TEST_CASE("C13-T12 allocation failure is atomic for native sites initial admissions") {
    auto key = [](auto& x) -> auto& { return x.id; };
    allocation_commit_points(pair<edi::AtomSite>(key), key, 0, 3);
}
TEST_CASE("C13-T12 allocation failure is atomic for native sites replacement and copy") {
    auto key = [](auto& x) -> auto& { return x.id; };
    allocation_commit_points(pair<edi::AtomSite>(key), key, 3, 6);
}
TEST_CASE("C13-T12 allocation failure is atomic for native sites copy and insertion") {
    auto key = [](auto& x) -> auto& { return x.id; };
    allocation_commit_points(pair<edi::AtomSite>(key), key, 6, 9);
}
TEST_CASE("C13-T12 allocation failure is atomic for native structures initial admissions") {
    auto key = [](auto& x) -> auto& { return x.name; };
    allocation_commit_points(pair<edi::Structure>(key), key, 0, 3);
}
TEST_CASE("C13-T12 allocation failure is atomic for native structures replacement and copy") {
    auto key = [](auto& x) -> auto& { return x.name; };
    allocation_commit_points(pair<edi::Structure>(key), key, 3, 6);
}
TEST_CASE("C13-T12 allocation failure is atomic for native structures copy and insertion") {
    auto key = [](auto& x) -> auto& { return x.name; };
    allocation_commit_points(pair<edi::Structure>(key), key, 6, 9);
}
TEST_CASE("C13-T12 allocation failure is atomic for native experiments initial admissions") {
    auto key = [](auto& x) -> auto& { return x.name; };
    allocation_commit_points(pair<edi::BraggPdExperiment>(key), key, 0, 3);
}
TEST_CASE("C13-T12 allocation failure is atomic for native experiments replacement and copy") {
    auto key = [](auto& x) -> auto& { return x.name; };
    allocation_commit_points(pair<edi::BraggPdExperiment>(key), key, 3, 6);
}
TEST_CASE("C13-T12 allocation failure is atomic for native experiments copy and insertion") {
    auto key = [](auto& x) -> auto& { return x.name; };
    allocation_commit_points(pair<edi::BraggPdExperiment>(key), key, 6, 9);
}
TEST_CASE("C13-T12 allocation failure is atomic for native orientation initial admissions") {
    auto key = [](auto& x) -> auto& { return x.structure_id; };
    allocation_commit_points(pair<edi::PrefOrient>(key), key, 0, 3);
}
TEST_CASE("C13-T12 allocation failure is atomic for native orientation replacement and copy") {
    auto key = [](auto& x) -> auto& { return x.structure_id; };
    allocation_commit_points(pair<edi::PrefOrient>(key), key, 3, 6);
}
TEST_CASE("C13-T12 allocation failure is atomic for native orientation copy and insertion") {
    auto key = [](auto& x) -> auto& { return x.structure_id; };
    allocation_commit_points(pair<edi::PrefOrient>(key), key, 6, 9);
}
TEST_CASE("C13-T12 allocation failure is atomic for native extract rules initial admissions") {
    auto key = [](auto& x) -> auto& { return x.id; };
    allocation_commit_points(pair<edi::SequentialExtractRule>(key), key, 0, 3);
}
TEST_CASE("C13-T12 allocation failure is atomic for native extract rules replacement and copy") {
    auto key = [](auto& x) -> auto& { return x.id; };
    allocation_commit_points(pair<edi::SequentialExtractRule>(key), key, 3, 6);
}
TEST_CASE("C13-T12 allocation failure is atomic for native extract rules copy and insertion") {
    auto key = [](auto& x) -> auto& { return x.id; };
    allocation_commit_points(pair<edi::SequentialExtractRule>(key), key, 6, 9);
}

#include "crysta/identity.hpp"
TEST_CASE("C13-T12 every writer family reaches the shared encoder domain") {
    const std::vector<std::pair<std::string, std::string>> bad{{"bad\nid", "0x0A"},
                                                               {"bad\rid", "0x0D"},
                                                               {std::string("bad\0id", 6), "0x00"},
                                                               {"bad\x01id", "0x01"},
                                                               {"bad\x7f"
                                                                "id",
                                                                "0x7F"},
                                                               {"b\xc3\xa4"
                                                                "d",
                                                                "0xC3"},
                                                               {"a' b\" c", "quot"}};
    for (const auto& category :
         {"atom site", "scattering length", "linked structure", "preferred orientation",
          "sequential-fit extract rule", "experiment", "fit-state row"}) {
        for (const auto& [value, diagnostic] : bad) {
            INFO(category, " ", diagnostic);
            bool refused = false;
            try {
                (void)crysta::encode_id(value, category);
            } catch (const std::invalid_argument& error) {
                refused = true;
                const std::string message(error.what());
                CHECK_MESSAGE(message.find(category) != std::string::npos,
                              " encoder refusal names the family that reached it");
                CHECK_MESSAGE(message.find(diagnostic) != std::string::npos,
                              " encoder refusal names the supplied forbidden byte or quote rule");
            }
            CHECK_MESSAGE(refused, " shared encoder refuses each supplied decoded value directly");
        }
        for (const auto& [value, expected] :
             std::vector<std::pair<std::string, std::string>>{{"_phase", "'_phase'"},
                                                              {"site a", "'site a'"},
                                                              {"a\tb", "'a\tb'"},
                                                              {"a'b\"c", "a'b\"c"},
                                                              {"\x27\x27", "\x27\x27\x27\x27"}}) {
            CHECK_MESSAGE(
                crysta::encode_id(value, category) == expected,
                " every encoder family follows the independent single-line spelling table");
        }
    }
}

TEST_CASE("C13-T12 persistent recovery retains native AtomSite") {
    auto key = [](auto& item) -> auto& { return item.id; };
    auto initial = pair<edi::AtomSite>(key);
    SUBCASE("populated owner copy") { persistent_recovery(initial, key, false); }
    SUBCASE("erase populated owner") { persistent_recovery(initial, key, true); }
}

TEST_CASE("C13-T12 persistent recovery retains native Structure") {
    auto key = [](auto& item) -> auto& { return item.name; };
    auto initial = pair<edi::Structure>(key);
    SUBCASE("populated owner copy") { persistent_recovery(initial, key, false); }
    SUBCASE("erase populated owner") { persistent_recovery(initial, key, true); }
}

TEST_CASE("C13-T12 persistent recovery retains native BraggPdExperiment") {
    auto key = [](auto& item) -> auto& { return item.name; };
    auto initial = pair<edi::BraggPdExperiment>(key);
    SUBCASE("populated owner copy") { persistent_recovery(initial, key, false); }
    SUBCASE("erase populated owner") { persistent_recovery(initial, key, true); }
}

TEST_CASE("C13-T12 persistent recovery retains native PrefOrient") {
    auto key = [](auto& item) -> auto& { return item.structure_id; };
    auto initial = pair<edi::PrefOrient>(key);
    SUBCASE("populated owner copy") { persistent_recovery(initial, key, false); }
    SUBCASE("erase populated owner") { persistent_recovery(initial, key, true); }
}

TEST_CASE("C13-T12 persistent recovery retains native SequentialExtractRule") {
    auto key = [](auto& item) -> auto& { return item.id; };
    auto initial = pair<edi::SequentialExtractRule>(key);
    SUBCASE("populated owner copy") { persistent_recovery(initial, key, false); }
    SUBCASE("erase populated owner") { persistent_recovery(initial, key, true); }
}

TEST_CASE("C13-T12 printable native AtomSite admission") {
    auto key = [](auto& x) -> auto& { return x.id; };
    arbitrary_id_entries(pair<edi::AtomSite>(key), key);
}

TEST_CASE("C13-T12 printable native Structure admission") {
    auto key = [](auto& x) -> auto& { return x.name; };
    arbitrary_id_entries(pair<edi::Structure>(key), key);
}

TEST_CASE("C13-T12 printable native BraggPdExperiment admission") {
    auto key = [](auto& x) -> auto& { return x.name; };
    arbitrary_id_entries(pair<edi::BraggPdExperiment>(key), key);
}

TEST_CASE("C13-T12 printable native PrefOrient admission") {
    auto key = [](auto& x) -> auto& { return x.structure_id; };
    arbitrary_id_entries(pair<edi::PrefOrient>(key), key);
}

TEST_CASE("C13-T12 printable native SequentialExtractRule admission") {
    auto key = [](auto& x) -> auto& { return x.id; };
    arbitrary_id_entries(pair<edi::SequentialExtractRule>(key), key);
}

#include "../../../core/src/fit_policy.hpp"
#include "edi/edits.hpp"

// Review-6 F2 before: no arbitrary-id witnesses for the helpers called by the app.
// After: invoke those exact native write routes, retaining the original owner state.
TEST_CASE("C13-T12 printable refusals at native app edit helpers") {
    for (const auto& [id, expected] : diagnostic_ids()) {
        auto key = [](auto& x) -> auto& { return x.id; };
        edi::Structure structure;
        structure.atom_sites = pair<edi::AtomSite>(key);
        structure.atom_sites[0]->id = id;
        const auto before = contents(structure.atom_sites, key);
        printable_collision(
            [&] { edi::rename_atom_site(structure, *structure.atom_sites[1], id); }, expected);
        CHECK_MESSAGE(contents(structure.atom_sites, key) == before,
                      " app site helper refusal preserves original identities and payload");
        structure.scattering_lengths_fm = {{id, 6.1}, {"other", 3.7}};
        const auto lengths = structure.scattering_lengths_fm;
        printable_collision([&] { edi::rename_scattering_length(structure, "other", id); },
                            expected);
        CHECK_MESSAGE(structure.scattering_lengths_fm == lengths,
                      " app scattering helper refusal cannot merge or erase entries");
        edi::Project project;
        auto names = [](auto& x) -> auto& { return x.name; };
        project.experiments = pair<edi::BraggPdExperiment>(names);
        project.experiments[0]->name = id;
        const auto banks = contents(project.experiments, names);
        printable_collision([&] { edi::rename_experiment(project, *project.experiments[1], id); },
                            expected);
        auto duplicate = *project.experiments[0];
        printable_collision([&] { edi::add_loaded_experiment(project, duplicate); }, expected);
        CHECK_MESSAGE(contents(project.experiments, names) == banks,
                      " app experiment rename and add refusals preserve both original banks");
    }
}

TEST_CASE("C13-T12 printable refusal at the joint fit site and bank collision") {
    for (const auto& [id, expected] : diagnostic_ids()) {
        edi::Structure structure;
        edi::AtomSite site;
        site.id = id;
        structure.atom_sites.push_back(site);
        edi::Project project;
        *project.structures.front() = structure;
        edi::ItemVec<edi::BraggPdExperiment> banks;
        edi::BraggPdExperiment bank;
        bank.name = id;
        banks.push_back(bank);
        std::vector<edi::PdDataBase> patterns(1);
        printable_collision([&] { edi::detail::validate_joint_request(project, banks, patterns); },
                            expected);
    }
}

// The arbitrary-id formatting seam used by the loader's composed slot check.
// The loader validates site-id domains earlier; this explicitly exercises the
// shared predicate with a literal composed id rather than mislabelling an earlier
// domain refusal as arrival at composition.
TEST_CASE("C13-T12 printable refusal at the composed fit state predicate") {
    for (const auto& [id, expected] : diagnostic_ids()) {
        const std::string composed = "structure." + id + ".fract_x";
        printable_collision(
            [&] {
                edi::require_unique_ids({composed, "unique", composed}, "fit-state row",
                                        "fit-state composition");
            },
            "structure." + expected + ".fract_x");
    }
}

// Review-6 F3 before: only direct-key aliases, no app helper success vehicle.
// After: both legal self-alias directions succeed, a DISTINCT sibling still refuses.
TEST_CASE("C13-T12 app experiment helper admits canonical self rename") {
    for (const auto& from : {std::string(), std::string("experiment")}) {
        const std::string to = from.empty() ? "experiment" : "";
        edi::Project project;
        project.experiments.clear();
        edi::BraggPdExperiment bank;
        bank.name = from;
        project.experiments.push_back(bank);
        auto held = project.experiments[0];
        CHECK_NOTHROW_MESSAGE(
            edi::rename_experiment(project, *held, to),
            " sole experiment may rename between empty and its canonical default");
        CHECK_MESSAGE((std::string(held->name) == to && project.experiments[0] == held),
                      " app helper legal rename updates the same original experiment");
        edi::BraggPdExperiment sibling;
        sibling.name = "sibling";
        project.experiments.push_back(sibling);
        collision([&] { edi::rename_experiment(project, *project.experiments[1], from); },
                  "experiment");
        CHECK_MESSAGE(std::string(project.experiments[1]->name) == "sibling",
                      " canonical collision with a distinct sibling still refuses atomically");
    }
}

TEST_CASE("C13-T12 printable refusal at experiment batch load") {
    namespace fs = std::filesystem;
    const auto root =
        fs::temp_directory_path() /
        ("-named-load-" +
         std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    struct Cleanup {
        fs::path path;
        ~Cleanup() {
            std::error_code e;
            fs::remove_all(path, e);
        }
    } cleanup{root};
    fs::create_directories(root);
    const auto fixture = fs::path(__FILE__).parent_path().parent_path().parent_path() /
                         "fixtures/c13_t4_march/model.edi";
    std::ifstream input(fixture);
    REQUIRE_MESSAGE(input.good(), " batch load reaches the committed valid bank vehicle");
    const std::string text((std::istreambuf_iterator<char>(input)), {});
    const auto at = text.find("data_experiment");
    const auto body = text.substr(text.find('\n', at)) +
                      "\nloop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_"
                      "su\n45 2 1\n46 3 1\n";
    // NUL and SOH are not STAR whitespace, so these datablock names actually reach
    // the helper. LF/TAB are token separators and are covered by in-memory routes.
    for (const auto& [id, expected] : std::vector<std::pair<std::string, std::string>>{
             {std::string("\0tail", 5), "\\x00tail"}, {"head\x01tail", "head\\x01tail"}}) {
        const auto file = (root / "bank.edi").string();
        std::ofstream(file, std::ios::binary) << "data_" << id << body;
        edi::Project project;
        project.experiments.clear();
        const auto control = edi::load_experiment_edi_files(project, {file});
        REQUIRE_MESSAGE((control.size() == 1 && std::string(control[0].name) == id),
                        " arbitrary datablock name actually reaches experiment batch admission");
        printable_collision([&] { (void)edi::load_experiment_edi_files(project, {file, file}); },
                            expected);
        edi::add_loaded_experiment(project, control[0]);
        printable_collision([&] { (void)edi::load_experiment_edi_files(project, {file}); },
                            expected);
        CHECK_MESSAGE(
            (project.experiments.size() == 1 && std::string(project.experiments[0]->name) == id),
            " refused batch load preserves the original experiment");
    }
}
