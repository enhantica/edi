// This host includes the production main and observes its real demo-driver dispatch.
// The observer never starts, stops, resets, selects or replaces a fit.
#define main production_main
#include "../../../app/main.cpp"
#undef main

#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QTimer>

#include "analysis_view_model.hpp"
#include "fit_view_model.hpp"
#include "session.hpp"

namespace {
QJsonObject observed;
std::vector<double> prefit;
QPointer<edi_app::ProjectViewModel> current;
std::vector<double> model_values(const edi::Project& project) {
    std::vector<double> result;
    for (const auto& named : edi::named_parameters(project))
        result.push_back(named.parameter->value.get());
    return result;
}
template <typename Record>
int correlation_count(const Record& record) {
    int count = 0;
    if constexpr (requires { record.correlations; })
        count += static_cast<int>(record.correlations.size());
    if constexpr (requires { record.scan_results; }) {
        for (const auto& [file, bundle] : record.scan_results)
            if (bundle && bundle->correlations)
                count += static_cast<int>(bundle->correlations->values->size());
    }
    return count;
}
QJsonArray result_rows(const edi_app::ProjectViewModel& view) {
    QJsonArray rows;
    if (const auto* scan = view.scanSession())
        for (std::size_t index = 0; index < scan->index().rows.size(); ++index)
            if (scan->index().rows[index].offset >= 0)
                rows.append(QString::fromStdString(scan->datasets().files[index]));
    return rows;
}
QString read_file(const QString& path) {
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly)) return {};
    return QString::fromUtf8(file.readAll());
}
void observe_fit_idle() {
    if (!current || !observed.contains("terminal_published") || result_rows(*current).empty())
        return;
    observed["calculation_pending"] = current->calculating();
    bool stale = false;
    for (const auto& experiment : current->project().experiments)
        stale = stale || !experiment->computed_current();
    observed["calculation_stale"] = stale;
}
void observe_project(edi_app::Session& session) {
    current = session.project();
    if (!current) return;
    auto* fit = current->fit();
    QObject::connect(current, &edi_app::ProjectViewModel::calculatingChanged, current,
                     [] { observe_fit_idle(); });
    QObject::connect(fit, &edi_app::FitViewModel::runningChanged, fit, [fit] {
        if (current && fit->running()) {
            prefit = model_values(current->project());
            observed["follow"] =
                fit->patternUpdates() == 2 && fit->following() ? "adaptive" : "other";
            observed["mode"] = current->analysis()->fittingMode();
            QJsonObject settings;
            const auto& project = current->project();
            if (project.minimizer_max_iterations)
                settings["_minimizer.max_iterations"] =
                    QString::number(project.minimizer_max_iterations);
            if (project.minimizer_type)
                settings["_minimizer.type"] = QString::fromStdString(*project.minimizer_type);
            if (!project.descent.empty())
                settings["_minimizer.descent"] = QString::fromStdString(project.descent);
            if (project.minimizer_chi_square_tolerance)
                settings["_minimizer.chi_square_tolerance"] =
                    QString::number(project.minimizer_chi_square_tolerance, 'g', 17);
            observed["settings"] = settings;
        }
    });
    QObject::connect(fit, &edi_app::FitViewModel::refused, fit,
                     [](const QString& reason) { observed["refused"] = QJsonArray{reason}; });
    QObject::connect(fit, &edi_app::FitViewModel::scanFinished, fit, [fit] {
        observed["terminal_published"] = !fit->running() && !fit->outcome().isEmpty();
        observed["outcome"] = fit->outcome();
        observed["completed_files"] = fit->scanFitted();
        if (current) {
            observed["results_csv"] = read_file(QString::fromStdString(current->project().path) +
                                                "/analysis/results.csv");
            observed["result_files"] = result_rows(*current);
            observe_fit_idle();
        }
    });
}
void install_observer() {
    QTimer::singleShot(0, QCoreApplication::instance(), [] {
        const auto windows = QGuiApplication::topLevelWindows();
        for (auto* window : windows) {
            auto* quick = qobject_cast<QQuickWindow*>(window);
            auto* engine = quick ? qmlEngine(quick->contentItem()) : nullptr;
            auto* session =
                engine ? engine->singletonInstance<edi_app::Session*>("edi.app", "Session")
                       : nullptr;
            if (!session) continue;
            QObject::connect(session, &edi_app::Session::projectChanged, session,
                             [session] { observe_project(*session); });
            observe_project(*session);
            QObject::connect(
                QCoreApplication::instance(), &QCoreApplication::aboutToQuit, session, [] {
                    if (current) {
                        const auto& project = current->project();
                        QJsonArray files;
                        for (const auto* name :
                             {"results.csv", "results-provenance.csv", "scan-notes.csv"})
                            if (QFile::exists(QString::fromStdString(project.path) + "/analysis/" +
                                              name))
                                files.append(name);
                        const auto rows = result_rows(*current);
                        observed["reset"] = QJsonObject{
                            {"remaining_files", files},
                            {"result_rows", rows},
                            {"dataset_fit_outcomes", rows},
                            {"dataset_correlations", correlation_count(project.fit_result)},
                            {"prefit_values_restored", model_values(project) == prefit},
                            {"undo_available", current->canUndo()},
                            {"calculation_pending", current->calculating()}};
                    }
                    QFile output(qEnvironmentVariable("EDI_TIMING_OBSERVER_OUTPUT"));
                    if (output.open(QIODevice::WriteOnly))
                        output.write(QJsonDocument(observed).toJson());
                });
            break;
        }
    });
}
Q_COREAPP_STARTUP_FUNCTION(install_observer)
}  // namespace
int main(int argc, char** argv) { return production_main(argc, argv); }
