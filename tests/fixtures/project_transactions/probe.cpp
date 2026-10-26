// Observe the real Session. Only asynchronous browser I/O is held at the link boundary.
#include <QCoreApplication>
#include <QDir>
#include <QDirIterator>
#include <QElapsedTimer>
#include <QFile>
#include <QGuiApplication>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QMap>
#include <QQmlApplicationEngine>
#include <QQmlComponent>
#include <QQmlExpression>
#include <QRegularExpression>
#include <QTemporaryDir>
#include <QThread>
#include <QtQml>
#include <QtTest/QSignalSpy>
#include <bit>
#include <cstdint>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <vector>

#include "engine_setup.hpp"
// Set only the boundary's startup capability, never Session/project state.
#define private public
#include "session.hpp"
#include "web_storage.hpp"
#undef private
#include "block_text.hpp"
#include "crysta/background_estimate.hpp"
#include "edi/io.hpp"
#include "edi/parameter_walk.hpp"
#include "edi/project_archive.hpp"
#include "experiment_view_model.hpp"
#include "fit_view_model.hpp"
#include "parameter_item.hpp"
#include "pattern_model.hpp"
#include "structure_view_model.hpp"
Q_IMPORT_QML_PLUGIN(edi_appPlugin)
using namespace edi_app;
namespace {
QStringList archiveSources, archiveTargets, stageKinds;
bool browser = false;
using Image = QMap<QString, QByteArray>;
QMap<QString, Image> durable;
bool aliasPlaces = false;
bool faultArmed = false, publicationCompleted = false;
QStringList postPublicationCalls;
void fallibleBoundary(const char* name) {
    if (!faultArmed || !publicationCompleted) return;
    postPublicationCalls.append(name);
    throw std::runtime_error("Independent refusal of fallible work after durable publication");
}
void need(bool, const char*);
Image image(const QString& root) {
    Image result;
    QDirIterator files(root, QDir::Files, QDirIterator::Subdirectories);
    while (files.hasNext()) {
        const auto name = files.next();
        QFile input(name);
        need(input.open(QIODevice::ReadOnly), "Submitted snapshot files remain readable");
        result.insert(QDir(root).relativeFilePath(name), input.readAll());
    }
    return result;
}

struct Job {
    QString action, key, kind, root;
    bool recovery;
    WebStorage::Answer answer;
    Image payload;
};
std::vector<Job> jobs;
QStringList drops;
void need(bool good, const char* why) {
    if (!good) throw std::runtime_error(why);
}
void turn() {
    QCoreApplication::processEvents();
    QCoreApplication::sendPostedEvents(nullptr, QEvent::DeferredDelete);
}
void settle(Session& session) {
    QElapsedTimer clock;
    clock.start();
    while (session.project() && session.project()->calculating() && clock.elapsed() < 10000) {
        turn();
        QThread::msleep(1);
    }
    need(session.project() && !session.project()->calculating(),
         "The real project's calculation must finish before the transaction starts");
}
QString copy(const QString& input, const QString& destination) {
    std::filesystem::copy(input.toStdString(), destination.toStdString(),
                          std::filesystem::copy_options::recursive);
    return destination;
}
QString bits(double value) { return QString::number(std::bit_cast<std::uint64_t>(value), 16); }
template <typename Column>
QJsonArray numberBits(const Column& values) {
    QJsonArray out;
    for (double value : values) out.append(bits(value));
    return out;
}
QJsonObject scientificState(const edi::Project& project) {
    const auto& m = project.metadata;
    const auto text = [](const std::string& value) { return QString::fromStdString(value); };
    const auto metric = [](const std::optional<double>& value) {
        return value ? QJsonValue(bits(*value)) : QJsonValue();
    };
    QJsonObject metadata{{"name", text(m.name)},
                         {"title", text(m.title)},
                         {"description", text(m.description)},
                         {"authors", text(m.authors)},
                         {"path", text(m.path)},
                         {"created", text(m.created)},
                         {"lastModified", text(m.last_modified)},
                         {"timestamp", text(m.timestamp)}};
    QJsonArray banks;
    for (const auto& bank : project.experiments) {
        QJsonObject row{{"name", text(bank->name.value())},
                        {"inputsDigest", QString::number(bank->background_estimate_inputs, 16)},
                        {"pointsDigest", QString::number(bank->background_estimate_points, 16)},
                        {"rp", metric(bank->fit_prof_r_factor)},
                        {"rwp", metric(bank->fit_prof_wr_factor)},
                        {"chi", metric(bank->fit_chi_square)}};
        if (bank->data) {
            const auto& data = *bank->data;
            row["calculated"] = numberBits(data.intensity_calc);
            row["background"] = numberBits(data.intensity_bkg);
            row["residual"] = numberBits(data.residual);
            row["spacing"] = numberBits(data.d_spacing);
            row["components"] = numberBits(data.component_intensities_net);
            QJsonArray status;
            for (const auto& value : data.calc_status) status.append(text(value));
            row["status"] = status;
        }
        banks.append(row);
    }
    return {{"metadata", metadata}, {"banks", banks}};
}
QJsonObject shownState(ProjectViewModel& project) {
    QJsonObject shown;
    for (auto* bank : project.findChildren<ExperimentViewModel*>()) {
        auto* model = bank->pattern();
        QJsonArray values, backgrounds;
        for (int row = 0; row < model->rowCount(); ++row) {
            const auto index = model->index(row, 0);
            const auto calculated = model->data(index, PatternModel::IntensityCalcRole);
            const auto background = model->data(index, PatternModel::IntensityBkgRole);
            values.append(calculated.isValid() ? QJsonValue(bits(calculated.toDouble()))
                                               : QJsonValue());
            backgrounds.append(background.isValid() ? QJsonValue(bits(background.toDouble()))
                                                    : QJsonValue());
        }
        shown[bank->name()] = QJsonObject{
            {"calculated", values}, {"background", backgrounds}, {"stale", model->stale()}};
    }
    return shown;
}
QString preciseInput(const QString& source, const QString& destination) {
    copy(source, destination);
    const QDir structures(destination + "/structures");
    const auto names = structures.entryList({"*.edi"}, QDir::Files, QDir::Name);
    need(names.size() == 1, "The precision stimulus selects the actual authored structure");
    const QString name = structures.filePath(names.front());
    QFile file(name);
    need(file.open(QIODevice::ReadOnly), "High-precision author input exists");
    QString data = QString::fromUtf8(file.readAll());
    file.close();
    const QRegularExpression tag("(?m)^_cell\\.length_a[ \t]+[^\\s]+$");
    need(data.contains(tag), "The authored cell witness reaches its actual tag");
    data.replace(tag, "_cell.length_a 1.23456789");
    need(file.open(QIODevice::WriteOnly | QIODevice::Truncate),
         "High-precision author input is writable");
    file.write(data.toUtf8());
    return destination;
}
QJsonObject state(Session& session) {
    QJsonArray parameters;
    if (session.project()) {
        auto copy = session.project()->project();
        for (const auto& entry : edi::parameter_entries(copy)) {
            const auto& parameter = *entry.parameter;
            parameters.append(QJsonObject{
                {"path", QString::fromStdString(entry.path)},
                {"value", static_cast<double>(parameter.value)},
                {"uncertainty",
                 parameter.uncertainty ? QJsonValue(*parameter.uncertainty) : QJsonValue()},
                {"free", static_cast<bool>(parameter.free)}});
        }
    }
    return {{"name", session.project() ? session.project()->name() : QString()},
            {"modified", session.project() && session.project()->modified()},
            {"path", session.project() ? session.project()->path() : QString()},
            {"location", session.projectLocation()},
            {"needsSaveAs", session.needsSaveAs()},
            {"example", session.openedExample()},
            {"archive", session.openedArchive()},
            {"parameters", parameters},
            {"scientific",
             session.project() ? scientificState(session.project()->project()) : QJsonObject()},
            {"shown", session.project() ? shownState(*session.project()) : QJsonObject()}};
}
void finish(size_t index, bool ok, const QString& input = {}, bool pump = true) {
    need(index < jobs.size(), "A completion must belong to an actually started I/O request");
    Job job = jobs[index];
    jobs[index].answer = {};
    need(bool(job.answer), "The fixture must deliver each terminal callback once");
    WebStorageAnswer answer;
    answer.ok = ok;
    answer.key = job.key;
    answer.kind = job.kind;
    answer.name = input.isEmpty() ? job.key : QFileInfo(input).fileName();
    answer.message = "Independent boundary refusal";
    if (!input.isEmpty()) answer.path = copy(input, job.root + "/" + QFileInfo(input).fileName());
    if (ok && job.action == "write" && !job.recovery)
        durable[aliasPlaces ? QString("working") : job.key] = job.payload;
    if (faultArmed && ok && job.action == "write" && !job.recovery) publicationCompleted = true;
    job.answer(answer);
    if (pump) turn();
}
void start(Session& session, const QString& route, const QString& key) {
    if (route == "Open")
        session.openWebProject("folder");
    else
        session.openStoredProject(key, route == "recovery");
}
QJsonObject overlap(const QString& source, const QString& first, const QString& second,
                    bool newerFirst, bool edit, bool replacement,
                    const QString& replacementKind = "desktop") {
    QTemporaryDir temp;
    Session session;
    need(session.openProject(QUrl::fromLocalFile(copy(source, temp.filePath("initial")))),
         "Overlap starts with an actual project");
    settle(session);
    jobs.clear();
    browser = true;
    // Install a browser place by opening through the actual receiver first.
    session.openWebProject("folder");
    finish(0, true, source);
    jobs.clear();
    settle(session);
    const QString initial = session.project()->name();
    QStringList loadErrors;
    QObject::connect(&session, &Session::loadFailed, &session,
                     [&](const QString& error) { loadErrors.append(error); });
    start(session, first, "older");
    need(jobs.size() == 1, "The older request must reach the actual storage boundary");
    if (!edit && !replacement) {
        start(session, second, "newer");
        need(jobs.size() == 2, "Both requests must be outstanding together");
    }
    if (edit) session.project()->setName("edited-while-reading");
    if (replacement) {
        browser = false;
        if (replacementKind == "example")
            need(session.openExample("pd-neut-cwl_cosio-d20"),
                 "The example replacement really opens");
        else if (replacementKind == "new")
            need(session.createProject("new-project", "", temp.filePath("new-project")),
                 "The New-project replacement really creates a project");
        else
            need(session.openProject(
                     QUrl::fromLocalFile(copy(source, temp.filePath("replacement")))),
                 "The desktop replacement really opens");
        session.project()->setName("different-project");
        browser = true;
    }
    const QString olderRoot = jobs[0].root;
    QJsonArray after;
    const QString a = copy(source, temp.filePath("older")),
                  b = copy(source, temp.filePath("newer"));
    auto rename = [](const QString& folder, const QByteArray& name) {
        QFile file(folder + "/project.edi");
        need(file.open(QIODevice::ReadOnly), "Fixture input is readable");
        auto text = file.readAll();
        file.close();
        auto lines = text.split('\n');
        bool found = false;
        for (auto& line : lines)
            if (line.startsWith("_metadata.name ")) {
                line = "_metadata.name " + name;
                found = true;
            }
        need(found, "The independent input has exactly the named metadata field");
        need(file.open(QIODevice::WriteOnly | QIODevice::Truncate),
             "Fixture input accepts its independent name");
        file.write(lines.join('\n'));
    };
    rename(a, "older");
    rename(b, "newer");
    if (edit || replacement) {
        finish(0, true, a);
        after.append(state(session));
    } else {
        finish(newerFirst ? 1 : 0, true, newerFirst ? b : a);
        after.append(state(session));
        finish(newerFirst ? 0 : 1, true, newerFirst ? a : b);
        after.append(state(session));
    }
    browser = false;
    return {{"first", first},
            {"second", second},
            {"newerFirst", newerFirst},
            {"edit", edit},
            {"replacement", replacement},
            {"replacementKind", replacementKind},
            {"initial", initial},
            {"after", after},
            {"olderRootRemoved", !QFileInfo::exists(olderRoot)},
            {"loadErrors", QJsonArray::fromStringList(loadErrors)}};
}
QJsonObject browserSave(const QString& source, const QString& kind, bool ok, bool editedAgain,
                        bool moving, bool unavailable, bool discard) {
    QTemporaryDir temp;
    Session session;
    browser = false;
    need(session.openProject(QUrl::fromLocalFile(copy(source, temp.filePath("input")))),
         "Save starts with a real project");
    settle(session);
    browser = true;
    WebStorage::instance()->usable_ = true;
    jobs.clear();
    drops.clear();
    session.openWebProject("folder");
    jobs[0].kind = kind;
    finish(0, true, source);
    settle(session);
    jobs.clear();
    drops.clear();
    QSignalSpy finished(&session, SIGNAL(webSaveFinished(bool)));
    int success = 0, errors = 0;
    QObject::connect(&session, &Session::webSaved, &session, [&](const QString&) { ++success; });
    QObject::connect(&session, &Session::webSaveFailed, &session,
                     [&](const QString&) { ++errors; });
    session.project()->setName("edited-before-save");
    settle(session);
    const auto before = state(session);
    if (unavailable) WebStorage::instance()->usable_ = false;
    bool returned = false;
    if (moving) {
        session.saveWebProjectAs(kind, false);
        need(jobs.size() == 1 && jobs[0].action == "pickSave",
             "Moving Save as must reach its real picker");
        finish(0, true);
    } else
        returned = session.save();
    QJsonObject pending = state(session);
    pending["success"] = success;
    pending["drops"] = drops.size();
    pending["returned"] = returned;
    const auto write = std::find_if(jobs.begin(), jobs.end(), [](const Job& job) {
        return job.action == "write" && !job.recovery;
    });
    const int index = write == jobs.end() ? -1 : int(write - jobs.begin());
    QJsonObject newer;
    if (index >= 0) {
        if (editedAgain) {
            session.project()->setName("newer-unsaved-edit");
            session.keepChanges();
            newer = state(session);
        }
        if (discard) session.discardKeptChanges();
        finish(size_t(index), ok);
    }
    const auto after = state(session);
    QJsonArray finishedValues;
    for (const auto& arguments : finished) finishedValues.append(arguments[0].toBool());
    browser = false;
    WebStorage::instance()->usable_ = true;
    return {{"kind", kind},
            {"ok", ok},
            {"editedAgain", editedAgain},
            {"moving", moving},
            {"unavailable", unavailable},
            {"discard", discard},
            {"before", before},
            {"pending", pending},
            {"newer", newer},
            {"after", after},
            {"success", success},
            {"errors", errors},
            {"drops", drops.size()},
            {"writes", index >= 0},
            {"finished", finishedValues}};
}
QJsonObject continuation(const QString& source, bool ok, bool changed, bool unavailable,
                         bool quit) {
    browser = true;
    WebStorage::instance()->usable_ = true;
    jobs.clear();
    drops.clear();
    QTemporaryDir temp;
    QQmlEngine engine;
    edi_app::configure_engine(engine);
    QQmlComponent component(&engine);
    component.loadFromModule("edi.app", "Main");
    std::unique_ptr<QObject> window(component.create());
    need(bool(window), qPrintable(component.errorString()));
    window->setProperty("visible", true);
    auto* session = engine.singletonInstance<Session*>("edi.app", "Session");
    need(
        session && session->openProject(QUrl::fromLocalFile(copy(source, temp.filePath("input")))),
        "Continuation starts with a real project");
    settle(*session);
    session->project()->setName("continuation-unsaved");
    QObject* dialog = window->findChild<QObject*>("unsavedChanges");
    need(dialog != nullptr, "The actual Main unsaved-changes dialog must exist");
    if (quit) {
        need(QMetaObject::invokeMethod(window.get(), "close"),
             "The actual close request must be accepted by the app window");
    } else {
        QQmlExpression ask(qmlContext(window.get()), window.get(),
                           "AppState.afterChanges(function() { Session.closeProject(); })");
        ask.evaluate();
        need(!ask.hasError(), qPrintable(ask.error().toString()));
    }
    turn();
    need(dialog->property("visible").toBool(),
         "Replacement and quit must reach the actual unsaved-changes dialog");
    if (unavailable) WebStorage::instance()->usable_ = false;
    need(QMetaObject::invokeMethod(dialog, "accepted"),
         "The actual dialog Save handler must execute");
    turn();
    auto pending = state(*session);
    pending["visible"] = window->property("visible").toBool();
    pending["quitting"] = window->property("quitting").toBool();
    const bool edited = changed && session->project();
    if (edited) session->project()->setName("changed-after-Save-choice");
    const auto write = std::find_if(jobs.begin(), jobs.end(), [](const Job& job) {
        return job.action == "write" && !job.recovery;
    });
    if (write != jobs.end()) finish(size_t(write - jobs.begin()), ok);
    for (int index = 0; index < 8; ++index) turn();
    auto after = state(*session);
    after["visible"] = window->property("visible").toBool();
    after["quitting"] = window->property("quitting").toBool();
    after["question"] = dialog->property("visible").toBool();
    window->setProperty("quitting", true);
    window->setProperty("visible", false);
    session->closeProject();
    browser = false;
    WebStorage::instance()->usable_ = true;
    return {{"ok", ok},        {"changed", changed}, {"unavailable", unavailable},
            {"quit", quit},    {"pending", pending}, {"after", after},
            {"edited", edited}};
}
QJsonObject archiveLink(const QString& source, const QString& kind) {
    QTemporaryDir temp;
    const QString folder = copy(source, temp.filePath("input"));
    QDir().mkpath(folder + "/reports");
    QFile report(folder + "/reports/original.html");
    need(report.open(QIODevice::WriteOnly), "An independent carried report must exist");
    report.write("independent report bytes\n");
    report.close();
    QFile external(temp.filePath("external.txt"));
    need(external.open(QIODevice::WriteOnly), "An independent external linked file must exist");
    external.write("independent external bytes\n");
    external.close();
    const std::string link = (folder + "/reports/alias.html").toStdString();
    if (kind == "internal")
        std::filesystem::create_symlink("original.html", link);
    else if (kind == "external")
        std::filesystem::create_symlink(external.fileName().toStdString(), link);
    else if (kind == "directory")
        std::filesystem::create_directory_symlink(folder.toStdString(), link);
    else
        std::filesystem::create_symlink("missing.html", link);
    bool ok = false;
    QString error;
    const QString destination = temp.filePath("result.zip");
    try {
        edi::write_project_archive(folder.toStdString(), destination.toStdString());
        ok = true;
    } catch (const std::exception& refusal) {
        error = QString::fromUtf8(refusal.what());
    }
    QFile archive(destination);
    const QByteArray data = archive.open(QIODevice::ReadOnly) ? archive.readAll() : QByteArray();
    return {{"kind", kind},
            {"ok", ok},
            {"error", error},
            {"archive", QString::fromLatin1(data.toBase64())}};
}
QJsonObject desktopSave(const QString& source, const QString& origin, const QString& target) {
    browser = false;
    QTemporaryDir temp;
    Session session;
    QString input = copy(source, temp.filePath("input"));
    if (origin == "zip") {
        QString zip = temp.filePath("original.zip");
        edi::write_project_archive(input.toStdString(), zip.toStdString());
        input = zip;
    }
    if (origin == "readonly") QFile::setPermissions(input, QFile::ReadOwner | QFile::ExeOwner);
    if (origin == "example")
        need(session.openExample("pd-neut-cwl_cosio-d20"),
             "The origin must be the real bundled example");
    else
        need(session.openProject(QUrl::fromLocalFile(input)),
             "The desktop origin must really open");
    settle(session);
    session.project()->currentStructure()->cell()->lengthA()->setValue(4.123456789);
    session.project()->setName("unsaved-refusal-edit");
    settle(session);
    const auto before = state(session);
    // ENOTDIR and an existing directory at a ZIP filename are reliable even as root.
    QFile blocker(temp.filePath("blocker"));
    need(blocker.open(QIODevice::WriteOnly), "Create an independent refusal boundary");
    blocker.write("keep");
    blocker.close();
    const QString bad =
        target == "folder" ? blocker.fileName() + "/child" : temp.filePath("occupied.zip");
    if (target != "folder") QDir().mkpath(bad);
    bool result = false;
    if (target == "ordinary") {
        QFile::remove(input);
        QDir().mkpath(input);
        result = session.save();
    } else
        result = session.saveProjectAs(QUrl::fromLocalFile(bad), target == "zip", false);
    auto refused = state(session);
    const QString error = session.lastError();
    const QString retry =
        target == "folder" ? temp.filePath("retry-folder") : temp.filePath("retry.zip");
    const bool retryOk =
        session.saveProjectAs(QUrl::fromLocalFile(retry), target != "folder", false);
    auto afterRetry = state(session);
    session.closeProject();
    const bool reopened = session.openProject(QUrl::fromLocalFile(retry));
    if (origin == "readonly")
        QFile::setPermissions(input, QFile::ReadOwner | QFile::WriteOwner | QFile::ExeOwner);
    return {{"origin", origin},
            {"target", target},
            {"before", before},
            {"result", result},
            {"refused", refused},
            {"error", error},
            {"retryOk", retryOk},
            {"afterRetry", afterRetry},
            {"reopened", reopened},
            {"reopenedName", reopened ? session.project()->name() : QString()}};
}
std::size_t nextWrite(std::size_t begin) {
    for (std::size_t i = begin; i < jobs.size(); ++i)
        if (jobs[i].action == "write" && !jobs[i].recovery && jobs[i].answer) return i;
    return jobs.size();
}
std::size_t beginMove(Session& session, const QString& kind, bool isCopy = false) {
    const std::size_t before = jobs.size();
    session.saveWebProjectAs(kind, isCopy);
    if (jobs.size() == before) return jobs.size();
    need(jobs[before].action == "pickSave",
         "A moving save starts at the actual destination picker");
    finish(before, true);
    return nextWrite(before + 1);
}
void openBrowserInput(Session& session, const QString& source, const QString& kind) {
    browser = false;
    need(session.openProject(QUrl::fromLocalFile(source)),
         "The independent precision input opens");
    settle(session);
    browser = true;
    WebStorage::instance()->usable_ = true;
    jobs.clear();
    drops.clear();
    session.openStoredProject("initial", false);
    need(jobs.size() == 1, "Opening reaches the held browser read");
    jobs[0].kind = kind;
    finish(0, true, source);
    settle(session);
    jobs.clear();
    drops.clear();
}
QJsonObject saveConflict(const QString& source, const QStringList& spec) {
    need(spec.size() == 8,
         "A save conflict declares kind, second intent, outcomes, order, edit and replacement");
    const QString kind = spec[1], second = spec[2], replacement = spec[7];
    const bool across = spec[0].startsWith("save-replaced-");
    const bool alias = spec[0].startsWith("save-alias-") || across;
    const QString firstAction = alias ? spec[0].section('-', 2) : QString("move");
    const bool firstOk = spec[3] == "1", secondFirst = spec[4] == "1", secondOk = spec[5] == "1",
               edit = spec[6] == "1";
    QTemporaryDir temp;
    Session session;
    const QString input = preciseInput(source, temp.filePath("precision-input"));
    openBrowserInput(session, input, alias ? kind : QString("folder"));
    aliasPlaces = alias;
    durable.clear();
    if (alias) durable["working"] = image(input);
    if (alias) session.project()->setName("first-submitted-revision");
    settle(session);
    QStringList messages;
    QObject::connect(&session, &Session::webSaved, &session,
                     [&](const QString& text) { messages.append(text); });
    QObject::connect(&session, &Session::webSaveFailed, &session,
                     [&](const QString& text) { messages.append(text); });
    const auto before = state(session);
    std::size_t first;
    if (firstAction == "save") {
        const auto start = jobs.size();
        session.save();
        first = nextWrite(start);
    } else
        first = beginMove(session, kind, firstAction == "copy");
    need(first < jobs.size(), "The first moving save reaches an actual held write");
    auto pending = state(session);
    if (edit) {
        session.project()->setName("edited-during-moving-save");
        session.project()->currentStructure()->cell()->lengthA()->setValue(1.45678901);
        settle(session);
        session.keepChanges();
    }
    const auto edited = state(session);
    if (replacement != "none") {
        browser = false;
        if (replacement == "Recent" || replacement == "Open" || replacement == "recovery") {
            browser = true;
            const auto read = jobs.size();
            start(session, replacement, "new-key-for-the-same-physical-place");
            need(jobs.size() == read + 1, "Project replacement reaches the actual browser read");
            jobs[read].kind = kind;
            finish(read, true, input);
        } else if (replacement == "example")
            need(session.openExample("pd-neut-cwl_cosio-d20"),
                 "A real example supersedes the save");
        else if (replacement == "new")
            need(session.createProject("replacement", "", temp.filePath("new")),
                 "A real New project supersedes the save");
        else
            need(session.openProject(
                     QUrl::fromLocalFile(copy(source, temp.filePath("replacement")))),
                 "A real desktop open supersedes the save");
        settle(session);
        browser = true;
    }
    if (across) {
        session.project()->setName("edited-replacement-revision");
        session.project()->currentStructure()->cell()->lengthA()->setValue(1.45678901);
        settle(session);
    }
    const auto replacementBefore = state(session);
    const auto countBefore = jobs.size();
    bool secondReturned = false;
    std::size_t secondWrite = jobs.size();
    if (!edit && (replacement == "none" || across)) {
        if (second == "save") {
            secondReturned = session.save();
            secondWrite = nextWrite(countBefore);
        } else
            secondWrite = beginMove(session, alias ? kind : second.mid(5), second == "copy");
    }
    const auto afterSecond = state(session);
    const auto secondJobs = jobs.size() - countBefore;
    const bool acceptedSecond = secondWrite < jobs.size() && jobs[secondWrite].action == "write";
    const QString secondAction = second.section('-', 0, 0);
    QStringList remaining;
    for (const auto& candidate : {"save", "move", "copy"})
        if (QString(candidate) != firstAction && QString(candidate) != secondAction)
            remaining.append(candidate);
    const QString third = remaining.isEmpty()
                              ? QString("save")
                              : remaining[remaining.size() > 1 && secondOk ? 1 : 0];
    const auto thirdStart = jobs.size();
    std::size_t thirdWrite = jobs.size();
    bool thirdReturned = false;
    if (alias && !edit && (replacement == "none" || across)) {
        if (third == "save") {
            thirdReturned = session.save();
            thirdWrite = nextWrite(thirdStart);
        } else
            thirdWrite = beginMove(session, kind == "folder" ? "zip" : "folder", third == "copy");
    }
    const auto afterThird = state(session);
    const auto thirdJobs = jobs.size() - thirdStart;
    const bool acceptedThird = thirdWrite < jobs.size() && jobs[thirdWrite].action == "write";

    QJsonArray after;
    auto done = [&](std::size_t index, bool ok) {
        finish(index, ok);
        settle(session);
        after.append(state(session));
    };
    if (acceptedSecond && secondFirst) done(secondWrite, secondOk);
    if (acceptedThird && secondFirst) done(thirdWrite, true);
    done(first, firstOk);
    if (acceptedSecond && !secondFirst) done(secondWrite, secondOk);
    if (acceptedThird && !secondFirst) done(thirdWrite, true);
    const auto completed = state(session);
    const auto dropsAfterFirst = drops;
    const auto messagesAfterFirst = messages;
    const auto durableProjection = [&](const QString& directory) {
        QJsonArray parameters;
        if (!alias || !durable.contains("working")) return parameters;
        const auto root = temp.filePath(directory);
        for (auto file = durable["working"].cbegin(); file != durable["working"].cend(); ++file) {
            const auto path = root + "/" + file.key();
            QDir().mkpath(QFileInfo(path).absolutePath());
            QFile out(path);
            need(out.open(QIODevice::WriteOnly), "Materialize the acknowledged boundary payload");
            out.write(file.value());
        }
        auto reopened = edi::load_project(root.toStdString());
        for (const auto& entry : edi::parameter_entries(reopened)) {
            const auto& parameter = *entry.parameter;
            parameters.append(QJsonObject{
                {"path", QString::fromStdString(entry.path)},
                {"value", static_cast<double>(parameter.value)},
                {"uncertainty",
                 parameter.uncertainty ? QJsonValue(*parameter.uncertainty) : QJsonValue()},
                {"free", static_cast<bool>(parameter.free)}});
        }
        return parameters;
    };
    const auto firstDurable = durableProjection("durable-at-first");
    const auto nextStart = jobs.size();
    bool nextReturned = false;
    bool nextReached = false;
    if (replacement == "none" || across) {
        WebStorage::instance()->usable_ = true;
        session.project()->setName("next-save-after-settlement");
        settle(session);
        nextReturned = session.save();
        const auto next = nextWrite(nextStart);
        nextReached = next < jobs.size();
        if (nextReached) finish(next, true);
        settle(session);
    }
    const auto final = state(session);
    const auto durableParameters = durableProjection("durable-after-next");
    aliasPlaces = false;
    browser = false;
    return {{"kind", kind},
            {"second", second},
            {"firstAction", firstAction},
            {"durableParameters", durableParameters},
            {"firstDurableParameters", firstDurable},
            {"firstOk", firstOk},
            {"secondFirst", secondFirst},
            {"secondOk", secondOk},
            {"edit", edit},
            {"replacement", replacement},
            {"before", before},
            {"pending", pending},
            {"edited", edited},
            {"replacementBefore", replacementBefore},
            {"afterSecond", afterSecond},
            {"secondJobs", int(secondJobs)},
            {"third", third},
            {"thirdJobs", int(thirdJobs)},
            {"thirdReturned", thirdReturned},
            {"afterThird", afterThird},
            {"secondReturned", secondReturned},
            {"after", after},
            {"completed", completed},
            {"messages", QJsonArray::fromStringList(messagesAfterFirst)},
            {"drops", QJsonArray::fromStringList(dropsAfterFirst)},
            {"nextReturned", nextReturned},
            {"nextReached", nextReached},
            {"final", final}};
}
QJsonObject rollback(const QString& source, const QStringList& spec) {
    need(spec.size() == 4, "A rollback declares route, browser place and clean or dirty start");
    const QString route = spec[1], kind = spec[2];
    const bool dirty = spec[3] == "dirty";
    QTemporaryDir temp;
    Session session;
    QString input = preciseInput(source, temp.filePath("precision-input"));
    browser = false;
    const bool web = route.startsWith("web-");
    if (web)
        openBrowserInput(session, input, kind);
    else {
        if (route == "zip-save") {
            const QString archive = temp.filePath("original.zip");
            edi::write_project_archive(input.toStdString(), archive.toStdString());
            input = archive;
        }
        need(session.openProject(QUrl::fromLocalFile(input)),
             "The rollback precision input really opens");
        settle(session);
    }
    if (dirty) session.project()->setName("dirty-before-refusal");
    settle(session);
    const auto before = state(session);
    bool returned = false;
    QString blocked;
    if (web) {
        const auto start = jobs.size();
        if (route == "web-move")
            beginMove(session, kind);
        else
            returned = session.save();
        const auto write = nextWrite(start);
        need(write < jobs.size(), "Publication refusal reaches the held real write callback");
        finish(write, false);
    } else if (route == "zip-save") {
        need(QFile::remove(input), "The actual archive becomes independently unwritable");
        need(QDir().mkpath(input),
             "An existing directory refuses archive replacement even as root");
        blocked = input;
        returned = session.save();
    } else {
        blocked = temp.filePath("missing-parent/result.zip");
        if (route == "zip-as-blocked") {
            QFile blocker(temp.filePath("blocker"));
            need(blocker.open(QIODevice::WriteOnly),
                 "An independent non-directory parent is created");
            blocker.write("keep");
            blocker.close();
            blocked = blocker.fileName() + "/result.zip";
        }
        returned = session.saveProjectAs(QUrl::fromLocalFile(blocked), true, false);
    }
    settle(session);
    const auto refused = state(session);
    bool retry = false;
    if (web) {
        WebStorage::instance()->usable_ = true;
        const auto start = jobs.size();
        if (route == "web-move")
            beginMove(session, kind);
        else
            retry = session.save();
        const auto write = nextWrite(start);
        if (write < jobs.size()) {
            finish(write, true);
            retry = true;
        }
    } else if (route == "zip-save") {
        need(QDir(blocked).removeRecursively(), "The independent archive obstruction is removed");
        retry = session.save();
    } else
        retry =
            session.saveProjectAs(QUrl::fromLocalFile(temp.filePath("retry.zip")), true, false);
    settle(session);
    const auto afterRetry = state(session);
    browser = false;
    return {{"route", route},       {"kind", kind},
            {"dirty", dirty},       {"before", before},
            {"returned", returned}, {"refused", refused},
            {"retry", retry},       {"afterRetry", afterRetry}};
}
QJsonObject afterPublication(const QString& source, const QStringList& spec) {
    need(spec.size() == 4,
         "A publication observation declares route, kind and initial modified state");
    const QString route = spec[1], kind = spec[2];
    const bool web = route.startsWith("web-"), dirty = spec[3] == "dirty";
    QTemporaryDir temp;
    Session session;
    QString input = preciseInput(source, temp.filePath("precision-input"));
    if (web)
        openBrowserInput(session, input, kind);
    else {
        browser = false;
        if (route == "zip-save") {
            const QString archive = temp.filePath("original.zip");
            edi::write_project_archive(input.toStdString(), archive.toStdString());
            input = archive;
        }
        need(session.openProject(QUrl::fromLocalFile(input)),
             "The publication input really opens");
        settle(session);
    }
    if (dirty) session.project()->setName("dirty-publication-witness");
    settle(session);
    const auto before = state(session);
    const QString originalFolder = session.project()->path();
    const auto originalBytes = image(originalFolder);
    jobs.clear();
    archiveSources.clear();
    archiveTargets.clear();
    durable.clear();
    postPublicationCalls.clear();
    publicationCompleted = false;
    faultArmed = true;
    bool returned = false;
    QString exception;
    const QString destination = temp.filePath("published.zip");
    try {
        if (web) {
            const auto start = jobs.size();
            returned =
                route == "web-save" ? session.save() : beginMove(session, kind) < jobs.size();
            const auto write = nextWrite(start);
            need(write < jobs.size(), "A valid browser publication reaches its real held write");
            finish(write, true, {}, false);
        } else if (route == "zip-save")
            returned = session.save();
        else
            returned = session.saveProjectAs(QUrl::fromLocalFile(destination), true, false);
        settle(session);  // queued publication work is covered by the same armed refusal
    } catch (const std::exception& error) {
        exception = QString::fromUtf8(error.what());
    }
    faultArmed = false;
    settle(session);
    const auto after = state(session);
    const auto calls = postPublicationCalls;
    const bool ownFolderExists = QFileInfo::exists(session.project()->path() + "/project.edi");
    bool ownFolderReadable = false;
    try {
        auto own = edi::load_project(session.project()->path().toStdString());
        ownFolderReadable = !own.structures.empty();
    } catch (...) {
    }
    QString publishedRoot;
    if (web && !durable.isEmpty()) {
        publishedRoot = temp.filePath("published-browser-check");
        const auto payload = durable.constBegin().value();
        for (auto f = payload.cbegin(); f != payload.cend(); ++f) {
            const QString path = publishedRoot + "/" + f.key();
            QDir().mkpath(QFileInfo(path).absolutePath());
            QFile out(path);
            need(out.open(QIODevice::WriteOnly),
                 "The independently published payload is materialized");
            out.write(f.value());
        }
    } else if (!web && publicationCompleted) {
        QFile archive(route == "zip-save" ? input : destination);
        need(archive.open(QIODevice::ReadOnly), "The actual published ZIP is readable");
        publishedRoot = QString::fromStdString(edi::unpack_project_archive(
            archive.readAll().toStdString(), temp.filePath("published-zip-check").toStdString()));
    }
    QJsonArray publishedParameters;
    if (!publishedRoot.isEmpty()) {
        auto saved = edi::load_project(publishedRoot.toStdString());
        for (const auto& entry : edi::parameter_entries(saved)) {
            const auto& p = *entry.parameter;
            publishedParameters.append(QJsonObject{
                {"path", QString::fromStdString(entry.path)},
                {"value", double(p.value)},
                {"uncertainty", p.uncertainty ? QJsonValue(*p.uncertainty) : QJsonValue()},
                {"free", bool(p.free)}});
        }
    }
    browser = false;
    return {{"before", before},
            {"after", after},
            {"returned", returned},
            {"exception", exception},
            {"published", publicationCompleted},
            {"calls", QJsonArray::fromStringList(calls)},
            {"ownFolderExists", ownFolderExists},
            {"ownFolderReadable", ownFolderReadable},
            {"publishedParameters", publishedParameters},
            {"snapshotMatches",
             !publishedRoot.isEmpty() && image(publishedRoot) == image(session.project()->path())},
            {"oldFolderUnchanged", image(originalFolder) == originalBytes}};
}
QJsonValue optionalNumber(const std::optional<double>& value) {
    return value ? QJsonValue(bits(*value)) : QJsonValue();
}
QJsonObject backgroundState(const edi::ExperimentBase& bank) {
    QJsonArray points, terms;
    for (const auto& p : bank.background)
        points.append(QJsonObject{{"id", QString::fromStdString(p->id.value())},
                                  {"position", bits(p->position)},
                                  {"value", bits(p->intensity.value)},
                                  {"su", optionalNumber(p->intensity.uncertainty)},
                                  {"free", bool(p->intensity.free)}});
    for (const auto& p : bank.background_terms)
        terms.append(QJsonObject{{"id", QString::fromStdString(p->id.value())},
                                 {"order", int(p->order)},
                                 {"value", bits(p->coef.value)},
                                 {"su", optionalNumber(p->coef.uncertainty)},
                                 {"free", bool(p->coef.free)}});
    const auto text = [](const std::optional<std::string>& value) {
        return value ? QJsonValue(QString::fromStdString(*value)) : QJsonValue();
    };
    return {{"type", QString::fromStdString(bank.background_type)},
            {"points", points},
            {"terms", terms},
            {"origin", optionalNumber(bank.background_origin)},
            {"minimum", optionalNumber(bank.background_x_min)},
            {"maximum", optionalNumber(bank.background_x_max)},
            {"mode", text(bank.background_estimate_mode)},
            {"method", text(bank.background_estimate_method)},
            {"width", optionalNumber(bank.background_estimate_width)},
            {"smoothness", optionalNumber(bank.background_estimate_smoothness)},
            {"tolerance", optionalNumber(bank.background_estimate_tolerance)},
            {"inPeaks", text(bank.background_estimate_in_peaks)},
            {"useModel", text(bank.background_estimate_use_model)},
            {"nPoints", bank.background_estimate_n_points
                            ? QJsonValue(*bank.background_estimate_n_points)
                            : QJsonValue()},
            {"maxTerms", bank.background_estimate_max_terms
                             ? QJsonValue(*bank.background_estimate_max_terms)
                             : QJsonValue()},
            {"inputs", QString::number(bank.background_estimate_inputs, 16)},
            {"pointsDigest", QString::number(bank.background_estimate_points, 16)}};
}
auto namedBank(const edi::Project& project, const char* name) {
    for (const auto& bank : project.experiments)
        if (bank->name.value() == name) return bank;
    throw std::runtime_error("The authored mixed-bank project retains both named banks");
}
bool pointsCoherent(const edi::ExperimentBase& bank) {
    std::vector<crysta::BackgroundPointValues> points;
    if (bank.background_type == "line-segment") {
        for (const auto& point : bank.background)
            points.push_back({point->id.value(), point->position, point->intensity.value,
                              point->intensity.free});
    } else {
        for (const auto& term : bank.background_terms)
            points.push_back({term->id.value(), static_cast<double>(int(term->order)),
                              term->coef.value, term->coef.free});
    }
    return bank.background_estimate_points == crysta::background_points_digest(points);
}
QJsonObject mixedSave(const QString& source, bool web) {
    QTemporaryDir temp;
    browser = web;
    auto core = edi::load_project(copy(source, temp.filePath("input")).toStdString());
    auto due = namedBank(core, "due");
    const auto mode = due->background_estimate_mode;
    const auto origin = due->background_origin;
    const auto minimum = due->background_x_min, maximum = due->background_x_max;
    const auto inputs = due->background_estimate_inputs, points = due->background_estimate_points;
    // Prepare an already-open model through the public model, without an opening Auto estimate.
    due->background_estimate_mode = "manual";
    // Opening preview is deliberately valid Manual state. Restore the authored
    // absent Auto constants before the actual save stimulus and its snapshot.
    if (due->background_type == "polynomial" && !origin) due->background_origin = 0.;
    if (due->background_type == "chebyshev" && (!minimum || !maximum)) {
        due->background_x_min = 10.;
        due->background_x_max = 60.;
    }
    ProjectViewModel project(std::move(core), nullptr);
    QElapsedTimer clock;
    clock.start();
    while (project.calculating() && clock.elapsed() < 10000) {
        turn();
        QThread::msleep(1);
    }
    need(!project.calculating(), "Initial Manual preview completes before the save stimulus");
    due->background_estimate_mode = mode;
    due->background_origin = origin;
    due->background_x_min = minimum;
    due->background_x_max = maximum;
    due->background_estimate_inputs = inputs;
    due->background_estimate_points = points;
    const auto before = backgroundState(*due);
    const auto shownBefore = shownState(project);
    const auto scientificBefore = scientificState(project.project());
    const QString output = temp.filePath("saved");
    const QString error = project.saveTo(output);
    const auto immediate = backgroundState(*namedBank(project.project(), "due"));
    clock.restart();
    while (project.calculating() && clock.elapsed() < 10000) {
        turn();
        QThread::msleep(1);
    }
    need(!project.calculating(), "The save's publication preview finishes");
    auto reopened = edi::load_project(output.toStdString());
    QFile analysis(output + "/analysis/analysis.edi");
    need(analysis.open(QIODevice::ReadOnly), "The save writes its actual analysis record");
    const auto analysisText = QString::fromUtf8(analysis.readAll());
    QJsonArray liveCurrent, fileCurrent, freshCurrent, liveInputs;
    const auto currentBank = namedBank(project.project(), "current");
    if (currentBank->background_type == "line-segment")
        for (const auto& point : currentBank->background)
            liveInputs.append(double(point->intensity.value));
    else
        for (const auto& term : currentBank->background_terms)
            liveInputs.append(double(term->coef.value));
    const auto currentValues = [](const edi::Project& p) {
        QJsonArray out;
        const auto& bank = namedBank(p, "current");
        if (bank->data)
            for (double value : bank->data->intensity_calc) out.append(value);
        return out;
    };
    liveCurrent = currentValues(project.project());
    fileCurrent = currentValues(reopened);
    for (std::size_t i = 0; i < reopened.experiments.size(); ++i)
        if (reopened.experiments[i]->name.value() == "due") {
            reopened.experiments.erase_at(i);
            break;
        }
    reopened.refresh_calculated_pattern();
    freshCurrent = currentValues(reopened);
    const auto after = backgroundState(*namedBank(project.project(), "due"));
    auto exactFile = edi::load_project(output.toStdString());
    browser = false;
    return {{"error", error},
            {"before", before},
            {"immediate", immediate},
            {"after", after},
            {"file", backgroundState(*namedBank(exactFile, "due"))},
            {"livePointsCoherent", pointsCoherent(*namedBank(project.project(), "due"))},
            {"filePointsCoherent", pointsCoherent(*namedBank(exactFile, "due"))},
            {"shownBefore", shownBefore},
            {"shownAfter", shownState(project)},
            {"scientificBefore", scientificBefore},
            {"scientificAfter", scientificState(project.project())},
            {"inputs", liveInputs},
            {"liveCurrent", liveCurrent},
            {"fileCurrent", fileCurrent},
            {"freshCurrent", freshCurrent},
            {"fileScience", scientificState(exactFile)},
            {"freshScience", scientificState(reopened)},
            {"analysis", analysisText}};
}
QJsonObject exactFields(const QString& source) {
    QTemporaryDir temp;
    browser = false;
    QQmlEngine engine;
    edi_app::configure_engine(engine);
    QQmlComponent main(&engine);
    main.loadFromModule("edi.app", "Main");
    std::unique_ptr<QObject> window(main.create());
    need(bool(window), qPrintable(main.errorString()));
    auto* session = engine.singletonInstance<Session*>("edi.app", "Session");
    need(
        session && session->openProject(QUrl::fromLocalFile(copy(source, temp.filePath("input")))),
        "Exact field input opens through the actual Session");
    settle(*session);
    need(session->saveProjectAs(QUrl::fromLocalFile(temp.filePath("saved")), false, false),
         "The exact field gate reaches actual Save as and adoption");
    settle(*session);
    QJsonArray rows;
    for (auto* item : session->project()->findChildren<ParameterItem*>()) {
        if (!(item->uid() == "instrument.setup_twotheta_bank" ||
              (item->blockName() == "phase" &&
               (item->rowLabel() == "A" || item->category() == "cell"))))
            continue;
        QQmlComponent field(&engine,
                            QUrl("qrc:/qt/qml/edi/app/qml/Components/ParameterField.qml"));
        std::unique_ptr<QObject> native(
            field.createWithInitialProperties({{"item", QVariant::fromValue(item)}}));
        need(bool(native), qPrintable(field.errorString()));
        rows.append(QJsonObject{{"uid", item->uid()},
                                {"name", item->name()},
                                {"row", item->rowLabel()},
                                {"block", item->blockName()},
                                {"value", item->value()},
                                {"fileValue", item->fileValue()},
                                {"fileSu", item->fileSu()},
                                {"text", native->property("text").toString()},
                                {"editText", native->property("editText").toString()}});
    }
    return {{"fields", rows},
            {"structureText", session->project()->currentStructure()->text()->text()},
            {"experimentText", session->project()->currentExperiment()->text()->text()}};
}
QJsonObject fitPublication(const QString& source, const QStringList& spec) {
    need(spec.size() == 3, "Fit/save observations declare route and timing");
    const QString route = spec[1], moment = spec[2];
    const bool web = route.startsWith("web-");
    const QString kind = route.endsWith("zip")       ? "zip"
                         : route.endsWith("browser") ? "browser"
                                                     : "folder";
    const bool isCopy = route.contains("copy");
    QTemporaryDir temp;
    Session session;
    QString input = preciseInput(source, temp.filePath("precision-input"));
    browser = false;
    if (web)
        openBrowserInput(session, input, kind);
    else {
        if (route == "zip-save" || route == "zip-copy-current") {
            const QString archive = temp.filePath("original.zip");
            edi::write_project_archive(input.toStdString(), archive.toStdString());
            input = archive;
        }
        need(session.openProject(QUrl::fromLocalFile(input)),
             "The fit guard opens its actual input");
        settle(session);
    }
    session.project()->setName("publication-fit-witness");
    settle(session);
    const QString workingBefore = session.project()->path();
    const QString destination =
        route == "folder-copy-current" ? workingBefore
        : route == "zip-copy-current"
            ? input
            : temp.filePath(route.startsWith("folder") ? "chosen-folder" : "chosen.zip");
    const bool destinationExisted = QFileInfo::exists(destination);
    const auto folderBefore = image(workingBefore);
    QFile archive(input);
    QByteArray archiveBefore;
    if (archive.open(QIODevice::ReadOnly)) archiveBefore = archive.readAll();
    jobs.clear();
    archiveSources.clear();
    archiveTargets.clear();
    stageKinds.clear();
    QStringList messages;
    QObject::connect(&session, &Session::webSaved, &session,
                     [&](const QString& t) { messages.append(t); });
    QObject::connect(&session, &Session::webSaveFailed, &session,
                     [&](const QString& t) { messages.append(t); });
    auto request = [&]() {
        if (web) {
            if (route.startsWith("web-save")) return session.save();
            beginMove(session, kind, isCopy);
            return !jobs.empty();
        }
        if (route == "zip-save") return session.save();
        return session.saveProjectAs(QUrl::fromLocalFile(destination), !route.startsWith("folder"),
                                     isCopy);
    };
    QJsonObject before, after;
    bool returned = false, runningReached = false;
    const auto heldBefore = state(session);
    std::size_t held = jobs.size();
    if (moment == "during") {
        request();
        held = nextWrite(0);
        need(held < jobs.size(), "A fit starts during an actual outstanding browser write");
    }
    int publicationsAtRequest = -1, stagesAtRequest = -1, jobsAtRequest = -1;
    auto* fit = session.project()->fit();
    if (moment != "success") {
        QObject::connect(fit, &FitViewModel::runningChanged, &session, [&]() {
            if (!fit->running() || runningReached) return;
            runningReached = true;
            before = state(session);
            if (moment == "during")
                finish(held, true, {}, false);
            else
                returned = request();
            after = state(session);
            publicationsAtRequest = archiveSources.size();
            stagesAtRequest = stageKinds.size();
            jobsAtRequest = jobs.size();
        });
        fit->start();
        need(runningReached,
             "The observer reaches the actual running fit, never a fabricated flag");
        fit->cancel();
        QElapsedTimer clock;
        clock.start();
        while (fit->running() && clock.elapsed() < 10000) {
            turn();
            QThread::msleep(1);
        }
        need(!fit->running(), "The independent fit witness terminates after its save observation");
    } else {
        before = state(session);
        returned = request();
        after = state(session);
        publicationsAtRequest = archiveSources.size();
        stagesAtRequest = stageKinds.size();
        jobsAtRequest = jobs.size();
    }
    QJsonArray archivedParameters;
    if (moment == "success" && returned) {
        const QString target = route == "zip-save" ? input : destination;
        QFile file(target);
        need(file.open(QIODevice::ReadOnly), "The published archive is readable independently");
        const auto bytes = file.readAll().toStdString();
        auto project = edi::load_project(
            edi::unpack_project_archive(bytes, temp.filePath("unpacked-check").toStdString()));
        for (const auto& entry : edi::parameter_entries(project)) {
            const auto& p = *entry.parameter;
            archivedParameters.append(QJsonObject{
                {"path", QString::fromStdString(entry.path)},
                {"value", static_cast<double>(p.value)},
                {"uncertainty", p.uncertainty ? QJsonValue(*p.uncertainty) : QJsonValue()},
                {"free", static_cast<bool>(p.free)}});
        }
    }
    QFile archiveAfterFile(input);
    QByteArray archiveAfter;
    if (archiveAfterFile.open(QIODevice::ReadOnly)) archiveAfter = archiveAfterFile.readAll();
    browser = false;
    return {{"route", route},
            {"moment", moment},
            {"before", before},
            {"after", after},
            {"heldBefore", heldBefore},
            {"returned", returned},
            {"runningReached", runningReached},
            {"publications", publicationsAtRequest},
            {"stages", stagesAtRequest},
            {"jobs", jobsAtRequest},
            {"sources", QJsonArray::fromStringList(archiveSources)},
            {"archivedParameters", archivedParameters},
            {"folderUnchanged", image(workingBefore) == folderBefore},
            {"archiveUnchanged", archiveAfter == archiveBefore},
            {"destinationCreated", !destinationExisted && QFileInfo::exists(destination)},
            {"messages", QJsonArray::fromStringList(messages)},
            {"drops", QJsonArray::fromStringList(drops)}};
}
}  // namespace
extern "C" void transaction_real_archive(const std::string&, const std::string&);
extern "C" std::string transaction_real_directory(const std::string&);
namespace edi {
void write_project_archive(const std::string& source, const std::string& target) {
    archiveSources.append(QString::fromStdString(source));
    archiveTargets.append(QString::fromStdString(target));
    transaction_real_archive(source, target);
    if (faultArmed) publicationCompleted = true;
}
std::string fresh_archive_directory(const std::string& kind) {
    stageKinds.append(QString::fromStdString(kind));
    return transaction_real_directory(kind);
}
}  // namespace edi
extern "C" edi::Project transaction_real_load_project(const std::string&, const edi::WarningSink&);
extern "C" void transaction_real_save_project(const edi::Project&, const std::string&);
extern "C" void transaction_real_save_project_as(edi::Project&, const std::string&);
extern "C" bool transaction_real_adopt_saved_values(edi::Project&, const std::string&);
extern "C" bool transaction_real_adopt_saved_project(edi::Project&, const std::string&);
extern "C" bool transaction_real_save_report_settings(const edi::Project&, const std::string&);
namespace edi {
Project load_project(const std::string& path, const WarningSink& warnings) {
    fallibleBoundary("load_project");
    return transaction_real_load_project(path, warnings);
}
void save_project(const Project& p, const std::string& path) {
    fallibleBoundary("save_project");
    transaction_real_save_project(p, path);
}
void save_project_as(Project& p, const std::string& path) {
    fallibleBoundary("save_project_as");
    transaction_real_save_project_as(p, path);
}
bool adopt_saved_values(Project& p, const std::string& path) {
    fallibleBoundary("adopt_saved_values");
    return transaction_real_adopt_saved_values(p, path);
}
bool adopt_saved_project(Project& p, const std::string& path) {
    fallibleBoundary("adopt_saved_project");
    return transaction_real_adopt_saved_project(p, path);
}
bool save_report_settings(const Project& p, const std::string& path) {
    fallibleBoundary("save_report_settings");
    return transaction_real_save_report_settings(p, path);
}
}  // namespace edi
extern "C" bool boundary_available() __asm__("__wrap__ZN7edi_app8WebFiles9availableEv");
extern "C" bool boundary_available() { return browser; }
extern "C" void
boundary_open(WebStorage*, const QString&, const QString& root, WebStorage::Answer answer) __asm__(
    "__wrap__ZN7edi_app10WebStorage8pickOpenERK7QStringS3_St8functionIFvRKNS_"
    "16WebStorageAnswerEEE");
