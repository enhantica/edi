#include <doctest/doctest.h>
#include <bit>
#include <cmath>
#include <limits>
#include <map>
#include <set>
#include <tuple>
#include "e04_t9_support.hpp"

TEST_CASE("E04-T9 D3 generator preserves endpoints and linear interpolation") {
    const auto out = e04_t9_fixture::interpolate({10, 20, 40}, {2, 6, 8}, {10, 15, 20, 30, 40});
    CHECK_MESSAGE(((out == std::vector<double>{2, 4, 6, 7, 8})),
                  " P12 deterministic stress input uses closed-form interpolation");
    auto stress = e04_t9_fixture::stress();
    CHECK_MESSAGE((stress.experiment().data->axis().size() == 50000),
                  " L1 D3 has exactly 50000 points");
    auto original = edi::load_project(e04_t9_fixture::echidna);
    CHECK_MESSAGE((stress.experiment().data->axis().front() == original.experiment().data->axis().front()),
                  " D3 retains the committed axis lower endpoint");
    CHECK_MESSAGE((stress.experiment().data->axis().back() == original.experiment().data->axis().back()),
                  " D3 retains the committed axis upper endpoint");
}

#if __has_include("edi/presentation.hpp")
#include "edi/presentation.hpp"
#include <crysta/analysis.hpp>
#include <crysta/computed.hpp>
#include <crysta/model.hpp>

