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
            {"beam", vm->beamModeToken()},
            {"file", view.experiments()->get(i, "file").toString()},
            {"range", QJsonArray{vm->measuredRange()->minimum(), vm->measuredRange()->maximum(),
                                 vm->measuredRange()->step()}}};
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
            view.loadStructure(QUrl::fromLocalFile(fixture + "/default.cif"));
            view.createExperiment();
            if (beam == "tof") view.setExperimentType(0, "beamMode", "time-of-flight");
            view.currentExperiment()->setRange(beam == "tof" ? 2400 : 14,
                                               beam == "tof" ? 2412 : 16, beam == "tof" ? 3 : 0.5);
            if (mode == "renamed") view.currentExperiment()->setName("User name");
            view.currentExperiment()->setDatasetWeight(2.5);
            view.apply(edi::Edit::append_excluded_region(
                           *const_cast<edi::Project&>(view.project()).experiments[0],
                           beam == "tof" ? 9000 : 60, beam == "tof" ? 9100 : 61),
                       false);
            result["before"] = state(view);
            const QString input = fixture + "/" + QString::fromLocal8Bit(argv[6]);
            const QString source = work + "/" + QFileInfo(input).fileName();
            std::filesystem::copy_file(input.toStdString(), source.toStdString(),
                                       std::filesystem::copy_options::overwrite_existing);
            result["loaded"] = load(view, 0, source);
            result["after"] = state(view);
            result["messages"] = messages(session);
            result["typeRefused"] = !view.setExperimentType(
                0, "beamMode", beam == "tof" ? "constant-wavelength" : "time-of-flight");
            result["afterTypeAttempt"] = state(view);
            if (mode == "mixed") {
                result["createdExtra"] = view.createExperiment();
                result["mixed"] = state(view);
                auto& p = const_cast<edi::Project&>(view.project());
                p.calculate();
                QJsonArray counts;
                for (const auto& e : p.experiments)
                    counts.append(static_cast<int>(e->data->intensity_calc.values().size()));
                result["calculated"] = counts;
                const auto fit = p.fit();
                result["fitPoints"] = static_cast<int>(fit.n_points_loaded);
                result["afterFit"] = state(view);
            } else {
                const QString saved = work + "/saved";
                result["saved"] = session.saveAs(QUrl::fromLocalFile(saved));
                session.closeProject();
                std::filesystem::remove(source.toStdString());
                if (escape == "source-reopen") {
                    std::ifstream reopened(source.toStdString());
                    if (!reopened) throw std::runtime_error("external data required on reopen");
                }
                result["opened"] = session.openProject(QUrl::fromLocalFile(saved));
                if (!result["opened"].toBool())
                    throw std::runtime_error("saved project did not reopen");
                result["reopened"] = state(*session.project());
                auto& opened = *session.project();
                result["ediLoadRefused"] =
                    !load(opened, 0, fixture + "/" + beam + "/three_columns/pattern.xye");
                result["afterEdiLoadAttempt"] = state(opened);
                edi_app::Session live;
                live.createProject("Live", "");
                auto& v = *live.project();
                v.createExperiment();
                if (beam == "tof") v.setExperimentType(0, "beamMode", "time-of-flight");
                v.currentExperiment()->setRange(beam == "tof" ? 2400 : 14,
                                                beam == "tof" ? 2412 : 16, beam == "tof" ? 3 : .5);
                result["firstLoad"] = load(v, 0, input);
                result["firstData"] = state(v);
                result["secondLoad"] =
                    load(v, 0, fixture + "/" + beam + "/three_columns/pattern.xye");
                result["secondData"] = state(v);
                v.undo();
                result["undoSecond"] = state(v);
                v.undo();
                result["undoFirst"] = state(v);
                result["undoTypeEditable"] = v.setExperimentType(
                    0, "beamMode", beam == "tof" ? "constant-wavelength" : "time-of-flight");
            }
        }
    } catch (const std::exception& error) {
        result["error"] = error.what();
    }
    std::cout << QJsonDocument(result).toJson(QJsonDocument::Compact).constData() << '\n';
}
