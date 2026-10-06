// Deterministic actions at real reader, worker and pointer boundaries.

bool settled(edi_app::ProjectViewModel& view) {
    return until(
        [&] { return !view.calculating() && !view.currentExperiment()->pattern()->stale(); });
}
edi_app::ParameterItem* cell_item(edi_app::ProjectViewModel& view) {
    for (int row = 0; row < view.parameters()->count(); ++row) {
        auto* item = view.parameters()->get(row, "parameter").value<edi_app::ParameterItem*>();
        if (item)
            for (const edi::NamedParameter& entry : edi::named_parameters(view.project()))
                if (entry.parameter == item->parameter() &&
                    entry.unique_name == "cosio.cell.length_a")
                    return item;
    }
    throw std::runtime_error("accident witness requires the fixture cell parameter");
}
QJsonObject scientific_state(edi_app::ProjectViewModel& view) {
    QJsonObject result = state(view);
    result["parameters"] = parameters(view);
    QJsonObject parameter_facts;
    for (const edi::NamedParameter& entry : edi::named_parameters(view.project())) {
        const auto& value = *entry.parameter;
        parameter_facts[QString::fromStdString(entry.unique_name)] = QJsonObject{
            {"value", static_cast<double>(value.value)},
            {"free", static_cast<bool>(value.free)},
            {"uncertainty",
             value.uncertainty.has_value() ? QJsonValue(*value.uncertainty) : QJsonValue()},
            {"start",
             value.start_value.has_value() ? QJsonValue(*value.start_value) : QJsonValue()},
            {"startUncertainty", value.start_uncertainty.has_value()
                                     ? QJsonValue(*value.start_uncertainty)
                                     : QJsonValue()}};
    }
    result["parameterFacts"] = parameter_facts;
    result["rows"] = table(view.experiments());
    result["summary"] = table(view.fit()->results());
    result["held"] = view.project().fit_result.held();
    result["template"] = QString::fromStdString(view.project().sequential_fit.template_file);
    result["stale"] = view.fit()->outOfDate();
    result["evolutionStale"] = view.evolution()->outOfDate();
    return result;
}
QJsonObject pending_action(const std::string& path, const std::string& action) {
    auto view = load(path);
    if (action == "start-fitting") {
        view->analysis()->setFittingMode("single");
        settled(*view);
    }
    if (action == "undo") {
        run(*view, "undo-seed", 0);
        view->fit()->reset();
        settled(*view);
    }
    const double initial = cell_item(*view)->value();
    const bool initial_free = cell_item(*view)->isFree();
    const int initial_bound = view->analysis()->maxIterations();
    const QString target = view->experiments()->get(1, "file").toString();
    held_read_path = path + "/experiments/d20_scan/" + target.toStdString();
    view->setCurrentExperimentIndex(1);
    const bool blocked = until([&] { return read_entered.available() > 0; }, 5000);
    const bool pending = view->calculating();
    QString refusal;
    auto connection = QObject::connect(view->fit(), &edi_app::FitViewModel::refused,
                                       [&](const QString& reason) { refusal = reason; });
    bool admitted = false;
    const bool before_stale = view->fit()->outOfDate();
    if (action == "start-fitting") {
        stage = "pending-fit";
        view->fit()->start();
        admitted = view->fit()->running();
    } else if (action == "start-scan") {
        stage = "pending-scan";
        view->fit()->start();
        admitted = view->fit()->running();
    } else if (action == "value") {
        cell_item(*view)->setValue(initial + 0.003125);
        refusal = cell_item(*view)->lastError();
        admitted = refusal.isEmpty();
    } else if (action == "free") {
        cell_item(*view)->setFree(!initial_free);
        refusal = cell_item(*view)->lastError();
        admitted = refusal.isEmpty();
    } else if (action == "setting") {
        view->analysis()->setMaxIterations(initial_bound + 7);
        refusal = view->analysis()->lastError();
        admitted = refusal.isEmpty();
    } else if (action == "reset") {
        view->fit()->reset();
        refusal = view->lastError();
        admitted = refusal.isEmpty();
    } else if (action == "undo") {
        view->undo();
        refusal = view->lastError();
        admitted = refusal.isEmpty();
    } else if (action == "saveas") {
        refusal = view->saveTo(QString::fromStdString(path + "-saved"));
        admitted = refusal.isEmpty();
    }
    const double accepted_value = cell_item(*view)->value();
    const bool accepted_free = cell_item(*view)->isFree();
    const int accepted_bound = view->analysis()->maxIterations();
    read_release.release(64);
    until([&] { return !view->fit()->running(); });
    const bool projected = settled(*view);
    held_read_path.clear();
    while (read_entered.tryAcquire()) {
    }
    while (read_release.tryAcquire()) {
    }
    if (action == "start-fitting" && !admitted) run(*view, "settled-fit", 0);
    QObject::disconnect(connection);
    return {{"blocked", blocked},
            {"pending", pending},
            {"admitted", admitted},
            {"refusal", refusal},
            {"projected", projected},
            {"target", target},
            {"beforeValue", initial},
            {"beforeFree", initial_free},
            {"acceptedValue", accepted_value},
            {"acceptedFree", accepted_free},
            {"acceptedBound", accepted_bound},
            {"value", cell_item(*view)->value()},
            {"free", cell_item(*view)->isFree()},
            {"bound", view->analysis()->maxIterations()},
            {"nativeInputs", native_fit_inputs},
            {"measuredHash", measured_pattern_hash(*view)},
            {"beforeStale", before_stale},
            {"after", scientific_state(*view)},
            {"files", result_files(path)}};
}
QJsonObject reset_state(const std::string& path) {
    auto view = load(path);
    auto scan = run(*view, "reset-scan", 0);
    const auto prior_scan = scientific_state(*view);
    view->setCurrentExperimentIndex(1);
    settled(*view);
    view->analysis()->setFittingMode("single");
    settled(*view);
    auto single = run(*view, "reset-single", 0);
    const auto prior_single = scientific_state(*view);
    view->undo();
    settled(*view);
    const auto undone_single = scientific_state(*view);
    const auto undo_save = view->saveTo(QString::fromStdString(path + "-single-undo"));
    auto reopened_undo = load(path + "-single-undo");
    view->analysis()->setFittingMode("single");
    settled(*view);
    auto again = run(*view, "reset-single-again", 0);
    view->analysis()->setFittingMode("sequential");
    settled(*view);
    const auto before = scientific_state(*view), before_files = result_files(view->project().path);
    view->fit()->reset();
    settled(*view);
    const auto reset = scientific_state(*view), reset_files = result_files(view->project().path);
    view->undo();
    settled(*view);
    return {{"scan", scan},
            {"single", single},
            {"again", again},
            {"priorScan", prior_scan},
            {"priorSingle", prior_single},
            {"undoSingle", undone_single},
            {"undoSaveError", undo_save},
            {"reopenedUndoSingle", scientific_state(*reopened_undo)},
            {"beforeReset", before},
            {"reset", reset},
            {"resetFiles", reset_files},
            {"undoReset", scientific_state(*view)},
            {"filesRestored", before_files == result_files(view->project().path)}};
}
QJsonObject io_rollback(const std::string& path, const std::string& action, int file) {
    auto view = load(path);
    run(*view, "io-seed", 0);
    const auto before = result_files(path), before_state = scientific_state(*view);
    QString refusal;
    auto connection = QObject::connect(view->fit(), &edi_app::FitViewModel::refused,
                                       [&](const QString& error) { refusal = error; });
    scan_contract_arm_io(path, file);
    if (action == "reset")
        view->fit()->reset();
    else
        view->undo();
    const int hit = scan_contract_disarm_io();
    QObject::disconnect(connection);
    if (refusal.isEmpty()) refusal = view->lastError();
    const auto after = result_files(path);
    QJsonArray retained;
    QDirIterator entries(QString::fromStdString(path), QDir::Files | QDir::Hidden,
                         QDirIterator::Subdirectories);
    while (entries.hasNext()) {
        QFile stored(entries.next());
        if (stored.open(QIODevice::ReadOnly))
            retained.append(QString::fromLatin1(
                QCryptographicHash::hash(stored.readAll(), QCryptographicHash::Sha256).toHex()));
    }
    return {{"hit", hit},
            {"refusal", refusal},
            {"before", before},
            {"after", after},
            {"retained", retained},
            {"beforeState", before_state},
            {"afterState", scientific_state(*view)}};
}
QJsonObject mixed_generation(const std::string& path, const std::string& edit) {
    auto view = load(path);
    const auto first = run(*view, "mixed-prefix", 1);
    const auto prefix = contents(path, "analysis/results.csv");
    QString edit_error;
    if (edit == "free") {
        cell_item(*view)->setFree(!cell_item(*view)->isFree());
        edit_error = cell_item(*view)->lastError();
    } else if (edit == "setting") {
        view->analysis()->setMaxIterations(view->analysis()->maxIterations() + 1);
        edit_error = view->analysis()->lastError();
    } else {
        cell_item(*view)->setValue(cell_item(*view)->value() + 0.001);
        edit_error = cell_item(*view)->lastError();
    }
    settled(*view);
    const auto continued = run(*view, "mixed-continue", 0);
    const auto mixed = scientific_state(*view);
    const bool kept = contents(path, "analysis/results.csv").startsWith(prefix);
    const auto saved = view->saveTo(QString::fromStdString(path + "-saved"));
    auto reopened = load(path + "-saved");
    const auto reopened_state = scientific_state(*reopened);
    reopened->fit()->reset();
    settled(*reopened);
    reopened->undo();
    settled(*reopened);
    const auto restored = scientific_state(*reopened);
    reopened->fit()->reset();
    settled(*reopened);
    auto fresh = run(*reopened, "mixed-fresh", 0);
    return {{"first", first},
            {"editError", edit_error},
            {"continued", continued},
            {"prefixKept", kept},
            {"mixed", mixed},
            {"saveError", saved},
            {"reopened", reopened_state},
            {"undoReset", restored},
            {"fresh", fresh},
            {"freshState", scientific_state(*reopened)}};
}

