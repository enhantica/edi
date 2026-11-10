// Observe operation-owned writes and decisions through the actual Session.
#include <QSignalMapper>
#include <QStandardPaths>
#include <atomic>

#include "collection_examples.hpp"
#include "online_fetch.hpp"
#include "online_sources.hpp"
namespace {
bool holdOperationFetch = false, holdOperationIndex = false;
std::mutex operationWriteMutex;
QStringList operationWritePaths;

std::atomic<bool> observingCanceledWrite = false;
std::atomic<int> operationWriteCalls = 0;
void recordOperationWrite(QIODevice* device) {
    const auto* file = qobject_cast<QFileDevice*>(device);
    if (!file) return;  // Pure in-memory preparation is not a filesystem write.
    ownerCoreAttempt();
    if (!observingCanceledWrite) return;
    ++operationWriteCalls;
    if (file) {
        std::lock_guard lock(operationWriteMutex);
        operationWritePaths.append(file->fileName());
    }
}
struct OperationFetch {
    QUrl url;
    edi_app::FetchDone done;
};
std::vector<OperationFetch> operationFetches;
}  // namespace
// Only references from copied app objects are redirected; these delegate to real Qt.
extern "C" bool operation_file_open(QFile* file, QIODeviceBase::OpenMode mode) {
    if (observingCanceledWrite && mode.testFlag(QIODeviceBase::WriteOnly))
        recordOperationWrite(file);
    return file->QFile::open(mode);
}
extern "C" bool operation_file_open_fd(QFile* file, int fd, QIODeviceBase::OpenMode mode,
                                       QFileDevice::FileHandleFlags flags) {
    if (observingCanceledWrite && mode.testFlag(QIODeviceBase::WriteOnly))
        recordOperationWrite(file);
    return file->QFile::open(fd, mode, flags);
}
extern "C" bool operation_file_open_stream(QFile* file, FILE* stream, QIODeviceBase::OpenMode mode,
                                           QFileDevice::FileHandleFlags flags) {
    if (observingCanceledWrite && mode.testFlag(QIODeviceBase::WriteOnly))
        recordOperationWrite(file);
    return file->QFile::open(stream, mode, flags);
}
extern "C" bool operation_file_open_permissions(QFile* file, QIODeviceBase::OpenMode mode,
                                                QFileDevice::Permissions permissions) {
    if (observingCanceledWrite && mode.testFlag(QIODeviceBase::WriteOnly))
        recordOperationWrite(file);
    return file->QFile::open(mode, permissions);
}
extern "C" qint64 operation_file_write_span(QIODevice* file, const char* bytes, qint64 size) {
    if (observingCanceledWrite) recordOperationWrite(file);
    return file->write(bytes, size);
}
extern "C" qint64 operation_file_write_array(QIODevice* file, const QByteArray& bytes) {
    if (observingCanceledWrite) recordOperationWrite(file);
    return file->write(bytes);
}
extern "C" qint64 operation_file_write_cstring(QIODevice* file, const char* bytes) {
    if (observingCanceledWrite) recordOperationWrite(file);
    return file->write(bytes);
}
extern "C" void transaction_real_fetch_from(QObject*, QNetworkAccessManager*&, const QStringList&,
                                            const QString&, edi_app::FetchDone, edi_app::FetchProgress);
extern "C" void transaction_real_fetch_url(QObject*, QNetworkAccessManager*&, const QUrl&,
                                           edi_app::FetchDone, edi_app::FetchProgress);
