#include <doctest/doctest.h>

#include <cstdlib>
#include <limits>
#include <memory>
#include <new>
#include <optional>
#include <type_traits>
#include <vector>

#include "edi/model.hpp"

// Exercise actual allocation failures, never a replacement of ItemVec's private
// binder. The counter is armed only around the one public operation, on this
// thread; doctest and unrelated work never run with it armed.
#include "../../fixtures/c34_t28_allocation_failure.hpp"

struct C34AdmissionRow {
    edi::detail::Written<double> value{1.25};
};
template <>
struct crysta::RowSchema<C34AdmissionRow> {
    static constexpr const char* name = "_admission_row";
    static constexpr auto fields = std::tuple{&C34AdmissionRow::value};
    static constexpr std::array items{"value"};
};
template <>
struct crysta::detail::ForeignTable<C34AdmissionRow> {
    using type = edi::ItemVec<C34AdmissionRow>;
};

namespace {
template <class Operation>
std::ptrdiff_t allocations_used(Operation operation) {
    constexpr auto initial = std::numeric_limits<std::ptrdiff_t>::max();
    c34_t28_fault::remaining = initial;
    try {
        operation();
    } catch (...) {
        c34_t28_fault::remaining = -1;
        throw;
    }
    const auto left = c34_t28_fault::remaining;
    c34_t28_fault::remaining = -1;
    REQUIRE_MESSAGE(left >= 0, "F27 the successful control cannot exhaust its allocation counter");
    return initial - left;
}

template <class R>
void every_allocation(std::type_identity<R>) {
    using Rows = edi::ItemVec<R>;
    const R pristine;
    std::optional<R> copied;
    const auto copy_allocations = allocations_used([&] { copied.emplace(pristine); });
    for (int route = 0; route != 4; ++route) {
        const auto admit = [route](Rows& target, const auto& item, const Rows& source) {
            if (route == 0) target.push_back(item);
            if (route == 1) target.push_back(*item);
            if (route == 2) target.assign({item});
            if (route == 3) target = source;
        };
        auto control_item = std::make_shared<R>();
        auto control_original = std::make_shared<R>();
        Rows control_source({control_original});
        Rows control_target;
        const auto required =
            allocations_used([&] { admit(control_target, control_item, control_source); });
        REQUIRE_MESSAGE((control_target.size() == 1 && control_target.record()),
                        "F27 allocation calibration must finish an actual successful admission");
        REQUIRE_MESSAGE(required < std::numeric_limits<std::ptrdiff_t>::max(),
                        "F27 the measured sweep must leave room for its successful control");
        INFO("normal admission allocations: ", required,
             "; default row-copy allocations: ", copy_allocations);
        bool completed = false;
        std::size_t refusals = 0;
        // The measured route supplies every throwing point plus the success at N.
        for (std::ptrdiff_t allocation = 0; allocation <= required; ++allocation) {
            INFO(route, allocation);
            auto item = std::make_shared<R>();
            auto original = std::make_shared<R>();
            Rows source({original});
            const auto source_record = source.record();
            const auto source_generation = source.category_stamp();
            Rows target;
            const auto generation = target.generation();
            const auto category = target.category_stamp();
            REQUIRE_MESSAGE(!target.record(),
                            " F27 a never-populated collection has no published identity");
            bool refused = false;
            c34_t28_fault::remaining = allocation;
            try {
                admit(target, item, source);
            } catch (const std::bad_alloc&) {
                refused = true;
            } catch (...) {
                c34_t28_fault::remaining = -1;
                throw;
            }
            c34_t28_fault::remaining = -1;
            CHECK_MESSAGE(
                (source.record() == source_record &&
                 source.category_stamp() == source_generation && source.front() == original),
                " F27 first admission never mutates its source collection");
            if (refused) {
                ++refusals;
                CHECK_MESSAGE(!target.record(),
                              " F27 failed first admission publishes no collection identity");
                CHECK_MESSAGE(target.empty(), " F27 allocation refusal stores no candidate row");
                CHECK_MESSAGE(
                    (target.generation() == generation && target.category_stamp() == category),
                    " F27 allocation refusal renews neither collection generation");
                if constexpr (edi::KeyedItem<R>)
                    CHECK_MESSAGE(edi::KeyTraits<R>::key(*item).owner() == nullptr,
                                  " F27 a refused candidate remains unattached");
            } else {
                completed = true;
                CHECK_MESSAGE(
                    (target.size() == 1 && target.record() && target.record()->owner == &target),
                    " F27 successful first admission publishes its live identity");
                CHECK_MESSAGE(target.generation() > generation,
                              " F27 only the admitted operation renews collection generation");
                break;
            }
        }
        CHECK_MESSAGE(refusals == static_cast<std::size_t>(required),
                      "F27 every measured allocation point must be injected before success");
        CHECK_MESSAGE(refusals > 0,
                      " F27 the fault injection really reaches throwing preparations");
        REQUIRE_MESSAGE(completed,
                        " F27 the exhaustive allocation sweep reaches a successful control");
    }
}
}  // namespace
TEST_CASE("C34-T28 F27 atom-site first admission is atomic at every allocation") {
    every_allocation(std::type_identity<edi::AtomSite>{});
}
TEST_CASE("C34-T28 F27 background first admission is atomic at every allocation") {
    every_allocation(std::type_identity<edi::LineSegment>{});
}
TEST_CASE("C34-T28 F27 texture first admission is atomic at every allocation") {
    every_allocation(std::type_identity<edi::PrefOrient>{});
}
TEST_CASE("C34-T28 F27 extract-rule first admission is atomic at every allocation") {
    every_allocation(std::type_identity<edi::SequentialExtractRule>{});
}
TEST_CASE("C34-T28 F27 structure first admission is atomic at every allocation") {
    every_allocation(std::type_identity<edi::Structure>{});
}
TEST_CASE("C34-T28 F27 experiment first admission is atomic at every allocation") {
    every_allocation(std::type_identity<edi::BraggPdExperiment>{});
}
TEST_CASE("C34-T28 F27 public schema first admission is atomic at every allocation") {
    every_allocation(std::type_identity<C34AdmissionRow>{});
}
