#include <doctest/doctest.h>

#include <memory>
#include <type_traits>
#include <vector>

#include "edi/model.hpp"

// Public schema-backed unkeyed callers reach the same admission route.
struct C34ForeignRow {
    edi::detail::Written<double> position{1.25};
    edi::Parameter intensity{31.25};
};
template <>
struct crysta::RowSchema<C34ForeignRow> {
    static constexpr const char* name = "_foreign_row";
    static constexpr auto fields = std::tuple{&C34ForeignRow::position, &C34ForeignRow::intensity};
    static constexpr std::array items{"position", "intensity"};
};
template <>
struct crysta::detail::ForeignTable<C34ForeignRow> {
    using type = edi::ItemVec<C34ForeignRow>;
};

namespace {
using Row = C34ForeignRow;
using Rows = edi::ItemVec<Row>;
template <class R>
void write_all(R& row, std::vector<edi::ItemVec<R>*> holders) {
    auto write = [&](auto& cell) {
        for (bool equal : {true, false}) {
            std::vector<std::uint64_t> before;
            for (const auto* rows : holders) before.push_back(rows->category_stamp());
            const auto value = cell.get();
            cell = equal ? value : value + 1.25;
            for (std::size_t i = 0; i < holders.size(); ++i) {
                CHECK_MESSAGE(holders[i]->category_stamp() > before[i],
                              " F19 every holder observes equal and changed row writes");
                CHECK_MESSAGE(holders[i]->front().get() == &row,
                              " F19 unkeyed admission preserves the exact shared item");
            }
        }
    };
    CHECK_MESSAGE((row.position.bound() && row.intensity.bound()),
                  " I14/F19 a surviving held row remains in column storage");
    write(row.position);
    write(row.intensity.value);
    for (auto* rows : holders) {
        const auto before = rows->category_stamp();
        row.intensity.uncertainty = row.intensity.uncertainty.get();
        CHECK_MESSAGE(rows->category_stamp() > before,
                      " F19 foreign holders see equal optional-attribute writes too");
    }
}
}  // namespace
TEST_CASE("C34-T28 F19 every foreign unkeyed admission route observes its cells") {
    for (int admission = 0; admission != 3; ++admission) {
        for (int removal = 0; removal != 6; ++removal) {
            INFO(admission, removal);
            auto item = std::make_shared<Row>();
            item->position = 12.5;
            item->intensity.value = 31.25;
            auto first = std::make_unique<Rows>();
            first->push_back(item);
            Rows second;
            if (admission == 0) second.push_back(item);
            if (admission == 1) second.assign({item});
            if (admission == 2) {
                second.push_back(Row{});
                second.replace_at(0, item);
            }
            REQUIRE_MESSAGE(second.front() == item,
                            " F19 the old foreign shared-pointer admission remains valid");
            write_all(*item, {first.get(), &second});
            auto other = std::make_shared<Row>();
            switch (removal) {
                case 0:
                    first->erase_at(0);
                    break;
                case 1:
                    first->clear();
                    break;
                case 2:
                    first->assign({other});
                    break;
                case 3:
                    first->replace_at(0, other);
                    break;
                case 4:
                    first.reset();
                    break;
                case 5: {
                    Rows moved(std::move(*first));
                    write_all(*item, {&moved, &second});
                    break;
                }
            }
            write_all(*item, {&second});
            // Reordering/replacing a surviving occurrence must repair storage,
            // not preserve an obsolete unbound-slot sentinel.
            second.push_back(other);
            second.assign({other, item});
            second.erase_at(0);
            second.replace_at(0, item);
            write_all(*item, {&second});
        }
    }
}
TEST_CASE("C34-T28 F19 duplicate unkeyed survivors remain stored after every replacement") {
    for (int admission = 0; admission != 3; ++admission)
        for (int removal = 0; removal != 4; ++removal) {
            INFO(admission, removal);
            auto item = std::make_shared<Row>();
            Rows rows;
            if (admission == 0) {
                rows.push_back(item);
                rows.push_back(item);
            }
            if (admission == 1) rows.assign({item, item});
            if (admission == 2) {
                rows.assign({item, std::make_shared<Row>()});
                rows.replace_at(1, item);
            }
            REQUIRE_MESSAGE((rows.size() == 2 && rows[0] == item && rows[1] == item),
                            " F19 the old duplicate unkeyed admission remains valid");
            write_all(*item, {&rows});
            if (removal == 0) rows.erase_at(0);
            if (removal == 1) rows.erase_at(1);
            if (removal == 2) rows.assign({item});
            if (removal == 3) {
                rows.replace_at(0, std::make_shared<Row>());
                rows.erase_at(0);
            }
            write_all(*item, {&rows});
        }
}
template <class RowType>
void keyed_controls(std::type_identity<RowType>) {
    using Collection = edi::ItemVec<RowType>;
    auto item = std::make_shared<RowType>();
    Collection first({item}), second;
    const auto before = first.category_stamp();
    CHECK_THROWS_AS_MESSAGE(second.push_back(item), std::invalid_argument,
                            " F19 keyed foreign admission still refuses before mutation");
    CHECK_THROWS_AS_MESSAGE(second.assign({item}), std::invalid_argument,
                            " F19 keyed foreign assignment still refuses before mutation");
    CHECK_THROWS_AS_MESSAGE(first.assign({item, item}), std::invalid_argument,
                            " F19 keyed duplicate admission still refuses before mutation");
    CHECK_MESSAGE((second.empty() && first.size() == 1 && first.category_stamp() == before),
                  " F19 failed keyed controls preserve both holders and generation");
    Collection replacement;
    replacement.push_back(RowType{});
    const auto kept = replacement.front();
    const auto replacement_stamp = replacement.category_stamp();
    CHECK_THROWS_AS_MESSAGE(replacement.replace_at(0, item), std::invalid_argument,
                            " F19 keyed foreign replacement still refuses before mutation");
    CHECK_MESSAGE((replacement.size() == 1 && replacement.front() == kept &&
                   replacement.category_stamp() == replacement_stamp && first.front() == item &&
                   first.category_stamp() == before),
                  " F19 refused replacement preserves both rows and generations");
}
TEST_CASE("C34-T28 F19 all keyed families retain foreign and duplicate refusal") {
    keyed_controls(std::type_identity<edi::AtomSite>{});
    keyed_controls(std::type_identity<edi::PrefOrient>{});
    keyed_controls(std::type_identity<edi::SequentialExtractRule>{});
    keyed_controls(std::type_identity<edi::Structure>{});
    keyed_controls(std::type_identity<edi::BraggPdExperiment>{});
    keyed_controls(std::type_identity<edi::LineSegment>{});
    keyed_controls(std::type_identity<edi::ExcludedRegion>{});
}

TEST_CASE("C34-T28 F19 caller-defined unkeyed schemas retain shared surviving storage") {
    auto item = std::make_shared<C34ForeignRow>();
    edi::ItemVec<C34ForeignRow> first, second;
    first.push_back(item);
    second.assign({item, item});
    write_all(*item, {&first, &second});
    first.clear();
    second.erase_at(0);
    write_all(*item, {&second});
    edi::ItemVec<C34ForeignRow> moved(std::move(second));
    write_all(*item, {&moved});
}
