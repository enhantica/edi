// Exercise every user-file fetch producer before its physical file/report frontier.
#include "online_search.hpp"
namespace {
QString completeOwnerCollection(const QString& folder) {
    operationCollection(folder, "owned network source");
    QFile index(folder + "/index.json");
    need(index.open(QIODevice::ReadOnly),
         "The request fixture reads its committed collection schema");
    auto document = QJsonDocument::fromJson(index.readAll()).object();
    index.close();
    auto entries = document["entries"].toArray();
    for (const auto& entry : entries)
        if (entry.toObject()["kind"] == "data") {
            auto added = entry.toObject();
            added["id"] = "owned-second-data";
            added["name"] = "Independent second measured input";
            QFile data(folder + "/owned-second.dat");
            need(data.open(QIODevice::WriteOnly),
                 "The batch request has a distinct authored second input");
            data.write("17.5 25 .5\n18 36 1.25\n18.5 49 2.5\n");
            data.close();
            auto files = added["files"].toArray();
            auto file = files[0].toObject();
            file["path"] = "owned-second.dat";
            files[0] = file;
            added["files"] = files;
            entries.append(added);
            break;
        }
    // The tutorial fixture distinguishes files by a valid comment. Refresh all
    // aliases of those same authored files, not only the tutorial alias.
    for (int at = 0; at < entries.size(); ++at) {
        auto entry = entries[at].toObject();
        auto files = entry["files"].toArray();
        for (int item = 0; item < files.size(); ++item) {
            auto fields = files[item].toObject();
            QFile file(folder + "/" + fields["path"].toString());
            need(file.open(QIODevice::ReadOnly),
                 "Every independent collection declaration names real bytes");
            const auto bytes = file.readAll();
            fields["bytes"] = bytes.size();
            fields["sha256"] = QString::fromLatin1(
                QCryptographicHash::hash(bytes, QCryptographicHash::Sha256).toHex());
            files[item] = fields;
        }
        entry["files"] = files;
        entries[at] = entry;
    }
    document["entries"] = entries;
    need(index.open(QIODevice::WriteOnly | QIODevice::Truncate),
         "The local collection stores its independently checked index");
    index.write(QJsonDocument(document).toJson());
    return folder;
}
QString configureOwnerCollection(Session& session, const QString& folder) {
    useOperationCollection(session, folder);
    auto* sources = session.onlineSources();
    QString id;
    for (const auto& source : sources->sources())
        if (!source.builtin) id = source.id;
    need(!id.isEmpty(), "The request uses an actual editable source identity");
    sources->setKinds(id, {"structure", "experiment", "data", "project"});
    pumpUntil([&] { return !session.collection_examples_->loading(); },
              "The ordinary source index completes before any payload is held");
    return id;
}
template <class Search>
bool cancelOwnedLoads(Search* search) {
    if constexpr (requires { search->cancelLoads(); }) {
        search->cancelLoads();
        return true;
    }
    return false;
}
QJsonObject networkOwner(const QString& source, const QStringList& spec) {
    need(spec.size() == 4,
         "A file request declares producer, retirement and terminal transport outcome");
    const auto kind = spec[1], retirement = spec[2];
    const bool success = spec[3] == "success", example = kind.startsWith("example");
    QTemporaryDir temp;
    Session session(nullptr);
    const auto input = copy(source, temp.filePath("original"));
    const auto successor = copy(source, temp.filePath("successor"));
    need(session.openProject(QUrl::fromLocalFile(input)),
         "The file request has an actual current project owner");
    settle(session);
    QPointer<ProjectViewModel> original = session.project();
    const auto collection = completeOwnerCollection(temp.filePath("source"));
    const auto id = configureOwnerCollection(session, collection);
    auto* search = session.onlineSearch();
    if (!example) {
        search->setKind(kind == "batch-data" || kind == "new-data" ? "data" : kind);
        search->setSourceId(id);
        search->search();
        pumpUntil([&] { return !search->busy(); },
                  "The real indexed search finishes before payload delivery is held");
        need(search->results()->rowCount() > 0, "The selected kind has a real indexed result");
    }
    QSignalSpy single(search, &OnlineSearch::fileReady), many(search, &OnlineSearch::filesReady);
    QSignalSpy messages(search, &OnlineSearch::messageChanged),
        details(search, &OnlineSearch::detailChanged);
    QSignalSpy finished(&session, &Session::exampleOpenFinished),
        failed(&session, &Session::loadFailed);
    operationFetches.clear();
    holdOperationFetch = true;
    struct StopNetworkObserver {
        ~StopNetworkObserver() {
            holdOperationFetch = false;
            holdOperationIndex = false;
            observingCanceledWrite = false;
            ownerBoundary = nullptr;
        }
    } stop;
    if (example) {
        QFile index(collection + "/index.json");
        need(index.open(QIODevice::ReadOnly),
             "The example request uses its declared local project id");
        QString projectId;
        for (const auto& entry :
             QJsonDocument::fromJson(index.readAll()).object()["entries"].toArray())
            if (entry.toObject()["kind"] == "project") {
                projectId = entry.toObject()["id"].toString();
                break;
            }
        need(!projectId.isEmpty(), "The independent collection actually contains a project");
        need(kind == "example-aside" ? session.openExampleAside(projectId)
                                     : session.openExample(projectId),
             "The actual Example or tutorial-aside producer admits its project request");
    } else if (kind == "batch-data") {
        need(search->results()->rowCount() > 1,
             "The batch request admits multiple distinct entries");
        search->loadMany({0, search->results()->rowCount() - 1}, original,
                         original->currentExperiment());
    } else
        search->load(0, original, kind == "data" ? original->currentExperiment() : nullptr);
    need(!operationFetches.empty(),
         "The requested public producer actually reaches a held file transport");
    OwnerBoundary stale;
    bool inside = false, alive = true, retired = false, refusalVisible = false,
         entryFenced = false;
    bool ownerPreservedAtRefusal = false;
    QSignalSpy operationRefusals(original, &ProjectViewModel::refused);
    int reports = 0, writes = 0;
    QStringList paths;
    const auto diskBefore = image(input, true), successorBefore = image(successor, true);
    QObject callbackContext;
    const auto complete = [&] {
        if (inside) return;
        inside = true;
        if (retirement == "cancel")
            need(cancelOwnedLoads(search),
                 "The actual checked-file producer exposes its cancel entry");
        else if (retirement == "close")
            session.closeProject();
        else if (retirement == "replace") {
            const bool admitted = session.openProject(QUrl::fromLocalFile(successor));
            refusalVisible = !admitted;
        } else if (retirement == "target-removed") {
            const auto count = original->project_->experiments.size();
            original->removeExperiment(original->currentExperimentIndex());
            retired = original->project_->experiments.size() < count;
        } else
            need(retirement == "none", "The owner retirement is an enumerated actual operation");
        if (retirement == "cancel")
            retired = true;
        else if (retirement == "close" || retirement == "replace")
            retired = !original || session.project() != original;
        ownerPreservedAtRefusal = original && session.project() == original;
        refusalVisible = refusalVisible || !session.lastError().isEmpty() ||
                         !operationRefusals.isEmpty() ||
                         (original && !original->lastError().isEmpty());
        alive = !original.isNull();
        const int before = single.size() + many.size() + messages.size() + details.size() +
                           finished.size() + failed.size();
        stale.entered = retired;
        ownerBoundary = &stale;
        operationWriteCalls = 0;
        {
            std::lock_guard lock(operationWriteMutex);
            operationWritePaths.clear();
        }
        observingCanceledWrite = true;
        for (std::size_t at = 0; at < operationFetches.size() && at < 64; ++at)
            if (operationFetches[at].done) finishOperationFetch(at, success);
        observingCanceledWrite = false;
        writes = operationWriteCalls + stale.writes;
        {
            std::lock_guard lock(operationWriteMutex);
            paths = operationWritePaths;
        }
        reports = single.size() + many.size() + messages.size() + details.size() +
                  finished.size() + failed.size() - before;
        ownerBoundary = nullptr;
    };
    if (retirement == "close" || retirement == "replace") {
        // A real metadata publication keeps the old QObject on its active
        // stack, so a pointer-only callback guard cannot pass by deletion alone.
        QObject::connect(original, &ProjectViewModel::projectEdited, &callbackContext, complete,
                         Qt::DirectConnection);
        original->setDescription("Independent active owner publication");
        turn();
        if (!inside && (!operationRefusals.isEmpty() || !original->lastError().isEmpty())) {
            entryFenced = true;
            complete();
        }
    } else
        complete();
    bool settled = true;
    for (const auto& request : operationFetches)
        if (request.done) settled = false;
    return {{"entered", inside},
            {"retired", retired},
            {"refusalVisible", refusalVisible},
            {"entryFenced", entryFenced},
            {"ownerPreservedAtRefusal", ownerPreservedAtRefusal},
            {"aliveInside", alive},
            {"writes", writes},
            {"reports", reports},
            {"paths", QJsonArray::fromStringList(paths)},
            {"settled", settled},
            {"delivered", single.size() + many.size() + finished.size()},
            {"userFilesIntact",
             image(input, true) == diskBefore && image(successor, true) == successorBefore}};
}
}  // namespace
