// SPDX-License-Identifier: BSD-3-Clause
#include "session.hpp"

#include <QCoreApplication>
#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QFileInfo>
#include <QJsonObject>
#include <QPointer>
#include <QUuid>
#include <algorithm>
#include <utility>
#include <filesystem>

#include "app_info.hpp"
#include "web_files.hpp"
#include "web_storage.hpp"
#include "edi/io.hpp"
#include "edi/project_archive.hpp"
#include "edi/parameter_walk.hpp"
#include "edi/scan.hpp"

namespace edi_app {
namespace {

const QString kExamples = QStringLiteral(":/edi/examples");

// A folder name for a project named `name`: no separators, never empty.
QString folderNameFor(const QString& name) {
    QString folder = name.trimmed();
    folder.replace(QLatin1Char('/'), QLatin1Char('_')).replace(QLatin1Char('\\'), QLatin1Char('_'));
    return folder.isEmpty() || folder == QStringLiteral(".") || folder == QStringLiteral("..") ? QStringLiteral("project")
                                                                                                  : folder;
}

QString newWebKey() { return QUuid::createUuid().toString(QUuid::WithoutBraces); }

}  // namespace

// ---- WarningListModel ---------------------------------------------------------------------------

WarningListModel::WarningListModel(QObject* parent) : RowTableModel({"message", "severity"}, parent) {}

void WarningListModel::setMessages(const QStringList& messages) {
    messages_.clear();
    for (qsizetype i = 0; i < messages.size(); ++i) {
        messages_.push_back({next_id_++, QStringLiteral("load:%1").arg(i), messages[i], QStringLiteral("warning")});
    }
    changed();
}

void WarningListModel::post(const QString& key, const QString& text, const QString& severity) {
    for (const Message& message : messages_) {
        if (message.key == key) {
            return;
        }
    }
    messages_.push_back({next_id_++, key, text, severity});
    changed();
}

void WarningListModel::withdraw(const QString& key) {
    for (std::size_t i = 0; i < messages_.size(); ++i) {
        if (messages_[i].key == key) {
            messages_.erase(messages_.begin() + static_cast<std::ptrdiff_t>(i));
            changed();
            return;
        }
    }
}

QStringList WarningListModel::keys(const QString& prefix) const {
    QStringList found;
    for (const Message& message : messages_) {
        if (message.key.startsWith(prefix)) {
            found.append(message.key);
        }
    }
    return found;
}

void WarningListModel::markViewed() {
    for (Message& message : messages_) {
        message.viewed = true;
    }
    recount();
}

void WarningListModel::dismiss(int row) {
    if (row < 0 || row >= static_cast<int>(messages_.size())) {
        return;
    }
    messages_.erase(messages_.begin() + row);
    changed();
}

void WarningListModel::dismissAll() {
    messages_.clear();
    changed();
}

void WarningListModel::changed() {
    publish();
    recount();
}

void WarningListModel::publish() {
    QList<Row> rows;
    for (const Message& message : messages_) {
        rows.append({reinterpret_cast<const void*>(static_cast<quintptr>(message.id)), {message.text, message.severity}});
    }
    setTableRows(rows);
}

void WarningListModel::recount() {
    const int unviewed = static_cast<int>(
        std::count_if(messages_.begin(), messages_.end(), [](const Message& message) { return !message.viewed; }));
    if (unviewed != unviewed_) {
        unviewed_ = unviewed;
        emit unviewedCountChanged();
    }
}

// ---- Session ------------------------------------------------------------------------------------

Session::Session(QObject* parent)
    : QObject(parent), examples_(new ExampleListModel(this)), warnings_(new WarningListModel(this)) {
    // crysta's warnings reach Messages, never only the terminal (the owner, 2026-10-23).
    edi::collect_engine_warnings();
    // What a crash left in the temporary directory (edi ADR-0052).
    edi::remove_stale_archive_directories();
    // The web app keeps a project's unsaved state a few seconds after its last edit (edi ADR-0052 §9).
    keep_timer_ = new QTimer(this);
    keep_timer_->setSingleShot(true);
    keep_timer_->setInterval(3000);
    connect(keep_timer_, &QTimer::timeout, this, &Session::keepChanges);
}

Session::~Session() { releaseTemporaryFolder(); }

void Session::releaseTemporaryFolder() {
    if (!temporary_folder_.isEmpty()) {
        edi::remove_archive_directory(temporary_folder_.toStdString());
        temporary_folder_.clear();
    }
}

bool Session::openProject(const QUrl& location) {
    if (openProjectAt(location)) {
        return true;
    }
    emit loadFailed(last_error_.isEmpty() ? tr("The project could not be opened") : last_error_);
    return false;
}

bool Session::openExample(const QString& exampleId) {
    if (openExampleNamed(exampleId)) {
        return true;
    }
    emit loadFailed(last_error_.isEmpty() ? tr("The project could not be opened") : last_error_);
    return false;
}

bool Session::openProjectAt(const QUrl& location) {
    if (!location.isLocalFile()) {
        setLastError(QStringLiteral("cannot open %1: only local projects (file: URLs) can be opened")
                         .arg(location.toString()));
        return false;
    }
    QString source = location.toLocalFile();
    // edi ADR-0052: a project record opens its folder; an archive is unpacked by the core into a temporary folder and
    // opens unsaved, so its first Save asks where to keep it.
    const QFileInfo given(source);
    if (given.isFile() && given.fileName() == QStringLiteral("project.edi")) {
        source = given.absolutePath();
    } else if (given.isFile() && edi::is_project_archive(source.toStdString())) {
        if (!open(source, {})) {
            return false;
        }
        temporary_folder_ = QString::fromStdString(project_->project().scan_data_root);
        // The archive is the project's location and Save rewrites it, unless it cannot be written back: a read-only
        // file or folder, or the browser's uploaded copy (owner, 2026-10-25).
        const QFileInfo folder(given.absolutePath());
        if (!WebFiles::available() && given.isWritable() && folder.isWritable()) {
            project_->workIn(QString::fromStdString(project_->project().scan_data_root));
            archive_location_ = given.absoluteFilePath();
            emit projectLocationChanged();
            emit needsSaveAsChanged();
            emit locationTextChanged();
            emit projectDirectoryUsed(archive_location_);
        } else {
            setOpenedArchive(given.fileName());
        }
        return true;
    }
    // A project in a folder this user may not write (a read-only tree) runs in a temporary copy, as an example does,
    // so a fit never writes into it; Save As writes the project where the user chooses.
    const QFileInfo folder(source), analysis(source + QStringLiteral("/analysis"));
    if (folder.isDir() && (!folder.isWritable() || (analysis.exists() && !analysis.isWritable()))) {
        if (extracted_ == nullptr || !extracted_->isValid()) {
            extracted_ = std::make_unique<QTemporaryDir>();
        }
        if (!extracted_->isValid()) {
            setLastError(QStringLiteral("cannot create a temporary copy of %1: %2").arg(source, extracted_->errorString()));
            return false;
        }
        const QString target = extracted_->filePath(QStringLiteral("read-only/") + folder.fileName());
        if (!openCopy(source, target, {})) {
            return false;
        }
        read_only_copy_ = true;
        read_only_source_ = folder.absoluteFilePath();
        emit needsSaveAsChanged();
        emit locationTextChanged();
        emit projectDirectoryUsed(folder.absoluteFilePath());
        return true;
    }
    const bool opened = open(source, {});
    if (opened) {
        emit projectDirectoryUsed(folder.absoluteFilePath());
    }
    return opened;
}

bool Session::copyTree(const QString& source, const QString& target, const QString& linked) {
    const QString shared =
        linked.isEmpty() ? QString() : QDir::cleanPath(QFileInfo(linked).absoluteFilePath()) + u'/';
    QDirIterator files(source, QDir::Files, QDirIterator::Subdirectories);
    while (files.hasNext()) {
        const QString file = files.next();
        const QString destination = target + file.mid(source.size());
        QDir().mkpath(QFileInfo(destination).absolutePath());
        // A scan data file is only read: the copy links to it, and copies it only where linking is refused (another
        // file system). Its permissions are the original's, so they are left alone.
        if (!shared.isEmpty() && QDir::cleanPath(QFileInfo(file).absoluteFilePath()).startsWith(shared)) {
            std::error_code error;
            std::filesystem::create_hard_link(file.toStdString(), destination.toStdString(), error);
            if (!error) {
                continue;
            }
        }
        if (!QFile::copy(file, destination)) {
            return false;
        }
        QFile::setPermissions(destination, QFile::ReadOwner | QFile::WriteOwner);
    }
    return true;
}

QString Session::projectLocation() const {
    if (project_ == nullptr) {
        return {};
    }
    if (!archive_location_.isEmpty()) {
        return archive_location_;
    }
    QString location = project_->path();
    if (ApplicationInfo::demoIdentity() && !opened_example_.isEmpty() && extracted_ != nullptr && extracted_->isValid()
        && location.startsWith(extracted_->path())) {
        location.replace(0, extracted_->path().size(), QStringLiteral("<temporary>"));
    }
    return location;
}

QString Session::locationText() const {
    if (project_ == nullptr) {
        return {};
    }
    // The web app (edi ADR-0052 §9): the disk's folder or .zip by its name, else the browser's own storage.
    if (WebFiles::available()) {
        const bool disk = web_place_.kind == QStringLiteral("folder") || web_place_.kind == QStringLiteral("zip");
        return disk ? web_place_.name : tr("In this browser only");
    }
    if (!archive_location_.isEmpty()) {
        return archive_location_;
    }
    if (!opened_example_.isEmpty()) {
        return tr("Not saved yet: example %1").arg(examples_->titleOf(opened_example_));
    }
    if (!opened_archive_.isEmpty()) {
        return tr("Not saved yet: opened from %1").arg(opened_archive_);
    }
    if (read_only_copy_) {
        return tr("Not saved yet: a copy of %1").arg(read_only_source_);
    }
    return project_->path();
}

bool Session::needsSaveAs() const {
    // Every project in the web app has its place, which Save writes.
    return project_ != nullptr && !WebFiles::available()
           && (project_->path().isEmpty() || !opened_example_.isEmpty() || read_only_copy_);
}

bool Session::save() {
    if (project_ != nullptr && WebFiles::available()) {
        // Saved in memory, where the project works, then written into its place. A project created in the browser
        // has no folder yet: it gets one in memory.
        QString folder = project_->path();
        if (folder.isEmpty()) {
            try {
                folder = QString::fromStdString(edi::fresh_archive_directory("web")) + QLatin1Char('/')
                         + folderNameFor(project_->name());
            } catch (const std::exception& refusal) {
                setLastError(QString::fromUtf8(refusal.what()));
                return false;
            }
            web_copy_ = QFileInfo(folder).absolutePath();
        }
        const QString error = project_->saveTo(folder);
        setLastError(error);
        if (!error.isEmpty()) {
            return false;
        }
        writeWebPlace();
        return true;
    }
    if (project_ == nullptr || needsSaveAs()) {
        setLastError(QStringLiteral("this project has no directory of its own yet: save it as"));
        return false;
    }
    const QString error = project_->saveTo(project_->path());
    setLastError(error);
    if (!error.isEmpty()) {
        return false;
    }
    if (!archive_location_.isEmpty()) {
        try {
            edi::write_project_archive(project_->path().toStdString(), archive_location_.toStdString());
        } catch (const std::exception& refusal) {
            setLastError(QString::fromUtf8(refusal.what()));
            return false;
        }
        emit projectDirectoryUsed(archive_location_);
        return true;
    }
    emit projectDirectoryUsed(QFileInfo(project_->path()).absoluteFilePath());
    return true;
}

bool Session::saveAs(const QUrl& directory) {
    if (project_ == nullptr) {
        return false;
    }
    if (!directory.isLocalFile()) {
        setLastError(QStringLiteral("cannot save to %1: only local directories (file: URLs)").arg(directory.toString()));
        return false;
    }
    archive_location_.clear();
    if (!saveInto(directory.toLocalFile())) {
        return false;
    }
    releaseTemporaryFolder();
    emit projectLocationChanged();
    emit needsSaveAsChanged();
    emit locationTextChanged();
    emit projectDirectoryUsed(QFileInfo(directory.toLocalFile()).absoluteFilePath());
    return true;
}

bool Session::saveInto(const QString& folder) {
    const QString error = project_->saveTo(folder);
    setLastError(error);
    if (!error.isEmpty()) {
        return false;
    }
    // Saved where the user chose, the project is no longer the example's, the archive's or the read-only tree's
    // temporary copy.
    read_only_copy_ = false;
    setOpenedArchive({});
    if (!opened_example_.isEmpty()) {
        opened_example_.clear();
        emit openedExampleChanged();
    }
    return true;
}

bool Session::saveProjectAs(const QUrl& target, bool zip, bool copy) {
    if (project_ == nullptr) {
        return false;
    }
    if (!target.isLocalFile()) {
        setLastError(QStringLiteral("cannot save to %1: only local files and folders (file: URLs)").arg(target.toString()));
        return false;
    }
    const QString where = target.toLocalFile();
    if (copy) {
        return saveCopy(where, zip);
    }
    if (!zip) {
        return saveAs(target);
    }
    // A project saved as a .zip works in a folder of its own and every Save rewrites the archive from it.
    QString folder;
    try {
        folder = QString::fromStdString(edi::fresh_archive_directory("saved"));
    } catch (const std::exception& refusal) {
        setLastError(QString::fromUtf8(refusal.what()));
        return false;
    }
    if (!saveInto(folder)) {
        edi::remove_archive_directory(folder.toStdString());
        return false;
    }
    releaseTemporaryFolder();
    temporary_folder_ = folder;
    archive_location_ = where;
    emit projectLocationChanged();
    emit needsSaveAsChanged();
    emit locationTextChanged();
    try {
        edi::write_project_archive(folder.toStdString(), where.toStdString());
    } catch (const std::exception& refusal) {
        setLastError(QString::fromUtf8(refusal.what()));
        return false;
    }
    emit projectDirectoryUsed(where);
    return true;
}

bool Session::saveCopy(const QString& target, bool zip) {
    // What a Save writes (round, adopt, recalculate, write), done on a copy of the project: the open project keeps its
    // own location and values.
    try {
        edi::Project copy = project_->project();
        const auto write = [&copy](const std::string& folder) {
            edi::save_project(copy, folder);
            edi::adopt_saved_project(copy, folder);
        };
        if (zip) {
            const std::string folder = edi::fresh_archive_directory("copy");
            try {
                write(folder);
                edi::write_project_archive(folder, target.toStdString());
            } catch (...) {
                edi::remove_archive_directory(folder);
                throw;
            }
            edi::remove_archive_directory(folder);
        } else {
            write(target.toStdString());
        }
    } catch (const std::exception& refusal) {
        setLastError(QString::fromUtf8(refusal.what()));
        return false;
    }
    setLastError({});
    return true;
}

bool Session::openExampleNamed(const QString& exampleId) {
    const QString source = kExamples + QLatin1Char('/') + exampleId + QStringLiteral("/project");
    if (!ExampleListModel::bundledIds().contains(exampleId) || !QFileInfo(source).isDir()) {
        setLastError(QStringLiteral("no bundled example named '%1'").arg(exampleId));
        return false;
    }
    if (extracted_ == nullptr || !extracted_->isValid()) {
        extracted_ = std::make_unique<QTemporaryDir>();
    }
    // An invalid directory's filePath() is empty, and removing the empty path below would remove the
    // working directory with everything in it: refuse first.
    if (!extracted_->isValid()) {
        setLastError(QStringLiteral("cannot create a directory for the example '%1': %2")
                         .arg(exampleId, extracted_->errorString()));
        return false;
    }
    // A fresh copy per open, so edits to an opened example never leak into the next open of it. A bundled example
    // lives in the application's resources, which crysta cannot read: its scan data are copied with it.
    const QString target = extracted_->filePath(exampleId + QStringLiteral("/project"));
    QDir(target).removeRecursively();
    QDirIterator files(source, QDir::Files, QDirIterator::Subdirectories);
    while (files.hasNext()) {
        const QString file = files.next();
        const QString destination = target + file.mid(source.size());
        QDir().mkpath(QFileInfo(destination).absolutePath());
        if (!QFile::copy(file, destination)) {
            setLastError(QStringLiteral("cannot extract the example '%1'").arg(exampleId));
            return false;
        }
        QFile::setPermissions(destination, QFile::ReadOwner | QFile::WriteOwner);
    }
    return open(target, exampleId);
}

bool Session::createProject(const QString& name, const QString& description, const QString& location,
                            const QString& suRule, const QString& title, const QString& authors,
                            bool reportLibraries) {
    ProjectViewModel* created = nullptr;
    try {
        edi::Project project = edi::empty_project(name.toStdString(), description.toStdString());
        if (!title.isEmpty()) {
            project.metadata.title = title.toStdString();
        }
        project.metadata.authors = authors.toStdString();
        if (suRule == QStringLiteral("iucr_19") || suRule == QStringLiteral("iucr_99")) {
            project.su_rule = suRule.toStdString();
        }
        project.report_html_offline = reportLibraries;
        created = new ProjectViewModel(std::move(project), this);
    } catch (const std::exception& refusal) {
        setLastError(QString::fromUtf8(refusal.what()));
        return false;
    }
    replaceProject(created, {}, {});
    if (location.isEmpty()) {
        return true;
    }
    const QString error = project_->saveTo(location);
    setLastError(error);
    if (!error.isEmpty()) {
        return false;
    }
    emit projectLocationChanged();
    emit needsSaveAsChanged();
    emit projectDirectoryUsed(QFileInfo(location).absoluteFilePath());
    return true;
}

void Session::closeProject() { replaceProject(nullptr, {}, {}); }

void Session::syncCalculationMessages() {
    // One message per distinct refusal: a project-wide refusal reaches every experiment's pattern alike.
    QStringList refusals;
    if (project_ != nullptr) {
        for (ExperimentViewModel* experiment : project_->experimentModels()) {
            const QString error = experiment->pattern()->calculationError();
            if (!error.isEmpty() && !refusals.contains(error)) {
                refusals.append(error);
            }
        }
    }
    const QString prefix = QStringLiteral("calculation:");
    for (const QString& key : warnings_->keys(prefix)) {
        if (!refusals.contains(key.mid(prefix.size()))) {
            warnings_->withdraw(key);
        }
    }
    for (const QString& refusal : refusals) {
        warnings_->post(prefix + refusal, tr("Calculation refused: %1").arg(refusal), QStringLiteral("error"));
    }
}

bool Session::projectDirectoryExists(const QString& path) const {
    // A recent project is a folder or a .zip it was saved as (edi ADR-0052).
    return !path.isEmpty() && (QFileInfo(path).isDir() || edi::is_project_archive(path.toStdString()));
}

QUrl Session::projectDirectoryUrl(const QString& path) const {
    return path.isEmpty() ? QUrl() : QUrl::fromLocalFile(path);
}

void Session::clearError() { setLastError({}); }

bool Session::open(const QString& directory, const QString& example) {
    QStringList warnings;
    ProjectViewModel* opened = nullptr;
    try {
        edi::Project project = edi::load_project(directory.toStdString(), [&warnings](const std::string& message) {
            warnings.append(QString::fromStdString(message));
        });
        // A project loads with any value it holds; the warnings that hold for them post once, the loader's own range
        // warnings included (the owner, 2026-10-23).
        for (const std::string& warning : edi::standing_warnings(project, false)) {
            warnings.append(QString::fromStdString(warning));
        }
        for (const std::string& warning : edi::take_engine_warnings()) {
            warnings.append(QString::fromStdString(warning));
        }
        opened = new ProjectViewModel(std::move(project), this);
    } catch (const std::exception& refusal) {
        setLastError(QString::fromUtf8(refusal.what()));  // the open project stays as it was
        return false;
    }
    replaceProject(opened, warnings, example);
    return true;
}

bool Session::openCopy(const QString& source, const QString& target, const QString& example) {
    QStringList warnings;
    ProjectViewModel* opened = nullptr;
    try {
        edi::Project project = edi::load_project(source.toStdString(), [&warnings](const std::string& message) {
            warnings.append(QString::fromStdString(message));
        });
        QString data;  // the scan data directory, linked rather than copied
        if (project.sequential_fit.declared()) {
            try {
                data = QString::fromStdString(edi::scan_datasets(project).directory);
            } catch (const std::exception&) {
                data.clear();  // no scan directory resolves: everything is copied
            }
        }
        QDir(target).removeRecursively();
        if (!copyTree(source, target, data)) {
            throw std::runtime_error("cannot make a temporary copy of " + source.toStdString());
        }
        project.path = target.toStdString();
        project.metadata.path = project.path;
        for (const std::string& warning : edi::standing_warnings(project, false)) {
            warnings.append(QString::fromStdString(warning));
        }
        for (const std::string& warning : edi::take_engine_warnings()) {
            warnings.append(QString::fromStdString(warning));
        }
        opened = new ProjectViewModel(std::move(project), this);
    } catch (const std::exception& refusal) {
        setLastError(QString::fromUtf8(refusal.what()));  // the open project stays as it was
        return false;
    }
    replaceProject(opened, warnings, example);
    return true;
}

void Session::setOpenedArchive(const QString& name) {
    if (name != opened_archive_) {
        opened_archive_ = name;
        emit openedArchiveChanged();
        emit locationTextChanged();
    }
}

void Session::replaceProject(ProjectViewModel* project, const QStringList& warnings, const QString& example) {
    keep_timer_->stop();
    const QString previous_web_copy = std::exchange(web_copy_, QString());
    // In the web app a project starts in the browser's own storage; an open from the disk or from a stored place
    // names its place once it is open.
    web_place_ = {};
    if (project != nullptr && WebFiles::available()) {
        web_place_ = {newWebKey(), QStringLiteral("browser"), folderNameFor(project->name())};
        connect(project, &ProjectViewModel::edited, keep_timer_, qOverload<>(&QTimer::start));
    }
    read_only_copy_ = false;
    read_only_source_.clear();
    archive_location_.clear();
    setOpenedArchive({});
    // Every piece of the session's state — the project, its load warnings, the example it came from,
    // the cleared error — is in place before any consumer is told, so a handler of one signal reads
    // the new state of the others; then each property signals only if it changed.
    ProjectViewModel* previous = project_;
    const QString previous_example = opened_example_;
    emit projectAboutToChange();
    project_ = project;
    opened_example_ = example;
    warnings_->setMessages(warnings);
    if (project_ != nullptr) {
        connect(project_, &ProjectViewModel::refused, this, &Session::setLastError);
        connect(project_, &ProjectViewModel::recalculated, this, &Session::syncCalculationMessages);
        // A load's or a removal's account: each one listed as its own message.
        connect(project_, &ProjectViewModel::message, this, [this](const QString& text) {
            warnings_->post(QStringLiteral("project:%1").arg(++project_messages_), text, QStringLiteral("warning"));
        });
        connect(project_, &ProjectViewModel::information, this, [this](const QString& text) {
            warnings_->post(QStringLiteral("project:%1").arg(++project_messages_), text, QStringLiteral("information"));
        });
    }
    syncCalculationMessages();  // the new project calculated before it was connected
    setLastError({});
    if ((previous != nullptr) != (project_ != nullptr)) {
        emit hasProjectChanged();
    }
    if (previous_example != opened_example_) {
        emit openedExampleChanged();
    }
    emit projectChanged();
    emit projectLocationChanged();
    emit locationTextChanged();
    emit needsSaveAsChanged();
    // The replaced project's temporary folder goes with it, once it is gone.
    const QString previous_folder = std::exchange(temporary_folder_, QString());
    if (previous != nullptr) {
        previous->deleteLater();
        // Free the replaced project's view-models, and the page items the views released for them,
        // now rather than at the next event-loop turn: projects opened back to back (a script, a
        // test) must hold one project's pages, not every one opened so far.
        QCoreApplication::sendPostedEvents(nullptr, QEvent::DeferredDelete);
    }
    if (!previous_folder.isEmpty()) {
        edi::remove_archive_directory(previous_folder.toStdString());
    }
    if (!previous_web_copy.isEmpty()) {
        QDir(previous_web_copy).removeRecursively();
    }
}

// ---- The web app's places (edi ADR-0052 §9) ---------------------------------------------------------

void Session::setWebPlace(const WebPlace& place) {
    web_place_ = place;
    emit locationTextChanged();
    emit projectLocationChanged();
}

bool Session::openWebCopy(const QString& path, const WebPlace& place) {
    const QFileInfo given(path);
    if (given.isFile() && edi::is_project_archive(path.toStdString())) {
        if (!open(path, {})) {
            return false;
        }
        // The project works in the folder the archive was unpacked into; a Save writes the archive from it.
        const QString unpacked = QString::fromStdString(project_->project().scan_data_root);
        project_->workIn(unpacked);
        temporary_folder_ = unpacked;
    } else {
        QString error;
        const QString folder = WebFiles::projectIn(path, error);
        if (folder.isEmpty()) {
            setLastError(QStringLiteral("cannot open %1: %2").arg(given.fileName(), error));
            return false;
        }
        if (!open(folder, {})) {
            return false;
        }
    }
    setWebPlace({place.key.isEmpty() ? newWebKey() : place.key, place.kind, place.name});
    return true;
}

void Session::openWebProject(const QString& kind) {
    QString root;
    try {
        root = QString::fromStdString(edi::fresh_archive_directory("web"));
    } catch (const std::exception& refusal) {
        setLastError(QString::fromUtf8(refusal.what()));
        emit loadFailed(last_error_);
        return;
    }
    // A project opened meanwhile is not replaced by the one that arrives late.
    const QPointer<ProjectViewModel> before = project_;
    WebStorage::instance()->pickOpen(kind, root, [this, root, before](const QJsonObject& answer) {
        if (before != project_ || !answer.value(QStringLiteral("ok")).toBool()) {
            QDir(root).removeRecursively();
            if (before == project_ && !answer.value(QStringLiteral("cancelled")).toBool()) {
                setLastError(answer.value(QStringLiteral("message")).toString());
                emit loadFailed(last_error_);
            }
            return;
        }
        const WebPlace place{answer.value(QStringLiteral("key")).toString(),
                             answer.value(QStringLiteral("kind")).toString(),
                             answer.value(QStringLiteral("name")).toString()};
        if (!openWebCopy(answer.value(QStringLiteral("path")).toString(), place)) {
            QDir(root).removeRecursively();
            emit loadFailed(last_error_);
            return;
        }
        web_copy_ = root;
        // A project uploaded from the disk is kept in the browser at once (owner, 2026-10-25).
        if (web_place_.kind == QStringLiteral("browser")) {
            writeWebPlace(false);
        }
    });
}

void Session::openStoredProject(const QString& key, bool recovery) {
    QString root;
    try {
        root = QString::fromStdString(edi::fresh_archive_directory("web"));
    } catch (const std::exception& refusal) {
        setLastError(QString::fromUtf8(refusal.what()));
        emit loadFailed(last_error_);
        return;
    }
    const QPointer<ProjectViewModel> before = project_;
    WebStorage::instance()->load(key, recovery, root, [this, root, before, recovery](const QJsonObject& answer) {
        if (before != project_ || !answer.value(QStringLiteral("ok")).toBool()) {
            QDir(root).removeRecursively();
            if (before == project_) {
                setLastError(answer.value(QStringLiteral("message")).toString());
                emit loadFailed(last_error_);
            }
            return;
        }
        const WebPlace place{answer.value(QStringLiteral("key")).toString(),
                             answer.value(QStringLiteral("kind")).toString(),
                             answer.value(QStringLiteral("name")).toString()};
        if (!openWebCopy(answer.value(QStringLiteral("path")).toString(), place)) {
            QDir(root).removeRecursively();
            emit loadFailed(last_error_);
            return;
        }
        web_copy_ = root;
        // The kept state holds changes its place does not: the project opens with them, unsaved.
        if (recovery) {
            project_->markUnsaved();
        }
    });
}

void Session::writeWebPlace(bool announce) {
    keep_timer_->stop();
    const WebPlace place = web_place_;
    WebStorage::instance()->write(place.key, place.kind, place.name, project_->path(), false,
                                  [this, place, announce](const QJsonObject& answer) {
                                      if (!answer.value(QStringLiteral("ok")).toBool()) {
                                          emit webSaveFailed(answer.value(QStringLiteral("message")).toString());
                                          return;
                                      }
                                      // Saved, the changes kept for a reload are no longer needed.
                                      WebStorage::instance()->dropRecovery(place.key);
                                      if (announce) {
                                          emit webSaved(place.kind);
                                      }
                                  });
}

QString Session::downloadName() const {
    const QString name = web_place_.name.isEmpty() ? folderNameFor(project_->name()) : web_place_.name;
    return name.endsWith(QStringLiteral(".zip"), Qt::CaseInsensitive) ? name : name + QStringLiteral(".zip");
}

void Session::saveWebProjectAs(const QString& kind, bool copy) {
    if (project_ == nullptr) {
        return;
    }
    const QPointer<ProjectViewModel> before = project_;
    WebStorage::instance()->pickSave(kind, downloadName(), web_place_.key, [this, before, kind, copy](
                                                                               const QJsonObject& answer) {
        if (before != project_ || project_ == nullptr || !answer.value(QStringLiteral("ok")).toBool()) {
            if (before == project_ && !answer.value(QStringLiteral("cancelled")).toBool()) {
                emit webSaveFailed(answer.value(QStringLiteral("message")).toString());
            }
            return;
        }
        const WebPlace place{answer.value(QStringLiteral("key")).toString(), kind,
                             answer.value(QStringLiteral("name")).toString()};
        QString root;
        try {
            root = QString::fromStdString(edi::fresh_archive_directory(copy ? "copy" : "web"));
        } catch (const std::exception& refusal) {
            emit webSaveFailed(QString::fromUtf8(refusal.what()));
            return;
        }
        const QString folder =
            root + QLatin1Char('/') + folderNameFor(kind == QStringLiteral("zip") ? project_->name() : place.name);
        if (copy) {
            // What a Save writes, done on a copy of the project, which stays where it is.
            try {
                edi::Project duplicate = project_->project();
                edi::save_project(duplicate, folder.toStdString());
                edi::adopt_saved_project(duplicate, folder.toStdString());
            } catch (const std::exception& refusal) {
                QDir(root).removeRecursively();
                emit webSaveFailed(QString::fromUtf8(refusal.what()));
                return;
            }
            WebStorage::instance()->write(place.key, place.kind, place.name, folder, false,
                                          [this, root, kind](const QJsonObject& written) {
                                              QDir(root).removeRecursively();
                                              if (written.value(QStringLiteral("ok")).toBool()) {
                                                  emit webSaved(kind);
                                              } else {
                                                  emit webSaveFailed(written.value(QStringLiteral("message")).toString());
                                              }
                                          });
            return;
        }
        // The project moves there: saved into a memory folder of its own, which it works in from now on.
        if (!saveInto(folder)) {
            QDir(root).removeRecursively();
            emit webSaveFailed(last_error_);
            return;
        }
        releaseTemporaryFolder();
        if (!web_copy_.isEmpty()) {
            QDir(web_copy_).removeRecursively();
        }
        web_copy_ = root;
        setWebPlace(place);
        writeWebPlace();
    });
}

void Session::downloadWebProject() {
    if (project_ == nullptr || !save()) {
        if (project_ != nullptr) {
            emit webSaveFailed(last_error_);
        }
        return;
    }
    QByteArray archive;
    try {
        const std::string bytes = edi::project_archive_bytes(project_->path().toStdString());
        archive = QByteArray(bytes.data(), static_cast<qsizetype>(bytes.size()));
    } catch (const std::exception& refusal) {
        emit webSaveFailed(QString::fromUtf8(refusal.what()));
        return;
    }
    const QString name = downloadName();
    if (!WebFiles::download(archive, name)) {
        emit webSaveFailed(tr("The browser could not download %1").arg(name));
        return;
    }
    emit webDownloaded(name);
}

void Session::discardKeptChanges() {
    keep_timer_->stop();
    if (WebFiles::available() && !web_place_.key.isEmpty()) {
        WebStorage::instance()->dropRecovery(web_place_.key);
    }
}

void Session::keepChanges() {
    if (!WebFiles::available() || project_ == nullptr || !project_->modified()) {
        return;
    }
    // A running fit changes the project on every step: its state is kept once it stops changing.
    if (project_->fit() != nullptr && project_->fit()->running()) {
        keep_timer_->start();
        return;
    }
    QString root;
    try {
        root = QString::fromStdString(edi::fresh_archive_directory("kept"));
        edi::Project kept = project_->project();
        edi::save_project(kept, root.toStdString());
    } catch (const std::exception&) {
        if (!root.isEmpty()) {
            QDir(root).removeRecursively();
        }
        return;  // nothing kept this time; the next edit tries again
    }
    const WebPlace place = web_place_;
    WebStorage::instance()->write(place.key, place.kind, place.name, root, true,
                                  [root](const QJsonObject&) { QDir(root).removeRecursively(); });
}

void Session::setLastError(const QString& error) {
    if (error != last_error_) {
        last_error_ = error;
        emit lastErrorChanged();
    }
}

}  // namespace edi_app
