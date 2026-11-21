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