namespace {
bool identical(double a, double b) {
    return (std::isnan(a) && std::isnan(b)) || std::bit_cast<std::uint64_t>(a) == std::bit_cast<std::uint64_t>(b);
}
const edi::PatternSeries& series(const edi::PatternPresentation& p, edi::SeriesKind kind) {
    auto it = std::find_if(p.series.begin(), p.series.end(), [=](const auto& s) { return s.kind == kind; });
    REQUIRE_MESSAGE((it != p.series.end()), " I16 every available category has its presentation series");
    return *it;
}
template<class Column>
void compare_points(const edi::PatternSeries& s, const Column& x, const Column& y) {
    std::set<std::size_t> rows;
    REQUIRE_MESSAGE((s.rows.size() == s.points.size()), " I16 every presented point carries row provenance");
    for (std::size_t i = 0; i < s.points.size(); ++i) {
        if (std::isnan(s.points[i].x)) {
            CHECK_MESSAGE((std::isnan(s.points[i].y)), " I20 a gap has NaN on both coordinates");
            continue;
        }
        const auto r = s.rows[i];
        REQUIRE_MESSAGE((r < x.size() && r < y.size()), " I16 provenance is within the independent category");
        CHECK_MESSAGE((identical(s.points[i].x, x[r])), " I16 x carries crysta's axis bits");
        CHECK_MESSAGE((identical(s.points[i].y, y[r])), " I14 values carry crysta's category bits");
        rows.insert(r);
    }
    std::size_t finite = 0;
    for (std::size_t i = 0; i < x.size(); ++i) if (std::isfinite(y[i])) ++finite;
    CHECK_MESSAGE((rows.size() == finite), " I17 full-resolution mode keeps every finite source row");
}
// Full-array oracle: enumerate each bin/run, independent of the production decimator and pixel helper.
std::set<std::size_t> oracle(const std::vector<double>& x, const std::vector<double>& low,
                             const std::vector<double>& high, double left, double right, int width) {
    std::set<std::size_t> keep;
    std::map<std::pair<int,int>, std::vector<std::size_t>> bins;
    int run = 0;
    bool gap = true;
    for (std::size_t r = 0; r < x.size(); ++r) {
        if (std::isnan(low[r]) || std::isnan(high[r])) { gap = true; continue; }
        if (gap) { ++run; gap = false; }
        if (x[r] < left || x[r] > right) continue;
        const int bin = std::clamp(static_cast<int>(std::floor((x[r] - left) / (right - left) * width)), 0, width - 1);
        bins[{run, bin}].push_back(r);
    }
    for (const auto& [key, rs] : bins) {
        (void)key;
        if (rs.size() <= 4) { keep.insert(rs.begin(), rs.end()); continue; }
        keep.insert(rs.front()); keep.insert(rs.back());
        keep.insert(*std::min_element(rs.begin(), rs.end(), [&](auto a, auto b) { return low[a] < low[b]; }));
        keep.insert(*std::max_element(rs.begin(), rs.end(), [&](auto a, auto b) { return high[a] < high[b]; }));
    }
    auto first = std::find_if(x.begin(), x.end(), [&](double v) { return v >= left; });
    auto end = std::find_if(x.begin(), x.end(), [&](double v) { return v > right; });
    if (first != x.begin()) keep.insert(static_cast<std::size_t>(first - x.begin() - 1));
    if (end != x.end()) keep.insert(static_cast<std::size_t>(end - x.begin()));
    return keep;
}
void exercise_decimator(const std::vector<double>& x, const std::vector<double>& lo,
                        const std::vector<double>& hi) {
    for (const int width : {1, 7, 400, 1200, 2400}) for (double fraction : {0.0, 0.17}) {
        const double left = x.front() + fraction * (x.back() - x.front());
        const double right = x.back() - fraction * (x.back() - x.front());
        const auto actual = edi::decimate_min_max(x, lo, hi, left, right, width);
        const auto expected = oracle(x, lo, hi, left, right, width);
        CHECK_MESSAGE((std::is_sorted(actual.begin(), actual.end())), " I17 kept rows are ascending");
        const std::set<std::size_t> retained(actual.begin(), actual.end());
        CHECK_MESSAGE((retained.size() == actual.size()), " I17 a retained row appears only once");
        // The invariant chooses an extremum value, not an arbitrary tied row.
        // Require bin/run first and last rows separately, then compare all extrema.
        std::map<std::pair<int,int>,std::vector<std::size_t>> bins;
        int run=0; bool gap=true;
        for (std::size_t r=0;r<x.size();++r) {
            if (std::isnan(lo[r]) || std::isnan(hi[r])) { gap=true; continue; }
            if (gap) { ++run; gap=false; }
            if (x[r]<left || x[r]>right) continue;
            int bin=std::clamp(static_cast<int>(std::floor((x[r]-left)/(right-left)*width)),0,width-1);
            bins[{run,bin}].push_back(r);
        }
        for (const auto& [key,rs] : bins) {
            (void)key;
            CHECK_MESSAGE((retained.count(rs.front()) && retained.count(rs.back())),
                          " I17 each pixel run retains its first and last visible row");
            double full_low=std::numeric_limits<double>::infinity(), kept_low=full_low;
            double full_high=-full_low, kept_high=full_high;
            for (auto r:rs) {
                full_low=std::min(full_low,lo[r]); full_high=std::max(full_high,hi[r]);
                if (retained.count(r)) { kept_low=std::min(kept_low,lo[r]); kept_high=std::max(kept_high,hi[r]); }
            }
            CHECK_MESSAGE((kept_low==full_low && kept_high==full_high),
                          " I18 independent per-pixel full-resolution low and high extrema survive decimation");
        }
        for (auto row:expected) if (x[row]<left || x[row]>right)
            CHECK_MESSAGE(retained.count(row)==1, " I17 viewport keeps the immediate adjacent row beyond each edge");
    }
}
}  // namespace

