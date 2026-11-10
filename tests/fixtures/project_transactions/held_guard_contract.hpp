// Query loss-prevention state while ordinary held-change publication is silent.
namespace {
QJsonObject heldGuard(const QString& source, const QStringList& spec) {
    need(spec.size() == 2, "A held guard declares its actual loss-prevention continuation");
    const auto action = spec[1];
    QTemporaryDir temp;
    Session session(nullptr);
    const auto input = copy(source, temp.filePath("original"));
    const auto replacement = copy(source, temp.filePath("replacement"));
    need(session.openProject(QUrl::fromLocalFile(input)),
         "The held guard starts from a real saved project");
    settle(session);
    if (action.startsWith("browser-")) openBrowserInput(session, input, "folder");
    QPointer<ProjectViewModel> original = session.project();
    ParameterItem* value = nullptr;
    for (auto* item : original->findChildren<ParameterItem*>())
        if (item->name() == "length_a") {
            value = item;
            break;
        }
    need(value, "The held guard reaches the real public lattice parameter");
    original->setIncludeDataOnSave("linked");
    value->setValue(10.0);
    settle(session);
    need(session.save(), "The authored initial lattice is saved through the actual Session");
    if (action.startsWith("browser-")) finishPolicyIo();
    settle(session);
    turn();
    pumpUntil([&] { return original && !original->property("saving").toBool(); },
              "The initial owned save finishes before the next held operation");
    need(!original->modified(), "The loss-prevention witness is initially genuinely clean");
    jobs.clear();
    if (action == "browser-open")
        session.openWebProject("folder");
    else if (action == "browser-stored")
        session.openStoredProject("newer", false);
    else if (action == "browser-recovery")
        session.openStoredProject("newer", true);
    QSignalSpy fields(value, &ParameterItem::valueChanged);
    QSignalSpy dirty(original, &ProjectViewModel::modifiedChanged);
    QSignalSpy edited(original, &ProjectViewModel::projectEdited);
    std::vector<std::unique_ptr<QSignalSpy>> projectSignals;
    const auto* projectMeta = original->metaObject();
    for (int at = projectMeta->methodOffset(); at < projectMeta->methodCount(); ++at) {
        const auto signal = projectMeta->method(at);
        const auto name = signal.name();
        if (signal.methodType() == QMetaMethod::Signal && name != "calculatingChanged" &&
            name != "calculationStarted" && name != "calculationFinished" &&
            name != "adjustingChanged")
            projectSignals.push_back(std::make_unique<QSignalSpy>(original, signal));
    }
    original->setAdjusting(true);
    value->setValue(10.3);
    settle(session);
    const bool heldDirty = original->modified();
    const int heldFields = fields.size(), heldModified = dirty.size(), heldEdited = edited.size();
    int heldProjectSignals = 0;
    for (const auto& signal : projectSignals) heldProjectSignals += signal->size();
    bool settlementDirty = true, readingSettlement = true;
    int settlementPublications = 0;
    QObject callbackContext;
    const auto guardQuery = QObject::connect(
        original, &ProjectViewModel::edited, &callbackContext,
        [&] {
            if (!readingSettlement) return;
            ++settlementPublications;
            settlementDirty = settlementDirty && original && original->modified();
        },
        Qt::DirectConnection);
    bool asideDirty = false;
    if (action == "aside") {
        need(session.setProjectAside(),
             "The tutorial set-aside request retains the actual held owner");
        asideDirty = session.projectSetAsideModified();
        session.restoreProjectSetAside();
    }
    if (action.startsWith("browser-")) {
        need(jobs.size() == 1, "The held edit follows one actually outstanding browser open");
        finish(0, true, replacement);
    }
    const bool preserved = original && session.project() == original;
    bool saved = false, reopened = false;
    if (preserved && action == "save") {
        saved = session.save();
        if (saved) {
            const auto written = edi::load_project(original->path().toStdString());
            reopened = !written.structures.empty() &&
                       written.structures[0]->cell.length_a.value.get() == 10.3;
        }
    }
    bool oneUndo = false, releasedDirty = false;
    if (preserved) {
        original->setAdjusting(false);
        settle(session);
        releasedDirty = original->modified();
        readingSettlement = false;
        QObject::disconnect(guardQuery);
        original->undo();
        settle(session);
        for (auto* restored : original->findChildren<ParameterItem*>())
            if (restored->name() == "length_a") {
                oneUndo = restored->value() == 10.0;
                break;
            }
    }
    readingSettlement = false;
    QObject::disconnect(guardQuery);
    return {{"heldDirty", heldDirty},
            {"heldProjectSignals", heldProjectSignals},
            {"heldFields", heldFields},
            {"heldModified", heldModified},
            {"heldEdited", heldEdited},
            {"preserved", preserved},
            {"asideDirty", asideDirty},
            {"saved", saved},
            {"reopened", reopened},
            {"releasedDirty", releasedDirty},
            {"oneUndo", oneUndo},
            {"settlementDirty", settlementDirty},
            {"settlementPublications", settlementPublications}};
}
}  // namespace