extern "C" void boundary_open(WebStorage*, const QString&, const QString& root,
                              WebStorage::Answer answer) {
    jobs.push_back({"Open", "picked", "folder", root, false, std::move(answer)});
}
extern "C" void
boundary_load(WebStorage*, const QString& key, bool recovery, const QString& root, WebStorage::Answer answer) __asm__(
    "__wrap__ZN7edi_app10WebStorage4loadERK7QStringbS3_St8functionIFvRKNS_16WebStorageAnswerEEE");
extern "C" void boundary_load(WebStorage*, const QString& key, bool recovery, const QString& root,
                              WebStorage::Answer answer) {
    jobs.push_back({"load", key, "folder", root, recovery, std::move(answer)});
}
extern "C" void
boundary_pick(WebStorage*, const QString& kind, const QString&, const QString&, WebStorage::Answer answer) __asm__(
    "__wrap__ZN7edi_app10WebStorage8pickSaveERK7QStringS3_S3_St8functionIFvRKNS_"
    "16WebStorageAnswerEEE");
extern "C" void boundary_pick(WebStorage*, const QString& kind, const QString&, const QString&,
                              WebStorage::Answer answer) {
    static int picked = 0;
    jobs.push_back({"pickSave",
                    "destination-" + QString::number(++picked),
                    kind,
                    {},
                    false,
                    std::move(answer)});
}
extern "C" void
boundary_write(WebStorage*, const QString& key, const QString& kind, const QString&, const QString& folder, bool recovery, WebStorage::Answer answer) __asm__(
    "__wrap__ZN7edi_app10WebStorage5writeERK7QStringS3_S3_S3_bSt8functionIFvRKNS_"
    "16WebStorageAnswerEEE");