TEST_CASE("E04-T9 gate 1 every CLI presentation equals crysta's independently loaded categories") {
    const auto paths = e04_t9::projects();
    REQUIRE_MESSAGE((!paths.empty()), " gate 1 committed CLI corpus is nonempty");
    for (const auto& path : paths) {
        INFO(path);
        auto reference = crysta::load_project(path);
        auto project = edi::load_project(path);
        project.calculate();
        REQUIRE_MESSAGE((project.experiments.size() == reference.experiments.size()),
                        " gate 1 every independently loaded bank is covered");
        for (std::size_t b = 0; b < project.experiments.size(); ++b) {
            auto& experiment = reference.experiments[b];
            const auto& computed = crysta::current(reference, experiment);
            const auto source = edi::capture_pattern(project, b);
            const auto p = edi::present_pattern(source, {});
            REQUIRE_MESSAGE((p.current), " I22 successful calculation presents current columns");
            const auto& data = *experiment.data;
            compare_points(series(p, edi::SeriesKind::Measured), data.grid, data.intensity);
            compare_points(series(p, edi::SeriesKind::Calculated), data.grid, computed.data().intensity_calc);
            compare_points(series(p, edi::SeriesKind::Background), data.grid, computed.data().intensity_bkg);
            compare_points(series(p, edi::SeriesKind::Residual), data.grid, crysta::residual(experiment));
            const auto& measured = series(p, edi::SeriesKind::Measured);
            REQUIRE_MESSAGE((measured.bar_low.size() == measured.points.size() && measured.bar_high.size() == measured.points.size()),
                            " I16 uncertainty ends remain aligned with measured provenance");
            for (std::size_t i = 0; i < measured.rows.size(); ++i) {
                auto r = measured.rows[i];
                CHECK_MESSAGE((identical(measured.bar_low[i], data.intensity[r] - data.sigma[r])),
                              " I16 lower bar is the independent measured minus one su");
                CHECK_MESSAGE((identical(measured.bar_high[i], data.intensity[r] + data.sigma[r])),
                              " I16 upper bar is the independent measured plus one su");
            }
            std::set<std::size_t> tick_rows;
            for (const auto& s : p.series) if (s.kind == edi::SeriesKind::BraggTicks)
                for (std::size_t i = 0; i < s.rows.size(); ++i) if (s.rows[i] < computed.refln().size()) {
                    CHECK_MESSAGE((identical(s.points[i].x, computed.refln().position[s.rows[i]])),
                                  " gate 1 ticks carry crysta reflection positions");
                    tick_rows.insert(s.rows[i]);
                }
            std::set<std::size_t> visible_ticks;
            for (std::size_t r=0;r<computed.refln().size();++r)
                if (computed.refln().position[r]>=data.grid[0] && computed.refln().position[r]<=data.grid[data.grid.size()-1])
                    visible_ticks.insert(r);
            CHECK_MESSAGE((tick_rows == visible_ticks),
                          " gate 1 full-resolution Bragg ticks cover every reflection within the full data viewport");
        }
    }
}

TEST_CASE("E04-T9 gate 2 independent pixel extrema over corpus and stress measurements") {
    auto paths = e04_t9::projects();
    paths.push_back("D3");
    for (const auto& path : paths) {
        INFO(path);
        auto project = path == "D3" ? e04_t9_fixture::stress() : edi::load_project(path);
        project.calculate();
        for (std::size_t b = 0; b < project.experiments.size(); ++b) {
            const auto s = edi::capture_pattern(project, b);
            REQUIRE_MESSAGE((s.x && s.meas && s.su && s.calc && s.bkg && s.resid),
                            " gate 2 fixture exposes every calculated and measured curve");
            for (auto column : {s.meas, s.calc, s.bkg, s.resid}) exercise_decimator(*s.x, *column, *column);
            auto low = *s.meas, high = low;
            for (std::size_t i = 0; i < low.size(); ++i) { low[i] -= (*s.su)[i]; high[i] += (*s.su)[i]; }
            exercise_decimator(*s.x, low, high);
        }
    }
}

TEST_CASE("E04-T9 display seams have closed-form nonidentity values") {
    CHECK_MESSAGE((edi::to_display(2500, edi::YScale::Sqrt) == 50), " seam 3 square root maps intensity units");
    CHECK_MESSAGE((edi::to_display(-4, edi::YScale::Sqrt) == -2), " I21 signed sqrt retains negative intensities");
    CHECK_MESSAGE((edi::to_display(1000, edi::YScale::Log10) == 3), " I21 log uses base ten");
    for (double v : {0., -5.}) CHECK_MESSAGE((std::isnan(edi::to_display(v, edi::YScale::Log10))), " I21 nonpositive log values are gaps");
    CHECK_MESSAGE((edi::from_display(-2, edi::YScale::Sqrt) == -4), " seam 3 inverse signed sqrt retains sign");
    CHECK_MESSAGE((edi::from_display(3, edi::YScale::Log10) == 1000), " seam 3 inverse log recovers original units");
    for (const auto& [d, scale, text] : std::vector<std::tuple<double,edi::YScale,std::string>>{
        {3,edi::YScale::Log10,"1000"},{6,edi::YScale::Log10,"1e+06"},
        {50,edi::YScale::Sqrt,"2500"},{-2,edi::YScale::Sqrt,"-4"},{1.5,edi::YScale::Linear,"1.5"}})
        CHECK_MESSAGE((edi::axis_label(d, scale) == text), " seam 14 axis labels use original units and C-locale six-digit formatting");
    CHECK_MESSAGE((edi::pixel_columns(401, 1.25) == 501), " seam 8 device pixel columns floor the scaled width");
    CHECK_MESSAGE((edi::pixel_columns(333, 1.5) == 499), " seam 8 fractional device ratio is not rounded up");
    CHECK_MESSAGE((edi::pixel_columns(.4, 1) == 1), " seam 8 subpixel width retains one column");
}

