#include <QCoreApplication>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <algorithm>
#include <array>
#include <cmath>
#include <iostream>
#include <memory>

#include "correlation_view_model.hpp"
#include "edi/io.hpp"

namespace {
int parsed = 0;
}
namespace edi {
double observed_correlation_value(const FitParameterCorrelation& row) {
    ++parsed;
    return correlation_value(row);
}
}  // namespace edi

// Compile the unmodified production view. Only its call to the real parser is counted;
// the observer returns the parser's actual value and never supplies a cached number.
#define correlation_value observed_correlation_value
#include "../../../app/src/correlation_view_model.cpp"
#undef correlation_value

namespace {
using Row = edi::FitParameterCorrelation;
using Rows = std::vector<std::shared_ptr<Row>>;

void define(Row& row, const char* id, const char* left, const char* right, const char* value) {
    row.id = id;
    row.source_kind = "deterministic";
    row.parameter_unique_name_i = left;
    row.parameter_unique_name_j = right;
    row.correlation = value;
}

QJsonObject snapshot(edi_app::CorrelationViewModel& view, const Rows& rows, bool admitted) {
    view.setLevel(0);
    view.setMaxParameters(64);
    QJsonArray labels, cells, pointers, writes;
    const auto names = view.labels();
    const auto values = view.values();
    for (const auto& name : names) labels.append(name);
    for (int i = 0; i < names.size(); ++i) {
        for (int j = 0; j < i; ++j) {
            const double value = values.at(i * names.size() + j);
            if (std::isfinite(value)) {
                const auto ends = std::minmax(names[i], names[j]);
                cells.append(QJsonObject{{"left", ends.first}, {"right", ends.second}, {"value", value}});
            }
        }
    }
    for (const auto& row : rows) {
        pointers.append(QString::number(reinterpret_cast<std::uintptr_t>(row.get())));
        writes.append(QString::number(row->correlation.written()));
    }
    return {{"parses", parsed}, {"available", view.available()}, {"labels", labels},
            {"cells", cells}, {"pointers", pointers}, {"writes", writes}, {"admitted", admitted}};
}

QJsonObject run(const std::string& channel, const std::string& scenario) {
    auto owner = std::make_shared<std::array<Row, 3>>();
    define(owner->at(0), "first", "bank.background.base.coef", "bank.background.ramp.coef", "0.50");
    define(owner->at(1), "second", "bank.background.base.coef", "bank.background.curve.coef", "-0.25");
    define(owner->at(2), "third", "bank.background.ramp.coef", "bank.background.curve.coef", "0.125");
    auto first = std::shared_ptr<Row>(owner, &owner->at(0));
    auto second = std::shared_ptr<Row>(owner, &owner->at(1));
    auto third = std::shared_ptr<Row>(owner, &owner->at(2));
    edi::Project project;
    project.experiment().name = "bank";
    project.fit_result.result_kind = "deterministic";
    edi_app::CorrelationViewModel view(nullptr);
    QJsonArray frames;
    const auto publish = [&](const Rows& rows, const std::string& file = "first.xy", int experiment = 0) {
        project.fit_result.correlations.assign(rows);
        bool admitted = project.fit_result.correlations.size() == rows.size();
        std::vector<std::shared_ptr<const Row>> input;
        for (std::size_t i = 0; i < rows.size(); ++i) {
            const auto& row = project.fit_result.correlations[i];
            admitted = admitted && row.get() == rows[i].get();
            input.push_back(row);
        }
        if (channel == "rows") view.setRows(file, input);
        else view.setRecord(project, experiment, true);
        frames.append(snapshot(view, rows, admitted));
    };
    if (scenario == "alias-reorder") {
        publish({first, second});
        publish({second, first});
    } else if (scenario == "tail-alias-replace") {
        publish({first, second});
        publish({first, third});
    } else if (scenario == "second-coefficient-write") {
        publish({first, second});
        second->correlation = "0.125";
        publish({first, second});
    } else if (scenario == "file-switch" && channel == "record") {
        project.experiments.push_back(std::make_shared<edi::BraggPdExperiment>());
        project.experiments.back()->name = "other";
        second->parameter_unique_name_i = "other.background.base.coef";
        second->parameter_unique_name_j = "other.background.ramp.coef";
        publish({first, second}, "", 0);
        publish({first, second}, "", 1);
        publish({first, second}, "", 0);
    } else {
        publish({first});
        if (scenario == "repeat") {
            publish({first});
            publish({first});
        } else if (scenario == "name-rename") {
            first->parameter_unique_name_i = "renamed.background.base.coef";
            first->parameter_unique_name_j = "renamed.background.ramp.coef";
            publish({first});
        } else if (scenario == "coefficient-write" || scenario == "same-value-write") {
            first->correlation = scenario == "coefficient-write" ? "-0.25" : "0.500";
            publish({first});
        } else if (scenario == "alias-replace") {
            publish({second});
        } else if (scenario == "owner-replace") {
            project.fit_result.correlations.clear();
            std::destroy_at(first.get());
            std::construct_at(first.get());
            define(*first, "first", "bank.background.base.coef", "bank.background.ramp.coef", "-0.875");
            publish({first});
        } else if (scenario == "replace-undo") {
            auto replacement = std::make_shared<Row>(*second);
            publish({replacement});
            publish({first});
        } else if (scenario == "clear-undo" || scenario == "clear-write-undo") {
            publish({});
            if (scenario == "clear-write-undo") first->correlation = "-0.25";
            publish({first});
        } else if (scenario == "file-switch") {
            publish({second}, "second.xy");
            publish({first});
        } else throw std::runtime_error("unknown loaded-cache observation scenario");
    }
    return {{"sameOwner", !first.owner_before(second) && !second.owner_before(first) &&
                          !first.owner_before(third) && !third.owner_before(first)},
            {"frames", frames}};
}
}  // namespace

int main(int argc, char** argv) {
    QCoreApplication application(argc, argv);
    if (argc != 3) return 2;
    try {
        std::cout << QJsonDocument(run(argv[1], argv[2])).toJson(QJsonDocument::Compact).constData() << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
