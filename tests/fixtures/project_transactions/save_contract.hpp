// Save policy and request ownership through the real Session, with only I/O held.
#include <QCryptographicHash>
#include <QtTest/QSignalSpy>
namespace {
struct PolicyQuestions {
    Session& session;
    QMetaMethod signal;
    std::unique_ptr<QSignalSpy> events;
    explicit PolicyQuestions(Session& owner) : session(owner) {
        const auto* meta = owner.metaObject();
        for (int index = 0; index < meta->methodCount(); ++index)
            if (meta->method(index).name() == "saveDataChoiceNeeded") signal = meta->method(index);
        need(signal.isValid(), "The real save policy exposes its actual deferred question");
        events = std::make_unique<QSignalSpy>(&owner, signal);
        need(events->isValid(), "The fixture observes the real question without replacing it");
    }
    int count() const { return static_cast<int>(events->size()); }
    bool tagged() const { return signal.parameterNames().contains("request"); }
    QVariant request() const {
        return tagged() && !events->isEmpty() ? events->last()[0] : QVariant();
    }
    qint64 bytes() const {
        return events->isEmpty() ? 0 : events->last()[tagged() ? 1 : 0].toLongLong();
    }
    bool large() const { return !events->isEmpty() && events->last()[tagged() ? 3 : 2].toBool(); }
    void answer(const QVariant& request, const QString& choice) {
        const auto* meta = session.metaObject();
        for (int index = 0; index < meta->methodCount(); ++index) {
            const auto method = meta->method(index);
            if (method.name() != "answerSaveData") continue;
            bool invoked = false;
            if (method.parameterCount() == 2) {
                QVariant token = request;
                const QByteArray type = method.parameterTypes().front();
                need(token.convert(QMetaType::fromName(type)),
                     "The question identity fits its actual answer receiver");
                invoked = method.invoke(&session, Qt::DirectConnection,
                                        QGenericArgument(type.constData(), token.constData()),
                                        QGenericArgument("QString", &choice));
            } else
                invoked = method.invoke(&session, Qt::DirectConnection,
                                        QGenericArgument("QString", &choice));
            need(invoked, "The injected reply reaches the real current or legacy answer receiver");
            return;
        }
        need(false, "A save question has its actual answer receiver");
    }
};
bool observeSavePolicy = false;
QJsonArray savePolicySnapshots;
QJsonObject dataHashes(const QString& folder) {
    QJsonObject hashes;
    for (const QString& name : QDir(folder).entryList({"*.dat"}, QDir::Files, QDir::Name)) {
        QFile file(QDir(folder).filePath(name));
        need(file.open(QIODevice::ReadOnly), "Independent scan input bytes remain readable");
        QCryptographicHash digest(QCryptographicHash::Sha256);
        need(digest.addData(&file), "Every saved scan file is hashed from its actual bytes");
        hashes.insert(name, QString::fromLatin1(digest.result().toHex()));
    }
    return hashes;
}
void captureSavePolicy(const QString& folder) {
    if (!observeSavePolicy) return;
    const auto saved = edi::load_project(folder.toStdString());
    const QString declared = QString::fromStdString(saved.sequential_fit.data_dir);
    const QString source =
        QFileInfo(QFileInfo(declared).isAbsolute() ? declared : QDir(folder).filePath(declared))
            .canonicalFilePath();
    need(!source.isEmpty(),
         "The saved declaration resolves to its existing measured input source");
    const QString root = QFileInfo(folder).canonicalFilePath();
    const QString relative = QDir(root).relativeFilePath(source);
    savePolicySnapshots.append(QJsonObject{
        {"description", QString::fromStdString(saved.metadata.description)},
        {"lengthA",
         saved.structures.empty() ? 0.0 : saved.structures.front()->cell.length_a.value.get()},
        {"source", source},
        {"external",
         relative == ".." || relative.startsWith("../") || QFileInfo(relative).isAbsolute()},
        {"hashes", dataHashes(source)}});
}
struct SavePolicyInput {
    QTemporaryDir temp;
    Session session;
    QString input, external, data;
    qint64 bytes = 0;
    QJsonObject hashes;
    SavePolicyInput(const QString& source, const QString& storage) : session(nullptr) {
        browser = false;
        input = copy(source, temp.filePath("input"));
        data = input + "/experiments/d20_scan";
        if (storage.endsWith("large")) {
            const auto names = QDir(data).entryList({"*.dat"}, QDir::Files, QDir::Name);
            need(!names.isEmpty(), "The large-save witness retains independent scan files");
            QFile padded(QDir(data).filePath(names.back()));
            need(padded.open(QIODevice::Append), "A measured input accepts valid comment padding");
            padded.write("\n#");
            const QByteArray comment(1024 * 1024, ' ');
            for (int block = 0; block < 101; ++block) padded.write(comment);
            padded.write("\n");
        }
        if (storage.startsWith("linked")) {
            external = temp.filePath("external");
            need(QDir().rename(data, external),
                 "The scan source is deliberately outside the project");
            data = external;
            QFile analysis(input + "/analysis/analysis.edi");
            need(analysis.open(QIODevice::ReadOnly),
                 "The saved analysis declares its scan source");
            auto text = analysis.readAll();
            analysis.close();
            need(text.contains("experiments/d20_scan"),
                 "The reference project has its declared scan folder");
            text.replace("experiments/d20_scan", external.toUtf8());
            need(analysis.open(QIODevice::WriteOnly | QIODevice::Truncate),
                 "The linked input declaration is writable");
            analysis.write(text);
        }
        for (const QString& name : QDir(data).entryList({"*.dat"}, QDir::Files))
            bytes += QFileInfo(QDir(data).filePath(name)).size();
        if (storage.endsWith("large"))
            need(bytes > 100LL * 1024 * 1024,
                 "The independent large input exceeds the owner warning threshold");
        hashes = dataHashes(data);
        need(!hashes.isEmpty(), "The save-policy oracle inventories independent measured files");
        need(session.openProject(QUrl::fromLocalFile(input)),
             "The real Session opens the linked or copied scan input");
        settle(session);
    }
};
bool requestPolicySave(Session& session, const QString& route, const QString& destination) {
    if (route == "save" || route == "web-save")
        return session.save();
    else if (route == "save-as")
        return session.saveAs(QUrl::fromLocalFile(destination));
    else if (route == "web-folder") {
        session.saveWebProjectAs("folder", false);
        return true;  // This public browser entry reports refusal asynchronously.
    } else if (route == "web-zip") {
        session.saveWebProjectAs("zip", false);
        return true;  // This public browser entry reports refusal asynchronously.
    } else if (route == "web-copy") {
        session.saveWebProjectAs("folder", true);
        return true;  // This public browser entry reports refusal asynchronously.
    } else if (route == "web-download") {
        session.downloadWebProject();
        return true;  // This public browser entry reports refusal asynchronously.
    } else
        return session.saveProjectAs(QUrl::fromLocalFile(destination), route.contains("zip"),
                                     route.contains("copy"));
}
void finishPolicyIo() {
    // Deliver actual picker/write callbacks, never reimplement the save decision.
    for (int pass = 0; pass < 8; ++pass) {
        bool delivered = false;
        for (std::size_t index = 0; index < jobs.size(); ++index) {
            if (!jobs[index].answer || jobs[index].recovery) continue;
            need(jobs[index].action == "pickSave" || jobs[index].action == "write",
                 "Only save-request I/O is completed by this fixture");
            finish(index, true);
            delivered = true;
            break;
        }
        if (!delivered) return;
    }
    need(false, "A single save finishes its bounded picker/write chain");
}
QJsonObject savePolicy(const QString& source, const QStringList& spec) {
    need(spec.size() == 5, "A policy case declares route, data storage, mode and answer");
    const QString route = spec[1], storage = spec[2], mode = spec[3], answer = spec[4];
    SavePolicyInput input(source, storage);
    Session& session = input.session;
    if (route.startsWith("web-")) openBrowserInput(session, input.input, "folder");
    if (route == "unsaved-folder") session.project()->project_->path.clear();
    session.project()->setIncludeDataOnSave(mode);
    const auto before = state(session);
    const auto originalBytes = image(input.input);
    const auto plan = session.project()->saveDataPlan();
    QString destination =
        input.temp.filePath(route.contains("zip") ? "destination.zip" : "destination");
    if (route.startsWith("existing-")) {
        if (route.contains("zip"))
            edi::write_project_archive(input.input.toStdString(), destination.toStdString());
        else
            need(QDir().mkpath(destination),
                 "The existing-destination witness creates its actual folder");
    }
    const auto destinationBefore = image(destination, true);
    PolicyQuestions questions(session);
    jobs.clear();
    stageKinds.clear();
    savePolicySnapshots = {};
    observeSavePolicy = true;
    requestPolicySave(session, route, destination);
    turn();
    // Asking after a real picker is valid too; no durable write may precede the decision.
    for (std::size_t index = 0; questions.count() == 0 && index < jobs.size(); ++index)
        if (jobs[index].answer && jobs[index].action == "pickSave") finish(index, true);
    const bool wroteBeforeAnswer =
        image(input.input) != originalBytes || image(destination, true) != destinationBefore ||
        std::any_of(jobs.begin(), jobs.end(),
                    [](const Job& job) { return job.action == "write" && !job.recovery; });
    if (questions.count()) questions.answer(questions.request(), answer);
    if (answer != "cancel") finishPolicyIo();
    turn();
    observeSavePolicy = false;
    return {{"questions", questions.count()},
            {"askedBytes", static_cast<double>(questions.bytes())},
            {"large", questions.large()},
            {"expectedSource", QFileInfo(input.data).canonicalFilePath()},
            {"sourceBytesUnchanged", dataHashes(input.data) == input.hashes},
            {"inputBytes", static_cast<double>(input.bytes)},
            {"planBytes", plan.value("bytes").toDouble()},
            {"wroteBeforeAnswer", wroteBeforeAnswer},
            {"before", before},
            {"after", state(session)},
            {"inputUnchanged", image(input.input) == originalBytes},
            {"destinationUnchanged", image(destination, true) == destinationBefore},
            {"expectedHashes", input.hashes},
            {"snapshots", savePolicySnapshots},
            {"error", session.lastError()}};
}
QJsonObject saveContinuation(const QString& source, const QStringList& spec) {
    need(spec.size() == 2, "A save continuation declares its owner-lifetime accident");
    const QString accident = spec[1];
    SavePolicyInput input(source, "linked");
    Session& session = input.session;
    session.project()->setIncludeDataOnSave("ask");
    PolicyQuestions questions(session);
    if (accident == "stray") {
        questions.answer(1701, "copy");
        session.save();
        return {{"questions", questions.count()}};
    }
    const QString destination = input.temp.filePath("old-destination");
    need(QDir().mkpath(destination), "The old request names an existing empty destination");
    session.saveProjectAs(QUrl::fromLocalFile(destination), false, false);
    need(questions.count() == 1, "The original save reaches its actual deferred policy question");
    if (accident == "valid") {
        questions.answer(questions.request(), "linked");
        return {{"published", QFileInfo(destination + "/project.edi").isFile()},
                {"questions", questions.count()}};
    }
    const auto oldRequest = questions.request();
    if (accident == "old-first" || accident == "new-first") {
        const QString newer = input.temp.filePath("new-destination");
        need(QDir().mkpath(newer), "The newer request has its own empty destination");
        const bool newerAccepted = session.saveProjectAs(QUrl::fromLocalFile(newer), false, false);
        if (questions.count() == 1) {
            const bool refused = !newerAccepted && image(newer).isEmpty();
            questions.answer(oldRequest, "linked");
            return {{"serialized", true},
                    {"refusedNew", refused},
                    {"oldPublished", QFileInfo(destination + "/project.edi").isFile()},
                    {"newUnchanged", image(newer).isEmpty()}};
        }
        need(questions.count() == 2, "Both accepted save questions remain separately observable");
        const auto beforeAnswer = state(session);
        if (accident == "old-first") {
            questions.answer(oldRequest, "copy");
            turn();
            const bool preserved = state(session) == beforeAnswer &&
                                   image(destination).isEmpty() && image(newer).isEmpty();
            questions.answer(questions.request(), "linked");
            return {{"serialized", false},
                    {"preserved", preserved},
                    {"newPublished", QFileInfo(newer + "/project.edi").isFile()},
                    {"oldUnchanged", image(destination).isEmpty()}};
        }
        questions.answer(questions.request(), "linked");
        const auto afterNew = state(session);
        const auto newBytes = image(newer);
        questions.answer(oldRequest, "copy");
        turn();
        return {{"serialized", false},
                {"preserved", state(session) == afterNew && image(newer) == newBytes},
                {"newPublished", QFileInfo(newer + "/project.edi").isFile()},
                {"oldUnchanged", image(destination).isEmpty()}};
    }
    const auto beforeOperation = state(session);
    bool admitted = true;
    if (accident == "close") {
        session.closeProject();
        admitted = session.project() == nullptr;
    } else if (accident == "create") {
        admitted = session.createProject("successor", "Successor project", input.temp.path());
        settle(session);
    } else if (accident == "open") {
        const auto other = copy(input.input, input.temp.filePath("successor"));
        admitted = session.openProject(QUrl::fromLocalFile(other));
        settle(session);
    } else if (accident == "source") {
        const auto names = QDir(input.data).entryList({"*.dat"}, QDir::Files, QDir::Name);
        QList<QUrl> files;
        for (int index = 0; index < 2; ++index)
            files.append(QUrl::fromLocalFile(QDir(input.data).filePath(names[index])));
        admitted = session.project()->loadDatasets(session.project()->currentExperiment(), files,
                                                   true, false);
        settle(session);
    } else
        need(false, "The save owner accident is explicitly enumerated");
    if (!admitted) {
        const bool preserved = state(session) == beforeOperation && image(destination).isEmpty();
        questions.answer(oldRequest, "linked");
        return {{"closedByRefusal", true}, {"preserved", preserved}};
    }
    const auto successor = state(session);
    const auto destinationBytes = image(destination);
    questions.answer(oldRequest, "copy");
    turn();
    const bool preserved = state(session) == successor && image(destination) == destinationBytes;
    if (!session.project()) {
        need(session.openProject(QUrl::fromLocalFile(input.input)),
             "A new owner opens after the close reply was rejected");
        settle(session);
    }
    if (session.project()) {
        session.project()->setIncludeDataOnSave("ask");
        session.saveProjectAs(QUrl::fromLocalFile(destination), false, false);
    }
    return {{"preserved", preserved}, {"questions", questions.count()}};
}
}  // namespace