TEST_CASE("E04-T9 gaps uncertainty panes freshness and phase placement") {
    auto col = [](std::vector<double> v) { return std::make_shared<const std::vector<double>>(std::move(v)); };
    const auto nan = std::numeric_limits<double>::quiet_NaN();
    edi::PatternSource s;
    s.x = col({10,20,30,40,50}); s.meas = col({100,4,2,3,5}); s.su = col({10,9,1,1,1});
    s.calc = col({80,nan,nan,2,4}); s.bkg = col({1,nan,nan,1,1}); s.resid = col({20,nan,nan,1,1});
    s.current = true; s.excluded = {{20,30}};
    s.phases = {{"a","Alpha",0,col({20}),{}},{"b","Beta",1,col({40}),{}}};
    edi::PatternView view; view.y_scale = edi::YScale::Sqrt;
    const auto p = edi::present_pattern(s, view);
    const auto& m = series(p, edi::SeriesKind::Measured);
    CHECK_MESSAGE((m.bar_low[0] == doctest::Approx(9.486832980505138)), " seam 6 lower error end transforms after subtracting su");
    CHECK_MESSAGE((m.bar_high[0] == doctest::Approx(10.488088481701515)), " seam 6 upper error end transforms after adding su");
    CHECK_MESSAGE((m.bar_low[1] == doctest::Approx(-2.23606797749979)), " seam 6 signed sqrt bar can cross zero");
    const auto& c = series(p, edi::SeriesKind::Calculated);
    CHECK_MESSAGE((std::count_if(c.points.begin(), c.points.end(), [](auto pt) { return std::isnan(pt.x) && std::isnan(pt.y); }) == 1),
                  " I20 contiguous excluded rows produce one gap, never zero-valued points");
    CHECK_MESSAGE((series(p, edi::SeriesKind::Residual).points[0].y == 20),
                  " I21 residual pane remains linear under main-pane transforms");
    REQUIRE_MESSAGE((p.layout.size() == 3), " I24 three panes describe measured projects with phases");
    CHECK_MESSAGE((p.layout[0].pane == edi::Pane::Main && p.layout[0].stretch == .7),
                  " I24 main pane is first with seven tenths of remaining height");
    CHECK_MESSAGE((p.layout[1].pane == edi::Pane::Bragg && p.layout[1].fixed_px == 36),
                  " seam 15 two phases reserve two 18px rows");
    CHECK_MESSAGE((p.layout[2].pane == edi::Pane::Residual && p.layout[2].stretch == .3),
                  " I24 residual is the bottom pane");
    for (const auto& tick : p.series) if (tick.kind == edi::SeriesKind::BraggTicks) {
        REQUIRE_MESSAGE((tick.points.size() >= 2), " I24 tick has two endpoints");
        const double low = tick.id == "bragg/a" ? 1.15 : .15;
        CHECK_MESSAGE((tick.points[0].y == doctest::Approx(low) && tick.points[1].y == doctest::Approx(low + .7)),
                      " seam 15 first structure is above the second, ticks cover central seventy percent");
    }
    view.y_scale = edi::YScale::Log10;
    const auto log = edi::present_pattern(s, view);
    CHECK_MESSAGE((std::isnan(series(log, edi::SeriesKind::Measured).bar_low[1])), " I21 nonpositive lower log error end stays NaN");
    auto project = edi::load_project(e04_t9_fixture::silicon); project.calculate();
    project.structure().cell.length_a.value += .125;
    const auto stale = edi::capture_pattern(project, 0);
    CHECK_MESSAGE((!stale.current && !stale.calc && !stale.bkg && !stale.resid && stale.phases.empty()),
                  " I22 stale capture cannot expose computed columns or reflections");
}
TEST_CASE("E04-T9 I17 identity modes and I23 authoritative style colors") {
    const std::vector<double> x{10,11,12,13,14,15}, y{2,8,1,7,4,6};
    const auto all = edi::decimate_min_max(x,y,y,10,15,0);
    CHECK_MESSAGE((all == std::vector<std::size_t>{0,1,2,3,4,5}), " I17 zero columns retain full-resolution visible rows");
    const std::vector<double> disorder{10,13,11,14,12,15};
    CHECK_MESSAGE((edi::decimate_min_max(disorder,y,y,10,15,1) == all), " I17 nonmonotonic axes retain all visible rows");
    CHECK_MESSAGE((edi::decimate_min_max(x,y,y,10,15,2) == all), " I17 pixel columns with at most four rows retain every row");
    auto project = edi::load_project(e04_t9_fixture::silicon); project.calculate();
    const auto p = edi::present_pattern(edi::capture_pattern(project,0),{});
    // Owner 2026-10-02,  item 7 requests thinner residual and Bragg lines.
    // Their 1-px values below are labelled regression pins of the chosen style;
    // the positive/thinner invariant separately proves the owner requirement.
    CHECK_MESSAGE(p.y_residual.title == "Residual",
                  " owner chart item 4 names the residual presentation axis Residual");
    const auto& styles = edi::pattern_style_table();
    for (const auto& [kind, light, dark, width] : std::vector<std::tuple<edi::SeriesKind,std::string,std::string,double>>{
        {edi::SeriesKind::Measured,"#03A9F4","#81D4FA",2},
        {edi::SeriesKind::Calculated,"#F44336","#EF9A9A",2},
        {edi::SeriesKind::Background,"#607D8B","#B0BEC5",1},
        {edi::SeriesKind::Residual,"#8BC34A","#C5E1A5",1},
        {edi::SeriesKind::BraggTicks,"#FF9800","#FFCC80",1}}) {
        const auto& s = series(p,kind);
        const auto style = std::find_if(styles.begin(),styles.end(),[&](const auto& v){return v.key==s.style;});
        REQUIRE_MESSAGE(style != styles.end(), " I23 every series resolves to the one authoritative style table");
        if (kind == edi::SeriesKind::Residual || kind == edi::SeriesKind::BraggTicks) {
            const double prior_width = kind == edi::SeriesKind::Residual ? 2.0 : 1.5;
            CHECK_MESSAGE((style->width_px > 0.0 && style->width_px < prior_width),
                          " owner chart item 7 keeps lines visible and thinner than their prior widths");
        }
        CHECK_MESSAGE((style->light == light && style->dark == dark && style->width_px == width),
                      " I23 independent palettes and prior widths match;  one-pixel widths are labelled regression pins");
        if (kind == edi::SeriesKind::Measured)
            CHECK_MESSAGE(style->marker_px == 5,
                          " I23 ADR-0017 section 15 measured markers have the owner-reviewed size");
    }
    const auto band = std::find_if(styles.begin(),styles.end(),[](const auto& s){return s.light=="#8C8C8C";});
    REQUIRE_MESSAGE(band != styles.end(), " P13 excluded band has the reference grey style");
    CHECK_MESSAGE((band->dark == "#8C8C8C" && band->opacity == .15), " seam 13 band opacity and grey are identical in both themes");
}
#else
#define E04_T9_RED(name) TEST_CASE(name) { FAIL_CHECK(" accepted presentation contract is not implemented on the red-first base"); }
E04_T9_RED(" gate 1 every CLI presentation equals crysta's independently loaded categories")
E04_T9_RED(" gate 2 independent pixel extrema over corpus and stress measurements")
E04_T9_RED(" display seams have closed-form nonidentity values")
E04_T9_RED(" gaps uncertainty panes freshness and phase placement")
E04_T9_RED(" I17 identity modes and I23 authoritative style colors")
#endif
