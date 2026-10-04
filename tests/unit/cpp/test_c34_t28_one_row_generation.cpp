#include <doctest/doctest.h>

#include <array>
#include <string>
#include <tuple>
#include <type_traits>

#include "edi/model.hpp"

namespace {
template <class O, class... C>
auto generations(const O& owner, std::tuple<C...>) {
    return std::array<std::string, sizeof...(C)>{edi::OneRow<C>(owner).generation()...};
}
template <class O, class... C, class Write>
void exercise(O& owner, std::tuple<C...> cats, const char* selected, bool changes, Write write) {
    const auto before = generations(owner, cats);
    const auto token = owner.table_row.token();
    write();
    const auto after = generations(owner, cats);
    std::size_t i = 0;
    (
        [&] {
            INFO(C::name);
            const bool affected = selected && std::string(C::name) == selected && changes;
            CHECK_MESSAGE(
                (after[i] != before[i]) == affected,
                " I21/R5 generations encode precisely schema cells and old renewal");
            CHECK_MESSAGE((edi::OneRow<C>::rows() == 1 && edi::OneRow<C>(owner).token() == token),
                          " I21 writes preserve the single row identity");
            ++i;
        }(),
        ...);
}
template <class O, class Cats, class Cell>
void routes(O& o, Cats cats, const char* name, Cell& cell) {
    auto edit = [&](bool changes, auto write) { exercise(o, cats, name, changes, write); };
    if constexpr (std::is_same_v<Cell, edi::Parameter>) {
        routes(o, cats, name, cell.value);
        routes(o, cats, name, cell.uncertainty);
        routes(o, cats, name, cell.free);
        routes(o, cats, name, cell.start_value);
        routes(o, cats, name, cell.start_uncertainty);
    } else if constexpr (requires {
                             cell.written();
                             cell.get();
                         }) {
        edit(true, [&] { cell = cell.get(); });
    } else if constexpr (requires {
                             cell.written();
                             cell.value();
                         }) {
        edit(true, [&] { cell = cell.value(); });
    } else if constexpr (requires {
                             cell.has_value();
                             cell.emplace();
                             cell.reset();
                         }) {
        if (!cell) edit(true, [&] { cell.emplace(); });
        edit(std::is_same_v<typename Cell::value_type, edi::Parameter>, [&] {
            const auto v = cell;
            cell = v;
        });
        routes(o, cats, name, *cell);
        edit(true, [&] { cell.reset(); });
    } else {
        edit(false, [&] {
            const auto v = cell;
            cell = v;
        });
        edit(true, [&] {
            if constexpr (std::is_same_v<Cell, std::string>)
                cell += "gate-2";
            else if constexpr (std::is_same_v<Cell, bool>)
                cell = !cell;
            else if constexpr (std::is_enum_v<Cell>)
                cell = static_cast<Cell>(static_cast<int>(cell) == 0 ? 1 : 0);
            else
                cell += 1;
        });
    }
}
template <class C, class O, class Cats>
void category(O& o, Cats cats) {
    std::apply([&](auto... member) { (routes(o, cats, C::name, o.*member), ...); }, C::columns);
}
template <class O, class... C>
void all(O& o, std::tuple<C...> cats) {
    (category<C>(o, cats), ...);
    const auto token = o.table_row.token();
    const O copy(o);
    CHECK_MESSAGE(copy.table_row.token() != token,
                  " I21 copies create independent row identities");
    o = copy;
    CHECK_MESSAGE(o.table_row.token() == token,
                  " I21 assignment retains the target row identity");
}
}  // namespace
TEST_CASE("C34-T28 edi one-row public schemas retain every cell and category boundary") {
    edi::Cell cell;
    all(cell, std::tuple<edi::CellCategory>{});
    edi::SpaceGroup sg;
    all(sg, std::tuple<edi::SpaceGroupCategory>{});
    edi::Geom geom;
    all(geom, std::tuple<edi::GeomCategory>{});
    edi::ExperimentType type;
    all(type, std::tuple<edi::ExperimentTypeCategory>{});
    edi::PeakBase peak;
    all(peak, std::tuple<edi::PeakCategory>{});
    edi::InstrumentBase instrument;
    all(instrument, std::tuple<edi::InstrumentCategory>{});
    edi::LinkedStructure link;
    all(link, std::tuple<edi::LinkedStructureCategory>{});
    edi::AbsorptionBase absorption;
    all(absorption, std::tuple<edi::AbsorptionCategory>{});
    edi::ExperimentBase experiment;
    const auto cats =
        std::tuple<edi::ScatteringSourceCategory, edi::JointFitCategory, edi::DataRangeCategory>{};
    all(experiment, cats);
    exercise(experiment, cats, nullptr, false, [&] { experiment.name = "outside"; });
    edi::Project project;
    const auto pcats =
        std::tuple<edi::FittingModeCategory, edi::MinimizerCategory, edi::ProjectStateCategory>{};
    all(project, pcats);
    exercise(project, pcats, nullptr, false, [&] { project.metadata.title = "outside"; });
    all(project.metadata, std::tuple<edi::MetadataCategory>{});
    all(project.sequential_fit, std::tuple<edi::SequentialFitCategory>{});
}
TEST_CASE("C34-T28 plain generation encoding distinguishes cell and optional boundaries") {
    edi::ProjectMetadata metadata;
    metadata.name = "a";
    metadata.title = "bc";
    auto before = edi::OneRow<edi::MetadataCategory>(metadata).generation();
    metadata.name = "ab";
    metadata.title = "c";
    CHECK_MESSAGE(before != edi::OneRow<edi::MetadataCategory>(metadata).generation(),
                  " I21 adjacent strings cannot alias in a one-row generation");
    edi::PeakBase peak;
    peak.cutoff_fwhm = 0.0;
    before = edi::OneRow<edi::PeakCategory>(peak).generation();
    peak.cutoff_fwhm = -0.0;
    CHECK_MESSAGE(before != edi::OneRow<edi::PeakCategory>(peak).generation(),
                  " I21 preserved plain doubles retain their exact representation");
}
