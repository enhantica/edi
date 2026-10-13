// SPDX-License-Identifier: BSD-3-Clause
#include <doctest/doctest.h>
#include <regex>
#include <string>
#include <vector>
#include <utility>
#include <cmath>
#include "edi/report_html.hpp"

TEST_CASE("Report I40 writes the signed coloured matrix as a text table") {
    edi::ReportModel model;
    model.name = "signed-correlation-witness";
    model.sections = {edi::ReportSection::Correlations};
    model.correlations = edi::ReportCorrelations{
        {"A", "B", "C"}, {1, -1, 0, -1, 1, 0, 0, 0, 1}, 0, 3, {}};
    // A=-B and C independent is a positive semidefinite correlation matrix.
    // Colour values come from the accepted ColorBrewer seam, never the writer.
    const auto html = edi::report_html(model);
    const auto start = html.find("<table class=\"correlations\">");
    REQUIRE_MESSAGE(start != std::string::npos,
                    "I40 the correlation figure is the actual preview-style HTML table");
    const auto end = html.find("</table>", start);
    REQUIRE_MESSAGE(end != std::string::npos, "I40 the correlation table has a complete boundary");
    const auto table = html.substr(start, end - start);
    const std::regex coloured("<td[^>]*background:\\s*(#[0-9a-fA-F]{6})[^>]*>([^<]*)</td>");
    std::vector<std::pair<std::string, std::string>> cells;
    for (auto i = std::sregex_iterator(table.begin(), table.end(), coloured);
         i != std::sregex_iterator(); ++i) cells.emplace_back((*i)[1], (*i)[2]);
    const std::vector<std::pair<std::string, std::string>> expected{
        {"#4575b4", "1.00"}, {"#d73027", "-1.00"}, {"#ffffff", "0.00"},
        {"#d73027", "-1.00"}, {"#4575b4", "1.00"}, {"#ffffff", "0.00"},
        {"#ffffff", "0.00"}, {"#ffffff", "0.00"}, {"#4575b4", "1.00"}};
    CHECK_MESSAGE(cells == expected,
                  "I40 each signed matrix coefficient is text in its independent reference colour");
    CHECK_MESSAGE((table.find("A") != std::string::npos && table.find("B") != std::string::npos &&
                  table.find("C") != std::string::npos),
                  "I40 the table retains every parameter label");
}

TEST_CASE("Report I41 keeps the reference HTML page width while PDF uses A4") {
    edi::ReportModel model;
    model.name = "reference-page-width";
    const auto html = edi::report_html(model);
    const std::regex shell("\\.report-shell\\s*\\{([^}]+)\\}");
    std::smatch rule;
    REQUIRE_MESSAGE(std::regex_search(html, rule, shell),
                    "I41 the exported HTML reaches its actual page-shell style");
    const std::regex width("(?:^|;)\\s*width:\\s*([0-9.]+)(cm|mm|px|pt)\\s*;");
    std::smatch value;
    const auto css = rule[1].str();
    REQUIRE_MESSAGE(std::regex_search(css, value, width),
                    "I41 the HTML page has a measurable physical width");
    const auto unit = value[2].str();
    const double scale = unit == "cm" ? 1 : unit == "mm" ? 0.1 : unit == "px" ? 2.54 / 96 : 2.54 / 72;
    // The owner's supplied diffraction-lib HTML, owner-lbco_simulation.html,
    // .report-shell width 21.59cm, recorded independently before this assertion.
    CHECK_MESSAGE(std::abs(std::stod(value[1]) * scale - 21.59) < 1e-6,
                  "I41 the HTML retains the reference's 21.59 cm width independently of PDF's A4 change");
}
