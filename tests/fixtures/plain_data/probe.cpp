#include <QElapsedTimer>
#include <QEventLoop>
#include <QFileInfo>
#include <QGuiApplication>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QMetaObject>
#include <QUrl>
#include <QtQml>
#include <filesystem>
#include <fstream>
#include <iostream>

#include "analysis_view_model.hpp"
#include "correlation_view_model.hpp"
#include "edi/io.hpp"
#include "experiment_view_model.hpp"
#include "fit_view_model.hpp"
#include "project_view_model.hpp"
#include "session.hpp"
#include "structure_view_model.hpp"
Q_IMPORT_QML_PLUGIN(edi_appPlugin)

namespace {
QJsonArray correlation_pairs(const edi::Project& project) {
    QJsonArray result;
    for (const auto& pair : project.fit_result.correlations)
        result.append(
            QJsonObject{{"i", QString::fromStdString(pair->parameter_unique_name_i.value())},
                        {"j", QString::fromStdString(pair->parameter_unique_name_j.value())},
                        {"coefficient", QString::fromStdString(pair->correlation.value())},
                        {"file", QString::fromStdString(pair->file_path.value())}});
    return result;
}
QJsonObject reference_state(const edi::Project& project) {
    QJsonArray aliases, links, textures;
    for (const auto& alias : project.aliases)
        aliases.append(QString::fromStdString(alias->parameter_unique_name.value()));
    for (const auto& bank : project.experiments) {
        for (const auto& row : bank->linked_structures)
            links.append(QString::fromStdString(row->structure_id.value()));
        for (const auto& row : bank->preferred_orientation)
            textures.append(QString::fromStdString(row->structure_id.value()));
    }
    return {{"aliases", aliases},
            {"pairs", correlation_pairs(project)},
            {"links", links},
            {"textures", textures}};
}
void settle_projection(edi_app::ProjectViewModel& view);
QJsonObject template_reference(edi_app::ProjectViewModel& view) {
    return reference_state(view.scanTemplate() ? *view.scanTemplate() : view.project());
}
void rename_action(edi_app::ProjectViewModel& view, const std::string& kind, const QString& name) {
    if (kind == "structure")
        view.structureModels()[0]->setName(name);
    else if (kind == "experiment")
        view.experimentModels()[0]->setName(name);
    else if (kind == "site") {
        if (!view.structureModels()[0]->atomSites()->setText(0, "label", name))
            throw std::runtime_error("the actual app site rename was refused");
    } else if (!view.experimentModels()[0]->background()->setId(0, name))
        throw std::runtime_error("the actual app point rename was refused");
}
QString block_name(edi_app::ProjectViewModel& view, const std::string& kind) {
    return kind == "structure" ? view.structureModels()[0]->name()
                               : view.experimentModels()[0]->name();
}
QJsonObject rename_lifecycle(const QString& fixture, const QString& work, const std::string& kind,
                             bool undo_rename = false, bool scan = false, bool refused = false,
                             bool historical = false) {
    const auto input = std::filesystem::path(work.toStdString()) / "input";
    std::filesystem::copy(fixture.toStdString(), input, std::filesystem::copy_options::recursive);
    auto core = edi::load_project(input.string());
    if (scan) {
        std::filesystem::create_directories(input / "experiments/scan");
        for (const char* file : {"01.xy", "02.xy"})
            if (!std::filesystem::exists(input / "experiments/scan" / file))
                std::ofstream(input / "experiments/scan" / file) << "40 5.125 1\n44 6.375 1\n";
        core.fitting_mode = "sequential";
        core.sequential_fit.data_dir = "experiments/scan";
        core.sequential_fit.file_pattern = "*.xy";
        core.sequential_fit.template_file = "02.xy";
    }
    if (refused) {
        if (kind == "structure") {
            edi::Structure occupied = core.structure();
            occupied.name = "taken";
            core.structures.push_back(occupied);
        } else {
            edi::BraggPdExperiment occupied = core.experiment();
            occupied.name = "taken";
            core.experiments.push_back(occupied);
            core.fitting_mode = "joint";
        }
    }
    if (historical) {
        if (scan)
            core.fit_sequential();
        else
            core.fit();
        if (core.fit_result.correlations.empty())
            throw std::runtime_error("a real fit must produce history before the row disappears");
        std::vector<edi::FitParameterCorrelation> reverse;
        for (const auto& row : core.fit_result.correlations) {
            edi::FitParameterCorrelation pair = *row;
            pair.id = pair.id.value() + "_reverse";
            const std::string first = pair.parameter_unique_name_i;
            pair.parameter_unique_name_i = pair.parameter_unique_name_j.value();
            pair.parameter_unique_name_j = first;
            reverse.push_back(pair);
        }
        for (const auto& pair : reverse) core.fit_result.correlations.push_back(pair);
        std::vector<std::shared_ptr<edi::PolynomialTerm>> kept;
        for (const auto& term : core.experiment().background_terms)
            if (term->id.value() != "curve") kept.push_back(term);
        core.experiment().background_terms.assign(std::move(kept));
    }
    if (core.structure().name.value() == "structure") {
        auto& cell = core.structure().cell;
        for (auto* parameter : {&cell.length_a, &cell.length_b, &cell.length_c, &cell.angle_alpha,
                                &cell.angle_beta, &cell.angle_gamma}) {
            parameter->start_value = parameter->value.get() + .125;
            parameter->start_uncertainty = .03125;
        }
    }
    std::vector<std::string> names;
    if (kind == "structure" || kind == "experiment") {
        const std::string structure_name = core.structure().name.value();
        const std::string experiment_name = core.experiment().name.value();
        for (const std::string field :
             {"length_a", "length_b", "length_c", "angle_alpha", "angle_beta", "angle_gamma"})
            names.push_back(structure_name + ".cell." + field);
        names.push_back(experiment_name + ".instrument.setup_wavelength");
        names.push_back(experiment_name + ".linked_structure." + structure_name + ".scale");
        if (core.experiment().preferred_orientation.empty()) {
            edi::PrefOrient texture;
            texture.structure_id = structure_name;
            texture.march_r = .73;
            texture.march_random_fract = .2;
            texture.index_l = 1;
            core.experiment().preferred_orientation.push_back(texture);
        }
        names.push_back(experiment_name + ".preferred_orientation." + structure_name + ".march_r");
        names.push_back(experiment_name + ".preferred_orientation." + structure_name +
                        ".march_random_fract");
    } else if (kind == "site")
        for (const std::string field : {"fract_x", "fract_y", "fract_z", "occupancy", "adp_iso"})
            names.push_back("phase.atom_site.A." + field);
    else
        names = {"bank.background.pA.intensity"};
    int ordinal = 0;
    for (const auto& name : names) {
        edi::ParameterAlias alias;
        alias.id = "ref" + std::to_string(ordinal);
        alias.parameter_unique_name = name;
        core.aliases.push_back(alias);
        for (bool first : {true, false}) {
            edi::FitParameterCorrelation pair;
            pair.id = "pair" + std::to_string(ordinal) + (first ? "i" : "j");
            pair.source_kind = "deterministic";
            pair.parameter_unique_name_i =
                first ? name : core.structure().name.value() + ".cell.length_b";
            pair.parameter_unique_name_j =
                first ? core.structure().name.value() + ".cell.length_b" : name;
            pair.correlation = "-0.625";
            if (scan) pair.file_path = "02.xy";
            core.fit_result.correlations.push_back(pair);
        }
        ++ordinal;
    }
    edi::save_project(core, input.string());
    edi_app::Session session;
    if (!session.openProject(QUrl::fromLocalFile(QString::fromStdString(input.string()))))
        throw std::runtime_error(session.lastError().toStdString());
    auto& view = *session.project();
    settle_projection(view);
    if (scan) {
        view.setCurrentExperimentIndex(0);
        settle_projection(view);
    }
    QJsonObject result{{"before", reference_state(view.project())},
                       {"beforeTemplate", template_reference(view)},
                       {"beforeCanUndo", view.canUndo()}};
    if (undo_rename) {
        result["nameBefore"] = block_name(view, kind);
        result["templateBefore"] =
            QString::fromStdString((view.scanTemplate() ? *view.scanTemplate() : view.project())
                                       .sequential_fit.template_file);
    }
    const QString wanted = refused                ? "taken"
                           : kind == "structure"  ? "new_phase"
                           : kind == "experiment" ? "new_bank"
                           : kind == "site"       ? "new_site"
                                                  : "new_point";
    rename_action(view, kind, wanted);
    settle_projection(view);
    result["renamed"] = reference_state(view.project());
    result["renamedTemplate"] = template_reference(view);
    result["renameCanUndo"] = view.canUndo();
    if (undo_rename) result["nameRenamed"] = block_name(view, kind);
    const QString saved = work + "/saved";
    if (!session.saveAs(QUrl::fromLocalFile(saved)))
        throw std::runtime_error(session.lastError().toStdString());
    if (undo_rename)
        view.undo();
    else {
        view.removeStructure(0);
        view.undo();
    }
    settle_projection(view);
    result["undone"] = reference_state(view.project());
    result["undoneTemplate"] = template_reference(view);
    if (undo_rename) {
        result["nameUndone"] = block_name(view, kind);
        result["undoCanUndo"] = view.canUndo();
        result["templateUndone"] =
            QString::fromStdString((view.scanTemplate() ? *view.scanTemplate() : view.project())
                                       .sequential_fit.template_file);
        if (!session.saveAs(QUrl::fromLocalFile(work + "/undone-saved")))
            throw std::runtime_error(session.lastError().toStdString());
    }
    session.closeProject();
    if (!session.openProject(QUrl::fromLocalFile(saved)))
        throw std::runtime_error(session.lastError().toStdString());
    settle_projection(*session.project());
    result["reopened"] = reference_state(session.project()->project());
    if (undo_rename) {
        result["nameReopened"] = block_name(*session.project(), kind);
        if (!refused) {
            const auto before_second = reference_state(session.project()->project());
            rename_action(*session.project(), kind, "another_name");
            session.project()->undo();
            settle_projection(*session.project());
            result["afterReloadBefore"] = before_second;
            result["afterReloadUndo"] = reference_state(session.project()->project());
        }
        session.closeProject();
        if (!session.openProject(QUrl::fromLocalFile(work + "/undone-saved")))
            throw std::runtime_error(session.lastError().toStdString());
        settle_projection(*session.project());
        if (scan) {
            session.project()->setCurrentExperimentIndex(0);
            settle_projection(*session.project());
        }
        result["undoReopened"] = reference_state(session.project()->project());
        result["undoReopenedTemplate"] = template_reference(*session.project());
    }
    return result;
}
QJsonObject matrix(edi_app::ProjectViewModel& view) {
    view.correlations()->setLevel(0);
    view.correlations()->setMaxParameters(3);
    QJsonArray labels, values;
    for (const auto& label : view.correlations()->labels()) labels.append(label);
    for (const auto value : view.correlations()->values()) values.append(value);
    return {
        {"labels", labels},
        {"values", values},
        {"available", view.correlations()->available()},
        {"emptyText", view.correlations()->emptyText()},
        {"pairs", correlation_pairs(view.scanTemplate() ? *view.scanTemplate() : view.project())}};
}
void settle_projection(edi_app::ProjectViewModel& view) {
    QElapsedTimer timer;
    timer.start();
    do {
        QCoreApplication::processEvents(QEventLoop::AllEvents, 10);
    } while (!view.pendingRefusal().isEmpty() && timer.elapsed() < 10000);
    if (!view.pendingRefusal().isEmpty())
        throw std::runtime_error(view.pendingRefusal().toStdString());
}
void fit_and_wait(edi_app::ProjectViewModel& view) {
    bool finished = false;
    const auto connection =
        QObject::connect(view.fit(), &edi_app::FitViewModel::finished, [&] { finished = true; });
    view.fit()->start();
    QElapsedTimer timer;
    timer.start();
    while (!finished && timer.elapsed() < 20000)
        QCoreApplication::processEvents(QEventLoop::AllEvents, 10);
    QObject::disconnect(connection);
    if (!finished || view.fit()->running() || view.fit()->outcome() != "success")
        throw std::runtime_error("the actual Single fit did not complete successfully");
}
QJsonObject correlation_lifecycle(const std::string& action, const QString& fixture,
                                  const QString& work, const QString& mode, bool history) {
    const auto input = std::filesystem::path(work.toStdString()) / "input";
    std::filesystem::copy(fixture.toStdString(), input, std::filesystem::copy_options::recursive);
    auto core = edi::load_project(input.string());
    const auto fit = [&](const edi::FileCompleteCallback& completed,
                         const edi::CancelCallback& cancelled) {
        return mode == "sequential" ? core.fit_sequential({}, {}, {}, completed, cancelled)
                                    : core.fit_independent({}, {}, {}, completed, cancelled);
    };
    QJsonObject result;
    if (action == "correlation-cancel") {
        core.sequential_fit.template_file = "01.xy";
        if (history) {
            edi::FitParameterCorrelation stale;
            stale.id = "previous";
            stale.source_kind = "deterministic";
            stale.parameter_unique_name_i = "bank.background.base.coef";
            stale.parameter_unique_name_j = "bank.background.ramp.coef";
            stale.correlation = "-0.125";
            stale.file_path = "01.xy";
            core.fit_result.correlations.push_back(stale);
        }
        int completed = 0;
        result["before"] = correlation_pairs(core);
        fit({}, [] { return true; });
        result["cancelBeforeAny"] = correlation_pairs(core);
        fit([&](const edi::ScanFileRecord&) { ++completed; }, [&] { return completed == 1; });
        result["completed"] = completed;
        result["cancelled"] = correlation_pairs(core);
        edi::save_project_as(core, (std::filesystem::path(work.toStdString()) / "saved").string());
        core = edi::load_project((std::filesystem::path(work.toStdString()) / "saved").string());
        result["reopened"] = correlation_pairs(core);
        QJsonArray resumed;
        fit(
            [&](const edi::ScanFileRecord& row) {
                resumed.append(QString::fromStdString(row.file_name));
            },
            {});
        result["resumedFiles"] = resumed;
        result["resumed"] = correlation_pairs(core);
        QJsonArray noop;
        fit(
            [&](const edi::ScanFileRecord& row) {
                noop.append(QString::fromStdString(row.file_name));
            },
            {});
        result["noopFiles"] = noop;
        result["noop"] = correlation_pairs(core);
        edi::save_project_as(
            core, (std::filesystem::path(work.toStdString()) / "completed-saved").string());
        result["memoryAfterSave"] = correlation_pairs(core);
        const auto saved_core = edi::load_project(
            (std::filesystem::path(work.toStdString()) / "completed-saved").string());
        result["completedReopened"] = correlation_pairs(saved_core);
        return result;
    }
    if (history) {
        core.sequential_fit.template_file = "02.xy";
        fit({}, {});
        // An independently assigned stale matrix makes replacement observable even
        // when Single and the preceding scan fit the same design matrix.
        for (const auto& pair : core.fit_result.correlations)
            if (pair->file_path.value() == "02.xy") pair->correlation = "-0.125";
        edi::save_project(core, input.string());
    }
    edi_app::Session session;
    if (!session.openProject(QUrl::fromLocalFile(QString::fromStdString(input.string()))))
        throw std::runtime_error(session.lastError().toStdString());
    auto& view = *session.project();
    settle_projection(view);
    view.setCurrentExperimentIndex(0);
    settle_projection(view);
    result["otherBefore"] = matrix(view);
    view.setCurrentExperimentIndex(1);
    settle_projection(view);
    result["before"] = matrix(view);
    view.analysis()->setFittingMode("single");
    settle_projection(view);
    if (view.analysis()->fittingMode() != "single")
        throw std::runtime_error("the admitted Single-mode edit did not take effect");
    fit_and_wait(view);
    result["fitted"] = matrix(view);
    view.setCurrentExperimentIndex(0);
    settle_projection(view);
    result["otherAfter"] = matrix(view);
    view.setCurrentExperimentIndex(1);
    settle_projection(view);
    result["selectedAgain"] = matrix(view);
    const QString saved = work + "/saved";
    if (!session.saveAs(QUrl::fromLocalFile(saved)))
        throw std::runtime_error(session.lastError().toStdString());
    view.undo();
    result["undone"] = matrix(view);
    session.closeProject();
    if (!session.openProject(QUrl::fromLocalFile(saved)))
        throw std::runtime_error(session.lastError().toStdString());
    session.project()->setCurrentExperimentIndex(1);
    settle_projection(*session.project());
    result["reopened"] = matrix(*session.project());
    if (history) {
        session.project()->analysis()->setFittingMode(mode);
        settle_projection(*session.project());
        session.project()->fit()->reset();
        result["reset"] = matrix(*session.project());
        session.project()->undo();
        result["undoReset"] = matrix(*session.project());
    }
    return result;
}
QJsonObject correlation_save_stability(const QString& fixture, const QString& work,
                                       const QString& mode, const std::string& scenario,
                                       bool later) {
    const auto input = std::filesystem::path(work.toStdString()) / "input";
    std::filesystem::copy(fixture.toStdString(), input, std::filesystem::copy_options::recursive);
    std::filesystem::copy_file(input / "experiments/scan/02.xy", input / "experiments/scan/03.xy");
    if (scenario == "partial") {
        // A larger third input lets the actual UI stop after the first two completion events.
        std::ofstream third(input / "experiments/scan/03.xy");
        for (int index = 0; index < 100000; ++index) {
            const double x = 40.0 + 12.0 * index / 99999.0;
            const double offset = x - 40.0;
            third << x << ' ' << 4.125 + .75 * offset + .125 * offset * offset << " 1\n";
        }
    }
    auto core = edi::load_project(input.string());
    core.sequential_fit.template_file = later ? "02.xy" : "01.xy";
    edi::save_project(core, input.string());
    edi_app::Session session;
    if (!session.openProject(QUrl::fromLocalFile(QString::fromStdString(input.string()))))
        throw std::runtime_error(session.lastError().toStdString());
    auto& view = *session.project();
    view.analysis()->setFittingMode(mode);
    const auto stop = QObject::connect(view.fit(), &edi_app::FitViewModel::scanFittedChanged, [&] {
        if (scenario == "partial" && view.fit()->scanFitted() >= 2) view.fit()->cancel();
    });
    bool finished = false;
    const auto finish = QObject::connect(view.fit(), &edi_app::FitViewModel::scanFinished,
                                         [&] { finished = true; });
    view.fit()->start();
    QElapsedTimer timer;
    timer.start();
    while (!finished && timer.elapsed() < 20000)
        QCoreApplication::processEvents(QEventLoop::AllEvents, 10);
    QObject::disconnect(stop);
    QObject::disconnect(finish);
    if (!finished || view.fit()->running() || view.fit()->scanFitted() < 2)
        throw std::runtime_error(
            "the real scan must complete enough datasets to reach a later template");
    QJsonObject result{{"fitted", view.fit()->scanFitted()},
                       {"outcome", view.fit()->outcome()},
                       {"template", later ? "02.xy" : "01.xy"}};
    for (int index : {0, 1}) {
        view.setCurrentExperimentIndex(index);
        settle_projection(view);
        result[index == 0 ? "firstLive" : "laterLive"] = matrix(view);
    }
    if (scenario == "single-undo") {
        view.setCurrentExperimentIndex(later ? 1 : 0);
        settle_projection(view);
        view.analysis()->setFittingMode("single");
        fit_and_wait(view);
        view.undo();
        settle_projection(view);
    } else if (scenario == "reset-undo") {
        view.fit()->reset();
        view.undo();
        settle_projection(view);
    }
    const QString saved = work + "/saved";
    if (!session.saveAs(QUrl::fromLocalFile(saved)))
        throw std::runtime_error(session.lastError().toStdString());
    result["savedPairs"] = correlation_pairs(edi::load_project(saved.toStdString()));
    result["otherAfterSave"] = matrix(view);
    // Core's unchanged save is a control for the app's cache aggregation.
    auto restored_core = edi::load_project(saved.toStdString());
    edi::save_project_as(restored_core, (work + "/core-copy").toStdString());
    session.closeProject();
    if (!session.openProject(QUrl::fromLocalFile(saved)))
        throw std::runtime_error(session.lastError().toStdString());
    for (int index : {0, 1}) {
        session.project()->setCurrentExperimentIndex(index);
        settle_projection(*session.project());
        result[index == 0 ? "firstReopened" : "laterReopened"] = matrix(*session.project());
    }
    if (!session.saveAs(QUrl::fromLocalFile(work + "/saved-again")))
        throw std::runtime_error(session.lastError().toStdString());
    session.closeProject();
    if (!session.openProject(QUrl::fromLocalFile(work + "/saved-again")))
        throw std::runtime_error(session.lastError().toStdString());
    if (!session.saveAs(QUrl::fromLocalFile(work + "/saved-third")))
        throw std::runtime_error(session.lastError().toStdString());
    return result;
}
QJsonObject template_persistence(const QString& fixture, const QString& work) {
    const auto input = std::filesystem::path(work.toStdString()) / "input";
    std::filesystem::copy(fixture.toStdString(), input, std::filesystem::copy_options::recursive);
    auto core = edi::load_project(input.string());
    core.sequential_fit.template_file = "01.xy";
    edi::save_project(core, input.string());
    edi_app::Session session;
    if (!session.openProject(QUrl::fromLocalFile(QString::fromStdString(input.string()))))
        throw std::runtime_error(session.lastError().toStdString());
    auto& view = *session.project();
    settle_projection(view);
    bool entered = false;
    const auto connection = QObject::connect(view.fit(), &edi_app::FitViewModel::runningChanged,
                                             [&] { entered = entered || view.fit()->running(); });
    view.fit()->start();
    QElapsedTimer timer;
    timer.start();
    while (view.fit()->running() && timer.elapsed() < 20000)
        QCoreApplication::processEvents(QEventLoop::AllEvents, 10);
    QObject::disconnect(connection);
    if (!entered || view.fit()->running())
        throw std::runtime_error("the actual scan did not enter and complete on its worker");
    QJsonObject result;
    for (int index : {0, 1}) {
        view.setCurrentExperimentIndex(index);
        settle_projection(view);
        result[index == 0 ? "templateLive" : "otherLive"] = matrix(view);
    }
    const QString saved = work + "/saved";
    if (!session.saveAs(QUrl::fromLocalFile(saved)))
        throw std::runtime_error(session.lastError().toStdString());
    result["savedPairs"] = correlation_pairs(edi::load_project(saved.toStdString()));
    result["otherAfterSave"] = matrix(view);
    session.closeProject();
    if (!session.openProject(QUrl::fromLocalFile(saved)))
        throw std::runtime_error(session.lastError().toStdString());
    for (int index : {0, 1}) {
        session.project()->setCurrentExperimentIndex(index);
        settle_projection(*session.project());
        result[index == 0 ? "templateReopened" : "otherReopened"] = matrix(*session.project());
    }
    return result;
}
QJsonArray numbers(const std::vector<double>& values) {
    QJsonArray result;
    for (double v : values) result.append(v);
    return result;
}
QJsonArray links(const edi::ExperimentBase& experiment) {
    QJsonArray result;
    for (const auto& link : experiment.linked_structures)
        result.append(QString::fromStdString(link->structure_id.value()));
    return result;
}
QJsonArray parameter_state(const std::vector<edi::Parameter*>& values) {
    QJsonArray result;
    for (const auto* parameter : values)
        result.append(QJsonArray{parameter->value.get(), parameter->free.get()});
    return result;
}
QJsonObject state(edi_app::ProjectViewModel& view) {
    const auto& p = view.project();
    QJsonArray experiments, structures, parameters;
    for (auto* parameter : const_cast<edi::Project&>(p).parameters())
        parameters.append(QJsonArray{parameter->value.get(), parameter->free.get()});
    for (int i = 0; i < static_cast<int>(p.experiments.size()); ++i) {
        const auto& e = *p.experiments[i];
        auto* vm = view.experimentModels()[i];
        QJsonArray excluded;
        for (const auto& region : e.excluded_regions)
            excluded.append(QJsonArray{region->first.get(), region->second.get()});
        QJsonObject row{
            {"excluded", excluded},
            {"name", QString::fromStdString(e.name.value())},
            {"simulation", e.calculation_only},
            {"links", links(e)},
            {"weight", vm->datasetWeight()},
            {"canLoadData", vm->canLoadData()},
            {"beam", vm->beamModeToken()},
            {"file", view.experiments()->get(i, "file").toString()},
            {"range", QJsonArray{vm->measuredRange()->minimum(), vm->measuredRange()->maximum(),
                                 vm->measuredRange()->step()}}};
        auto& mutable_e = *const_cast<edi::BraggPdExperiment*>(&e);
        row["instrument"] = parameter_state(mutable_e.instrument.parameters());
        row["peak"] = parameter_state(mutable_e.peak.parameters());
        QJsonArray background;
        for (const auto& point : e.background)
            background.append(QJsonArray{point->position.get(), point->intensity.value.get(),
                                         point->intensity.free.get()});
        row["background"] = background;
        if (e.data.has_value()) {
            const auto& d = *e.data;
            const auto axis = e.effective_beam_mode() == edi::BeamModeEnum::CONSTANT_WAVELENGTH
                                  ? d.two_theta.get()
                                  : d.time_of_flight.get();
            row["x"] = axis ? numbers(*axis) : QJsonArray{};
            row["y"] = numbers(d.intensity_meas.get());
            row["sigma"] = numbers(d.intensity_meas_su.get());
        }
        experiments.append(row);
    }
    for (const auto& s : p.structures) {
        QJsonArray sites;
        for (const auto& site : s->atom_sites) {
            sites.append(QJsonObject{
                {"id", QString::fromStdString(site->id.value())},
                {"type", QString::fromStdString(site->type_symbol.value())},
                {"xyz", QJsonArray{site->fract_x.value.get(), site->fract_y.value.get(),
                                   site->fract_z.value.get()}},
                {"occupancy", site->occupancy.value.get()},
                {"biso", site->adp_iso.value.get()}});
        }
        structures.append(QJsonObject{
            {"name", QString::fromStdString(s->name.value())},
            {"group", QString::fromStdString(s->space_group.name_h_m.value())},
            {"cell", QJsonArray{s->cell.length_a.value.get(), s->cell.length_b.value.get(),
                                s->cell.length_c.value.get(), s->cell.angle_alpha.value.get(),
                                s->cell.angle_beta.value.get(), s->cell.angle_gamma.value.get()}},
            {"sites", sites}});
    }
    return {{"experiments", experiments},
            {"fittingMode",
             QString::fromStdString(p.fitting_mode.empty() ? "single" : p.fitting_mode)},
            {"structures", structures},
            {"parameters", parameters},
            {"canCreate", view.canCreateExperiment()},
            {"canUndo", view.canUndo()}};
}
bool create(edi_app::ProjectViewModel& view) {
    bool result = false;
    return QMetaObject::invokeMethod(&view, "createStructure", Q_RETURN_ARG(bool, result)) &&
           result;
}
bool load(edi_app::ProjectViewModel& view, int index, const QString& file) {
    bool result = false;
    return QMetaObject::invokeMethod(&view, "loadData", Q_RETURN_ARG(bool, result),
                                     Q_ARG(int, index), Q_ARG(QUrl, QUrl::fromLocalFile(file))) &&
           result;
}
QJsonArray messages(edi_app::Session& session) {
    QJsonArray result;
    auto* model = session.loadWarnings();
    for (int i = 0; i < model->count(); ++i) result.append(model->get(i, "message").toString());
    return result;
}
void configure(edi_app::ProjectViewModel& view, const QString& beam, bool renamed) {
    if (!create(view) || !view.createExperiment())
        throw std::runtime_error("lifecycle setup refused");
    if (beam == "tof" && !view.setExperimentType(0, "beamMode", "time-of-flight"))
        throw std::runtime_error("TOF lifecycle setup refused");
    auto* vm = view.currentExperiment();
    vm->setRange(beam == "tof" ? 2400 : 14, beam == "tof" ? 2412 : 16, beam == "tof" ? 3 : 0.5);
    if (renamed) {
        vm->setName("User_name");
        if (vm->name() != "User_name")
            throw std::runtime_error("renamed lifecycle setup did not retain its valid user name");
    }
    vm->setDatasetWeight(2.5);
    auto& experiment = *const_cast<edi::Project&>(view.project()).experiments[0];
    if (beam == "tof") {
        experiment.instrument.calib_d_to_tof_offset.value = 7.0;
        experiment.peak.broad_gauss_sigma_0.value = 0.0625;
    } else {
        if (!experiment.instrument.calib_twotheta_offset || !experiment.peak.broad_gauss_w)
            throw std::runtime_error("CWL lifecycle settings unavailable");
        experiment.instrument.calib_twotheta_offset->value = 0.125;
        experiment.peak.broad_gauss_w->value = 0.0625;
    }
    if (experiment.background.empty()) {
        edi::LineSegment point;
        point.position = beam == "tof" ? 2400 : 14;
        point.intensity.value = 4.25;
        experiment.background.push_back(point);
    } else {
        experiment.background[0]->intensity.value = 4.25;
    }
    experiment.excluded_regions =
        edi::excluded_region_rows({{beam == "tof" ? 9000 : 60, beam == "tof" ? 9100 : 61}});
}
}  // namespace
int main(int argc, char** argv) {
    QGuiApplication app(argc, argv);
    if (argc < 2) return 2;
    const std::string mode = argv[1];
    if (argc != (mode == "identity" ? 8 : 7)) return 2;
    const std::string escape = argv[5];
    const QString fixture = QString::fromLocal8Bit(argv[2]);
    const QString work = QString::fromLocal8Bit(argv[3]);
    const QString beam = QString::fromLocal8Bit(argv[4]);
    QJsonObject result;
    try {
        if (mode == "correlation-historical-rename") {
            result = rename_lifecycle(fixture, work, escape, true, beam == "scan", false, true);
            std::cout << QJsonDocument(result).toJson(QJsonDocument::Compact).constData() << '\n';
            return 0;
        }
        if (mode == "correlation-default-rename") {
            result = rename_lifecycle(fixture, work, "structure", true, beam == "scan");
            std::cout << QJsonDocument(result).toJson(QJsonDocument::Compact).constData() << '\n';
            return 0;
        }
        if (mode == "correlation-rename-undo") {
            result = rename_lifecycle(fixture, work, escape, true, beam == "scan",
                                      std::string(argv[6]) == "refusal");
            std::cout << QJsonDocument(result).toJson(QJsonDocument::Compact).constData() << '\n';
            return 0;
        }
        if (mode == "correlation-save-stability") {
            result = correlation_save_stability(fixture, work, beam, escape,
                                                std::string(argv[6]) == "later");
            std::cout << QJsonDocument(result).toJson(QJsonDocument::Compact).constData() << '\n';
            return 0;
        }
        if (mode == "correlation-template") {
            result = template_persistence(fixture, work);
            std::cout << QJsonDocument(result).toJson(QJsonDocument::Compact).constData() << '\n';
            return 0;
        }
        if (mode == "correlation-rename") {
            result = rename_lifecycle(fixture, work, escape);
            std::cout << QJsonDocument(result).toJson(QJsonDocument::Compact).constData() << '\n';
            return 0;
        }
        if (mode == "correlation-single" || mode == "correlation-cancel") {
            result = correlation_lifecycle(mode, fixture, work, beam, escape == "history");
            std::cout << QJsonDocument(result).toJson(QJsonDocument::Compact).constData() << '\n';
            return 0;
        }
        edi_app::Session session;
        if (!session.createProject("Scratch", ""))
            throw std::runtime_error("create project refused");
        auto& view = *session.project();
        if (mode == "identity") {
            configure(view, beam, false);
            const bool experiments = escape == "experiment";
            const std::string spelling = argv[6];
            const int occupied = argc > 7 ? std::stoi(argv[7]) : 1;
            for (int i = 1; i < occupied; ++i) {
                if (!(experiments ? view.createExperiment() : view.createStructure()))
                    throw std::runtime_error("identity setup creation refused");
            }
            for (int i = 0; i < occupied; ++i) {
                const auto name = spelling + std::to_string(i + 1);
                if (experiments)
                    view.experimentModels()[i]->setName(QString::fromStdString(name));
                else {
                    const auto old_name = view.project().structures[i]->name.value();
                    view.structureModels()[i]->setName(QString::fromStdString(name));
                    // Fixture setup: retain the loaded link identities when choosing user
                    // spellings.
                    auto& project = const_cast<edi::Project&>(view.project());
                    for (auto& experiment : project.experiments)
                        for (auto& link : experiment->linked_structures)
                            if (link->structure_id.value() == old_name) link->structure_id = name;
                }
            }
            result["before"] = state(view);
            result["beforeSaved"] = session.saveAs(QUrl::fromLocalFile(work + "/before-saved"));
            result["beforeSaveError"] = session.lastError();
            result["created"] = experiments ? view.createExperiment() : view.createStructure();
            result["after"] = state(view);
            view.undo();
            result["undone"] = state(view);
            result["recreated"] = experiments ? view.createExperiment() : view.createStructure();
            const auto saved = work + "/saved";
            result["saved"] = session.saveAs(QUrl::fromLocalFile(saved));
            result["saveError"] = session.lastError();
            if (result["saved"].toBool()) {
                session.closeProject();
                result["opened"] = session.openProject(QUrl::fromLocalFile(saved));
                if (result["opened"].toBool()) result["reopened"] = state(*session.project());
            }
        } else if (mode == "structure") {
            result["created"] = create(view);
            result["first"] = state(view);
            result["createdSecond"] = create(view);
            result["second"] = state(view);
            view.undo();
            result["undo"] = state(view);
        } else if (mode == "links") {
            if (!create(view) || !create(view))
                throw std::runtime_error("Create structure unavailable");
            view.createExperiment();
            result["newExperiment"] = state(view);
            if (!create(view)) throw std::runtime_error("third structure creation refused");
            if (escape == "link-new") {
                auto& p = const_cast<edi::Project&>(view.project());
                edi::LinkedStructure link;
                link.structure_id = p.structures.back()->name.value();
                p.experiments[0]->linked_structures.push_back(link);
            }
            result["newStructure"] = state(view);
            view.removeStructure(0);
            result["removed"] = state(view);
            result["messages"] = messages(session);
            view.undo();
            result["undo"] = state(view);
        } else {
            configure(view, beam, mode == "renamed");
            result["before"] = state(view);
            const QString input = fixture + "/" + QString::fromLocal8Bit(argv[6]);
            const QString source = work + "/" + QFileInfo(input).fileName();
            std::filesystem::copy_file(input.toStdString(), source.toStdString(),
                                       std::filesystem::copy_options::overwrite_existing);
            const int previous_messages = session.loadWarnings()->count();
            result["loaded"] = load(view, 0, source);
            if (escape == "retain-nonpositive" && result["loaded"].toBool()) {
                auto& p = const_cast<edi::Project&>(view.project());
                auto& d = *p.experiments[0]->data;
                auto axis = d.two_theta.get();
                axis->push_back(18.0);
                d.two_theta = axis;
                auto intensity = d.intensity_meas.get();
                intensity.push_back(0.0);
                d.intensity_meas = intensity;
                auto sigma = d.intensity_meas_su.get();
                sigma.push_back(1.0);
                d.intensity_meas_su = sigma;
            }
            result["after"] = state(view);
            QJsonArray import_messages;
            const auto all_messages = messages(session);
            for (int i = previous_messages; i < all_messages.size(); ++i)
                import_messages.append(all_messages[i]);
            result["messages"] = import_messages;
            result["typeRefused"] = !view.setExperimentType(
                0, "beamMode", beam == "tof" ? "constant wavelength" : "time-of-flight");
            result["afterTypeAttempt"] = state(view);
            view.currentExperiment()->setRange(25, 28, 0.75);
            result["rangeRefused"] = !view.currentExperiment()->lastError().isEmpty();
            result["afterRangeAttempt"] = state(view);
            if (mode == "mixed") {
                result["createdExtra"] = view.createExperiment();
                result["mixed"] = state(view);
                auto& p = const_cast<edi::Project&>(view.project());
                p.experiments[0]->linked_structures[0]->scale.free = true;
                p.calculate();
                QJsonArray counts;
                for (const auto& e : p.experiments)
                    counts.append(static_cast<int>(e->data->intensity_calc.values().size()));
                result["calculated"] = counts;
                const auto fit = p.fit();
                result["fitPoints"] = static_cast<int>(fit.n_points_loaded);
                result["afterFit"] = state(view);
            } else if (mode != "counts") {
                const QString saved = work + "/saved";
                result["saved"] = session.saveAs(QUrl::fromLocalFile(saved));
                if (!result["saved"].toBool())
                    throw std::runtime_error("saved project write refused: " +
                                             session.lastError().toStdString());
                session.closeProject();
                std::filesystem::remove(source.toStdString());
                if (escape == "source-reopen") {
                    std::ifstream reopened(source.toStdString());
                    if (!reopened) throw std::runtime_error("external data required on reopen");
                }
                result["opened"] = session.openProject(QUrl::fromLocalFile(saved));
                if (!result["opened"].toBool())
                    throw std::runtime_error("saved project did not reopen: " +
                                             session.lastError().toStdString());
                result["reopened"] = state(*session.project());
                result["reopenedTypeRefused"] = !session.project()->setExperimentType(
                    0, "beamMode", beam == "tof" ? "constant wavelength" : "time-of-flight");
                result["afterReopenedTypeAttempt"] = state(*session.project());
                session.project()->currentExperiment()->setRange(25, 28, 0.75);
                result["reopenedRangeRefused"] =
                    !session.project()->currentExperiment()->lastError().isEmpty();
                result["afterReopenedRangeAttempt"] = state(*session.project());
                edi_app::Session imported;
                imported.createProject("Imported", "");
                auto& opened = *imported.project();
                for (const auto& entry :
                     std::filesystem::directory_iterator(saved.toStdString() + "/structures")) {
                    if (!opened.loadStructure(
                            QUrl::fromLocalFile(QString::fromStdString(entry.path().string()))))
                        throw std::runtime_error("saved structure import refused");
                }
                QList<QUrl> experimentFiles;
                for (const auto& entry :
                     std::filesystem::directory_iterator(saved.toStdString() + "/experiments")) {
                    experimentFiles.append(
                        QUrl::fromLocalFile(QString::fromStdString(entry.path().string())));
                }
                if (!opened.loadExperiments(experimentFiles))
                    throw std::runtime_error("saved experiment import refused");
                result["ediImported"] = state(opened);
                result["ediLoadSucceeded"] =
                    load(opened, 0, fixture + "/" + beam + "/three_columns/pattern.xye");
                result["afterEdiLoadAttempt"] = state(opened);
                edi_app::Session live;
                live.createProject("Live", "");
                auto& v = *live.project();
                configure(v, beam, mode == "renamed");
                result["beforeLive"] = state(v);
                result["firstLoad"] = load(v, 0, input);
                result["firstData"] = state(v);
                const QString replacement = work + "/replacement.xye";
                std::filesystem::copy_file(
                    (fixture + "/" + beam + "/three_columns/pattern.xye").toStdString(),
                    replacement.toStdString());
                result["secondLoad"] = load(v, 0, replacement);
                result["secondData"] = state(v);
                v.undo();
                result["undoSecond"] = state(v);
                v.undo();
                result["undoFirst"] = state(v);
                result["undoTypeEditable"] = v.setExperimentType(
                    0, "beamMode", beam == "tof" ? "constant wavelength" : "time-of-flight");
                result["afterUndoTypeEdit"] = state(v);
                v.currentExperiment()->setRange(31, 34, 0.75);
                result["undoRangeEditable"] = v.currentExperiment()->lastError().isEmpty();
                result["afterUndoRangeEdit"] = state(v);
            }
        }
    } catch (const std::exception& error) {
        result["error"] = error.what();
    }
    std::cout << QJsonDocument(result).toJson(QJsonDocument::Compact).constData() << '\n';
}
