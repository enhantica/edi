// Reenter through real adoption announcements; scientific truth comes from
// actual durable readback.
namespace {
QJsonObject adoptionBoundary(const QString& source, const QStringList& spec) {
    need(spec.size() == 4,
         "Adoption declares its actual Save route, "
         "notification and listener action");
    const auto route = spec[1], signal = spec[2], action = spec[3];
    QTemporaryDir temp;
    Session session(nullptr);
    auto input = copy(source, temp.filePath("original"));
    const auto successor = copy(source, temp.filePath("successor"));
    const auto successorBefore = image(successor, true);
    QString target =
        temp.filePath(route.contains("zip") || route == "save-archive" ? "saved.zip" : "saved");
    if (route == "save-archive") {
        edi::write_project_archive(input.toStdString(), target.toStdString());
        input = target;
    }
    need(session.openProject(QUrl::fromLocalFile(input)),
         "Adoption opens its independent saved scientific input");
    settle(session);
    if (route.startsWith("web-"))
        openBrowserInput(session, session.project()->path(),
                         route.contains("zip")       ? "zip"
                         : route.contains("browser") ? "browser"
                                                     : "folder");
    const QPointer<ProjectViewModel> original = session.project();
    original->setIncludeDataOnSave("linked");
    original->setDescription("An independently authored dirty state before adoption");
    need(original->modified(),
         "The dirty-clear listener must observe an actual "
         "dirty-to-clean transition");
    const auto actualValue = [&] {
        need(original && session.project() == original,
             "A scientific observation belongs to its original current owner");
        return double(original->project().structure().cell.length_a.value);
    };
    const double plannedValue = actualValue();
    bool stimulusCompleted = false;
    bool entered = false, editAccepted = false, replaced = false, explicitRefusal = false;
    double requested = 0, observedInside = 0;
    QPointer<ProjectViewModel> replacement;
    QString replacementLocation, replacementArchive, replacementProjectLocation;
    bool replacementNeedsSaveAs = false;
    QSignalSpy refused(original, &ProjectViewModel::refused);
    QObject callbackContext;
    const auto reenter = [&] {
        if (entered || !original || session.project() != original) return;
        if (signal == "clean" && original->modified()) return;
        entered = true;
        std::cerr << "boundary-reached: adoption announcement; real listener reentry\n"
                  << std::flush;
        const int beforeRefusals = refused.size();
        const auto priorSessionError = session.lastError();
        const auto priorModelError = original->lastError();
        if (action == "replace") {
            session.openProject(QUrl::fromLocalFile(successor));
            replaced = !original || session.project() != original;
            if (replaced) {
                replacement = session.project();
                need(replacement && QFileInfo(replacement->path()).canonicalFilePath() ==
                                        QFileInfo(successor).canonicalFilePath(),
                     "An admitted replacement actually opens its independently "
                     "authored folder");
                replacementLocation = session.locationText();
                replacementProjectLocation = session.projectLocation();
                replacementArchive = session.openedArchive();
                replacementNeedsSaveAs = session.needsSaveAs();
            }
        } else {
            need(action == "edit", "The adoption listener uses an actual enumerated entry");
            ParameterItem* value = nullptr;
            for (auto* candidate : original->findChildren<ParameterItem*>())
                if (candidate->name() == "length_a") {
                    value = candidate;
                    break;
                }
            need(value, "The adoption listener reaches a real scientific value editor");
            requested = actualValue() + .037125;
            value->setValue(requested);
            observedInside = actualValue();
            editAccepted = observedInside == requested;
            explicitRefusal = !value->lastError().isEmpty();
        }
        explicitRefusal =
            explicitRefusal || refused.size() > beforeRefusals ||
            (!session.lastError().isEmpty() && session.lastError() != priorSessionError) ||
            (original && !original->lastError().isEmpty() &&
             original->lastError() != priorModelError);
        stimulusCompleted = true;
    };
    if (signal == "path")
        QObject::connect(original, &ProjectViewModel::pathChanged, &callbackContext, reenter,
                         Qt::DirectConnection);
    else {
        need(signal == "clean",
             "The listener watches an actual adoption or dirty-clear announcement");
        QObject::connect(original, &ProjectViewModel::modifiedChanged, &callbackContext, reenter,
                         Qt::DirectConnection);
    }
    jobs.clear();
    durable.clear();
    const auto originalFolder = original->path();
    forceSerializedBrowser = true;
    const auto resetTransport = qScopeGuard([] { forceSerializedBrowser = false; });
    const bool returned = boundarySaveRequest(session, route, target);
    finishPolicyIo();
    need(!entered || stimulusCompleted,
         "The actual listener completes its intended real edit or replacement observation");
    turn();
    if (session.project()) settle(session);
    QString published;
    if (route.startsWith("web-")) {
        need(durable.size() == 1,
             "The actual browser save publishes exactly one owned destination");
        published = temp.filePath("observed-browser-output");
        need(QDir().mkpath(published),
             "The browser output is materialized from actual serialized bytes");
        const auto& payload = durable.first();
        for (auto at = payload.begin(); at != payload.end(); ++at) {
            const auto file = QDir(published).filePath(at.key());
            need(QDir().mkpath(QFileInfo(file).path()),
                 "Every serialized member retains its real relative path");
            QFile output(file);
            need(
                output.open(QIODevice::WriteOnly) && output.write(at.value()) == at.value().size(),
                "The adoption oracle reads exactly the actual serialized output "
                "bytes");
        }
    } else
        published = route == "save" ? originalFolder : target;
    QTemporaryDir decoded;
    if (QFileInfo(published).isFile()) {
        QFile archive(published);
        need(archive.open(QIODevice::ReadOnly),
             "Actual archive save bytes are readable for scientific readback");
        QString error;
        published = edi_app::WebFiles::unpack(archive.readAll(), decoded.path(), error);
        need(!published.isEmpty(), "The actual saved archive contains a readable project");
    }
    const auto written = edi::load_project(published.toStdString());
    const auto durableValue = double(written.structure().cell.length_a.value);
    const bool current = original && session.project() == original;
    const double finalValue = current ? actualValue() : 0.;
    const bool dirtyBeforeUndo = current && original->modified();
    const bool replacementOwnerRetained =
        !replaced || (replacement && session.project() == replacement &&
                      session.locationText() == replacementLocation &&
                      session.projectLocation() == replacementProjectLocation &&
                      session.openedArchive() == replacementArchive &&
                      session.needsSaveAs() == replacementNeedsSaveAs);
    double afterUndo = 0.;
    bool undoAvailable = false;
    if (current && editAccepted) {
        undoAvailable = original->canUndo();
        original->undo();
        settle(session);
        afterUndo = actualValue();
    }
    return {{"entered", entered},
            {"returned", returned},
            {"editAccepted", editAccepted},
            {"replaced", replaced},
            {"explicitRefusal", explicitRefusal},
            {"current", current},
            {"modified", dirtyBeforeUndo},
            {"replacementOwnerRetained", replacementOwnerRetained},
            {"durableDescription", QString::fromStdString(written.metadata.description)},
            {"plannedValue", plannedValue},
            {"requested", requested},
            {"observedInside", observedInside},
            {"finalValue", finalValue},
            {"durableValue", durableValue},
            {"undoAvailable", undoAvailable},
            {"afterUndo", afterUndo},
            {"successorIntact", image(successor, true) == successorBefore}};
}
}  // namespace
