// SPDX-License-Identifier: BSD-3-Clause
#include "session.hpp"

#include <QCoreApplication>
#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QFileInfo>
#include <algorithm>

#include "app_info.hpp"
#include "edi/io.hpp"

namespace edi_app {
namespace {

const QString kExamples = QStringLiteral(":/edi/examples");

// "pd-neut-cwl" -> "powder, neutrons, constant wavelength" (the registry's documented id grammar).
QString technique(const QString& code) {
    const QStringList parts = code.split(QLatin1Char('-'));
    const QString form = parts.value(0) == QLatin1String("pd") ? QStringLiteral("powder") : parts.value(0);
    const QString probe = parts.value(1) == QLatin1String("neut")   ? QStringLiteral("neutrons")
                          : parts.value(1) == QLatin1String("xray") ? QStringLiteral("X-rays")
                                                                    : parts.value(1);
    const QString mode = parts.value(2) == QLatin1String("cwl")   ? QStringLiteral("constant wavelength")
                         : parts.value(2) == QLatin1String("tof") ? QStringLiteral("time-of-flight")
                                                                  : parts.value(2);
    return QStringLiteral("%1, %2, %3").arg(form, probe, mode);
}

}  // namespace

// ---- ExampleListModel ---------------------------------------------------------------------------

ExampleListModel::ExampleListModel(QObject* parent) : RowTableModel({"exampleId", "name", "description"}, parent) {
    QList<Row> rows;
    const QStringList ids = bundledIds();
    for (qsizetype i = 0; i < ids.size(); ++i) {
        // <technique>_<sample>[-<instrument>]_<variant>
        const QStringList parts = ids[i].split(QLatin1Char('_'));
        const QString name = parts.mid(1).join(QLatin1Char(' '));
        rows.append({reinterpret_cast<const void*>(i + 1), {ids[i], name, technique(parts.value(0))}});
    }
    setTableRows(rows);
}

QStringList ExampleListModel::bundledIds() {
    QFile index(kExamples + QStringLiteral("/index.txt"));
    if (!index.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return {};
    }
    return QString::fromUtf8(index.readAll()).split(QLatin1Char('\n'), Qt::SkipEmptyParts);
}

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
    : QObject(parent), examples_(new ExampleListModel(this)), warnings_(new WarningListModel(this)) {}

Session::~Session() = default;

bool Session::openProject(const QUrl& directory) {
    if (!directory.isLocalFile()) {
        setLastError(QStringLiteral("cannot open %1: only local project directories (file: URLs) can be opened")
                         .arg(directory.toString()));
        return false;
    }
    // A project in a folder this user may not write (a read-only tree) runs in a temporary copy, as an example does,
    // so a fit never writes into it; Save As writes the project where the user chooses.
    const QString source = directory.toLocalFile();
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
        QDir(target).removeRecursively();
        if (!copyTree(source, target)) {
            setLastError(QStringLiteral("cannot make a temporary copy of %1").arg(source));
            return false;
        }
        if (!open(target, {})) {
            return false;
        }
        read_only_copy_ = true;
        emit needsSaveAsChanged();
        return true;
    }
    return open(source, {});
}

bool Session::copyTree(const QString& source, const QString& target) {
    QDirIterator files(source, QDir::Files, QDirIterator::Subdirectories);
    while (files.hasNext()) {
        const QString file = files.next();
        const QString destination = target + file.mid(source.size());
        QDir().mkpath(QFileInfo(destination).absolutePath());
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
    QString location = project_->path();
    if (ApplicationInfo::demoIdentity() && !opened_example_.isEmpty() && extracted_ != nullptr && extracted_->isValid()
        && location.startsWith(extracted_->path())) {
        location.replace(0, extracted_->path().size(), QStringLiteral("<temporary>"));
    }
    return location;
}

bool Session::needsSaveAs() const {
    return project_ != nullptr && (project_->path().isEmpty() || !opened_example_.isEmpty() || read_only_copy_);
}

bool Session::save() {
    if (project_ == nullptr || needsSaveAs()) {
        setLastError(QStringLiteral("this project has no directory of its own yet: save it as"));
        return false;
    }
    const QString error = project_->saveTo(project_->path());
    setLastError(error);
    return error.isEmpty();
}

bool Session::saveAs(const QUrl& directory) {
    if (project_ == nullptr) {
        return false;
    }
    if (!directory.isLocalFile()) {
        setLastError(QStringLiteral("cannot save to %1: only local directories (file: URLs)").arg(directory.toString()));
        return false;
    }
    const QString error = project_->saveTo(directory.toLocalFile());
    setLastError(error);
    if (!error.isEmpty()) {
        return false;
    }
    // Saved where the user chose, the project is no longer the example's or the read-only tree's temporary copy.
    read_only_copy_ = false;
    if (!opened_example_.isEmpty()) {
        opened_example_.clear();
        emit openedExampleChanged();
    }
    emit projectLocationChanged();
    emit needsSaveAsChanged();
    return true;
}

bool Session::openExample(const QString& exampleId) {
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
    // A fresh copy per open, so edits to an opened example never leak into the next open of it.
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

bool Session::createProject(const QString& name, const QString& description) {
    ProjectViewModel* created = nullptr;
    try {
        created = new ProjectViewModel(edi::empty_project(name.toStdString(), description.toStdString()), this);
    } catch (const std::exception& refusal) {
        setLastError(QString::fromUtf8(refusal.what()));
        return false;
    }
    replaceProject(created, {}, {});
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

void Session::clearError() { setLastError({}); }

bool Session::open(const QString& directory, const QString& example) {
    QStringList warnings;
    ProjectViewModel* opened = nullptr;
    try {
        edi::Project project = edi::load_project(directory.toStdString(), [&warnings](const std::string& message) {
            warnings.append(QString::fromStdString(message));
        });
        opened = new ProjectViewModel(std::move(project), this);
    } catch (const std::exception& refusal) {
        setLastError(QString::fromUtf8(refusal.what()));  // the open project stays as it was
        return false;
    }
    replaceProject(opened, warnings, example);
    return true;
}

void Session::replaceProject(ProjectViewModel* project, const QStringList& warnings, const QString& example) {
    read_only_copy_ = false;
    // Every piece of the session's state — the project, its load warnings, the example it came from,
    // the cleared error — is in place before any consumer is told, so a handler of one signal reads
    // the new state of the others; then each property signals only if it changed.
    ProjectViewModel* previous = project_;
    const QString previous_example = opened_example_;
    project_ = project;
    opened_example_ = example;
    warnings_->setMessages(warnings);
    if (project_ != nullptr) {
        connect(project_, &ProjectViewModel::refused, this, &Session::setLastError);
        connect(project_, &ProjectViewModel::recalculated, this, &Session::syncCalculationMessages);
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
    emit needsSaveAsChanged();
    if (previous != nullptr) {
        previous->deleteLater();
        // Free the replaced project's view-models, and the page items the views released for them,
        // now rather than at the next event-loop turn: projects opened back to back (a script, a
        // test) must hold one project's pages, not every one opened so far.
        QCoreApplication::sendPostedEvents(nullptr, QEvent::DeferredDelete);
    }
}

void Session::setLastError(const QString& error) {
    if (error != last_error_) {
        last_error_ = error;
        emit lastErrorChanged();
    }
}

}  // namespace edi_app
