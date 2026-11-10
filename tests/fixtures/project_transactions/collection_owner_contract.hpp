// Inject only collection delivery; native admission, hydration and publication run.
namespace {
struct ExactCollectionTarget {
    std::shared_ptr<edi::BraggPdExperiment> object;
    QString label, entry, digest, text;
    QJsonArray rows;
};
template <class VM>
QJsonObject collectionOwner(Session& session, VM* model, const QString& root,
                            const QString& source, const QStringList& spec) {
    if constexpr (!requires(VM& value) {
                      value.fetchCollectionData(std::function<void(const QString&)>{});
                  }) {
        return {{"supported", false}};
    } else {
        need(spec.size() == 6,
             "A collection request declares producers, dependency join, outcome and retirement");
        const auto first = spec[1], second = spec[2], join = spec[3], outcome = spec[4],
                   retirement = spec[5];
        const QByteArray bytesX("17.5 4 .5\n18 9 1.25\n18.5 16 2.5\n");
        const QByteArray bytesY("17.5 25 .5\n18 36 1.25\n18.5 49 2.5\n");
        const QPointer<VM> owner(model);
        struct Pending {
            QString id;
            std::function<void(const QByteArray&, const QString&)> done;
        };
        std::vector<Pending> pending;
        std::vector<ExactCollectionTarget> authoredTargets;
        const auto witnessAlive = std::make_shared<std::atomic<bool>>(true);
        struct EndWitness {
            std::shared_ptr<std::atomic<bool>> alive;
            ~EndWitness() { *alive = false; }
        } endWitness{witnessAlive};
        const auto admit = [&](const QString& id, const QByteArray& bytes) {
            QString text;
            for (const auto& [name, body] : model->savedFiles())
                if (name.starts_with("experiments/") && name.ends_with(".edi")) {
                    text = QString::fromStdString(body);
                    break;
                }
            need(!text.isEmpty(), "The engine supplies only valid experiment setup syntax");
            const auto start = text.indexOf(
                QRegularExpression("(?m)^loop_[\\t ]*\\r?\\n[\\t ]*(?=_(?:data|refln)\\.)"));
            if (start >= 0) text.truncate(start);
            text.remove(QRegularExpression(
                "(?m)^_data_source\\.(?:path|collection_id|digest)[^\\n]*\\n?"));
            text.replace(QRegularExpression("(?m)^data_[^\\n]+"), "data_owned_" + id);
            const auto digest =
                QCryptographicHash::hash(bytes, QCryptographicHash::Sha256).toHex();
            text += "\n_data_source.collection_id 'owned-" + id + "'\n_data_source.digest '" +
                    digest + "'\n";
            const auto file = QDir(root).filePath("owned-" + id + ".edi");
            QFile native(file);
            need(native.open(QIODevice::WriteOnly),
                 "The pending experiment is an independently declared native input");
            native.write(text.toUtf8());
            native.close();
            const bool admitted = model->loadExperiments({QUrl::fromLocalFile(file)});
            settle(session);
            if (admitted) {
                const auto held =
                    model->project_->experiments[model->project_->experiments.size() - 1];
                const QJsonArray expected =
                    id == "X" ? QJsonArray{QJsonArray{17.5, 4, .5}, QJsonArray{18, 9, 1.25},
                                           QJsonArray{18.5, 16, 2.5}}
                              : QJsonArray{QJsonArray{17.5, 25, .5}, QJsonArray{18, 36, 1.25},
                                           QJsonArray{18.5, 49, 2.5}};
                authoredTargets.push_back(
                    {held, id, "owned-" + id, QString::fromLatin1(digest), text, expected});
                model->setCurrentExperimentIndex(model->project_->experiments.size() - 1);
            }
            return admitted;
        };
        need(admit("X", bytesX),
             "The actual initial importer admits its valid pending input before an operation "
             "begins");
        turn();
        pumpUntil([&] { return !model->property("saving").toBool(); },
                  "The initial admission finishes before a fetch operation begins");
        need(model->needsCollectionData(), "The first admitted dependency is genuinely pending");
        model->setCollectionFetcher([&, witnessAlive](const QString& id, auto done) {
            if (*witnessAlive) pending.push_back({id, std::move(done)});
        });
        struct Receipt {
            std::vector<ExactCollectionTarget> wanted;
            int calls = 0;
            bool successMissing = false, refusedWhileBusy = false;
            QString error;
        };
        std::vector<std::shared_ptr<Receipt>> receipts;
        bool retired = false, stopped = false, publicationEntered = false, aliveInside = false;
        int lateReports = 0, startsAfterStop = 0;
        bool retirementRefused = false, refusalVisible = false;
        QSignalSpy refusals(model, &VM::refused);
        QObject callbackContext;
        auto* fit = model->fit();
        QObject::connect(fit, &FitViewModel::runningChanged, &callbackContext, [&] {
            if (owner && fit->running()) {
                if (stopped) ++startsAfterStop;
                fit->cancel();  // No numerical result is claimed by this ownership witness.
            }
        });
        const auto ready = [&](const ExactCollectionTarget& target) {
            if (!owner || retired) return false;
            for (const auto& experiment : owner->project_->experiments)
                if (experiment.get() == target.object.get())
                    return QString::fromStdString(experiment->collection_id) == target.entry &&
                           QString::fromStdString(experiment->data_digest) == target.digest &&
                           independentRowsObserved(*experiment) == target.rows;
            return false;
        };
        const auto request = [&](const QString& kind) {
            if (kind == "download")
                model->downloadCollectionData();
            else if (kind == "fit")
                fit->start();
            else
                need(kind == "fetch", "The request uses an enumerated actual collection entry");
            auto receipt = std::make_shared<Receipt>();
            for (const auto& experiment : model->project_->experiments)
                if (!experiment->collection_id.empty() && !experiment->data &&
                    !experiment->reflections) {
                    const auto found = std::find_if(
                        authoredTargets.begin(), authoredTargets.end(), [&](const auto& target) {
                            return target.object.get() == experiment.get();
                        });
                    need(found != authoredTargets.end(),
                         "Every requested dependency retains its authored exact target");
                    receipt->wanted.push_back(*found);
                }
            receipts.push_back(receipt);
            const bool wasBusy = !pending.empty();
            const auto admitting = std::make_shared<bool>(true);
            model->fetchCollectionData(
                [&, receipt, wasBusy, admitting, witnessAlive](const QString& error) {
                    if (!*witnessAlive) return;
                    ++receipt->calls;
                    if (retired || !owner) {
                        ++lateReports;
                        return;
                    }
                    receipt->error = error;
                    receipt->refusedWhileBusy = !error.isEmpty() && wasBusy && *admitting;
                    if (error.isEmpty())
                        for (const auto& target : receipt->wanted)
                            if (!ready(target)) receipt->successMissing = true;
                });
            *admitting = false;
        };
        request(first);
        bool yAdmitted = false, xRemoved = false;
        if (join != "same") {
            if (join == "replace") {
                const auto index = model->currentExperimentIndex();
                model->removeExperiment(index);
                settle(session);
                xRemoved = true;
                for (const auto& member : model->project_->experiments)
                    if (member->collection_id == "owned-X") xRemoved = false;
            }
            yAdmitted = admit("Y", bytesY);
            if (join == "selected") model->setCurrentExperimentIndex(0);
        }
        request(second);
        const auto successor = QDir(root).filePath("successor");
        if (retirement.startsWith("replace")) copy(source, successor);
        Image successorBefore;
        if (QFileInfo(successor).isDir()) successorBefore = image(successor, true);
        const auto retire = [&] {
            if (publicationEntered) return;
            publicationEntered = true;
            std::cerr << "boundary-reached: actual collection publication; retire actual owner\n"
                      << std::flush;
            if (retirement.startsWith("close"))
                session.closeProject();
            else {
                const bool admitted = session.openProject(QUrl::fromLocalFile(successor));
                refusalVisible = !admitted;
            }
            retired = !owner || session.project() != owner;
            retirementRefused = !retired;
            refusalVisible = refusalVisible || !session.lastError().isEmpty() ||
                             !refusals.isEmpty() || (owner && !owner->lastError().isEmpty());
            aliveInside = !owner.isNull();
        };
        if (retirement.endsWith("pattern")) {
            for (auto* experiment : model->template findChildren<ExperimentViewModel*>())
                QObject::connect(experiment, &ExperimentViewModel::patternSourceChanged,
                                 &callbackContext, retire, Qt::DirectConnection);
        } else if (retirement.endsWith("missing"))
            QObject::connect(model, &VM::missingDataFileChanged, &callbackContext, retire,
                             Qt::DirectConnection);
        else if (retirement.endsWith("error")) {
            if (first == "fit")
                QObject::connect(fit, &FitViewModel::refused, &callbackContext, retire,
                                 Qt::DirectConnection);
            else
                QObject::connect(model, &VM::lastErrorChanged, &callbackContext, retire,
                                 Qt::DirectConnection);
        }
        if (retirement == "stop") {
            stopped = true;
            fit->cancel();
        }
        std::size_t completed = 0;
        for (; completed < pending.size() && completed < 64; ++completed) {
            const auto id = pending[completed].id;
            auto done = std::move(pending[completed].done);
            if (!done) continue;
            const bool fail = outcome == "failure" || (outcome == "partial" && id == "owned-Y");
            done(fail              ? QByteArray()
                 : id == "owned-X" ? bytesX
                                   : bytesY,
                 fail ? "Independent transport refusal for " + id : QString());
            turn();
        }
        QJsonArray reports;
        for (const auto& receipt : receipts) {
            QJsonArray wanted;
            for (const auto& target : receipt->wanted) wanted.append(target.label);
            reports.append(QJsonObject{{"calls", receipt->calls},
                                       {"successMissing", receipt->successMissing},
                                       {"refusedWhileBusy", receipt->refusedWhileBusy},
                                       {"error", receipt->error},
                                       {"wanted", wanted}});
        }
        QJsonArray data;
        if (owner && !retired) {
            for (const auto& target : authoredTargets)
                for (const auto& experiment : owner->project_->experiments)
                    if (experiment.get() == target.object.get())
                        data.append(QJsonObject{{"label", target.label},
                                                {"entry", target.entry},
                                                {"rows", independentRowsObserved(*experiment)}});
        }
        return {{"supported", true},
                {"yAdmitted", yAdmitted},
                {"xRemoved", xRemoved},
                {"retirementRefused", retirementRefused},
                {"refusalVisible", refusalVisible},
                {"reports", reports},
                {"data", data},
                {"transportCalls", int(pending.size())},
                {"settled", completed == pending.size()},
                {"publicationEntered", publicationEntered},
                {"aliveInside", aliveInside},
                {"lateReports", lateReports},
                {"startsAfterStop", startsAfterStop},
                {"successorIntact",
                 successorBefore.isEmpty() || image(successor, true) == successorBefore}};
    }
}
QJsonObject collectionOwnership(const QString& source, const QStringList& spec) {
    QTemporaryDir temp;
    Session session(nullptr);
    need(session.openProject(QUrl::fromLocalFile(copy(source, temp.filePath("original")))),
         "The collection boundary opens its independently saved scientific input");
    settle(session);
    return collectionOwner(session, session.project(), temp.path(), source, spec);
}
}  // namespace