struct ChartActor {
    edi_app::ProjectViewModel& view;
    QQmlEngine engine;
    std::unique_ptr<QObject> root;
    QQuickWindow* window = nullptr;
    QQuickItem* chart = nullptr;
    QQuickItem* pointer = nullptr;
    QObject* layer = nullptr;
    explicit ChartActor(edi_app::ProjectViewModel& model) : view(model) {
        edi_app::use_fresh_settings();
        edi_app::configure_engine(engine);
        engine.rootContext()->setContextProperty("probeProject", &view);
        QQmlComponent component(&engine);
        component.setData(
            "import QtQuick\nimport QtQuick.Window\nimport edi.app\nWindow { width:1000; "
            "height:450; visible:true; EvolutionChart { objectName: \"actor.chart\"; width:1000; "
            "height:400; project:probeProject } }",
            QUrl("qrc:/accident-chart.qml"));
        until([&] { return component.status() != QQmlComponent::Loading; });
        root.reset(component.create());
        if (!root) throw std::runtime_error(component.errorString().toStdString());
        window = qobject_cast<QQuickWindow*>(root.get());
        QList<QQuickItem*> pending{window->contentItem()};
        while (!pending.isEmpty()) {
            auto* item = pending.takeLast();
            pending.append(item->childItems());
            if (item->objectName() == "actor.chart") chart = item;
            if (item->objectName() == "evolution.pointer") pointer = item;
            if (item->objectName() == "evolution.points") layer = item;
        }
        if (!chart || !pointer || !layer)
            throw std::runtime_error(
                "actual Evolution chart must expose its pointer and draw layer");
        QCoreApplication::processEvents();
    }
    QJsonArray axes() const {
        return {layer->property("xMin").toDouble(), layer->property("xMax").toDouble(),
                layer->property("yMin").toDouble(), layer->property("yMax").toDouble()};
    }
    QJsonArray zoom() const {
        QQmlExpression expression(engine.rootContext(), chart, "zoom");
        QVariant value = expression.evaluate();
        if (value.canConvert<QJSValue>()) value = value.value<QJSValue>().toVariant();
        return QJsonArray::fromVariantList(value.toList());
    }
    void mouse(QEvent::Type type, QPointF local, Qt::MouseButton button,
               Qt::MouseButtons buttons) {
        const auto position = pointer->mapToScene(local);
        QMouseEvent event(type, position, position, window->mapToGlobal(position.toPoint()),
                          button, buttons, Qt::NoModifier);
        QCoreApplication::sendEvent(window, &event);
        QCoreApplication::processEvents();
    }
    void click(QPointF point, Qt::MouseButton button) {
        mouse(QEvent::MouseButtonPress, point, button, button);
        mouse(QEvent::MouseButtonRelease, point, button, Qt::NoButton);
    }
    void wheel(int delta = 120) {
        const auto position =
            pointer->mapToScene(QPointF(pointer->width() * 0.4, pointer->height() * 0.4));
        QWheelEvent event(position, window->mapToGlobal(position.toPoint()), {}, QPoint(0, delta),
                          Qt::NoButton, Qt::NoModifier, Qt::NoScrollPhase, false);
        QCoreApplication::sendEvent(window, &event);
        QCoreApplication::processEvents();
    }
    QPointF point(int index) const {
        const auto a = axes();
        const auto p = layer_points.at(index).toArray();
        return {(p[0].toDouble() - a[0].toDouble()) / (a[1].toDouble() - a[0].toDouble()) *
                    pointer->width(),
                (a[3].toDouble() - p[1].toDouble()) / (a[3].toDouble() - a[2].toDouble()) *
                    pointer->height()};
    }
};
QJsonObject gesture_accidents(const std::string& path, const std::string& gesture) {
    auto view = load(path);
    view->evolution()->setXMode(1);
    ChartActor actor(*view);
    const auto before = actor.axes();
    const int selected = view->currentExperimentIndex();
    auto endpoint = actor.point(gesture == "right" || gesture == "left" ? 1 : 2);
    endpoint.setX(std::clamp(endpoint.x(), 0.1, actor.pointer->width() - 0.1));
    endpoint.setY(std::clamp(endpoint.y(), 0.1, actor.pointer->height() - 0.1));
    auto start =
        endpoint - QPointF(actor.pointer->width() * 0.08, -actor.pointer->height() * 0.08);
    if (gesture == "horizontal") start.setY(endpoint.y());
    if (gesture == "vertical") start.setX(endpoint.x());
    if (gesture == "wheel" || gesture == "wheel-out" || gesture == "wheel-zero") {
        actor.wheel(gesture == "wheel" ? 120 : gesture == "wheel-out" ? -120 : 0);
    } else if (gesture == "axis" || gesture == "parameter") {
        actor.wheel();
        if (gesture == "axis")
            view->evolution()->setXMode(0);
        else
            view->evolution()->setCurrentParameter(1);
        QCoreApplication::processEvents();
    } else if (gesture == "right" || gesture == "left") {
        if (gesture == "right") actor.wheel();
        actor.click(endpoint, gesture == "right" ? Qt::RightButton : Qt::LeftButton);
    } else {
        actor.mouse(QEvent::MouseButtonPress, start, Qt::LeftButton, Qt::LeftButton);
        actor.mouse(QEvent::MouseMove, endpoint, Qt::NoButton, Qt::LeftButton);
        actor.mouse(QEvent::MouseButtonRelease, endpoint, Qt::LeftButton, Qt::NoButton);
    }
    return {{"before", before},
            {"after", actor.axes()},
            {"zoom", actor.zoom()},
            {"beforeSelection", selected},
            {"selection", view->currentExperimentIndex()},
            {"width", actor.pointer->width()},
            {"height", actor.pointer->height()},
            {"start", QJsonArray{start.x(), start.y()}},
            {"end", QJsonArray{endpoint.x(), endpoint.y()}}};
}
QJsonObject live_zoom(const std::string& path) {
    auto view = load(path);
    view->evolution()->setXMode(1);
    ChartActor actor(*view);
    QJsonArray during;
    completion_action = [&](int count) {
        if (count == 1) actor.wheel();
        during.append(
            QJsonObject{{"count", count}, {"axes", actor.axes()}, {"zoom", actor.zoom()}});
    };
    auto fitted = run(*view, "live-zoom", 0);
    completion_action = {};
    return {{"run", fitted}, {"during", during}, {"axes", actor.axes()}, {"zoom", actor.zoom()}};
}
QJsonObject range_accident(const std::string& path, const std::string& axis,
                           const std::string& shape, const std::string& route) {
    auto project = edi::load_project(path);
    project.sequential_fit = {};
    project.fitting_mode = "single";
    std::unique_ptr<edi_app::ProjectViewModel> view;
    const edi::Project* model = &project;
    if (route == "gui") {
        view = load(path);
        model = &view->project();
    }
    auto& experiment = project.experiment();
    experiment.calculation_only = true;
    const double start =
        shape == "collapsed" ? (axis == "cw" ? 128.0 : 16000.0) : (axis == "cw" ? 8.125 : 16000.0);
    const double ulp = std::nextafter(start, std::numeric_limits<double>::infinity()) - start;
    const double step = shape == "collapsed" ? ulp / 4.0 : (axis == "cw" ? 0.125 : 12.5);
    const double end = shape == "collapsed" ? start + ulp * 4.0 : start + 10.0 * step;
    QString refusal, save_error;
    bool admitted = false;
    QJsonArray grid, reopened, before;
    for (double value : model->experiment().data->axis()) before.append(value);
    if (view) {
        view->currentExperiment()->setRange(start, end, step);
        refusal = view->currentExperiment()->lastError();
        admitted = refusal.isEmpty();
        if (admitted) settled(*view);
    } else {
        try {
            edi::Edit::data_range(experiment, start, end, step)();
            admitted = true;
        } catch (const std::exception& error) {
            refusal = error.what();
        }
    }
    for (double value : model->experiment().data->axis()) grid.append(value);
    if (admitted) {
        try {
            if (view)
                save_error = view->saveTo(QString::fromStdString(path + "-saved"));
            else
                edi::save_project(project, path + "-saved");
            if (save_error.isEmpty()) {
                auto saved = edi::load_project(path + "-saved");
                for (double value : saved.experiment().data->axis()) reopened.append(value);
            }
        } catch (const std::exception& error) {
            save_error = error.what();
        }
    }
    return {{"admitted", admitted}, {"refusal", refusal}, {"saveError", save_error},
            {"before", before},     {"grid", grid},       {"reopened", reopened},
            {"start", start},       {"end", end},         {"step", step}};
}
QJsonObject result_boundary(const std::string& path) {
    auto view = load(path);
    const auto before = result_files(path), before_state = scientific_state(*view);
    auto fitted = run(*view, "invalid-result-start", 0);
    const auto after = result_files(path);
    return {{"run", fitted},
            {"unchanged", before == after},
            {"before", before_state},
            {"state", scientific_state(*view)}};
}

