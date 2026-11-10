// The actual FitJob remains the optimizer and publisher. The public polled seam
// supplies deterministic failure/Stop, and the original typed completion runs whole.
namespace {
struct EndingFitObservation {
    QString ending;
    edi::Project* live = nullptr;
    QPointer<FitViewModel> fit;
    std::atomic<int> polls = 0;
    std::mutex mutex;
    std::condition_variable changed;
    bool stopDelivered = false;
    bool finished = false;
    edi::FitStatus status = edi::FitStatus::ERROR;
    QString refusal;
};
std::shared_ptr<EndingFitObservation> endingFitObservation;
}  // namespace

// This ordinary typed function receives the constructor's explicit this pointer.
// The builder proves the entire compiler-demangled signature before rebinding
// only the app's undefined import. The actual core constructor is untouched.
void operation_fit_job_ctor(edi::FitJob* self, edi::Project& live, edi::work::Worker& worker,
                            edi::FitJob::Hooks hooks, edi::FitJob::Seams seams,
                            edi::CancelCallback checkpoint) {
    if (const auto context = endingFitObservation) {
        need(!context->live, "One ending witness observes exactly one actual FitJob owner");
        context->live = &live;
        const auto originalPoll = std::move(seams.polled);
        seams.polled = [context, originalPoll](int poll) {
            context->polls = poll;
            if (originalPoll) originalPoll(poll);
            if (poll != 1) return;
            if (context->ending == "error")
                throw std::runtime_error(
                    "Independently requested worker failure at its public poll seam");
            if (context->ending == "stop") {
                QMetaObject::invokeMethod(
                    context->fit,
                    [context] {
                        need(bool(context->fit), "Stop retains the original actual fit receiver");
                        context->fit->cancel();
                        std::lock_guard lock(context->mutex);
                        context->stopDelivered = true;
                        context->changed.notify_all();
                    },
                    Qt::QueuedConnection);
                std::unique_lock lock(context->mutex);
                need(context->changed.wait_for(lock, std::chrono::seconds(10),
                                               [&] { return context->stopDelivered; }),
                     "The actual owner receives Stop before the worker reads cancellation");
            }
        };
        const auto originalFinished = std::move(hooks.finished);
        hooks.finished = [context, originalFinished](const edi::FitReport& report) {
            context->status = report.status;
            context->refusal = QString::fromStdString(report.refusal);
            if (originalFinished) originalFinished(report);
            context->finished = true;
        };
    }
    new (static_cast<void*>(self))
        edi::FitJob(live, worker, std::move(hooks), std::move(seams), std::move(checkpoint));
}
namespace {
QJsonArray fitEndingParameters(const edi::Project& source) {
    auto project = source;
    QJsonArray values;
    for (const auto& entry : edi::parameter_entries(project)) {
        const auto& p = *entry.parameter;
        values.append(
            QJsonObject{{"path", QString::fromStdString(entry.path)},
                        {"value", double(p.value)},
                        {"uncertainty", p.uncertainty ? QJsonValue(*p.uncertainty) : QJsonValue()},
                        {"free", bool(p.free)}});
    }
    return values;
}
QJsonObject fitEndingBoundary(const QString& source, const QStringList& spec) {
    need(spec.size() == 5,
         "A fit ending declares its actual entry, notification, outcome and save route");
    const auto entry = spec[1], moment = spec[2], ending = spec[3], route = spec[4];
    const auto context = std::make_shared<EndingFitObservation>();
    context->ending = ending;
    endingFitObservation = context;
    const auto disarm = qScopeGuard([] { endingFitObservation.reset(); });
    QTemporaryDir temp;
    Session session(nullptr);
    auto input = preciseInput(source, temp.filePath("original"));
    if (route == "save-archive") {
        const auto zip = temp.filePath("original.zip");
        edi::write_project_archive(input.toStdString(), zip.toStdString());
        input = zip;
    }
    need(session.openProject(QUrl::fromLocalFile(input)),
         "The fit ending opens its real scientific input");
    settle(session);
    if (route.startsWith("web-")) {
        // Browser opening constructs a second model. Only the actual active job is observed.
        endingFitObservation.reset();
        context->live = nullptr;
        endingFitObservation = context;
        openBrowserInput(session, session.project()->path(), "browser");
    }
    auto* owner = session.project();
    auto* fit = owner->fit();
    need(context->live == &owner->project(),
         "The seam belongs to the active original fit project");
    context->fit = fit;
    endingFitObservation.reset();
    owner->setIncludeDataOnSave("linked");
    owner->analysis()->setMaxIterations(2);
    ParameterItem* scale = nullptr;
    for (auto* item : owner->findChildren<ParameterItem*>()) {
        item->setFree(false);
        if (!scale && item->name() == "scale") scale = item;
    }
    need(scale, "The independent saved powder input has an actual scale editor");
    scale->setValue(scale->value() * 1.173);
    scale->setFree(true);
    need(scale->isFree(), "The actual optimizer has one nontrivial admitted free scale");
    settle(session);
    owner->setDescription("Independently authored fit-ending save state");
    jobs.clear();
    durable.clear();
    stageKinds.clear();
    archiveSources.clear();
    const auto target = temp.filePath(route.contains("zip") ? "result.zip" : "result");
    const auto originalPath = owner->path();
    const bool oldTransport = forceSerializedBrowser;
    forceSerializedBrowser = true;
    const auto restore = qScopeGuard([oldTransport] { forceSerializedBrowser = oldTransport; });
    const auto priorSessionError = session.lastError();
    const auto priorModelError = owner->lastError();
    QSignalSpy refused(owner, &ProjectViewModel::refused);
    QSignalSpy saveFailed(&session, &Session::webSaveFailed);
    bool reached = false, returned = false, held = false;
    QString error;
    QJsonArray parametersAtPlan;
    const auto request = [&] {
        if (route.startsWith("assistant-")) {
            const QPointer<ProjectViewModel> original(owner);
            if (!session.requestAssistantSaveAs(
                    "fit-ending", "result", original, session.assistant_epoch_,
                    [&session, original] { return original && session.project() == original; },
                    [&session](const QUrl& url, bool zip, bool copy) {
                        return session.saveProjectAs(url, zip, copy);
                    },
                    [] {}))
                return false;
            return session.completeAssistantSaveAs("fit-ending", QUrl::fromLocalFile(target),
                                                   route.contains("zip"), false);
        }
        return boundarySaveRequest(session, route, target);
    };
    const auto attempt = [&] {
        if (reached) return;
        reached = true;
        std::cerr << "boundary-reached: actual fit ending; real Save request\n" << std::flush;
        returned = request();
        parametersAtPlan = fitEndingParameters(owner->project());
        error = (session.lastError() != priorSessionError ? session.lastError() : QString()) +
                (owner->lastError() != priorModelError ? owner->lastError() : QString());
        // A real asynchronous write remains held until the entire terminal callback returns.
        held = nextWrite(0) < jobs.size();
    };
    if (moment == "running-false")
        QObject::connect(
            fit, &FitViewModel::runningChanged, &session,
            [&] {
                if (!fit->running()) attempt();
            },
            Qt::DirectConnection);
    const auto nativeCompletion = [&](const edi::FitReport&, bool) {
        if (moment == "native-result") attempt();
    };
    if (entry == "ordinary")
        fit->start();
    else if (entry == "native")
        fit->startNative(nativeCompletion);
    else {
        need(entry == "visible-native", "Every fit entry is one actual enumerated consumer");
        const auto identity = fit->beginAttempt();
        const auto token = fit->prepareNativeCompletion(nativeCompletion, identity);
        fit->start();
        fit->discardNativePreparation(token);
    }
    if (!context->finished) {
        QEventLoop loop;
        QTimer deadline, check;
        deadline.setSingleShot(true);
        QObject::connect(&deadline, &QTimer::timeout, &loop, &QEventLoop::quit);
        QObject::connect(&check, &QTimer::timeout, &loop, [&] {
            if (context->finished) loop.quit();
        });
        deadline.start(10000);
        check.start(1);
        loop.exec();
    }
    need(context->finished, "The real optimizer delivers its complete original terminal callback");
    need(reached, "The declared actual fit notification reaches the Save entry");
    const auto afterTerminal = fitEndingParameters(owner->project());
    const bool dirtyAfterTerminal = owner->modified();
    const int jobsAtTerminal = jobs.size(), stagesAtTerminal = stageKinds.size();
    const bool explicitRefusal = !error.isEmpty() || !refused.isEmpty() || !saveFailed.isEmpty();
    finishPolicyIo();
    settle(session);
    const auto afterWrite = fitEndingParameters(owner->project());
    int readbacks = 0;
    const auto readPublished = [&] {
        QString published;
        QTemporaryDir decoded;
        if (route.startsWith("web-")) {
            need(!durable.isEmpty(),
                 "The post-terminal browser control publishes real serialized bytes");
            published = temp.filePath("readback-" + QString::number(readbacks++));
            need(QDir().mkpath(published), "The independent readback folder exists");
            for (auto it = durable.last().begin(); it != durable.last().end(); ++it) {
                const auto name = QDir(published).filePath(it.key());
                need(QDir().mkpath(QFileInfo(name).path()),
                     "A saved member retains its relative location");
                QFile file(name);
                need(
                    file.open(QIODevice::WriteOnly) && file.write(it.value()) == it.value().size(),
                    "The readback contains the actual writer bytes");
            }
        } else if (route == "save-archive")
            published = input;  // The actual user archive, never its retired unpacked folder.
        else
            published = route == "save" ? originalPath : target;
        if (QFileInfo(published).isFile()) {
            QFile file(published);
            need(file.open(QIODevice::ReadOnly), "The actual archive control is readable");
            QString refusal;
            published = edi_app::WebFiles::unpack(file.readAll(), decoded.path(), refusal);
            need(!published.isEmpty(), "The actual archive control contains an admitted project");
        }
        return edi::load_project(published.toStdString());
    };
    const bool firstCompleted = held || (returned && !explicitRefusal);
    const bool firstClean = !owner->modified();
    const auto firstLiveDescription = owner->description();
    QJsonArray firstDurable;
    QString firstDescription;
    if (firstCompleted) {
        auto first = readPublished();
        firstDurable = fitEndingParameters(first);
        firstDescription = QString::fromStdString(first.metadata.description);
    }
    // This control is additional evidence, never a substitute for the first save's result.
    const bool retry = request();
    finishPolicyIo();
    settle(session);
    auto readback = readPublished();
    return {{"reached", reached},
            {"firstCompleted", firstCompleted},
            {"firstClean", firstClean},
            {"firstDurable", firstDurable},
            {"firstDescription", firstDescription},
            {"firstLiveDescription", firstLiveDescription},
            {"polls", context->polls.load()},
            {"stopped", context->stopDelivered},
            {"terminalStatus", int(context->status)},
            {"terminalError", context->refusal},
            {"returned", returned},
            {"held", held},
            {"explicitRefusal", explicitRefusal},
            {"parametersAtPlan", parametersAtPlan},
            {"afterTerminal", afterTerminal},
            {"afterWrite", afterWrite},
            {"dirtyAfterTerminal", dirtyAfterTerminal},
            {"jobsAtTerminal", jobsAtTerminal},
            {"stagesAtTerminal", stagesAtTerminal},
            {"retry", retry},
            {"final", fitEndingParameters(owner->project())},
            {"durable", fitEndingParameters(readback)},
            {"modified", owner->modified()},
            {"durableDescription", QString::fromStdString(readback.metadata.description)},
            {"success", context->status != edi::FitStatus::ERROR &&
                            context->status != edi::FitStatus::CANCELLED &&
                            context->status != edi::FitStatus::SUPERSEDED},
            {"error", context->status == edi::FitStatus::ERROR},
            {"cancelled", context->status == edi::FitStatus::CANCELLED}};
}
}  // namespace
