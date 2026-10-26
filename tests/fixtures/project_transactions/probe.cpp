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
#include <QQmlApplicationEngine>
#include <QQmlComponent>
#include <QQmlExpression>
#include <QTemporaryDir>
#include <QThread>
#include <QtQml>
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
#include "edi/project_archive.hpp"
Q_IMPORT_QML_PLUGIN(edi_appPlugin)
using namespace edi_app;
namespace {
bool browser = false;
struct Job {
    QString action, key, kind, root;
    bool recovery;
    WebStorage::Answer answer;
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
QJsonObject state(Session& session) {
    return {{"name", session.project() ? session.project()->name() : QString()},
            {"modified", session.project() && session.project()->modified()},
            {"path", session.project() ? session.project()->path() : QString()},
            {"location", session.projectLocation()},
            {"needsSaveAs", session.needsSaveAs()},
            {"example", session.openedExample()},
            {"archive", session.openedArchive()}};
}
void finish(size_t index, bool ok, const QString& input = {}) {
    need(index < jobs.size(), "A completion must belong to an actually started I/O request");
    Job job = jobs[index];
    jobs[index].answer = {};
    need(bool(job.answer), "The fixture must deliver each terminal callback once");
    WebStorageAnswer answer;
    answer.ok = ok;
    answer.key = job.key;
    answer.kind = job.kind;
    answer.name = QFileInfo(input).fileName();
    answer.message = "Independent boundary refusal";
    if (!input.isEmpty()) answer.path = copy(input, job.root + "/" + QFileInfo(input).fileName());
    job.answer(answer);
    turn();
}
void start(Session& session, const QString& route, const QString& key) {
    if (route == "Open")
        session.openWebProject("folder");
    else
        session.openStoredProject(key, route == "recovery");
}
QJsonObject overlap(const QString& source, const QString& first, const QString& second,
                    bool newerFirst, bool edit, bool replacement) {
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
        need(session.openProject(QUrl::fromLocalFile(copy(source, temp.filePath("replacement")))),
             "The independent replacement really opens");
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
    int success = 0, errors = 0;
    QObject::connect(&session, &Session::webSaved, &session, [&](const QString&) { ++success; });
    QObject::connect(&session, &Session::webSaveFailed, &session,
                     [&](const QString&) { ++errors; });
    session.project()->setName("edited-before-save");
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
            {"writes", index >= 0}};
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
    session.project()->setName("unsaved-refusal-edit");
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
}  // namespace
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
    jobs.push_back({"pickSave", "destination", kind, {}, false, std::move(answer)});
}
extern "C" void
boundary_write(WebStorage*, const QString& key, const QString& kind, const QString&, const QString& folder, bool recovery, WebStorage::Answer answer) __asm__(
    "__wrap__ZN7edi_app10WebStorage5writeERK7QStringS3_S3_S3_bSt8functionIFvRKNS_"
    "16WebStorageAnswerEEE");
extern "C" void boundary_write(WebStorage*, const QString& key, const QString& kind,
                               const QString&, const QString& folder, bool recovery,
                               WebStorage::Answer answer) {
    jobs.push_back({"write", key, kind, folder, recovery, std::move(answer)});
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
        if (group == "overlap")
            for (const auto& first : {"Open", "Recent", "recovery"})
                for (const auto& second : {"Open", "Recent", "recovery"})
                    for (bool order : {false, true})
                        rows.append(overlap(source, first, second, order, false, false));
        else if (group == "read-edits")
            for (const auto& route : {"Open", "Recent", "recovery"})
                for (bool replacement : {false, true})
                    rows.append(overlap(source, route, "", false, !replacement, replacement));
        else if (group == "browser-save") {
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
        else if (group == "continuation") {
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
