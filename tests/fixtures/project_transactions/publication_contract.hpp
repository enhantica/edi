// Mutate actual filesystem inputs after a decision and observe real publication.
namespace {
bool forceSerializedBrowser = false;
Image sealTree(const QString& folder) {
    Image out;
    const QFileInfo root(folder);
    if (root.isFile() || root.isSymLink()) {
        QFile file(folder);
        out["."] = root.isSymLink() ? "link:" + QFile::encodeName(root.symLinkTarget())
                   : file.open(QIODevice::ReadOnly) ? "file:" + file.readAll()
                                                    : "unreadable";
        return out;
    }
    if (root.isDir()) out["."] = "directory";
    QDirIterator walk(folder,
                      QDir::AllEntries | QDir::Hidden | QDir::System | QDir::NoDotAndDotDot,
                      QDirIterator::Subdirectories);
    while (walk.hasNext()) {
        const auto file = walk.next();
        const QFileInfo info(file);
        const auto key = QDir(folder).relativeFilePath(file);
        if (info.isSymLink())
            out[key] = "link:" + QFile::encodeName(info.symLinkTarget());
        else if (info.isDir())
            out[key] = "directory";
        else {
            QFile input(file);
            out[key] = input.open(QIODevice::ReadOnly) ? "file:" + input.readAll() : "unreadable";
        }
    }
    return out;
}
struct SealProbe {
    QString source, live, relative, phase, mutation, victim, outside;
    Image expected, baseline, changedSource;
    QMap<QString, QByteArray> directEntries;
    bool scanPayload = false, ownerNeighbors = false, recordPayload = false, committed = false;
    QJsonArray recordPublications;
    QString recordBefore;
    bool armed = false, changed = false, injecting = false, crossed = false;
    int copies = 0, cores = 0, publications = 0;
    QJsonArray wrong;
    QStringList boundaries;
};
// ADR-0069 owns only the direct entity documents in these two folders.
// The independent projection keeps nested documents and every other byte.
Image sealNeighborPayload(Image full, bool entityFolder) {
    if (!entityFolder) return full;
    for (const auto& key : full.keys()) {
        const auto suffix = QFileInfo(key).suffix().toLower();
        if (!key.contains('/') && key != "." && (suffix == "edi" || suffix == "cif"))
            full.remove(key);
    }
    return full;
}
SealProbe* sealProbe = nullptr;
QString sealRecordText(const QString& path) {
    QFile file(path);
    return file.open(QIODevice::ReadOnly) ? QString::fromUtf8(file.readAll()) : QString();
}
void sealCaptureRecord(const QString& path, const QString& boundary) {
    auto* p = sealProbe;
    if (!p || !p->armed || p->injecting) return;
    ++p->publications;
    const auto text = sealRecordText(path);
    p->recordPublications.append(QJsonObject{{"boundary", boundary}, {"text", text}});
}

void sealMutate(const QString& at) {
    auto* p = sealProbe;
    if (!p || !p->armed || p->changed) return;
    p->changed = true;
    const auto beforeSource = sealTree(p->source);
    p->injecting = true;
    p->boundaries.append(at);
    const auto path = QDir(p->source).filePath(p->victim);
    const auto write = [](const QString& name, const QByteArray& bytes) {
        QFile file(name);
        need(file.open(QIODevice::WriteOnly | QIODevice::Truncate),
             "The independent filesystem accident reaches its authored file");
        need(file.write(bytes) == bytes.size(), "The authored accident writes every byte");
    };
    if (p->mutation == "same-size") {
        const auto before = std::filesystem::last_write_time(path.toStdString());
        QFile file(path);
        need(file.open(QIODevice::ReadOnly),
             "The equal-size stimulus reads its actual authored bytes");
        auto bytes = file.readAll();
        file.close();
        need(bytes.contains("independent content A"),
             "The content stimulus reaches its authored marker");
        bytes.replace("independent content A", "independent content B");
        write(path, bytes);
        std::filesystem::last_write_time(path.toStdString(), before);
    } else if (p->mutation == "remove")
        need(QFile::remove(path), "The planned file is actually removed");
    else if (p->mutation == "add" || p->mutation == "hidden")
        write(QDir(p->source).filePath(p->mutation == "hidden" ? ".unplanned" : "unplanned.bin"),
              "unplanned independent bytes\n");
    else if (p->mutation == "symlink") {
        const auto outside = p->outside.isEmpty() ? p->source + "-outside" : p->outside;
        write(outside, "independent content B\n");
        need(QFile::remove(path) && QFile::link(outside, path),
             "The planned regular file becomes an actual external symlink");
    } else if (p->mutation == "directory") {
        need(QFile::remove(path) && QDir().mkpath(path),
             "The planned regular file becomes a directory");
    } else if (p->mutation == "rename") {
        need(QFile::rename(path, path + ".moved"), "The planned file changes its actual name");
    } else if (p->mutation == "unreadable") {
        need(QFile::setPermissions(path, {}), "The actual planned input loses read permission");
        QFile check(path);
        need(!check.open(QIODevice::ReadOnly), "The runtime really cannot read the planned input");
    } else
        need(p->mutation == "unchanged", "The filesystem stimulus is explicitly declared");
    // The fixture's external accident is not attributed to the product writer.
    const auto relative = QDir(p->live).relativeFilePath(p->source);
    p->changedSource = sealTree(p->source);
    if (relative != ".." && !relative.startsWith("../") && !QDir::isAbsolutePath(relative)) {
        // Exclude only this external accident, never earlier product writes.
        auto keys = beforeSource.keys();
        for (const auto& key : p->changedSource.keys())
            if (!keys.contains(key)) keys.append(key);
        for (const auto& key : keys) {
            if (beforeSource.contains(key) == p->changedSource.contains(key) &&
                beforeSource.value(key) == p->changedSource.value(key))
                continue;
            const auto physical = key == "." ? p->source : QDir(p->source).filePath(key);
            const auto liveKey = QDir(p->live).relativeFilePath(physical);
            if (p->changedSource.contains(key))
                p->baseline[liveKey] = p->changedSource.value(key);
            else
                p->baseline.remove(liveKey);
        }
    }
    p->injecting = false;
}
void sealCheck(const QString& folder, const QString& boundary) {
    auto* p = sealProbe;
    if (!p || !p->armed || p->injecting) return;
    if (p->recordPayload) {
        sealCaptureRecord(QDir(folder).filePath("project.edi"), boundary);
        return;
    }
    ++p->publications;
    Image actual;
    try {
        if (p->scanPayload) {
            const auto project = edi::load_project(folder.toStdString());
            const auto declared = QString::fromStdString(project.sequential_fit.data_dir);
            QString resolved;
            if (!QFileInfo(declared).isAbsolute())
                resolved = QDir(folder).filePath(declared);
            else if (QFileInfo(folder).absoluteFilePath() == QFileInfo(p->live).absoluteFilePath())
                resolved = declared;
            else if (!p->live.endsWith(".zip")) {
                const auto inside = QDir(p->live).relativeFilePath(declared);
                if (inside != ".." && !inside.startsWith("../") && !QDir::isAbsolutePath(inside))
                    resolved = QDir(folder).filePath(inside);
            }
            const auto relative = QDir(QFileInfo(folder).canonicalFilePath())
                                      .relativeFilePath(QFileInfo(resolved).canonicalFilePath());
            if (!declared.isEmpty() && !resolved.isEmpty() && relative != ".." &&
                !relative.startsWith("../") && !QDir::isAbsolutePath(relative))
                actual = sealTree(resolved);
        } else
            actual = sealNeighborPayload(sealTree(QDir(folder).filePath(p->relative)),
                                         p->ownerNeighbors);
    } catch (const std::exception&) { /* An unprovable candidate cannot be certified. */
    }
    if (actual != p->expected)
        p->wrong.append(QJsonObject{{"boundary", boundary}, {"folder", folder}});
}
void sealBeforeCore() {
    if (!sealProbe || !sealProbe->armed) return;
    ++sealProbe->cores;
    if (sealProbe->phase == "pre-core") sealMutate("last app precheck to actual core writer");
}
void sealAfterCore(const QString& folder) {
    sealCommitted(folder);
    if (!sealProbe || !sealProbe->armed) return;
    // The candidate is retained even when an outer check later refuses it.
    if (QFileInfo(folder).absoluteFilePath() == QFileInfo(sealProbe->live).absoluteFilePath())
        sealCheck(folder, "core returned into user destination");
}
void sealBeforeCopy(const QString& from, const QString& target) {
    auto* p = sealProbe;
    if (!p || !p->armed || p->injecting) return;
    const auto relative = QDir(p->source).relativeFilePath(from);
    const auto nested = QDir(from).relativeFilePath(p->source);
    const bool ancestor = QFileInfo(from).isDir() && nested != ".." && !nested.startsWith("../") &&
                          !QDir::isAbsolutePath(nested);
    if (!ancestor &&
        (relative == ".." || relative.startsWith("../") || QDir::isAbsolutePath(relative)))
        return;
    if (p->scanPayload && !QFileInfo(from).isDir()) {
        const auto live = QDir(p->live).relativeFilePath(target);
        if (live != ".." && !live.startsWith("../") && !QDir::isAbsolutePath(live))
            p->directEntries[target] = p->expected.value(relative, "unplanned");
    }
    ++p->copies;
    if (p->phase == "copy" && (relative == p->victim || ancestor))
        sealMutate(ancestor ? "actual recursive tree copy" : "actual planned payload transfer");
}
void sealAfterCopy(const QString& target) {
    auto* p = sealProbe;
    if (!p || !p->armed || p->injecting) return;
    if (p->recordPayload) {
        if (QFileInfo(target).absoluteFilePath() ==
            QFileInfo(QDir(p->live).filePath("project.edi")).absoluteFilePath())
            sealCaptureRecord(target, "actual record copy into user destination");
        return;
    }
    if (p->scanPayload) {
        if (p->directEntries.contains(target) &&
            sealTree(target).value(".") != p->directEntries.value(target))
            p->wrong.append(QJsonObject{{"boundary", "linked data copied into user destination"},
                                        {"entry", target}});
        return;
    }
    const auto key = QDir(QDir(p->live).filePath(p->relative)).relativeFilePath(target);
    if (key == ".." || key.startsWith("../") || QDir::isAbsolutePath(key)) return;
    // A partially copied correct set is allowed; a single unplanned published
    // entry is not, even if a later refusal removes or rewrites it.
    const auto actual =
        sealNeighborPayload(sealTree(QDir(p->live).filePath(p->relative)), p->ownerNeighbors);
    if (p->ownerNeighbors && !actual.contains(key)) return;
    if (!p->expected.contains(key) || actual.value(key) != p->expected.value(key))
        p->wrong.append(
            QJsonObject{{"boundary", "actual copy into user destination"}, {"entry", key}});
}
Image sealArchivePayload(const QByteArray&, const QString&);
void sealBeforeRename(const QString& from, const QString& to) {
    auto* p = sealProbe;
    if (!p || !p->armed || p->injecting) return;
    const auto relative = QDir(p->live).relativeFilePath(to);
    if (relative == ".." || relative.startsWith("../") || QDir::isAbsolutePath(relative)) return;
    p->crossed = true;
    if (sealTree(from) == p->baseline) {
        ++p->publications;
        return;
    }
    if (!p->changed) sealMutate("actual native publication frontier");
    if (p->recordPayload && QFileInfo(from).isFile() &&
        QFileInfo(to).absoluteFilePath() ==
            QFileInfo(QDir(p->live).filePath("project.edi")).absoluteFilePath()) {
        sealCaptureRecord(from, "actual record rename into user destination");
        return;
    }
    // A whole-folder rename exposes the source tree. An individual document
    // rename exposes the already seeded live folder.
    if (p->live.endsWith(".zip") && QFileInfo(from).isFile()) {
        QFile archive(from);
        if (archive.open(QIODevice::ReadOnly))
            sealArchivePayload(archive.readAll(), "actual native archive publication");
        else {
            ++p->publications;
            p->wrong.append(QJsonObject{{"boundary", "unreadable native archive publication"}});
        }
    } else
        sealCheck(QFileInfo(from).isDir() ? from : p->live, "native rename frontier");
}
Image sealArchivePayload(const QByteArray& bytes, const QString& boundary) {
    auto* p = sealProbe;
    if ((!p || !p->armed) && !forceSerializedBrowser) return {};
    QTemporaryDir decoded;
    QString error;
    const auto folder = edi_app::WebFiles::unpack(bytes, decoded.path(), error);
    if (folder.isEmpty()) {
        if (!p)
            throw std::runtime_error("The actual browser archive must be independently readable");
        ++p->publications;
        p->wrong.append(
            QJsonObject{{"boundary", boundary}, {"error", "unreadable project archive"}});
        return {};
    }
    sealCheck(folder, boundary);
    return image(folder);
}
bool sealBrowserPayload(const QString& folder, const QString& kind, bool recovery, Image& payload,
                        QString& problem) {
    auto* p = sealProbe;
    if (recovery || ((!p || !p->armed) && !forceSerializedBrowser)) {
        payload = image(folder);
        return true;
    }
    if (p && !p->changed) sealMutate("actual browser serialization boundary");
    Image staged;
    bool ready = true;
    observe_browser_serialization(kind, folder, recovery, staged, problem, ready);
    if (!ready) return false;
    if (p) p->crossed = true;
    if (kind == "zip") {
        payload = sealArchivePayload(staged.value(""), "actual browser archive transport");
    } else {
        QTemporaryDir decoded;
        for (auto at = staged.begin(); at != staged.end(); ++at) {
            const auto target = QDir(decoded.path()).filePath(at.key());
            need(QDir().mkpath(QFileInfo(target).path()),
                 "The injected transport materializes its actual staged directory");
            QFile file(target);
            need(file.open(QIODevice::WriteOnly) && file.write(at.value()) == at.value().size(),
                 "The injected transport retains every actual staged byte");
        }
        sealCheck(decoded.path(), "actual browser folder transport");
        payload = staged;
    }
    return true;
}
void sealArchiveWrite(const QString& folder, const QString& target) {
    auto* p = sealProbe;
    if (!p || !p->armed ||
        QFileInfo(target).absoluteFilePath() != QFileInfo(p->live).absoluteFilePath())
        return;
    p->crossed = true;
    if (!p->changed) sealMutate("actual archive publication frontier");
    Q_UNUSED(folder);  // The actual finished archive is checked at its native publication.
}
void sealCommitted(const QString& target) {
    if (sealProbe && sealProbe->armed &&
        QFileInfo(target).absoluteFilePath() == QFileInfo(sealProbe->live).absoluteFilePath())
        sealProbe->committed = true;
}
void sealStorageCommitted() {
    if (sealProbe && sealProbe->armed) sealProbe->committed = true;
}
void sealBeforeArchiveBytes() {
    if (sealProbe && sealProbe->armed && !sealProbe->changed)
        sealMutate("actual archive packing boundary");
}
void sealBrowserDownload(const QByteArray& bytes) {
    if (!sealProbe || !sealProbe->armed) return;
    if (!sealProbe->changed) sealMutate("actual browser archive handoff");
    sealArchivePayload(bytes, "actual browser archive bytes");
    sealProbe->committed = true;
}
bool boundarySaveRequest(Session& session, const QString& route, const QString& target) {
    if (route.startsWith("assistant-")) {
        const auto owner = QPointer<ProjectViewModel>(session.project());
        need(session.requestAssistantSaveAs(
                 "independent-save-choice", "sealed", owner, session.assistant_epoch_,
                 [&session, owner] { return owner && session.project() == owner; },
                 [&session](const QUrl& where, bool zip, bool copy) {
                     return session.saveProjectAs(where, zip, copy);
                 },
                 [] {}),
             "The assistant chooser request is admitted by its actual owner protocol");
        return session.completeAssistantSaveAs("independent-save-choice",
                                               QUrl::fromLocalFile(target), route.contains("zip"),
                                               route.contains("copy"));
    } else if (route == "save-archive" || route.startsWith("web-save-"))
        session.save();
    else if (route == "web-browser" || route == "web-copy-browser")
        session.saveWebProjectAs("browser", route.contains("copy"));
    else
        return requestPolicySave(session, route, target);
    return true;
}
template <class Project>
bool locateSealedFolder(Project* project, const QUrl& url, const QString& missing) {
    if constexpr (requires { project->locateDataFolder(url, missing); })
        return project->locateDataFolder(url, missing);
    else
        return project->locateDataFolder(url);
}
QJsonObject sealedPublication(const QString& source, const QStringList& spec) {
    need(
        spec.size() == 5 || spec.size() == 6,
        "A sealed publication declares route, late boundary, mutation, spelling and payload role");
    const auto route = spec[1], phase = spec[2], mutation = spec[3], spelling = spec[4];
    SavePolicyInput input(source, "linked");
    auto& session = input.session;
    if (route.startsWith("web-"))
        openBrowserInput(session, input.input,
                         route == "web-save-zip"       ? "zip"
                         : route == "web-save-browser" ? "browser"
                                                       : "folder");
    const bool scanPayload = spec.size() == 6 && spec[5] == "scan";
    need(scanPayload || route != "unsaved-folder",
         "Carried-tree cases use routes that actually copy an existing tree; model-only saves "
         "have separate snapshot gates");
    SealProbe probe;
    probe.scanPayload = scanPayload;
    probe.recordPayload = spec.size() == 6 && spec[5] == "project-record";
    probe.ownerNeighbors = spec.size() == 6 && spec[5].startsWith("neighbors-");
    probe.relative =
        probe.ownerNeighbors ? spec[5].mid(QString("neighbors-").size()) : "user-inputs";
    need(
        !probe.ownerNeighbors || probe.relative == "structures" || probe.relative == "experiments",
        "The writer-neighbor witness declares one actual entity folder");
    probe.outside = input.temp.filePath("outside-payload");
    probe.source = QDir(session.project()->path()).filePath(probe.relative);
    if (scanPayload) {
        probe.source = input.data;
        if (spelling != "plain") {
            const auto renamed = input.data + (spelling == "pipe"      ? "|part"
                                               : spelling == "newline" ? "\npart"
                                                                       : QString::fromUtf8("-é"));
            need(QDir().rename(input.data, renamed),
                 "The scan's actual folder has its legal authored separator spelling");
            need(locateSealedFolder(session.project(), QUrl::fromLocalFile(renamed), input.data),
                 "The actual Locate producer admits the scan folder with its legal native "
                 "spelling");
            settle(session);
            probe.source = renamed;
        }
        const auto names = QDir(probe.source).entryList({"*.dat"}, QDir::Files, QDir::Name);
        need(!names.isEmpty(), "The linked scan's independent source has actual planned frames");
        probe.victim = names.back();
        for (const auto& name : names) {
            QFile file(QDir(probe.source).filePath(name));
            need(file.open(QIODevice::Append),
                 "The raw-data control keeps valid rows and adds only an authored marker");
            file.write("\n# independent content A\n");
        }
        if (route == "unsaved-folder") {
            session.project()->project_->scan_data_root = session.project()->project_->path;
            session.project()->project_->path.clear();
            session.project()->project_->metadata.path.clear();
        }
    } else if (probe.recordPayload) {
        probe.relative = "";
        probe.source = session.project()->path();
        probe.victim = "project.edi";
        QFile file(QDir(probe.source).filePath(probe.victim));
        need(file.open(QIODevice::Append),
             "The real project record accepts authored carried CIF items");
        file.write("\n_audit.note 'independent content A'\n");
        if (spelling == "literal")
            file.write(
                "_audit.other\n;first authored paragraph\n_metadata.name literal carried "
                "words\n\nlast authored paragraph\n;\n");
        else {
            need(spelling == "scalar",
                 "The record control explicitly declares its authored scalar form");
            file.write("_audit.other 'independently authored carried record'\n");
        }
        file.close();
        probe.recordBefore = sealRecordText(file.fileName());
        need(probe.recordBefore.contains("independent content A"),
             "The planned retained record contains its original independently authored content");
        session.project()->setDescription("Independently authored live save description");
    } else {
        need(QDir().mkpath(probe.source),
             "The carried-payload witness owns a normal retained folder");
        probe.victim = probe.ownerNeighbors    ? "notes.txt"
                       : spelling == "pipe"    ? "payload|part.bin"
                       : spelling == "newline" ? "payload\npart.bin"
                       : spelling == "unicode" ? QString::fromUtf8("payload-é.bin")
                                               : "payload.bin";
        const QStringList names =
            probe.ownerNeighbors
                ? QStringList{probe.victim, "untouched.bin", "nested/phase.edi", "nested/bank.CiF"}
                : QStringList{probe.victim, "untouched.bin", "retained.bin"};
        for (const auto& name : names) {
            need(QDir().mkpath(QFileInfo(QDir(probe.source).filePath(name)).path()),
                 "The authored nested entity-folder neighbors have real parent directories");
            QFile file(QDir(probe.source).filePath(name));
            need(file.open(QIODevice::WriteOnly),
                 "The authored payload has ordinary and hidden files");
            file.write("independent content A\n");
        }
    }
    probe.phase = phase;
    probe.mutation = mutation;
    probe.expected = sealNeighborPayload(sealTree(probe.source), probe.ownerNeighbors);
    QString target = input.temp.filePath(
        route.contains("zip") || route == "save-archive" ? "sealed.zip" : "sealed");
    if (route == "save-archive") {
        edi::write_project_archive(session.project()->path().toStdString(), target.toStdString());
        need(session.openProject(QUrl::fromLocalFile(target)),
             "The archive Save uses a real archive-opened user project");
        settle(session);
        if (!scanPayload) probe.source = QDir(session.project()->path()).filePath(probe.relative);
    }
    if (route.startsWith("existing-") || route == "save-as") {
        if (route.contains("zip"))
            edi::write_project_archive(input.input.toStdString(), target.toStdString());
        else {
            copy(input.input, target);
            QFile old(target + "/previous-destination.bin");
            need(old.open(QIODevice::WriteOnly),
                 "The existing destination has independent prior user bytes");
            old.write("previous user state Z\n");
        }
    }
    probe.live = route == "save" ? session.project()->path() : target;
    probe.baseline = sealTree(probe.live);
    const bool privateWorkingSource =
        !scanPayload && QFileInfo(session.project()->path()).absoluteFilePath() !=
                            QFileInfo(input.input).absoluteFilePath();
    const auto originalUserSource = sealTree(input.input);
    session.project()->setIncludeDataOnSave("ask");
    PolicyQuestions questions(session);
    QSignalSpy webFailures(&session, &Session::webSaveFailed);
    boundaryDownload = route == "web-download";
    struct ResetDownload {
        ~ResetDownload() { boundaryDownload = false; }
    } resetDownload;
    jobs.clear();
    boundarySaveRequest(session, route, target);
    turn();
    for (std::size_t index = 0; questions.count() == 0 && index < jobs.size(); ++index)
        if (jobs[index].answer && jobs[index].action == "pickSave") finish(index, true);
    need(questions.count() == 1, "The actual operation plans A before the late input accident");
    sealProbe = &probe;
    struct ResetSeal {
        ~ResetSeal() { sealProbe = nullptr; }
    } resetSeal;
    probe.armed = true;
    questions.answer(questions.request(), "copy");
    finishPolicyIo();
    turn();
    // If a new question is owed, it stays unanswered. No decision for A may
    // authorize publication of B before that independently visible question.
    const bool replanned = questions.count() > 1;
    const bool refused = !session.lastError().isEmpty() || !webFailures.isEmpty();
    const bool unchanged = sealTree(probe.live) == probe.baseline;
    const bool finalMatches =
        sealNeighborPayload(sealTree(QDir(probe.live).filePath(probe.relative)),
                            probe.ownerNeighbors) == probe.expected;
    auto wrong = probe.wrong;
    sealProbe = nullptr;
    return {{"recordBefore", probe.recordBefore},
            {"recordAfter", sealRecordText(QDir(probe.source).filePath("project.edi"))},
            {"recordSourceExists", QFileInfo::exists(QDir(probe.source).filePath("project.edi"))},
            {"recordPrivateSource", privateWorkingSource},
            {"recordPublications", probe.recordPublications},
            {"originalUserSourceConserved", sealTree(input.input) == originalUserSource},
            {"externalDataConserved", dataHashes(input.data) == input.hashes},
            {"role", spec.size() == 6 ? spec[5] : "plain"},
            {"injected", probe.changed},
            {"boundaries", QJsonArray::fromStringList(probe.boundaries)},
            {"coreCalls", probe.cores},
            {"copyCalls", probe.copies},
            {"frontier", probe.crossed},
            {"observedPublications", probe.publications},
            {"wrongPublications", wrong},
            {"refused", refused},
            {"committed", probe.committed},
            {"replanned", replanned},
            {"destinationUnchanged", unchanged},
            {"finalMatches", finalMatches},
            {"sourceConserved",
             privateWorkingSource
                 ? sealTree(input.input) == originalUserSource
                 : !probe.changed ||
                       sealNeighborPayload(sealTree(probe.source), probe.ownerNeighbors) ==
                           sealNeighborPayload(probe.changedSource, probe.ownerNeighbors)},
            {"error", session.lastError()}};
}
}  // namespace
extern "C" bool operation_file_copy(const QString& source, const QString& target) {
    ownerCoreAttempt();
    ownerCoreAttempt();
    sealBeforeCopy(source, target);
    const bool result = QFile::copy(source, target);
    if (result) sealAfterCopy(target);
    return result;
}
extern "C" bool operation_dir_rename(QDir* folder, const QString& source, const QString& target) {
    sealBeforeRename(QDir::isAbsolutePath(source) ? source : folder->filePath(source),
                     QDir::isAbsolutePath(target) ? target : folder->filePath(target));
    const bool result = folder->rename(source, target);
    if (result) sealCommitted(QDir::isAbsolutePath(target) ? target : folder->filePath(target));
    return result;
}
extern "C" bool operation_file_rename(QFile* file, const QString& target) {
    ownerCoreAttempt();
    sealBeforeRename(file->fileName(), target);
    const bool result = file->rename(target);
    if (result) sealCommitted(target);
    return result;
}
extern "C" bool operation_file_rename_static(const QString& source, const QString& target) {
    ownerCoreAttempt();
    sealBeforeRename(source, target);
    const bool result = QFile::rename(source, target);
    if (result) sealCommitted(target);
    return result;
}
extern "C" bool publication_copy_file(const std::filesystem::path& source,
                                      const std::filesystem::path& target,
                                      std::filesystem::copy_options options,
                                      std::error_code& error) {
    ownerCoreAttempt();
    sealBeforeCopy(QString::fromStdString(source.string()),
                   QString::fromStdString(target.string()));
    const bool result = std::filesystem::copy_file(source, target, options, error);
    if (result) sealAfterCopy(QString::fromStdString(target.string()));
    return result;
}
extern "C" void publication_copy(const std::filesystem::path& source,
                                 const std::filesystem::path& target,
                                 std::filesystem::copy_options options, std::error_code& error) {
    ownerCoreAttempt();
    sealBeforeCopy(QString::fromStdString(source.string()),
                   QString::fromStdString(target.string()));
    std::filesystem::copy(source, target, options, error);
    // Recursive standard-library work has no user callbacks inside it. Retain
    // its complete live result before the caller can validate or roll it back.
    auto* p = sealProbe;
    if (p && p->armed && !p->injecting) {
        const auto relative =
            QDir(p->live).relativeFilePath(QString::fromStdString(target.string()));
        if (relative != ".." && !relative.startsWith("../") && !QDir::isAbsolutePath(relative)) {
            if (p->recordPayload) {
                if (QFileInfo::exists(QDir(p->live).filePath("project.edi")))
                    sealCaptureRecord(QDir(p->live).filePath("project.edi"),
                                      "actual recursive record publication");
                return;
            }
            if (p->scanPayload) {
                sealCheck(p->live, "recursive linked-data copy into user destination");
                return;
            }
            const auto actual = sealNeighborPayload(sealTree(QDir(p->live).filePath(p->relative)),
                                                    p->ownerNeighbors);
            for (auto at = actual.begin(); at != actual.end(); ++at)
                if (!p->expected.contains(at.key()) || p->expected.value(at.key()) != at.value())
                    p->wrong.append(
                        QJsonObject{{"boundary", "recursive copy into user destination"},
                                    {"entry", at.key()}});
        }
    }
}
extern "C" void publication_rename(const std::filesystem::path& source,
                                   const std::filesystem::path& target, std::error_code& error) {
    ownerCoreAttempt();
    sealBeforeRename(QString::fromStdString(source.string()),
                     QString::fromStdString(target.string()));
    std::filesystem::rename(source, target, error);
    if (!error) sealCommitted(QString::fromStdString(target.string()));
}

extern "C" void publication_hard_link(const std::filesystem::path& source,
                                      const std::filesystem::path& target,
                                      std::error_code& error) {
    ownerCoreAttempt();
    sealBeforeCopy(QString::fromStdString(source.string()),
                   QString::fromStdString(target.string()));
    std::filesystem::create_hard_link(source, target, error);
    if (!error) sealAfterCopy(QString::fromStdString(target.string()));
}
