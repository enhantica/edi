#include <doctest/doctest.h>
#include <algorithm>
#include <cctype>
#include <filesystem>
#include <fstream>
#include <limits>
#include <regex>
#include <sstream>
#include "edi/palette.hpp"
#include "edi/presentation.hpp"
#include "edi/report_html.hpp"

#include "../../fixtures/approved_palettes/assignments.hpp"

TEST_CASE("Every structure count retains its approved Bragg colour") {
    for (const auto& expected : approved_palette::cases) {
        CAPTURE(expected.scheme);
        CAPTURE(expected.count);
        CAPTURE(expected.dark);
        const auto scheme = edi::colour_scheme_from_name(expected.scheme);
        REQUIRE_MESSAGE(scheme.has_value(), "Every independently approved palette resolves through the public API");
        const auto styles = edi::pattern_style_table(*scheme, 1, expected.count);
        edi::PatternSource source;
        source.x = std::make_shared<const std::vector<double>>(std::initializer_list<double>{10,20});
        source.meas = std::make_shared<const std::vector<double>>(std::initializer_list<double>{2,3});
        source.calc = source.meas;
        source.current = true;
        for (std::size_t place = 0; place < expected.count; ++place)
            source.phases.push_back({std::to_string(place), "Structure " + std::to_string(place), place,
                std::make_shared<const std::vector<double>>(std::initializer_list<double>{12.5}), {}, {}});
        const auto shown = edi::present_pattern(source, {});
        std::size_t place = 0;
        for (const auto& series : shown.series) if (series.kind == edi::SeriesKind::BraggTicks) {
            CAPTURE(place);
            const auto row = std::find_if(styles.begin(), styles.end(), [&](const auto& style) { return style.key == series.style; });
            REQUIRE_MESSAGE(row != styles.end(), "Every per-structure series resolves a style beyond the categorical group");
            REQUIRE_MESSAGE(place < expected.colours.size(), "The presentation cannot invent extra structures");
            CHECK_MESSAGE((expected.dark ? row->dark : row->light) == expected.colours[place],
                          "Each tick style equals the approved coordinate or independent whole-group Oklab gradient");
            CHECK_MESSAGE(edi::structure_colour(*scheme, place, expected.count, expected.dark) == expected.colours[place],
                          "Structure icons and tick styles share the independently expected count-aware assignment");
            REQUIRE_MESSAGE(place < shown.bragg_labels.size(), "Every structure retains a row label alongside its ticks");
            CHECK_MESSAGE(shown.bragg_labels[place].style == series.style, "Row labels and ticks retain the same complete structure identity");
            ++place;
        }
        CHECK_MESSAGE(place == source.phases.size(), "Every structure reaches the presentation at categorical and gradient counts");
    }
}

TEST_CASE("Static report borders every filled and empty correlation cell") {
    const double empty = std::numeric_limits<double>::quiet_NaN();
    for (const std::vector<double> values : {std::vector<double>{empty,empty,.65,empty},
                                           std::vector<double>{1,-.25,-.25,1}}) {
        edi::ReportModel model;
        model.sections = {edi::ReportSection::Correlations};
        model.contents = {{"correlations", "Correlations", true}};
        model.correlations = edi::ReportCorrelations{{"alpha", "beta"}, values, .2, 2, {}};
        const auto html = edi::report_static_html(model, 400);
        const std::regex cells(R"(<td\b[^>]*width="43"[^>]*>)");
        std::size_t count = 0;
        for (auto it = std::sregex_iterator(html.begin(), html.end(), cells); it != std::sregex_iterator(); ++it) {
            const std::string cell = it->str();
            for (const auto side : {"top", "right", "bottom", "left"})
                CHECK_MESSAGE(cell.find(std::string("border-") + side + ":") != std::string::npos,
                              "The PDF text source borders every correlation cell on all sides, including missing values");
            ++count;
        }
        CHECK_MESSAGE(count == 4, "The independent two-by-two matrix reaches every actual static report cell");
    }
}
