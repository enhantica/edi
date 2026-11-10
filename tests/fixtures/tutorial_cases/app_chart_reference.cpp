// SPDX-License-Identifier: BSD-3-Clause
// Reference producer: the exact Qt-free services called by PatternChartController,
// never report_model.cpp, report_html.cpp or report.js. UI REGRESSION PINS, not diffraction accuracy.
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

#include "edi/io.hpp"
#include "edi/model.hpp"
#include "edi/presentation.hpp"

namespace {
void lines(const std::vector<edi::HoverLine>& values) {
    std::cout << '[';
    bool first = true;
    for (const auto& line : values) {
        if (!first) std::cout << ',';
        first = false;
        std::cout << "{\"text\":" << std::quoted(line.text) << ",\"style\":" << std::quoted(line.style)
                  << ",\"segments\":[";
        bool segment_first = true;
        for (const auto& segment : line.segments) {
            if (!segment_first) std::cout << ',';
            segment_first = false;
            std::cout << "{\"text\":" << std::quoted(segment.text)
                      << ",\"style\":" << std::quoted(segment.style) << '}';
        }
        std::cout << "]}";
    }
    std::cout << ']';
}
}

int main(int argc, char** argv) {
    if (argc != 2) throw std::invalid_argument("give the reference project path");
    auto project = edi::load_project(argv[1]);
    project.calculate();
    const auto source = edi::capture_pattern(project, 0);
    const auto shown = edi::present_pattern(source, {});
    const auto table = edi::pattern_style_table(edi::kDefaultColourScheme, project.experiments.size(),
                                               project.structures.size());
    const edi::PatternSeries* measured = nullptr;
    for (const auto& series : shown.series) {
        if (series.kind == edi::SeriesKind::Measured) measured = &series;
    }
    if (!measured || measured->points.empty()) throw std::runtime_error("reference needs measured points");
    std::size_t point = 0;
    double distance = std::numeric_limits<double>::infinity();
    for (std::size_t i = 0; i < measured->points.size(); ++i) {
        if (std::isfinite(measured->points[i].x) && std::abs(measured->points[i].x - 83.6) < distance) {
            point = i;
            distance = std::abs(measured->points[i].x - 83.6);
        }
    }
    std::cout << std::setprecision(17) << "{\"kind\":\"app UI regression pins\",\"styles\":[";
    bool first = true;
    for (const auto& style : table) {
        if (!first) std::cout << ',';
        first = false;
        std::cout << "{\"key\":" << std::quoted(style.key) << ",\"light\":" << std::quoted(style.light)
                  << ",\"dark\":" << std::quoted(style.dark) << '}';
    }
    std::cout << "],\"point\":{\"x\":" << measured->points[point].x
              << ",\"y\":" << measured->points[point].y << ",\"lines\":";
    lines(edi::hover_readout(source, *measured, point));
    std::cout << "},\"tick\":{";
    bool found = false;
    for (const auto& series : shown.series) {
        if (series.kind != edi::SeriesKind::BraggTicks) continue;
        for (std::size_t i = 0; i < series.points.size(); ++i) {
            const auto readout = edi::hover_readout(source, series, i);
            std::string text;
            for (const auto& line : readout) {
                text += line.text;
                for (const auto& part : line.segments) text += part.text;
            }
            if (text.find("(3 2 1)") == std::string::npos) continue;
            std::cout << "\"id\":" << std::quoted(series.id) << ",\"style\":" << std::quoted(series.style)
                      << ",\"x\":" << series.points[i].x << ",\"y\":" << series.points[i].y
                      << ",\"lines\":";
            lines(readout);
            found = true;
            break;
        }
        if (found) break;
    }
    if (!found) throw std::runtime_error("the independent nontrivial (3 2 1) tick must exist");
    std::cout << "}}\n";
}
