// Untitled recovery uses the real Project page, edit timer and storage callbacks.
QJsonObject untitledWorkState(const edi::Project& project) {
    QJsonArray cells;
    for (const auto& structure : project.structures) {
        const auto& c = structure->cell;
        cells.append(QJsonArray{c.length_a.value.get(), c.length_b.value.get(),
                                c.length_c.value.get(), c.angle_alpha.value.get(),
                                c.angle_beta.value.get(), c.angle_gamma.value.get()});
    }
    return {{"structures", int(project.structures.size())},
            {"experiments", int(project.experiments.size())},
            {"cells", cells}};
}
QJsonObject untitledRecovery() {
    browser = true;
    WebStorage::instance()->usable_ = true;
    jobs.clear();
    drops.clear();
    QTemporaryDir temp;
    QQmlEngine engine;
    edi_app::configure_engine(engine);
    QQmlComponent component(&engine);
    component.loadFromModule("edi.app", "Main");
    std::unique_ptr<QObject> window(component.create());
    need(bool(window), qPrintable(component.errorString()));
    window->setProperty("visible", true);
    auto* session = engine.singletonInstance<Session*>("edi.app", "Session");
    QQmlExpression open(qmlContext(window.get()), window.get(),
                        "AppState.open(AppState.Page.Project)");
    open.evaluate();
    need(!open.hasError(), "The ordinary Project page entrance executes");
    const auto pageReady = [&] {
        const int wanted = window->property("pagesWanted").toInt();
        return wanted > 0 && window->property("pagesBuilt").toInt() == wanted;
    };
    QElapsedTimer ready;
    ready.start();
    while (!pageReady() && ready.elapsed() < 10000) {
        turn();
        QThread::msleep(1);
    }
    need(pageReady(), "The real Project page finishes loading before observing untitled state");
    QJsonObject result{{"untitled", session->hasProject()},
                       {"needsSaveAs", session->needsSaveAs()}};
    if (!session->hasProject()) return result;
    need(session->project()->createStructure(), "The real untitled project accepts a structure");
    session->project()->currentStructure()->cell()->lengthA()->setValue(7.125);
    session->project()->setTitle("Unsaved neutron work");
    settle(*session);
    result["before"] = untitledWorkState(session->project()->project());
    // Deliver the edit timer's actual event without sleeping for its wall-clock delay.
    need(QMetaObject::invokeMethod(session->keep_timer_, "timeout", Qt::DirectConnection),
         "The existing recovery timer receives its timeout");
    for (int pass = 0; pass < 8; ++pass) turn();
    int write = -1;
    for (size_t i = 0; i < jobs.size(); ++i)
        if (jobs[i].action == "write" && jobs[i].recovery) write = int(i);
    result["writesRecovery"] = write >= 0;
    if (write < 0) return result;
    const auto job = jobs[size_t(write)];
    result["key"] = job.key;
    const auto kept = copy(job.root, temp.filePath("recovery"));
    result["snapshotExists"] = QFileInfo::exists(kept + "/project.edi");
    finish(size_t(write), true);
    session->closeProject();
    session->openStoredProject(job.key, true);
    int read = -1;
    for (size_t i = 0; i < jobs.size(); ++i)
        if (jobs[i].action == "load" && jobs[i].recovery) read = int(i);
    result["readsRecovery"] = read >= 0;
    if (read < 0) return result;
    finish(size_t(read), true, kept);
    settle(*session);
    result["after"] = untitledWorkState(session->project()->project());
    result["title"] = session->project()->title();
    result["modified"] = session->project()->modified();
    result["stillUntitled"] = session->needsSaveAs();
    window->setProperty("quitting", true);
    window->setProperty("visible", false);
    return result;
}

QJsonObject untitledPublication(const QString& mode) {
    browser = true;
    WebStorage::instance()->usable_ = true;
    jobs.clear();
    publications.clear();
    QTemporaryDir temp;
    QQmlEngine engine;
    edi_app::configure_engine(engine);
    QQmlComponent component(&engine);
    component.loadFromModule("edi.app", "Main");
    std::unique_ptr<QObject> window(component.create());
    need(bool(window), qPrintable(component.errorString()));
    window->setProperty("visible", true);
    auto* session = engine.singletonInstance<Session*>("edi.app", "Session");
    need(session && session->startUntitledProject(), "The app owns an actual browser untitled project");
    need(session->project()->createStructure(), "The queued project owns a real scientific structure");
    session->project()->setTitle("Snapshot at the time of Save");
    settle(*session);
    auto* dialog = window->findChild<QObject*>("unsavedChanges");
    need(dialog, "Browser Quit reaches the actual window guard");
    need(QMetaObject::invokeMethod(window.get(), "close"), "The actual window receives Quit");
    turn();
    need(dialog->property("visible").toBool(), "The unsaved browser work prompts before Quit");
    need(QMetaObject::invokeMethod(dialog, "accept"), "The window dispatches the actual guard Save");
    turn();
    const auto id = session->untitledOperationId();
    need(id > 0, "Quit's Save creates an identified naming request");
    QSignalSpy settled(session, &Session::untitledSettled);
    QSignalSpy reopened(dialog, SIGNAL(aboutToShow()));
    need(reopened.isValid(), "The original Quit prompt exposes whether the action ran again");
    const bool admitted = session->acceptUntitled(id, "browser-publication", "", "", "Snapshot at the time of Save", "", false);
    need(admitted && publications.size() == 1, "The first save reaches a single actual browser publication request");
    const auto publication = publications.front();
    need(publication.id == id && !publication.stage.isEmpty(), "The original guard naming owns the browser stage");
    const bool pending = settled.isEmpty() && window->property("visible").toBool();
    const auto decision = publication.check();
    need(decision.outcome == QLatin1String("go"), "The unmodified staged snapshot enters the actual precommit check");
    const bool commit = mode != QLatin1String("refused");
    const QString committedFolder = temp.filePath("committed");
    if (commit) copy(publication.folder, committedFolder);
    const bool file = QFileInfo::exists(committedFolder + "/project.edi");
    QString title;
    if (file)
        title = QString::fromStdString(
            edi::load_project(committedFolder.toStdString(), edi::ProjectLoadMode::Construction).metadata.title);
    WebStorageAnswer answer;
    answer.ok = commit;
    answer.outcome = commit ? QStringLiteral("published") : QStringLiteral("rejected");
    answer.message = commit ? QString() : QStringLiteral("Independent durable storage refusal");
    publication.answer(answer);
    for (int pass = 0; pass < 8; ++pass) turn();
    QJsonArray states;
    bool ids = true;
    for (const auto& args : settled) {
        ids = ids && args.at(0).toULongLong() == id;
        states.append(args.at(1).toString());
    }
    const auto visible = window->property("visible").toBool();
    const auto modified = session->project() && session->project()->modified();
    window->setProperty("quitting", true);
    window->setProperty("visible", false);
    publications.clear();
    browser = false;
    return {{"mode", mode}, {"pending", pending}, {"ids", ids}, {"states", states},
            {"durable", file}, {"title", title}, {"visible", visible}, {"modified", modified},
            {"reopened", !reopened.isEmpty()}};
}
