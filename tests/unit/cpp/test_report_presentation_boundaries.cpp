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

template<class Scheme>
auto structure_styles(Scheme scheme, std::size_t count) {
    if constexpr (requires { edi::pattern_style_table(scheme, 1, count); })
        return edi::pattern_style_table(scheme, 1, count);
    else
        return edi::pattern_style_table(scheme);
}

TEST_CASE("Every structure palette entry and wraparound retains its Bragg colour") {
    const auto root = std::filesystem::path(__FILE__).parent_path().parent_path().parent_path().parent_path();
    for (const auto name : edi::colour_scheme_names()) {
        CAPTURE(name);
        std::string filename;
        for (const unsigned char letter : name) {
            if (std::isupper(letter)) filename += '-';
            filename += static_cast<char>(std::tolower(letter));
        }
        std::ifstream file(root / "data/palettes" / (filename + ".tsv"));
        REQUIRE_MESSAGE(file.good(), "ADR-0038 the frozen palette data supplies the consumer reference");
        std::vector<std::pair<std::string, std::string>> colours;
        for (std::string line; std::getline(file, line);) {
            std::istringstream row(line);
            std::string role, light, dark;
            std::size_t index = 0;
            if (row >> role >> index >> light >> dark; role == "structure") colours.emplace_back(light, dark);
        }
        REQUIRE_MESSAGE(!colours.empty(), "ADR-0038 every supplied scheme declares its structure set");
        const auto scheme = edi::colour_scheme_from_name(name);
        REQUIRE_MESSAGE(scheme.has_value(), "Every frozen scheme token resolves through the public palette API");
        const auto styles = structure_styles(*scheme, 2 * colours.size() + 1);
        edi::PatternSource source;
        source.x = std::make_shared<const std::vector<double>>(std::initializer_list<double>{10,20});
        source.meas = std::make_shared<const std::vector<double>>(std::initializer_list<double>{2,3});
        source.calc = source.meas;
        source.current = true;
        for (std::size_t place = 0; place < 2 * colours.size() + 1; ++place)
            source.phases.push_back({std::to_string(place), "Structure " + std::to_string(place), place,
                std::make_shared<const std::vector<double>>(std::initializer_list<double>{12.5}), {}, {}});
        const auto shown = edi::present_pattern(source, {});
        std::size_t place = 0;
        for (const auto& series : shown.series) if (series.kind == edi::SeriesKind::BraggTicks) {
            CAPTURE(place);
            const auto row = std::find_if(styles.begin(), styles.end(), [&](const auto& style) { return style.key == series.style; });
            REQUIRE_MESSAGE(row != styles.end(), "Every Bragg series resolves a style, including entries past the third");
            const auto& expected = colours[place % colours.size()];
            CHECK_MESSAGE(row->light == expected.first, "Bragg ticks retain the frozen structure colour in the light theme");
            CHECK_MESSAGE(row->dark == expected.second, "Bragg ticks retain the frozen structure colour in the dark theme");
            CHECK_MESSAGE(edi::structure_colour(*scheme, place, false) == expected.first,
                          "Structure lists and Bragg consumers agree with each actual palette entry and wraparound");
            REQUIRE_MESSAGE(place < shown.bragg_labels.size(), "Every structure retains a row label alongside its ticks");
            CHECK_MESSAGE(shown.bragg_labels[place].style == series.style, "Bragg row labels retain the same colour identity as their ticks");
            ++place;
        }
        CHECK_MESSAGE(place == source.phases.size(), "The complete structure set and wraparound all reach the presentation");
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