namespace edi_app {
void fetch_url(QObject* owner, QNetworkAccessManager*& manager, const QUrl& url, FetchDone done,
               FetchProgress progress) {
    if (holdOperationFetch) {
        operationFetches.push_back({url, std::move(done)});
        return;
    }
    if (url.scheme() == "http" || url.scheme() == "https") {
        done({}, "Offline observer refuses an uninjected HTTP request", false);
        return;
    }
    transaction_real_fetch_url(owner, manager, url, std::move(done), std::move(progress));
}
void fetch_from(QObject* owner, QNetworkAccessManager*& manager, const QStringList& bases,
                const QString& path, FetchDone done, FetchProgress progress) {
    const bool remote = std::any_of(bases.begin(), bases.end(), [](const auto& base) {
        return base.startsWith("http:") || base.startsWith("https:");
    });
    if (holdOperationFetch && (path != "index.json" || holdOperationIndex || remote)) {
        need(!bases.isEmpty(), "A held file belongs to an actually indexed collection source");
        operationFetches.push_back({joined_url(bases.front(), path), std::move(done)});
        return;
    }
    if (remote) {
        done({}, "Offline observer refuses an uninjected HTTP collection", false);
        return;
    }
    transaction_real_fetch_from(owner, manager, bases, path, std::move(done), std::move(progress));
}
}  // namespace edi_app
namespace {
void finishOperationFetch(std::size_t index, bool success) {
    need(index < operationFetches.size() && bool(operationFetches[index].done),
         "Each injected file completion belongs to one actual fetch");
    auto done = std::move(operationFetches[index].done);
    if (!success) {
        done({}, "Independent earlier file refusal", false);
        turn();
        return;
    }
    QFile file(operationFetches[index].url.toLocalFile());
    need(file.open(QIODevice::ReadOnly),
         "The held response reads independent local collection bytes");
    done(file.readAll(), {}, false);
    turn();
}
QString operationCollection(const QString& root, const QString& suffix) {
    const QDir fixture(QFileInfo(QString::fromUtf8(__FILE__)).absolutePath() +
                       "/../online_sources/easydiffraction");
    copy(fixture.path(), root);
    QFile index(root + "/index.json");
    need(index.open(QIODevice::ReadOnly),
         "The operation fixture retains the independent collection index");
    auto document = QJsonDocument::fromJson(index.readAll()).object();
    index.close();
    auto entries = document["entries"].toArray();
    for (const auto& kind : {QString("structure"), QString("data")}) {
        QJsonObject entry;
        for (const auto& value : entries)
            if (value.toObject()["kind"].toString() == kind) {
                entry = value.toObject();
                break;
            }
        need(!entry.isEmpty(), "The independent collection supplies both tutorial inputs");
        entry["id"] = kind == "structure" ? "tutorial-lbco" : "tutorial-hrpt";
        auto files = entry["files"].toArray();
        auto item = files[0].toObject();
        QFile payload(root + "/" + item["path"].toString());
        need(payload.open(QIODevice::ReadWrite | QIODevice::Append),
             "Each local collection owns distinguishable valid file bytes");
        payload.write("\n# independent operation " + suffix.toUtf8() + "\n");
        payload.close();
        need(payload.open(QIODevice::ReadOnly),
             "The declared payload can be independently hashed");
        const auto bytes = payload.readAll();
        item["bytes"] = bytes.size();
        item["sha256"] = QString::fromLatin1(
            QCryptographicHash::hash(bytes, QCryptographicHash::Sha256).toHex());
        files[0] = item;
        entry["files"] = files;
        entries.append(entry);
    }
    document["entries"] = entries;
    need(index.open(QIODevice::WriteOnly | QIODevice::Truncate),
         "The collection writes its independently computed declarations");
    index.write(QJsonDocument(document).toJson());
    return root;
}
void useOperationCollection(Session& session, const QString& folder) {
    auto* sources = session.onlineSources();
    QString id;
    for (const auto& source : sources->sources())
        if (!source.builtin) id = source.id;
    if (id.isEmpty()) {
        sources->add();
        id = sources->sources().last().id;
    }
    sources->setKinds(id, {"structure", "data"});
    const auto url = QUrl::fromLocalFile(folder).toString();
    sources->setUrl(id, url);
    need(sources->urlOf(id) == url,
         "The ordinary editable source selects the actual local collection");
    pumpUntil([&] { return !session.collection_examples_->loading(); },
              "The real collection finishes indexing the selected local source");
    need(session.collection_examples_->knows("tutorial-lbco") &&
             session.collection_examples_->knows("tutorial-hrpt"),
         "Both tutorial inputs come through the actual checked index");
}
QJsonObject operationFiles(const QString& source, const QStringList& spec) {
    need(spec.size() == 4,
         "A file operation declares its kind, completion order and terminal outcome");
    const QString kind = spec[1], order = spec[2];
    const bool oldSuccess = spec[3] == "success", canceledAlone = order == "without-successor";
    QTemporaryDir temp;
    Session session(nullptr);
    need(session.openProject(QUrl::fromLocalFile(copy(source, temp.filePath("project")))),
         "The operation owner opens its independent project");
    settle(session);
    const auto first = operationCollection(temp.filePath("first-source"), "A");
    const auto second = operationCollection(temp.filePath("second-source"), "B");
    useOperationCollection(session, first);
    struct Reply {
        int id;
        QUrl folder;
    };
    const auto destination = QUrl::fromLocalFile(temp.filePath("requested-files"));
    const auto requestFiles = [&] {
        return kind == "save" ? session.saveTutorialFiles(destination)
                              : session.stageTutorialFiles();
    };
    std::vector<Reply> successes;
    QList<int> failures;
    QObject::connect(&session, &Session::tutorialFilesStaged, &session,
                     [&](int id, const QUrl& folder) { successes.push_back({id, folder}); });
    QObject::connect(&session, &Session::tutorialFilesSaved, &session,
                     [&](int id) { successes.push_back({id, destination}); });
    QObject::connect(&session, &Session::tutorialFilesFailed, &session,
                     [&](int id, const QString&) { failures.append(id); });
    operationFetches.clear();
    holdOperationFetch = true;
    const int oldRequest = requestFiles();
    need(operationFetches.size() == 1,
         "The original operation reaches its first actual file boundary");
    useOperationCollection(session, second);
    const int currentRequest = canceledAlone ? 0 : requestFiles();
    need(operationFetches.size() == (canceledAlone ? 1U : 2U),
         "Only admitted operations own an actual held response");
    auto deliverChain = [&](std::size_t index, bool success) {
        auto size = operationFetches.size();
        finishOperationFetch(index, success);
        while (operationFetches.size() > size) {
            const auto next = size++;
            finishOperationFetch(next, success);
        }
    };
    bool oldFilesUnchanged = false;
    int oldWriteCalls = 0;
    auto deliverOld = [&] {
        const auto root = QStandardPaths::writableLocation(QStandardPaths::TempLocation);
        const auto before = image(root, true);
        const int beforeWrites = operationWriteCalls.load();
        observingCanceledWrite = true;
        const auto stopObserving = qScopeGuard([] { observingCanceledWrite = false; });
        deliverChain(0, oldSuccess);
        oldWriteCalls = operationWriteCalls.load() - beforeWrites;
        oldFilesUnchanged = image(root, true) == before;
    };
    auto deliverCurrent = [&] { deliverChain(1, true); };
    if (canceledAlone) {
        deliverOld();
    } else if (order == "old-first") {
        deliverOld();
        deliverCurrent();
    } else {
        deliverCurrent();
        deliverOld();
    }
    turn();
    holdOperationFetch = false;
    int oldReports = failures.count(oldRequest), currentReports = failures.count(currentRequest);
    QUrl folder;
    for (const auto& reply : successes) {
        oldReports += reply.id == oldRequest;
        if (reply.id == currentRequest) {
            ++currentReports;
            folder = reply.folder;
        }
    }
    if (canceledAlone)
        return {{"oldReports", oldReports},
                {"oldWriteCalls", oldWriteCalls},
                {"oldFilesUnchanged", oldFilesUnchanged}};
    need(folder.isLocalFile(),
         "The current successful operation publishes its actual staging folder");
    const auto files = image(folder.toLocalFile());
    QFile index(second + "/index.json");
    need(index.open(QIODevice::ReadOnly),
         "The current byte oracle reads its independent local index");
    const auto entries = QJsonDocument::fromJson(index.readAll()).object()["entries"].toArray();
    bool currentBytes = true;
    for (const auto& pair : {qMakePair(QString("tutorial-lbco"), QString("lbco.cif")),
                             qMakePair(QString("tutorial-hrpt"), QString("hrpt.xye"))}) {
        QByteArray expected;
        for (const auto& entry : entries) {
            const auto row = entry.toObject();
            if (row["id"].toString() != pair.first) continue;
            QFile payload(second + "/" + row["files"].toArray()[0].toObject()["path"].toString());
            need(payload.open(QIODevice::ReadOnly),
                 "The current byte oracle reads its independently declared input");
            expected = payload.readAll();
        }
        need(!expected.isEmpty() && files.contains(pair.second),
             "Both independent current inputs reach staging");
        currentBytes = currentBytes && files[pair.second] == expected;
    }
    const bool loaded =
        session.project()->loadStructure(QUrl::fromLocalFile(folder.toLocalFile() + "/lbco.cif"));
    settle(session);
    return {{"oldWriteCalls", oldWriteCalls},
            {"oldFilesUnchanged", oldFilesUnchanged},
            {"oldReports", oldReports},
            {"currentReports", currentReports},
            {"currentBytes", currentBytes},
            {"laterLoad", loaded},
            {"distinctRequests", oldRequest != currentRequest}};
}
QJsonObject nestedOperationSave(const QString& source, const QStringList& spec) {
    need(spec.size() == 3, "Nested save declares an entry route and owner transition");
    const QString route = spec[1], transition = spec[2];
    SavePolicyInput input(source, "linked");
    Session& session = input.session;
    if (route.startsWith("web-")) openBrowserInput(session, input.input, "folder");
    auto* original = session.project();
    original->setIncludeDataOnSave("ask");
    PolicyQuestions questions(session);
    const QString outer = input.temp.filePath("outer"),
                  inner = input.temp.filePath(route.contains("zip") ? "inner.zip" : "inner");
    if (route.startsWith("existing-")) {
        if (route.contains("zip"))
            edi::write_project_archive(input.input.toStdString(), inner.toStdString());
        else
            need(QDir().mkpath(inner),
                 "The nested existing-place request owns an actual destination");
    }
    const auto innerBefore = image(inner, true);
    bool armed = false, entered = false, replacementAdmitted = true;
    bool prepared = false, innerRefused = false;
    QSignalSpy webReplies(&session, &Session::webSaveFinished);
    // Listen at every public model notification, independent of which save site emits it.
    QSignalMapper mapper;
    const auto slot = mapper.metaObject()->method(mapper.metaObject()->indexOfSlot("map()"));
    QList<QObject*> senders{&session, original};
    senders.append(original->findChildren<QObject*>());
    for (auto* sender : senders) {
        mapper.setMapping(sender, 0);
        const auto* meta = sender->metaObject();
        for (int index = 0; index < meta->methodCount(); ++index) {
            const auto method = meta->method(index);
            if (method.methodType() == QMetaMethod::Signal)
                need(bool(QObject::connect(sender, method, &mapper, slot, Qt::AutoConnection)),
                     "Every actual model signal reaches the shared reentry boundary");
        }
    }
    QObject::connect(
        &mapper, &QSignalMapper::mappedInt, &session,
        [&](int) {
            if (!armed || entered) return;
            entered = true;
            if (transition == "replacement") {
                const auto next = copy(input.input, input.temp.filePath("successor"));
                replacementAdmitted = session.openProject(QUrl::fromLocalFile(next));
                if (!replacementAdmitted) return;
                settle(session);
            }
            session.project()->setIncludeDataOnSave("ask");
            if (route == "unsaved-folder") session.project()->project_->path.clear();
            const auto attempts = nativeSaveAttempts.load();
            const auto livePath = session.project()->path();
            const auto liveBefore = livePath.isEmpty() ? Image{} : image(livePath, true);
            const auto destinationBefore = image(inner, true);
            const auto writesBefore = std::count_if(jobs.begin(), jobs.end(), [](const Job& job) {
                return job.action == "write" && !job.recovery;
            });
            const auto filesBefore =
                image(QStandardPaths::writableLocation(QStandardPaths::TempLocation), true);
            const auto repliesBefore = webReplies.size();
            const bool accepted = requestPolicySave(session, route, inner);
            innerRefused = !accepted && !session.lastError().isEmpty();
            for (auto index = repliesBefore; index < webReplies.size(); ++index)
                innerRefused = innerRefused || !webReplies[index][0].toBool();
            for (std::size_t index = 0; questions.count() == 1 && index < jobs.size(); ++index)
                if (jobs[index].answer && jobs[index].action == "pickSave") finish(index, true);
            const bool inputChanged = !livePath.isEmpty() && image(livePath, true) != liveBefore;
            const auto writesAfter = std::count_if(jobs.begin(), jobs.end(), [](const Job& job) {
                return job.action == "write" && !job.recovery;
            });
            prepared = inputChanged || image(inner, true) != destinationBefore ||
                       writesAfter > writesBefore;
            if (questions.count() == 1)
                prepared = prepared || nativeSaveAttempts.load() != attempts ||
                           image(QStandardPaths::writableLocation(QStandardPaths::TempLocation),
                                 true) != filesBefore;
            if (questions.count() > 1) questions.answer(questions.request(), "cancel");
        },
        Qt::DirectConnection);
    jobs.clear();
    session.saveProjectAs(QUrl::fromLocalFile(outer), false, false);
    pumpUntil([&] { return questions.count() == 1; },
              "The outer Ask owns its actual independent decision");
    armed = true;
    questions.answer(questions.request(), "linked");
    pumpUntil([&] { return entered; },
              "The accepted outer save reaches an actual observable model boundary");
    armed = false;
    turn();
    const bool published = QFileInfo::exists(outer + "/project.edi");
    bool linked = false;
    if (published) {
        const auto saved = edi::load_project(outer.toStdString());
        const auto declared = QString::fromStdString(saved.sequential_fit.data_dir);
        const auto resolved =
            QFileInfo(QFileInfo(declared).isAbsolute() ? declared : QDir(outer).filePath(declared))
                .canonicalFilePath();
        linked = resolved == QFileInfo(input.data).canonicalFilePath() &&
                 dataHashes(resolved) == input.hashes;
    }
    return {{"entered", entered},
            {"replacementAdmitted", replacementAdmitted},
            {"questions", questions.count() - 1},
            {"innerPrepared", prepared},
            {"innerRefused", innerRefused},
            {"innerUnchanged", image(inner, true) == innerBefore},
            {"sourceBytesUnchanged", dataHashes(input.data) == input.hashes},
            {"outerPublished", published},
            {"outerLinked", linked}};
}

}  // namespace
