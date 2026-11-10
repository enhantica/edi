// Authored measured files at the common importer and final save boundaries.
namespace {
void linkedReady(Session& session) {
    pumpUntil(
        [&] {
            auto* p = session.project();
            return p && !p->calculating() && !p->view_reading_;
        },
        "The requested data projection and calculation finish before observation or save");
}
template <class Experiment>
void preserveLinkWhenClearingLocation(Experiment& experiment, const QString& root) {
    if constexpr (requires { experiment.data_path; }) {
        const QString path = QString::fromStdString(experiment.data_path);
        if (!path.isEmpty() && !QFileInfo(path).isAbsolute())
            experiment.data_path = QDir(root).absoluteFilePath(path).toStdString();
    }
}
QString independentMeasuredFile(const QString& directory, const QString& name, const QString& form,
                                bool successor) {
    need(QDir().mkpath(directory), "Independent measured inputs own their source directory");
    const QString file = QDir(directory).filePath(name + ".dat");
    QFile out(file);
    need(out.open(QIODevice::WriteOnly), "Independent measured input is physically materialized");
    const bool sc = form.startsWith("single-crystal"), tof = form.endsWith("tof");
    if (sc) {
        if (successor)
            out.write(tof ? "2 1 3 28.5 .7 1.25\n-2 1 3 19.2 1.3 1.75\n0 0 2 -14.5 .2 2.25\n"
                          : "2 1 3 28.5 .7\n-2 1 3 19.2 1.3\n0 0 2 -14.5 .2\n");
        else
            out.write(tof ? "2 1 3 18.5 .7 1.25\n-2 1 3 9.2 1.3 1.75\n0 0 2 -4.5 .2 2.25\n"
                          : "2 1 3 18.5 .7\n-2 1 3 9.2 1.3\n0 0 2 -4.5 .2\n");
    } else if (successor)
        out.write(tof ? "3500 14 .5\n3600 19 1.25\n3700 26 2.5\n"
                      : "17.5 14 .5\n18 19 1.25\n18.5 26 2.5\n");
    else
        out.write(tof ? "3500 4 .5\n3600 9 1.25\n3700 16 2.5\n"
                      : "17.5 4 .5\n18 9 1.25\n18.5 16 2.5\n");
    return file;
}
template <class Experiment>
QString observedFileLink(const Experiment& experiment) {
    if constexpr (requires { experiment.data_path; })
        return QString::fromStdString(experiment.data_path);
    else
        return {};  // The pre-feature model has no representation; the gate reports that boundary.
}
QJsonArray independentRowsObserved(const edi::BraggPdExperiment& experiment) {
    QJsonArray rows;
    if (experiment.reflections) {
        const auto& data = *experiment.reflections;
        for (std::size_t index = 0; index < data.size(); ++index) {
            QJsonArray row{data.index_h[index], data.index_k[index], data.index_l[index],
                           data.intensity_meas[index], data.intensity_meas_su[index]};
            if (experiment.effective_beam_mode() == edi::BeamModeEnum::TIME_OF_FLIGHT &&
                !data.wavelength.empty())
                row.append(data.wavelength[index]);
            rows.append(row);
        }
    } else if (experiment.data) {
        const auto& data = *experiment.data;
        for (std::size_t index = 0; index < data.intensity_meas.size(); ++index)
            rows.append(QJsonArray{data.axis()[index], data.intensity_meas[index],
                                   data.intensity_meas_su[index]});
    }
    return rows;
}
QJsonObject finalLinkedObservation(const QString& folder) {
    QJsonArray records;
    const auto project = edi::load_project(folder.toStdString());
    for (const auto& experiment : project.experiments) {
        const auto declared = observedFileLink(*experiment);
        const QString path =
            QFileInfo(declared).isAbsolute() ? declared : QDir(folder).filePath(declared);
        QFile text(folder + "/experiments/" + QString::fromStdString(experiment->name.value()) +
                   ".edi");
        need(text.open(QIODevice::ReadOnly),
             "The final saved experiment has a readable actual declaration");
        records.append(
            QJsonObject{{"name", QString::fromStdString(experiment->name.value())},
                        {"text", QString::fromUtf8(text.readAll())},
                        {"declared", declared},
                        {"physicalSource",
                         declared.isEmpty() ? QString() : QFileInfo(path).canonicalFilePath()},
                        {"rows", independentRowsObserved(*experiment)}});
    }
    const QString declaredScan = QString::fromStdString(project.sequential_fit.data_dir);
    const QString scan =
        declaredScan.isEmpty()
            ? QString()
            : QFileInfo(QFileInfo(declaredScan).isAbsolute() ? declaredScan
                                                             : QDir(folder).filePath(declaredScan))
                  .canonicalFilePath();
    return {{"experiments", records},
            {"scanDirectory", declaredScan},
            {"physicalScan", scan},
            {"scanHashes", scan.isEmpty() ? QJsonObject{} : dataHashes(scan)}};
}
QString publishedLinkedFolder(Session& session, const QString& route, const QString& destination,
                              QTemporaryDir& temp) {
    if (route.startsWith("web-")) {
        for (auto entry = jobs.crbegin(); entry != jobs.crend(); ++entry) {
            if (entry->action != "write" || entry->recovery) continue;
            const auto root = temp.filePath("published-browser");
            for (auto file = entry->payload.cbegin(); file != entry->payload.cend(); ++file) {
                const auto target = QDir(root).filePath(file.key());
                need(QDir().mkpath(QFileInfo(target).absolutePath()),
                     "The actual browser payload keeps its member directories");
                QFile out(target);
                need(out.open(QIODevice::WriteOnly),
                     "The actual browser payload is independently materialized");
                out.write(file.value());
            }
            return root;
        }
        return {};
    }
    const auto target = route == "save" ? session.project()->path() : destination;
    if (route.contains("zip")) {
        QFile archive(target);
        if (!archive.open(QIODevice::ReadOnly)) return {};
        return QString::fromStdString(edi::unpack_project_archive(
            archive.readAll().toStdString(), temp.filePath("published-archive").toStdString()));
    }
    return QFileInfo::exists(target + "/project.edi") ? target : QString();
}
QJsonObject linkedPayload(const QString& source, const QStringList& spec) {
    need(spec.size() == 5,
         "A linked payload declares form, transition, save route and save policy");
    const auto form = spec[1], transition = spec[2], route = spec[3], mode = spec[4];
    QTemporaryDir temp;
    Session session(nullptr);
    browser = false;
    const auto input = copy(source, temp.filePath("input"));
    const auto a = independentMeasuredFile(temp.filePath("sourceA"), "patternA", form, false);
    const auto b = independentMeasuredFile(temp.filePath("sourceB"), "patternB", form, true);
    const auto a2 = independentMeasuredFile(temp.filePath("sourceA"), "patternA2", form, false);
    const auto c = independentMeasuredFile(temp.filePath("sourceB"), "patternC", form, true);
    const auto beforeA = image(temp.filePath("sourceA"), true),
               beforeB = image(temp.filePath("sourceB"), true);
    need(session.openProject(QUrl::fromLocalFile(input)),
         "The linked witness opens its independent setup project");
    linkedReady(session);
    auto* project = session.project();
    while (!project->project().experiments.empty()) project->removeExperiment(0);
    const bool sc = form.startsWith("single-crystal"), tof = form.endsWith("tof");
    const bool created = project->loadDataIntoNewExperiment(
        QUrl::fromLocalFile(a), sc ? "single crystal" : "powder",
        tof ? "time-of-flight" : "constant wavelength", "neutron");
    if (!created) return {{"admitted", false}, {"error", project->lastError()}};
    linkedReady(session);
    if (auto* item =
            project->currentExperiment()->instrument()->parameterNamed("setup_wavelength"))
        item->setValue(1.6);
    if (auto* item =
            project->currentExperiment()->instrument()->parameterNamed("calib_d_to_tof_linear"))
        item->setValue(10000);
    linkedReady(session);
    const bool linked = project->loadDatasets(project->currentExperiment(),
                                              {QUrl::fromLocalFile(a)}, false, false);
    if (!linked) return {{"admitted", false}, {"error", project->lastError()}};
    linkedReady(session);
    project->removeExperiment(0);
    project->setCurrentExperimentIndex(0);
    linkedReady(session);
    project->setIncludeDataOnSave("linked");
    const auto seed = temp.filePath("linked-seed");
    const bool seedSaved = session.saveProjectAs(QUrl::fromLocalFile(seed), false, false);
    linkedReady(session);
    if (!seedSaved) return {{"admitted", false}, {"error", session.lastError()}};
    const auto initial = finalLinkedObservation(seed);
    project = session.project();
    bool replaced = true;
    if (transition == "ordinary")
        replaced = project->loadDataInto(project->currentExperiment(), QUrl::fromLocalFile(b));
    else if (transition == "full-experiment") {
        const auto directory = temp.filePath("full-source");
        need(QDir().mkpath(directory),
             "The full experiment owns a source base distinct from the project");
        auto text = initial["experiments"].toArray().first().toObject()["text"].toString();
        const auto start = text.indexOf(
            QRegularExpression("(?m)^loop_[\\t ]*\\r?\\n[\\t ]*(?=_(?:data|refln)\\.)"));
        if (start >= 0) text.truncate(start);
        text.remove(
            QRegularExpression("(?m)^_data_source\\.(?:path|collection_id|digest)[^\\n]*\\n?"));
        text.replace(QRegularExpression("(?m)^data_[^\\n]+"), "data_full_successor");
        text.replace(QRegularExpression("(?m)^_data_source\\.file_name[^\\n]*"),
                     "_data_source.file_name patternB.dat");
        text += "_data_source.path ../sourceB/patternB.dat\n";
        const auto file = QDir(directory).filePath("successor.edi");
        QFile out(file);
        need(out.open(QIODevice::WriteOnly),
             "The full experiment declaration is independently materialized");
        out.write(text.toUtf8());
        out.close();
        replaced = project->loadExperiments({QUrl::fromLocalFile(file)});
        if (replaced) {
            linkedReady(session);
            project->removeExperiment(0);
            project->setCurrentExperimentIndex(0);
        }
    } else if (transition == "reflection-batch") {
        const auto file = temp.filePath("multiple.int");
        QFile out(file);
        need(out.open(QIODevice::WriteOnly),
             "The authored FullProf file contains three distinct dataset ids");
        if (tof)
            out.write(
                "Dataset and wavelength witness\n(3i4,2f12.4,i4,2f8.4)\n0 0 0\n2 1 3 9 .3 2 1.3 "
                "84\n1 2 3 -4 .7 7 1.5 88\n2 1 3 12 .4 2 1.7 92\n3 1 2 5 .2 4 1.9 94\n0 0 0 0 0 7 "
                "2.1 90\n");
        else
            out.write(
                "Dataset witness\n(3i4,2f12.4,i4)\n1.6 0 0\n2 1 3 9 .3 2\n1 2 3 -4 .7 7\n2 1 3 12 "
                ".4 2\n3 1 2 5 .2 4\n0 0 0 0 0 7\n");
        out.close();
        replaced = project->loadDatasets(project->currentExperiment(), {QUrl::fromLocalFile(file)},
                                         false, true);
        if (replaced) {
            linkedReady(session);
            project->removeExperiment(0);
            project->setCurrentExperimentIndex(0);
        }
    } else if (transition == "batch-copy" || transition == "batch-link") {
        replaced = project->loadDatasets(project->currentExperiment(), {QUrl::fromLocalFile(b)},
                                         false, transition == "batch-copy");
        if (replaced) {
            linkedReady(session);
            project->removeExperiment(0);
            project->setCurrentExperimentIndex(0);
        }
    } else if (QStringList{"scan-copy", "scan-link", "scan-replace-copy", "scan-replace-link"}
                   .contains(transition)) {
        const bool replacing = transition.startsWith("scan-replace-");
        const bool copying = transition.endsWith("copy");
        const QList<QUrl> files =
            replacing ? QList<QUrl>{QUrl::fromLocalFile(a), QUrl::fromLocalFile(a2)}
                      : QList<QUrl>{QUrl::fromLocalFile(b), QUrl::fromLocalFile(c)};
        replaced = project->loadDatasets(project->currentExperiment(), files, true, copying);
        linkedReady(session);
        project->setCurrentExperimentIndex(0);
        linkedReady(session);
        if (replaced && replacing)
            replaced = project->loadDataInto(project->currentExperiment(), QUrl::fromLocalFile(b));
        linkedReady(session);
    } else if (transition != "unchanged" && transition != "relocate")
        need(false, "The experiment replacement is a declared public boundary");
    linkedReady(session);
    if (route.startsWith("web-")) {
        session.project()->setIncludeDataOnSave("linked");
        session.save();
        openBrowserInput(session, session.project()->path(), "folder");
    }
    project = session.project();
    project->setIncludeDataOnSave(mode);
    if (route == "unsaved-folder") {
        const auto root = project->path();
        for (auto& experiment : project->project_->experiments)
            preserveLinkWhenClearingLocation(*experiment, root);
        project->project_->path.clear();
    }
    const auto destination = temp.filePath(route.contains("zip") ? "output.zip" : "output");
    if (route.startsWith("existing-")) {
        if (route.contains("zip"))
            edi::write_project_archive(project->path().toStdString(), destination.toStdString());
        else
            need(QDir().mkpath(destination),
                 "The linked save reaches an existing actual destination");
    }
    jobs.clear();
    PolicyQuestions questions(session);
    requestPolicySave(session, route, destination);
    turn();
    if (questions.count())
        questions.answer(questions.request(), mode == "all" ? "copy" : "linked");
    finishPolicyIo();
    turn();
    const auto published = publishedLinkedFolder(session, route, destination, temp);
    QJsonObject result{{"admitted", true},
                       {"replaced", replaced},
                       {"initial", initial},
                       {"sourceA", QFileInfo(a).canonicalFilePath()},
                       {"sourceB", QFileInfo(b).canonicalFilePath()},
                       {"sourcesUnchanged", image(temp.filePath("sourceA"), true) == beforeA &&
                                                image(temp.filePath("sourceB"), true) == beforeB},
                       {"published", !published.isEmpty()},
                       {"error", session.lastError()}};
    if (!published.isEmpty()) {
        result["saved"] = finalLinkedObservation(published);
        if (transition == "relocate") {
            need(QDir().rename(temp.filePath("sourceA"), temp.filePath("movedA")),
                 "The original external source physically moves before missing-data opening");
            browser = false;
            session.closeProject();
            const bool opened = session.openProject(QUrl::fromLocalFile(published));
            result["missingOpened"] = opened;
            if (opened) {
                linkedReady(session);
                project = session.project();
                result["missingMarked"] =
                    !project->property("missingDataFile").toString().isEmpty();
                const auto moved = QUrl::fromLocalFile(temp.filePath("movedA/patternA.dat"));
                bool located = false;
                const bool invoked = QMetaObject::invokeMethod(
                    project, "locateDataFile", Qt::DirectConnection, Q_RETURN_ARG(bool, located),
                    Q_ARG(edi_app::ExperimentViewModel*, project->currentExperiment()),
                    Q_ARG(QUrl, moved));
                result["located"] = invoked && located;
                linkedReady(session);
                result["missingCleared"] =
                    project->property("missingDataFile").toString().isEmpty();
                project->setIncludeDataOnSave("linked");
                const bool saved = session.save();
                result["relocatedSaved"] = saved;
                if (saved) result["relocated"] = finalLinkedObservation(session.project()->path());
                result["movedSource"] = QFileInfo(moved.toLocalFile()).canonicalFilePath();
            }
        } else if (mode == "all") {
            need(QDir().rename(temp.filePath("sourceA"), temp.filePath("movedA")),
                 "Include-all reopen deliberately removes its original linked source");
            need(QDir().rename(temp.filePath("sourceB"), temp.filePath("movedB")),
                 "Include-all reopen removes the replacement source too");
            result["withoutSources"] = finalLinkedObservation(published);
        }
    }
    browser = false;
    return result;
}
}  // namespace
