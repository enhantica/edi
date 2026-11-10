// Request ownership at synchronous publication reentry and shared-fetch delivery.
namespace {
struct OwnerBoundary {
    bool entered = false, retiring = false;
    int writes = 0, reports = 0;
};
OwnerBoundary* ownerBoundary = nullptr;
void ownerCoreAttempt() {
    if (QThread::currentThread() != QCoreApplication::instance()->thread()) return;
    if (ownerBoundary && ownerBoundary->entered && !ownerBoundary->retiring)
        ++ownerBoundary->writes;
}
QJsonObject ownerAtSettlement(const QString& source, const QStringList& spec) {
    need(spec.size() == 4,
         "A settlement owner declares its public save, signal and retirement action");
    const auto route = spec[1], signal = spec[2], action = spec[3];
    QTemporaryDir temp;
    Session session(nullptr);
    const auto input = copy(source, temp.filePath("original"));
    const auto replacement = copy(source, temp.filePath("successor"));
    need(session.openProject(QUrl::fromLocalFile(input)),
         "Settlement starts from a real saved owner");
    settle(session);
    if (route.startsWith("web-"))
        openBrowserInput(session, input,
                         route == "web-save-zip"       ? "zip"
                         : route == "web-save-browser" ? "browser"
                                                       : "folder");
    QPointer<ProjectViewModel> original = session.project();
    original->setIncludeDataOnSave("linked");
    need(session.save(), "The initial owner is clean before the actual held edit");
    if (route.startsWith("web-")) finishPolicyIo();
    settle(session);
    turn();
    pumpUntil([&] { return original && !original->property("saving").toBool(); },
              "The initial owned save finishes before the next held operation");
    need(!original->modified(), "The settlement witness has no earlier dirty-state shortcut");
    ParameterItem* value = nullptr;
    for (auto* item : original->findChildren<ParameterItem*>())
        if (item->name() == "length_a") {
            value = item;
            break;
        }
    need(value, "Settlement owns an actual editable scientific parameter");
    QString target = temp.filePath(
        route.contains("zip") || route == "save-archive" ? "requested.zip" : "requested");
    if (route == "save-archive") {
        edi::write_project_archive(original->path().toStdString(), target.toStdString());
        need(session.openProject(QUrl::fromLocalFile(target)),
             "Archive settlement uses its ordinary Save entry");
        settle(session);
        original = session.project();
        value = nullptr;
        for (auto* item : original->findChildren<ParameterItem*>())
            if (item->name() == "length_a") {
                value = item;
                break;
            }
        need(value, "The archive owner retains its actual parameter before the hold");
    }
    if (route == "unsaved-folder") {
        original->project_->scan_data_root = original->project_->path;
        original->project_->path.clear();
        original->project_->metadata.path.clear();
    }
    original->setAdjusting(true);
    value->setValue(value->value() * 1.013);
    settle(session);
    OwnerBoundary observed;
    bool aliveInCallback = false, attempted = false, refusalVisible = false,
         ownerPreservedAtRefusal = false;
    QSignalSpy refused(original, &ProjectViewModel::refused);
    Image settledImage;
    QObject callbackContext;
    const auto report = [&] {
        if (observed.entered && !observed.retiring) ++observed.reports;
    };
    QObject::connect(original, &ProjectViewModel::edited, &callbackContext, report,
                     Qt::DirectConnection);
    QObject::connect(original, &ProjectViewModel::projectEdited, &callbackContext, report,
                     Qt::DirectConnection);
    QObject::connect(original, &ProjectViewModel::modifiedChanged, &callbackContext, report,
                     Qt::DirectConnection);
    const auto retire = [&] {
        if (attempted) return;
        attempted = true;
        observed.retiring = true;
        std::cerr << "boundary-reached: real held settlement; retire actual request owner\n"
                  << std::flush;
        if (action == "close")
            session.closeProject();
        else {
            const bool admitted = session.openProject(QUrl::fromLocalFile(replacement));
            refusalVisible = !admitted;
        }
        observed.entered = !original || session.project() != original;
        ownerPreservedAtRefusal = original && session.project() == original;
        refusalVisible = refusalVisible || !session.lastError().isEmpty() || !refused.isEmpty() ||
                         (original && !original->lastError().isEmpty());
        aliveInCallback = !original.isNull();
        settledImage = image(temp.path(), true);
        observed.retiring = false;
    };
    if (signal == "edited")
        QObject::connect(original, &ProjectViewModel::edited, &callbackContext, retire,
                         Qt::DirectConnection);
    else
        QObject::connect(original, &ProjectViewModel::modifiedChanged, &callbackContext, retire,
                         Qt::DirectConnection);
    PolicyQuestions questions(session);
    jobs.clear();
    ownerBoundary = &observed;
    boundaryDownload = route == "web-download";
    struct ResetOwner {
        ~ResetOwner() {
            ownerBoundary = nullptr;
            boundaryDownload = false;
        }
    } reset;
    boundarySaveRequest(session, route, target);
    turn();
    const auto reportsBeforeAnswer = questions.count();
    // A retired request must not have created any question or storage job that
    // another user could later answer as if it belonged to the successor.
    int pendingWrites = 0;
    for (const auto& job : jobs)
        if (!job.recovery && job.action == "write") ++pendingWrites;
    const bool intact = !observed.entered || image(temp.path(), true) == settledImage;
    return {{"entered", attempted},
            {"retired", observed.entered},
            {"refusalVisible", refusalVisible},
            {"ownerPreservedAtRefusal", ownerPreservedAtRefusal},
            {"aliveInCallback", aliveInCallback},
            {"writesAfterRetirement", observed.writes + pendingWrites},
            {"reportsAfterRetirement", observed.reports + reportsBeforeAnswer},
            {"userTreesIntact", intact}};
}
}  // namespace