QJsonObject outcome_settings(const std::string& path) {
    auto view = load(path);
    const auto before = table(view->experiments());
    const auto files_before = result_files(path);
    view->analysis()->setMaxIterations(view->analysis()->maxIterations() + 7);
    settled(*view);
    return {{"before", before},
            {"after", table(view->experiments())},
            {"unchanged", files_before == result_files(path)}};
}
QJsonObject indexed_edit(const std::string& path) {
    auto view = load(path);
    QFile original(QString::fromStdString(path + "/analysis/results.csv"));
    if (!original.open(QIODevice::ReadOnly))
        throw std::runtime_error("indexed witness needs CSV bytes");
    QByteArray text = original.readAll();
    original.close();
    const auto position = text.indexOf("10.126");
    if (position < 0)
        throw std::runtime_error("indexed witness needs its independent second cell");
    text.replace(position, 6, "XX.XXX");
    if (!original.open(QIODevice::WriteOnly | QIODevice::Truncate))
        throw std::runtime_error("indexed witness must edit the actual resource");
    original.write(text);
    original.close();
    view->setCurrentExperimentIndex(1);
    settled(*view);
    return {{"value", cell_item(*view)->value()},
            {"error", view->lastError()},
            {"patternError", view->currentExperiment()->pattern()->calculationError()},
            {"outcome", view->currentExperiment()->fitOutcome()}};
}