extern "C" void boundary_write(WebStorage*, const QString& key, const QString& kind,
                               const QString&, const QString& folder, bool recovery,
                               WebStorage::Answer answer) {
    jobs.push_back({"write", key, kind, folder, recovery, std::move(answer), image(folder)});
}
extern "C" void boundary_drop(WebStorage*, const QString& key) __asm__(
    "__wrap__ZN7edi_app10WebStorage12dropRecoveryERK7QString");
extern "C" void boundary_drop(WebStorage*, const QString& key) { drops.append(key); }
int main(int argc, char** argv) {
    qputenv("QT_QPA_PLATFORM", "offscreen");
    QGuiApplication app(argc, argv);
    edi_app::use_fresh_settings();
    try {
        need(argc == 3, "Requires the independent project folder and the named observation group");
        QString source = argv[1], group = argv[2];
        QJsonArray rows;
        if (group.startsWith("save-conflict/") || group.startsWith("save-alias-") ||
            group.startsWith("save-replaced-"))
            rows.append(saveConflict(source, group.split('/')));
        else if (group == "exact-fields")
            rows.append(exactFields(source));
        else if (group == "mixed-desktop" || group == "mixed-web")
            rows.append(mixedSave(source, group == "mixed-web"));
        else if (group.startsWith("fit-save/"))
            rows.append(fitPublication(source, group.split('/')));
        else if (group.startsWith("after-publication/"))
            rows.append(afterPublication(source, group.split('/')));
        else if (group.startsWith("rollback/"))
            rows.append(rollback(source, group.split('/')));
        else if (group == "overlap")
            for (const auto& first : {"Open", "Recent", "recovery"})
                for (const auto& second : {"Open", "Recent", "recovery"})
                    for (bool order : {false, true})
                        rows.append(overlap(source, first, second, order, false, false));
        else if (group == "read-edits") {
            for (const auto& route : {"Open", "Recent", "recovery"}) {
                rows.append(overlap(source, route, "", false, true, false));
                for (const auto& replacementKind : {"example", "new", "desktop"})
                    rows.append(overlap(source, route, "", false, false, true, replacementKind));
            }
        } else if (group == "browser-save") {
            for (const auto& kind : {"browser", "folder", "zip"})
                for (bool ok : {false, true})
                    for (bool moving : {false, true})
                        if (kind != QString("browser") || !moving)
                            rows.append(
                                browserSave(source, kind, ok, false, moving, false, false));
        } else if (group == "newer-recovery")
            for (const auto& kind : {"browser", "folder", "zip"}) {
                rows.append(browserSave(source, kind, true, true, false, false, false));
                rows.append(browserSave(source, kind, false, false, false, true, false));
            }
        else if (group == "archive-links") {
            for (const auto& kind : {"internal", "external", "directory", "broken"})
                rows.append(archiveLink(source, kind));
        } else if (group == "continuation") {
            for (bool quit : {false, true}) {
                rows.append(continuation(source, false, false, false, quit));
                rows.append(continuation(source, true, false, false, quit));
                rows.append(continuation(source, true, true, false, quit));
                rows.append(continuation(source, false, false, true, quit));
            }
        } else if (group == "desktop-save") {
            for (const auto& origin : {"folder", "zip", "example", "readonly"})
                for (const auto& target : {"folder", "zip"})
                    rows.append(desktopSave(source, origin, target));
            rows.append(desktopSave(source, "zip", "ordinary"));
        } else
            throw std::runtime_error("Unknown observation group");
        std::cout << QJsonDocument(rows).toJson(QJsonDocument::Compact).constData() << '\n';
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 2;
    }
}
