// Freeze-or-replan at actual save questions and browser picker callbacks.
namespace {
QJsonObject snapshotSave(const QString& source, const QStringList& spec) {
    need(spec.size() == 4, "A snapshot case declares route, held continuation and input change");
    const QString route = spec[1], boundary = spec[2], mutation = spec[3];
    SavePolicyInput input(source, "linked");
    Session& session = input.session;
    if (route.startsWith("web-")) openBrowserInput(session, input.input, "folder");
    if (route == "unsaved-folder") session.project()->project_->path.clear();
    session.project()->setIncludeDataOnSave("ask");
    session.project()->setDescription("Independent planned state A");
    ParameterItem* lattice = nullptr;
    for (auto* item : session.project()->findChildren<ParameterItem*>())
        if (item->name() == "length_a") {
            lattice = item;
            break;
        }
    need(lattice, "The planned input has its actual editable scientific lattice value");
    lattice->setValue(10.3);
    settle(session);
    const auto names = QDir(input.data).entryList({"*.dat"}, QDir::Files, QDir::Name);
    need(names.size() >= 2, "Snapshot changes retain a populated independent scan inventory");
    const QString changedFile = QDir(input.data).filePath(names.front());
    {
        QFile file(changedFile);
        need(file.open(QIODevice::Append),
             "An authored comment identifies external content state A");
        file.write("\n# external content state A\n");
    }
    const auto hashesA = dataHashes(input.data);
    const QString destination =
        input.temp.filePath(route.contains("zip") ? "snapshot.zip" : "snapshot");
    if (route.startsWith("existing-")) {
        if (route.contains("zip"))
            edi::write_project_archive(input.input.toStdString(), destination.toStdString());
        else
            need(QDir().mkpath(destination), "The snapshot route reaches an existing destination");
    }
    const auto inputBefore = image(input.input, true);
    const auto destinationBefore = image(destination, true);
    PolicyQuestions questions(session);
    jobs.clear();
    savePolicySnapshots = {};
    observeSavePolicy = true;
    requestPolicySave(session, route, destination);
    turn();
    for (std::size_t index = 0; questions.count() == 0 && index < jobs.size(); ++index)
        if (jobs[index].answer && jobs[index].action == "pickSave") finish(index, true);
    need(questions.count() == 1,
         "The original Ask describes the actual pre-change input inventory");
    const auto originalRequest = questions.request();
    const auto plannedBytes = questions.bytes();
    int picker = -1;
    if (boundary == "picker") {
        questions.answer(originalRequest, "copy");
        turn();
        for (std::size_t index = 0; index < jobs.size(); ++index)
            if (jobs[index].answer && jobs[index].action == "pickSave") picker = int(index);
        need(picker >= 0, "The accident holds the actual browser destination picker");
    }
    if (mutation == "model") {
        session.project()->setDescription("Independent live state B");
        lattice->setValue(10.4);
        settle(session);
    }
    if (mutation == "same-size") {
        const auto file = std::filesystem::path(changedFile.toStdString());
        const auto time = std::filesystem::last_write_time(file);
        QFile data(changedFile);
        need(data.open(QIODevice::ReadOnly), "External content state A is independently readable");
        auto bytes = data.readAll();
        data.close();
        need(bytes.contains("external content state A"),
             "The equal-size change targets its authored comment");
        bytes.replace("external content state A", "external content state B");
        need(data.open(QIODevice::WriteOnly | QIODevice::Truncate),
             "The source is independently mutated outside the model");
        data.write(bytes);
        data.close();
        std::filesystem::last_write_time(file, time);
    } else if (mutation == "add-file") {
        QFile added(QDir(input.data).filePath("independent-new-frame.dat"));
        need(added.open(QIODevice::WriteOnly),
             "An external inventory addition is independently authored");
        added.write("17.5 4 .5\n18 9 1.25\n18.5 16 2.5\n");
    } else if (mutation == "remove-file") {
        need(QFile::remove(QDir(input.data).filePath(names.back())),
             "An external inventory removal is real");
    } else if (mutation == "grow-large") {
        QFile data(changedFile);
        need(data.open(QIODevice::Append),
             "The changed source crosses the warning threshold before resuming");
        data.write("\n#");
        const QByteArray padding(1024 * 1024, ' ');
        for (int block = 0; block < 101; ++block) data.write(padding);
        data.write("\n");
    } else
        need(mutation == "model", "The snapshot mutation is a declared independent accident");
    const auto hashesB = dataHashes(input.data);
    if (boundary == "question")
        questions.answer(originalRequest, "copy");
    else
        finish(std::size_t(picker), true);
    turn();
    const bool replanned = questions.count() > 1;
    const bool warned = replanned && questions.large();
    bool publishedBeforeReplan = false;
    if (replanned) {
        // An earlier prepared owned snapshot is allowed; actual browser publication
        // and a changed ordinary user destination may not precede the new decision.
        for (const auto& job : jobs)
            if (job.action == "write" && !job.recovery) publishedBeforeReplan = true;
        publishedBeforeReplan = publishedBeforeReplan || image(input.input, true) != inputBefore ||
                                image(destination, true) != destinationBefore;
        questions.answer(questions.request(), mutation == "grow-large" ? "cancel" : "copy");
    }
    finishPolicyIo();
    turn();
    observeSavePolicy = false;
    // The latest real core write is what reaches native publication or the held
    // browser write boundary. Intermediate stages are never treated as final output.
    QJsonObject written;
    if (!savePolicySnapshots.isEmpty()) written = savePolicySnapshots.last().toObject();
    bool published =
        image(input.input, true) != inputBefore || image(destination, true) != destinationBefore;
    for (const auto& job : jobs)
        if (job.action == "write" && !job.recovery) published = true;
    return {{"published", published},
            {"snapshots", savePolicySnapshots},
            {"written", written},
            {"hashesA", hashesA},
            {"hashesB", hashesB},
            {"plannedBytes", double(plannedBytes)},
            {"replanned", replanned},
            {"warned", warned},
            {"publishedBeforeReplan", publishedBeforeReplan},
            {"sourceUnchangedBySave", dataHashes(input.data) == hashesB},
            {"error", session.lastError()}};
}
}  // namespace
