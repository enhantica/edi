// Independent receipts retain each exact object, declaration and digest, including equal IDs.
namespace {
struct ExactCollectionReceipt {
    std::vector<ExactCollectionTarget> targets;
    int calls = 0;
    bool falseSuccess = false, refusedWhileBusy = false;
    QString error;
    QJsonArray atCompletion;
};
template <class VM>
QJsonObject exactCollectionOwner(Session& session, VM* model, const QString& root,
                                 const QStringList& spec) {
    if constexpr (!requires(VM& value) {
                      value.fetchCollectionData(std::function<void(const QString&)>{});
                  }) {
        return {{"supported", false}};
    } else {
        need(spec.size() == 6,
             "The exact-target boundary declares scenario, producer, outcome, order and mutation");
        const auto scenario = spec[1], producer = spec[2], outcome = spec[3], order = spec[4],
                   mutation = spec[5];
        const QByteArray bytesX("17.5 4 .5\n18 9 1.25\n18.5 16 2.5\n");
        const QByteArray bytesY("17.5 25 .5\n18 36 1.25\n18.5 49 2.5\n");
        const QJsonArray rowsX{QJsonArray{17.5, 4, .5}, QJsonArray{18, 9, 1.25},
                               QJsonArray{18.5, 16, 2.5}};
        const QJsonArray rowsY{QJsonArray{17.5, 25, .5}, QJsonArray{18, 36, 1.25},
                               QJsonArray{18.5, 49, 2.5}};
        QPointer<VM> owner(model);
        std::vector<ExactCollectionTarget> targets;
        const auto admit = [&](const QString& label, const QString& entry, const QByteArray& bytes,
                               const QJsonArray& rows) {
            QString text;
            for (const auto& [name, body] : model->savedFiles())
                if (name.starts_with("experiments/") && name.ends_with(".edi")) {
                    text = QString::fromStdString(body);
                    break;
                }
            need(!text.isEmpty(), "Only valid experiment setup syntax comes from the engine");
            const auto start = text.indexOf(
                QRegularExpression("(?m)^loop_[\\t ]*\\r?\\n[\\t ]*(?=_(?:data|refln)\\.)"));
            if (start >= 0) text.truncate(start);
            text.remove(QRegularExpression(
                "(?m)^_data_source\\.(?:path|collection_id|digest)[^\\n]*\\n?"));
            text.replace(QRegularExpression("(?m)^data_[^\\n]+"), "data_" + label);
            const QString digest = QString::fromLatin1(
                QCryptographicHash::hash(bytes, QCryptographicHash::Sha256).toHex());
            text += "\n_data_source.collection_id '" + entry + "'\n_data_source.digest '" +
                    digest + "'\n";
            const auto path = QDir(root).filePath(label + ".edi");
            QFile file(path);
            need(file.open(QIODevice::WriteOnly),
                 "An exact target has its own authored declaration");
            need(file.write(text.toUtf8()) == text.toUtf8().size(),
                 "Every independently declared target is completely written");
            file.close();
            const bool accepted = model->loadExperiments({QUrl::fromLocalFile(path)});
            settle(session);
            if (accepted) {
                const auto held =
                    model->project_->experiments[model->project_->experiments.size() - 1];
                targets.push_back({held, label, entry, digest, text, rows});
            }
            return accepted;
        };
        need(admit("first_target", "owned-X", bytesX, rowsX),
             "The first exact target is admitted before any fetch starts");
        bool added = false;
        if (scenario == "pre-existing" || scenario == "retry" || scenario == "observer") {
            added = admit("second_target", "owned-X", bytesX, rowsX);
            need(added, "Both distinct equal-ID targets exist before the operation");
        }
        turn();
        struct Pending {
            QString entry;
            std::function<void(const QByteArray&, const QString&)> done;
        };
        std::vector<Pending> pending;
        const auto alive = std::make_shared<std::atomic<bool>>(true);
        struct EndWitness {
            std::shared_ptr<std::atomic<bool>> alive;
            ~EndWitness() { *alive = false; }
        } endWitness{alive};
        model->setCollectionFetcher([&, alive](const QString& entry, auto done) {
            if (*alive) pending.push_back({entry, std::move(done)});
        });
        const auto states = [&](const std::vector<ExactCollectionTarget>& wanted) {
            QJsonArray result;
            for (const auto& target : wanted) {
                bool present = false, sameDeclaration = false;
                QJsonArray rows;
                QString observedEntry, observedDigest;
                if (owner && session.project() == owner)
                    for (const auto& held : owner->project_->experiments)
                        if (held.get() == target.object.get()) {
                            present = true;
                            sameDeclaration =
                                QString::fromStdString(held->collection_id) == target.entry &&
                                QString::fromStdString(held->data_digest) == target.digest;
                            observedEntry = QString::fromStdString(held->collection_id);
                            observedDigest = QString::fromStdString(held->data_digest);
                            rows = independentRowsObserved(*held);
                        }
                result.append(QJsonObject{{"label", target.label},
                                          {"present", present},
                                          {"sameDeclaration", sameDeclaration},
                                          {"entry", observedEntry},
                                          {"digest", observedDigest},
                                          {"rows", rows},
                                          {"expected", target.rows}});
            }
            return result;
        };
        if (scenario == "observer") {
            const auto originals = targets;
            const auto file = QDir(root).filePath("independent-observer-rows.dat");
            QFile data(file);
            need(data.open(QIODevice::WriteOnly) && data.write(bytesX) == bytesX.size(),
                 "The observer control retains its independently authored measurements");
            data.close();
            const auto indexOf = [&](const auto& target) {
                for (std::size_t at = 0; at < model->project_->experiments.size(); ++at)
                    if (model->project_->experiments[at].get() == target.object.get()) return at;
                throw std::runtime_error("The observer control reaches its exact current object");
            };
            const auto selected = mutation == "second-only" ? 1 : 0;
            need(model->fillCollectionData(indexOf(originals[selected]), file),
                 "Only the selected exact observer-control object receives the authored rows");
            if (mutation == "removed" || mutation == "replacement") {
                model->removeExperiment(static_cast<int>(indexOf(originals.front())));
                settle(session);
                if (mutation == "replacement") {
                    need(admit("replacement_target", "owned-X", bytesX, rowsX),
                         "The observer control admits a distinct replacement with the same "
                         "resource ID");
                    need(model->fillCollectionData(indexOf(targets.back()), file),
                         "The replacement's own data cannot stand in for the retired original");
                }
            } else if (mutation == "entry")
                originals.front().object->collection_id = "independent-changed-entry";
            else if (mutation == "digest")
                originals.front().object->data_digest =
                    QCryptographicHash::hash(bytesY, QCryptographicHash::Sha256)
                        .toHex()
                        .toStdString();
            else
                need(mutation == "first-only" || mutation == "second-only",
                     "The observer-control accident is enumerated");
            return {{"supported", true},
                    {"observer", states(originals)},
                    {"distinctObjects", originals[0].object != originals[1].object}};
        }
        std::vector<std::shared_ptr<ExactCollectionReceipt>> receipts;
        bool mutationEntered = false, mutationAccepted = false, mutationRefused = false;
        int staleReports = 0, fitStartsMissing = 0, fitStartsAfterStop = 0;
        bool stopped = false;
        QObject callbackContext;
        QSignalSpy refusals(model, &VM::refused);
        const auto mutate = [&] {
            if (mutationEntered || mutation == "none" || !owner || session.project() != owner)
                return;
            mutationEntered = true;
            const int refusalCount = refusals.size();
            const auto previousError = model->lastError();
            const auto target = targets.front();
            std::size_t index = model->project_->experiments.size();
            for (std::size_t at = 0; at < model->project_->experiments.size(); ++at)
                if (model->project_->experiments[at].get() == target.object.get()) index = at;
            need(index < model->project_->experiments.size(),
                 "The injected mutation reaches its original exact target");
            std::cerr << "boundary-reached: mutate original exact fetch target\n" << std::flush;
            if (mutation.startsWith("remove"))
                model->removeExperiment(static_cast<int>(index));
            else {
                auto text = target.text;
                if (mutation.startsWith("entry"))
                    text.replace("_data_source.collection_id 'owned-X'",
                                 "_data_source.collection_id 'owned-Y'");
                else {
                    need(mutation.startsWith("digest"), "The exact-target mutation is enumerated");
                    text.replace(
                        target.digest,
                        QString::fromLatin1(
                            QCryptographicHash::hash(bytesY, QCryptographicHash::Sha256).toHex()));
                }
                const auto error = model->applyText(
                    "experiments/" + QString::fromStdString(target.object->name) + ".edi", text);
                mutationRefused = !error.isEmpty();
            }
            const auto now = states({target})[0].toObject();
            mutationAccepted = !now["present"].toBool() || !now["sameDeclaration"].toBool();
            mutationRefused =
                mutationRefused || refusals.size() > refusalCount ||
                (!model->lastError().isEmpty() && model->lastError() != previousError);
        };
        const auto fitTargets = targets;
        auto* fit = model->fit();
        QObject::connect(fit, &FitViewModel::runningChanged, &callbackContext, [&] {
            if (!fit->running()) return;
            if (stopped) ++fitStartsAfterStop;
            for (const auto& item : states(fitTargets)) {
                const auto state = item.toObject();
                if (!state["present"].toBool() || !state["sameDeclaration"].toBool() ||
                    state["rows"] != state["expected"])
                    ++fitStartsMissing;
            }
            fit->cancel();
        });
        const auto request = [&] {
            auto receipt = std::make_shared<ExactCollectionReceipt>();
            for (const auto& target : targets)
                if (!target.object->data && !target.object->reflections)
                    receipt->targets.push_back(target);
            receipts.push_back(receipt);
            const bool busy = !pending.empty();
            const auto admitting = std::make_shared<bool>(true);
            model->fetchCollectionData([&, receipt, busy, admitting, alive](const QString& error) {
                if (!*alive) return;
                ++receipt->calls;
                if (!owner || session.project() != owner) {
                    ++staleReports;
                    return;
                }
                receipt->error = error;
                receipt->refusedWhileBusy = busy && *admitting && !error.isEmpty();
                receipt->atCompletion = states(receipt->targets);
                if (error.isEmpty())
                    for (const auto& item : receipt->atCompletion) {
                        const auto state = item.toObject();
                        if (!state["present"].toBool() || !state["sameDeclaration"].toBool() ||
                            state["rows"] != state["expected"])
                            receipt->falseSuccess = true;
                    }
                if (receipts.front() == receipt && mutation.endsWith("callback")) mutate();
            });
            *admitting = false;
        };
        const auto startProducer = [&] {
            if (producer == "download")
                model->downloadCollectionData();
            else if (producer == "fit")
                fit->start();
            else
                need(producer == "fetch", "The exact target uses an actual enumerated producer");
        };
        // Change the actual producer/observer join order, not just a label on serial transports.
        if (order == "reverse") {
            request();
            startProducer();
        } else {
            startProducer();
            request();
        }
        bool admissionRefused = false, reindexed = false, reindexRefused = false;
        if (scenario == "added" || scenario == "different") {
            const int beforeRefusals = refusals.size();
            added =
                admit("second_target", scenario == "added" ? "owned-X" : "owned-Y",
                      scenario == "added" ? bytesX : bytesY, scenario == "added" ? rowsX : rowsY);
            admissionRefused =
                !added && (refusals.size() > beforeRefusals || !model->lastError().isEmpty());
        }
        if (scenario == "reindex") {
            const auto before = model->project_->experiments.size();
            const int beforeRefusals = refusals.size();
            model->removeExperiment(0);
            reindexed = model->project_->experiments.size() < before;
            reindexRefused =
                !reindexed && (refusals.size() > beforeRefusals || !model->lastError().isEmpty());
        }
        request();
        if (mutation.endsWith("publish"))
            for (auto* experiment : model->template findChildren<ExperimentViewModel*>())
                QObject::connect(experiment, &ExperimentViewModel::patternSourceChanged,
                                 &callbackContext, mutate, Qt::DirectConnection);
        if (scenario == "stop") {
            stopped = true;
            fit->cancel();
        }
        QJsonArray transportOrder;
        QElapsedTimer draining;
        draining.start();
        int completed = 0;
        bool retryIssued = false;
        QJsonArray partialTargets;
        while (draining.elapsed() < 10000 && completed < 32) {
            std::size_t selected = pending.size();
            for (std::size_t at = 0; at < pending.size(); ++at)
                if (pending[at].done && (selected == pending.size() || order == "reverse"))
                    selected = at;
            if (selected != pending.size()) {
                const auto entry = pending[selected].entry;
                auto done = std::move(pending[selected].done);
                const bool failed = outcome == "failure" ||
                                    (outcome == "partial" && entry == "owned-Y") ||
                                    (scenario == "retry" && !retryIssued && completed == 1);
                transportOrder.append(entry);
                done(failed               ? QByteArray()
                     : entry == "owned-Y" ? bytesY
                                          : bytesX,
                     failed ? "Independent exact-target transport refusal" : QString());
                ++completed;
            }
            turn();
            const bool transportsDone = std::none_of(pending.begin(), pending.end(),
                                                     [](const auto& p) { return bool(p.done); });
            bool currentDone = true;
            for (const auto& receipt : receipts) {
                bool current = true;
                for (const auto& item : states(receipt->targets)) {
                    const auto state = item.toObject();
                    current =
                        current && state["present"].toBool() && state["sameDeclaration"].toBool();
                }
                if (current && receipt->calls == 0) currentDone = false;
            }
            if (transportsDone && currentDone) {
                if (scenario == "retry" && !retryIssued) {
                    partialTargets = states(targets);
                    retryIssued = true;
                    request();  // A real later request retries only its still-unfilled original
                                // object.
                    draining.restart();
                } else
                    break;
            }
        }
        settle(session);
        QJsonArray reports;
        for (const auto& receipt : receipts) {
            bool current = true;
            for (const auto& item : states(receipt->targets)) {
                const auto state = item.toObject();
                current =
                    current && state["present"].toBool() && state["sameDeclaration"].toBool();
            }
            reports.append(QJsonObject{{"calls", receipt->calls},
                                       {"error", receipt->error},
                                       {"falseSuccess", receipt->falseSuccess},
                                       {"refusedWhileBusy", receipt->refusedWhileBusy},
                                       {"targets", receipt->atCompletion},
                                       {"wantedCount", int(receipt->targets.size())},
                                       {"stillCurrent", current}});
        }
        return {{"supported", true},
                {"reports", reports},
                {"retryIssued", retryIssued},
                {"partialTargets", partialTargets},
                {"added", added},
                {"admissionRefused", admissionRefused},
                {"reindexed", reindexed},
                {"reindexRefused", reindexRefused},
                {"transportOrder", transportOrder},
                {"distinctObjects", targets.size() < 2 || targets[0].object != targets[1].object},
                {"mutationEntered", mutationEntered},
                {"mutationAccepted", mutationAccepted},
                {"mutationRefused", mutationRefused},
                {"staleReports", staleReports},
                {"fitStartsMissing", fitStartsMissing},
                {"fitStartsAfterStop", fitStartsAfterStop},
                {"transportCalls", int(pending.size())},
                {"finalTargets", states(targets)},
                {"settled", std::none_of(pending.begin(), pending.end(),
                                         [](const auto& p) { return bool(p.done); })}};
    }
}
QJsonObject exactCollectionOwnership(const QString& source, const QStringList& spec) {
    QTemporaryDir temp;
    Session session(nullptr);
    need(session.openProject(QUrl::fromLocalFile(copy(source, temp.filePath("exact-owner")))),
         "The exact-target boundary starts from its independently saved powder project");
    settle(session);
    return exactCollectionOwner(session, session.project(), temp.path(), spec);
}
}  // namespace
