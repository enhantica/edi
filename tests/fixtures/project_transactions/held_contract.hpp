// Listen at the value-publication boundary, before any downstream consumer guards.
#include "experiment_models.hpp"
namespace {
QJsonObject heldPublication(const QString& source, const QStringList& spec) {
    need(spec.size() == 2, "A held-publication case declares its calculation completion order");
    const QString order = spec[1];
    QTemporaryDir temp;
    Session session(nullptr);
    need(session.openProject(QUrl::fromLocalFile(copy(source, temp.filePath("input")))),
         "The held boundary uses an independently retained scientific input");
    settle(session);
    auto* project = session.project();
    ParameterItem* item = nullptr;
    for (auto* parameter : project->findChildren<ParameterItem*>())
        if (parameter->name() == "length_a") {
            item = parameter;
            break;
        }
    need(item, "The independent input has an editable nontrivial lattice parameter");
    auto* experiment = project->currentExperiment();
    need(experiment, "A held value reaches an actual calculated experiment");
    std::vector<std::unique_ptr<QSignalSpy>> fields;
    for (auto* parameter : project->findChildren<ParameterItem*>()) {
        const auto* meta = parameter->metaObject();
        for (int index = meta->methodOffset(); index < meta->methodCount(); ++index) {
            const auto method = meta->method(index);
            if (method.methodType() == QMetaMethod::Signal && method.name() != "lastErrorChanged")
                fields.push_back(std::make_unique<QSignalSpy>(parameter, method));
        }
    }
    auto fieldCount = [&] {
        int count = 0;
        for (const auto& spy : fields) count += spy->size();
        return count;
    };
    QSignalSpy selected(item, &ParameterItem::valueChanged);
    QSignalSpy changed(project, &ProjectViewModel::recalculated);
    QSignalSpy edited(project, &ProjectViewModel::projectEdited);
    QSignalSpy charts(experiment, &ExperimentViewModel::patternSourceChanged);
    auto* table = experiment->singleCrystalReflections();
    QSignalSpy tableReset(table, &QAbstractItemModel::modelReset);
    QSignalSpy tableData(table, &QAbstractItemModel::dataChanged);
    QSignalSpy tableLayout(table, &QAbstractItemModel::layoutChanged);
    const double before = item->value();
    const double last = before * 1.003;
    project->setAdjusting(true);
    std::vector<std::unique_ptr<QSignalSpy>> projectSignals;
    const auto* meta = project->metaObject();
    for (int at = meta->methodOffset(); at < meta->methodCount(); ++at) {
        const auto method = meta->method(at);
        const auto name = method.name();
        if (method.methodType() == QMetaMethod::Signal && name != "calculatingChanged" &&
            name != "calculationStarted" && name != "calculationFinished")
            projectSignals.push_back(std::make_unique<QSignalSpy>(project, method));
    }
    const auto projectCount = [&] {
        int n = 0;
        for (const auto& signal : projectSignals) n += signal->size();
        return n;
    };
    QJsonArray steps;
    for (const double factor : {1.001, 1.002, 1.003}) {
        const auto generation = experiment->patternGeneration();
        item->setValue(before * factor);
        if (order != "release-busy" || factor != 1.003) settle(session);
        steps.append(
            QJsonObject{{"project", projectCount()},
                        {"fields", fieldCount()},
                        {"general", int(changed.size())},
                        {"edits", int(edited.size())},
                        {"tables", int(tableReset.size() + tableData.size() + tableLayout.size())},
                        {"charted", experiment->patternGeneration() > generation},
                        {"busy", project->calculating()}});
    }
    project->setAdjusting(false);
    settle(session);
    turn();
    const int releaseChanges = selected.size(), releaseGeneral = changed.size(),
              releaseEdits = edited.size();
    const bool finalValue = item->value() == last;
    project->undo();
    settle(session);
    return {{"steps", steps},
            {"chartUpdates", int(charts.size())},
            {"releaseChanges", releaseChanges},
            {"releaseGeneral", releaseGeneral},
            {"releaseEdits", releaseEdits},
            {"finalValue", finalValue},
            {"oneUndo", item->value() == before}};
}
}  // namespace
