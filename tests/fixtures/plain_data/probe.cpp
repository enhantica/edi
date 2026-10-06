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

#include "edi/io.hpp"
#include "experiment_view_model.hpp"
#include "project_view_model.hpp"
#include "session.hpp"
Q_IMPORT_QML_PLUGIN(edi_appPlugin)

namespace {
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
        for (const auto& region : e.excluded_regions.get())
            excluded.append(QJsonArray{region.first, region.second});
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
    experiment.excluded_regions = std::vector<std::pair<double, double>>{
        {beam == "tof" ? 9000 : 60, beam == "tof" ? 9100 : 61}};
}
}  // namespace
int main(int argc, char** argv) {
    QGuiApplication app(argc, argv);
    if (argc != 7) return 2;
    const std::string mode = argv[1], escape = argv[5];
    const QString fixture = QString::fromLocal8Bit(argv[2]);
    const QString work = QString::fromLocal8Bit(argv[3]);
    const QString beam = QString::fromLocal8Bit(argv[4]);
    QJsonObject result;
    try {
        edi_app::Session session;
        if (!session.createProject("Scratch", ""))
            throw std::runtime_error("create project refused");
        auto& view = *session.project();
        if (mode == "structure") {
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
                result["ediLoadRefused"] =
                    !load(opened, 0, fixture + "/" + beam + "/three_columns/pattern.xye");
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
