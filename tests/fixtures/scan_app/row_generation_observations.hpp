// File identities come from the fixture directory; no fit or optimizer is needed.
QJsonObject row_generation(const std::string& path, const std::string& route,
                           const std::string& change, const std::string& access) {
    auto view = load(path);
    if (route == "reset-undo") {
        view->fit()->reset();
        if (!settled(*view) || !view->canUndo())
            throw std::runtime_error("row observer requires a settled, undoable Reset fits");
    }
    auto* model = view->experiments();
    const QJsonArray before = table(model);
    QJsonArray notifications;
    int file_role = -1, experiment_role = -1;
    const auto roles = model->roleNames();
    for (auto it = roles.cbegin(); it != roles.cend(); ++it) {
        if (it.value() == "file") file_role = it.key();
        if (it.value() == "experiment") experiment_role = it.key();
    }
    if (file_role < 0 || experiment_role < 0)
        throw std::runtime_error("row observer requires the production file and experiment roles");
    auto read = [&](int row, const QString& role, int role_id) {
        return access == "get" ? model->get(row, role) : model->data(model->index(row), role_id);
    };
    auto snapshot = [&] {
        QJsonArray rows;
        for (int row = 0; row < model->count(); ++row) {
            // Flush before each read so a checked-container abort names the reached signal/row.
            std::cerr << "row-generation " << route << ' ' << change << ' ' << access
                      << " read " << row << '/' << model->count() << std::endl;
            const QString file = read(row, "file", file_role).toString();
            QObject* experiment = read(row, "experiment", experiment_role).value<QObject*>();
            rows.append(QJsonObject{{"row", row}, {"file", file},
                                    {"experimentName", experiment ? experiment->property("name").toString()
                                                                   : QString()}});
        }
        return rows;
    };
    auto record = [&](const char* signal, int first, int last) {
        std::cerr << "row-generation signal " << signal << ' ' << first << ' ' << last << std::endl;
        notifications.append(QJsonObject{{"signal", signal}, {"first", first}, {"last", last},
                                         {"count", model->count()}, {"rows", snapshot()}});
    };
    QObject::connect(model, &QAbstractItemModel::rowsAboutToBeRemoved, view.get(),
                     [&](const QModelIndex&, int first, int last) { record("removing", first, last); });
    QObject::connect(model, &QAbstractItemModel::rowsAboutToBeInserted, view.get(),
                     [&](const QModelIndex&, int first, int last) { record("inserting", first, last); });
    QObject::connect(model, &QAbstractItemModel::rowsInserted, view.get(),
                     [&](const QModelIndex&, int first, int last) { record("inserted", first, last); });
    QObject::connect(model, &QAbstractItemModel::dataChanged, view.get(),
                     [&](const QModelIndex& first, const QModelIndex& last, const QList<int>&) {
                         record("changed", first.row(), last.row());
                     });
    std::vector<std::filesystem::path> files;
    const auto directory = std::filesystem::path(path) / "experiments/d20_scan";
    for (const auto& entry : std::filesystem::directory_iterator(directory))
        if (entry.path().extension() == ".dat") files.push_back(entry.path());
    std::sort(files.begin(), files.end());
    if (files.size() != 3) throw std::runtime_error("row observer requires three authored files");
    if (change == "shrink")
        std::filesystem::remove(files.back());
    else if (change == "empty")
        for (const auto& file : files) std::filesystem::remove(file);
    else if (change == "grow")
        std::filesystem::copy_file(files.front(), directory / "zz-added.dat");
    else if (change == "same")
        std::filesystem::rename(files.back(), directory / "zz-replacement.dat");

    QString error;
    bool replaced = false;
    QPointer<edi_app::ExperimentViewModel> prior_template;
    if (change == "template") {
        // The same structural replacement used by Load data/Undo reaches the
        // QObject lifetime boundary, keeping the file list and template values.
        prior_template = view->currentExperiment();
        auto& project = const_cast<edi::Project&>(view->project());
        edi::BraggPdExperiment replacement(project.experiment());
        error = view->apply(edi::Edit::load_data(project, project.experiment(),
                                               std::move(replacement)), true);
    } else if (route == "reset-undo") {
        view->undo();
        error = view->lastError();
    } else {
        const auto destination = route == "save-as" ? path + "-saved" : path;
        error = view->saveTo(QString::fromStdString(destination));
    }
    const bool ready = settled(*view);
    if (change == "template") {
        QCoreApplication::sendPostedEvents(nullptr, QEvent::DeferredDelete);
        replaced = prior_template.isNull() && view->currentExperiment() != nullptr;
    }
    const QJsonArray after = snapshot();
    QJsonArray reopened;
    if (route == "reopen") {
        auto fresh = load(path);
        reopened = table(fresh->experiments());
    }
#if defined(__GLIBCXX__) && defined(_GLIBCXX_ASSERTIONS)
    constexpr bool checked_containers = true;
#elif defined(_LIBCPP_VERSION)
    constexpr bool checked_containers = _LIBCPP_HARDENING_MODE == _LIBCPP_HARDENING_MODE_EXTENSIVE;
#else
    constexpr bool checked_containers = false;
#endif
    return {{"before", before}, {"notifications", notifications}, {"after", after},
            {"reopened", reopened}, {"error", error}, {"settled", ready},
            {"scan", view->scan()}, {"replaced", replaced},
            {"checkedContainers", checked_containers}};
}
