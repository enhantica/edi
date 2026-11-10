// One physical inventory controls defaults and planning for all representations.
namespace {
QJsonObject linkedInventoryContract(const QString& source, const QStringList& spec) {
    need(
        spec.size() == 6,
        "An inventory case declares representation, count/size boundary, preference and location");
    const QString representation = spec[1], boundary = spec[2], preference = spec[3],
                  location = spec[4], form = spec[5];
    const int count = boundary == "count-20" ? 20 : boundary == "count-21" ? 21 : 2;
    qint64 desired = -1;
    if (boundary.startsWith("bytes-"))
        desired = 50LL * 1024 * 1024 + (boundary == "bytes-below"   ? -1
                                        : boundary == "bytes-above" ? 1
                                                                    : 0);
    const bool scan = representation == "scan" || representation == "mixed",
               mixed = representation == "mixed";
    QTemporaryDir temp;
    Session session(nullptr);
    browser = false;
    const auto input = copy(source, temp.filePath("input"));
    const QString filesRoot = temp.filePath("external");
    QList<QUrl> files;
    for (int index = 0; index < count; ++index) {
        const bool separate = mixed && index == count - 1;
        const auto file = independentMeasuredFile(
            separate ? temp.filePath("experiment-source") : filesRoot,
            QString("frame%1").arg(index, 3, 10, QLatin1Char('0')), form, false);
        if (scan && !separate) {
            QFile data(file);
            need(data.open(QIODevice::ReadOnly),
                 "A scan file keeps its independent measured rows");
            const auto bytes = data.readAll();
            data.close();
            need(data.open(QIODevice::WriteOnly | QIODevice::Truncate),
                 "The scan fixture declares its required temperature metadata");
            data.write("TEMP 20.0\n");
            data.write(bytes);
        }
        files.append(QUrl::fromLocalFile(file));
    }
    qint64 bytes = 0;
    for (const auto& file : files) bytes += QFileInfo(file.toLocalFile()).size();
    if (desired >= 0) {
        auto last = files.back().toLocalFile();
        QFile data(last);
        need(desired >= bytes + 3 && data.open(QIODevice::Append),
             "The size boundary contains valid independent data before comment padding");
        data.write("\n#");
        qint64 left = desired - bytes - 3;
        const QByteArray block(1024 * 1024, ' ');
        while (left > 0) {
            const auto amount = std::min<qint64>(left, block.size());
            need(data.write(block.constData(), amount) == amount,
                 "Every requested byte reaches the physical threshold fixture");
            left -= amount;
        }
        data.write("\n");
        data.close();
        bytes = desired;
    }
    if (scan) {
        QFile analysis(input + "/analysis/analysis.edi");
        need(analysis.open(QIODevice::ReadOnly),
             "The independent scan setup declares its data directory");
        auto text = analysis.readAll();
        analysis.close();
        need(text.contains("experiments/d20_scan"),
             "The retained scan setup names its original source");
        text.replace("experiments/d20_scan", filesRoot.toUtf8());
        need(analysis.open(QIODevice::WriteOnly | QIODevice::Truncate),
             "The scan setup links the newly authored outside folder");
        analysis.write(text);
        analysis.close();
        if (mixed) {
            QFile experiment(input + "/experiments/d20.edi");
            need(experiment.open(QIODevice::ReadOnly),
                 "The mixed input has its actual experiment template");
            auto text = experiment.readAll();
            experiment.close();
            const auto data = text.indexOf("loop_\n_data.two_theta");
            need(data >= 0, "The independent template contains its original measured loop");
            text.truncate(data);
            text += "_data_source.path \"" + files.back().toLocalFile().toUtf8() + "\"\n";
            need(experiment.open(QIODevice::WriteOnly | QIODevice::Truncate),
                 "The mixed template explicitly links a distinct measured file");
            experiment.write(text);
        }
    }
    const bool opened = session.openProject(QUrl::fromLocalFile(input));
    if (!opened) return {{"admitted", false}, {"error", session.lastError()}};
    linkedReady(session);
    auto* project = session.project();
    bool admitted = true;
    if (!scan) {
        if (form.startsWith("single-crystal")) {
            while (!project->project().experiments.empty()) project->removeExperiment(0);
            admitted = project->loadDataIntoNewExperiment(
                files.front(), "single crystal",
                form.endsWith("tof") ? "time-of-flight" : "constant wavelength", "neutron");
            if (admitted) linkedReady(session);
            if (admitted)
                if (auto* wave = project->currentExperiment()->instrument()->parameterNamed(
                        "setup_wavelength"))
                    wave->setValue(1.6);
            linkedReady(session);
        }
        if (admitted)
            admitted = project->loadDatasets(project->currentExperiment(), files, false, false);
        if (admitted) {
            linkedReady(session);
            project->removeExperiment(0);
            project->setCurrentExperimentIndex(0);
            linkedReady(session);
        }
    }
    if (!admitted) return {{"admitted", false}, {"error", project->lastError()}};
    if (location == "unsaved") {
        const auto before = project->path();
        for (auto& experiment : project->project_->experiments)
            preserveLinkWhenClearingLocation(*experiment, before);
        project->project_->path.clear();
        if (project->scan_template_) {
            for (auto& experiment : project->scan_template_->experiments)
                preserveLinkWhenClearingLocation(*experiment, before);
            project->scan_template_->path.clear();
        }
    }
    if (preference != "unset") project->setIncludeDataOnSave(preference);
    const auto plan = project->saveDataPlan();
    qint64 actualBytes = 0;
    for (const auto& file : files) actualBytes += QFileInfo(file.toLocalFile()).size();
    return {{"admitted", true},
            {"files", count},
            {"bytes", double(actualBytes)},
            {"mode", project->includeDataOnSave()},
            {"plan", QJsonObject::fromVariantMap(plan)}};
}
}  // namespace
