// SPDX-License-Identifier: BSD-3-Clause
#include "session.hpp"

#include <QCoreApplication>
#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QFileInfo>
#include <QPointer>
#include <QUuid>
#include "assistant_result.hpp"
#include "../../core/src/assistant_project_io.hpp"
#include "edi/calculation.hpp"
#include "edi/parameter_walk.hpp"
#include "../../core/src/canonical_encoding.hpp"
#include <bit>
#include <tuple>
#include <algorithm>
#include <utility>
#include <filesystem>

#include "app_info.hpp"
#include "edi/io.hpp"
#include "edi/scan.hpp"

namespace edi_app {
namespace {

const QString kExamples = QStringLiteral(":/edi/examples");

// Initial host construction moves ItemVec ownership, renewing collection
// generations without changing its scientific definition. Check that definition
// at this one preparation boundary; all later writes use strict final-owner stamps.
struct ResultDefinition {
    std::string model;
    using Parameter = std::tuple<std::string, std::string, std::uint64_t,
        std::optional<std::uint64_t>, bool, std::optional<std::uint64_t>,
        std::optional<std::uint64_t>, edi::Dependence, const edi::ParameterSpec*,
        std::uint64_t, std::uint64_t, std::uint64_t, std::uint64_t, std::uint64_t>;
    std::vector<Parameter> parameters;
    std::vector<std::tuple<std::string, std::string, std::uint64_t>> aliases;
    std::vector<std::tuple<std::string, std::string, std::uint64_t, bool, std::uint64_t>> constraints;
    bool operator==(const ResultDefinition&) const = default;
};
ResultDefinition result_definition(edi::Project& project) {
    ResultDefinition result;
    result.model = edi::detail::canonical_encoding(project);
    const auto bits = [](double v) { return std::bit_cast<std::uint64_t>(v); };
    const auto optional_bits = [&bits](std::optional<double> v) -> std::optional<std::uint64_t> {
        return v ? std::optional{bits(*v)} : std::nullopt;
    };
    for (const auto& entry : edi::parameter_entries(project)) {
        const auto& p = *entry.parameter;
        result.parameters.emplace_back(entry.block_name, entry.path, bits(p.value.get()),
            optional_bits(p.uncertainty.get()), p.free.get(), optional_bits(p.start_value.get()),
            optional_bits(p.start_uncertainty.get()), p.dependence, p.spec,
            p.value.written(), p.uncertainty.written(), p.free.written(),
            p.start_value.written(), p.start_uncertainty.written());
    }
    for (const auto& a : project.aliases)
        result.aliases.emplace_back(a->id.value(), a->parameter_unique_name.value(), a->parameter_unique_name.written());
    for (const auto& c : project.constraints)
        result.constraints.emplace_back(c->id.value(), c->expression.value(), c->expression.written(), c->enabled.get(), c->enabled.written());
    return result;
}

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

struct Session::SaveIntent {
    QString id;
    QPointer<ProjectViewModel> project;
    quint64 epoch;
    edi::WorkStamps stamps;
    std::shared_ptr<ImmutableAssistantResult> result;
    bool fresh;
    bool native = false;
    QUrl parent;
    QString leaf;
    std::function<bool()> current;
    std::function<bool(const QUrl&, const QString&)> start;
    std::function<void()> cancelled;
};

Session::Session(QObject* parent)
    : QObject(parent), assistant_(new AssistantViewModel(this)), examples_(new ExampleListModel(this)), warnings_(new WarningListModel(this)) {
    connect(assistant_, &AssistantViewModel::conversationRetired, this, &Session::retireAssistantIntent);
}

#ifndef __EMSCRIPTEN__
Session::Session(edi::assistant::native::NativeDependencies dependencies, QObject* parent)
    : QObject(parent), assistant_(new AssistantViewModel(std::move(dependencies), this)),
      examples_(new ExampleListModel(this)), warnings_(new WarningListModel(this)) {
    connect(assistant_, &AssistantViewModel::conversationRetired, this, &Session::retireAssistantIntent);
}
#endif

Session::~Session() {
    disconnect(assistant_, nullptr, this, nullptr);
    assistant_->setProject(nullptr);
    delete project_; project_ = nullptr; // Finish file-backed readers before destroying the snapshot lease.
}

bool Session::openProject(const QUrl& directory) {
    if (openProjectAt(directory)) {
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

bool Session::openProjectAt(const QUrl& directory) {
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
        if (!openCopy(source, target, {})) {
            return false;
        }
        read_only_copy_ = true;
        emit needsSaveAsChanged();
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
    QString location = project_->path();
    if (ApplicationInfo::demoIdentity() && !opened_example_.isEmpty() && extracted_ != nullptr && extracted_->isValid()
        && location.startsWith(extracted_->path())) {
        location.replace(0, extracted_->path().size(), QStringLiteral("<temporary>"));
    }
    return location;
}

bool Session::needsSaveAs() const {
    return project_ != nullptr && (fresh_result_ || project_->path().isEmpty() || !opened_example_.isEmpty() || read_only_copy_);
}

bool Session::save() {
    if (save_intent_ && save_intent_->native) {
        auto intent = std::move(save_intent_); // Consume before the real button action can reenter.
        const bool matches = !intent->fresh;
        return consumeAssistantSave(std::move(intent), matches);
    }
    if (project_ == nullptr || needsSaveAs()) {
        setLastError(QStringLiteral("this project has no directory of its own yet: save it as"));
        return false;
    }
    const QPointer<Session> receiver(this);
    const QPointer<ProjectViewModel> original(project_);
    const auto replacement = replacement_generation_;
    const auto current = [&] { return receiver && original && project_ == original && replacement_generation_ == replacement; };
    QString error;
    try { error = original->saveTo(original->path()); }
    catch (...) { error = tr("Saving could not confirm its full result. Inspect the saved directory before repeating."); }
    const bool saved = error.isEmpty();
    if (!current()) return saved;
    setLastError(error);
    if (!current()) return saved;
    if (saved) emit projectDirectoryUsed(QFileInfo(original->path()).absoluteFilePath());
    return saved;
}

bool Session::saveAs(const QUrl& directory) {
    if (fresh_result_) {
        setLastError(tr("Choose a parent directory and a fresh project folder through Save As.")); return false;
    }
    if (project_ == nullptr) {
        return false;
    }
    if (!directory.isLocalFile()) {
        setLastError(QStringLiteral("cannot save to %1: only local directories (file: URLs)").arg(directory.toString()));
        return false;
    }
    const QPointer<Session> receiver(this);
    const QPointer<ProjectViewModel> original(project_);
    const auto replacement = replacement_generation_;
    const auto current = [&] { return receiver && original && project_ == original && replacement_generation_ == replacement; };
    const QString destination = directory.toLocalFile();
    QString error;
    try { error = original->saveTo(destination); }
    catch (...) { error = tr("Saving could not confirm its full result. Inspect the saved directory before repeating."); }
    const bool saved = error.isEmpty();
    if (!current()) return saved;
    setLastError(error);
    if (!saved || !current()) return saved;
    // Saved where the user chose; only this original owner changes its presentation.
    read_only_copy_ = false;
    if (!opened_example_.isEmpty()) {
        opened_example_.clear();
        emit openedExampleChanged();
        if (!current()) return saved;
    }
    emit projectLocationChanged();
    if (!current()) return saved;
    emit needsSaveAsChanged();
    if (!current()) return saved;
    emit projectDirectoryUsed(QFileInfo(destination).absoluteFilePath());
    return saved;
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

struct Session::ProjectCreationOutcome {
    QPointer<ProjectViewModel> owner;
    quint64 replacement = 0;
    bool has_owner = false;
    QString error;
};
bool Session::createProject(const QString& name, const QString& description, const QString& location,
                            const QString& suRule, const QString& title, const QString& authors,
                            bool reportLibraries, const QString& assistantIntent) {
    return createProjectImpl(name, description, location, suRule, title, authors, reportLibraries, assistantIntent, nullptr);
}
QVariantMap Session::createProjectWithOutcome(const QString& name, const QString& description, const QString& location,
                            const QString& suRule, const QString& title, const QString& authors,
                            bool reportLibraries, const QString& assistantIntent) {
    const QPointer<Session> receiver(this);
    ProjectCreationOutcome outcome;
    const bool success = createProjectImpl(name, description, location, suRule, title, authors,
                                          reportLibraries, assistantIntent, &outcome);
    if (!receiver) return {};
    const bool current = (!outcome.has_owner || outcome.owner) && project_ == outcome.owner &&
        replacement_generation_ == outcome.replacement;
    return {{"success", success}, {"current", current}, {"error", outcome.error},
        {"owner", QVariant::fromValue(static_cast<QObject*>(outcome.owner.data()))},
        {"has_owner", outcome.has_owner}, {"replacement", QString::number(outcome.replacement)}};
}
bool Session::creationOutcomeCurrent(const QVariantMap& outcome) const {
    const auto original = outcome.value("owner").value<QObject*>();
    return (!outcome.value("has_owner").toBool() || original) && project_ == original &&
        outcome.value("replacement").toString() == QString::number(replacement_generation_);
}
bool Session::createProjectImpl(const QString& name, const QString& description, const QString& location,
                            const QString& suRule, const QString& title, const QString& authors,
                            bool reportLibraries, const QString& assistantIntent, ProjectCreationOutcome* outcome) {
    const QPointer<Session> receiver(this);
    if (outcome) { outcome->owner = project_; outcome->has_owner = project_ != nullptr; outcome->replacement = replacement_generation_; }
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
        const auto failure = QString::fromUtf8(refusal.what());
        if (outcome) outcome->error = failure;
        if (receiver) setLastError(failure);
        return false;
    }
    const QPointer<ProjectViewModel> originalCreated(created);
    const bool assistantCreation = !assistantIntent.isEmpty();
    try {
        if (assistantCreation && (!location.isEmpty() || !assistant_->prepareOrdinaryProjectCreation(created, assistantIntent))) {
            if (originalCreated) originalCreated->deleteLater();
            return false;
        }
    } catch (const std::exception&) {
        if (originalCreated) originalCreated->deleteLater();
        return false; // Original native receipt retains the failure; never use B's error.
    }
    if (!receiver || !originalCreated) return false;
    bool committed = false;
    quint64 committedReplacement = 0;
    const bool presented = replaceProject(created, {}, {}, false, {}, {}, assistantCreation, &committed, &committedReplacement);
    if (outcome && committed) {
        outcome->owner = originalCreated; outcome->has_owner = true; outcome->replacement = committedReplacement;
    }
    if (receiver && assistantCreation) assistant_->finishOrdinaryProjectCreation(originalCreated, assistantIntent, committed);
    const auto current = [&] { return receiver && originalCreated && project_ == originalCreated &&
        committed && replacement_generation_ == committedReplacement; };
    if (!presented || !current()) return false;
    if (location.isEmpty()) {
        return true;
    }
    const QString error = originalCreated->saveTo(location);
    if (outcome) outcome->error = error;
    if (!current()) return false;
    setLastError(error);
    if (!current() || !error.isEmpty()) return false;
    emit projectLocationChanged();
    if (!current()) return false;
    emit needsSaveAsChanged();
    if (!current()) return false;
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
    return !path.isEmpty() && QFileInfo(path).isDir();
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
        opened = new ProjectViewModel(std::move(project), this);
    } catch (const std::exception& refusal) {
        setLastError(QString::fromUtf8(refusal.what()));  // the open project stays as it was
        return false;
    }
    return replaceProject(opened, warnings, example);
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
        opened = new ProjectViewModel(std::move(project), this);
    } catch (const std::exception& refusal) {
        setLastError(QString::fromUtf8(refusal.what()));  // the open project stays as it was
        return false;
    }
    return replaceProject(opened, warnings, example);
}

bool Session::replaceProject(ProjectViewModel* project, const QStringList& warnings, const QString& example,
                             bool managedResult, std::shared_ptr<ImmutableAssistantResult> result,
                             std::optional<edi::WorkStamps> resultStamps, bool nativePrepared, bool* nativeCommitted, quint64* committedReplacement) {
    // Same-pointer/null nested replacements still supersede this stack. Capture
    // the candidate while live, before any assistant or Qt callback can retire it.
    const QPointer<ProjectViewModel> target(project);
    const bool has_target = project != nullptr;
    if (replacement_generation_ == UINT64_MAX) throw std::length_error("Session replacement identity is exhausted");
    const auto replacement = ++replacement_generation_;
    const QPointer<Session> receiver(this);
    const auto current = [&] { return receiver && replacement_generation_ == replacement && (!has_target || target); };
    const QPointer<ProjectViewModel> original(project_);
    retireAssistantIntent();
    if (!current()) return false;
    if (managedResult) {
        try { if (!assistant_->attachProject(target, true)) return false; }
        catch (...) {
            // Preparation failed before the host project commit. Restore the old
            // attachment fail-closed; never leave a borrowed candidate dangling.
            if (current() && project_ == original && (!original || !original->retired_))
                try { (void)assistant_->attachProject(original, false); } catch (...) {}
            throw;
        }
    }
    if (!current()) return false;
    auto previous_result = std::move(assistant_result_); // Transferred to the retired PVM until its actual deletion.
    assistant_result_ = std::move(result); fresh_result_ = bool(assistant_result_);
    result_edited_ = false; result_saved_stamps_ = std::move(resultStamps);
    read_only_copy_ = false;
    // Every piece of the session's state — the project, its load warnings, the example it came from,
    // the cleared error — is in place before any consumer is told, so a handler of one signal reads
    // the new state of the others; then each property signals only if it changed.
    ProjectViewModel* previous = project_;
    const QPointer<ProjectViewModel> previous_owner(previous);
    const bool previous_idle = previous == nullptr || (previous->publication_depth_ == 0 && !previous->editing_);
    if (previous != nullptr) {
        // Retire authority immediately, but never destroy a QObject whose
        // synchronous publication stack may have called close/replaceProject.
        disconnect(previous, nullptr, this, nullptr);
        previous->retire();
        previous->retired_result_ = std::move(previous_result);
        if (previous_idle) previous->deleteLater();
    }
    const QString previous_example = opened_example_;
    if (nativePrepared && !assistant_->commitNativeProject(target))
        throw std::runtime_error("Native creation owner changed before publication");
    project_ = target; // Adjacent to the nonallocating native Controller/receipt swap.
    if (nativeCommitted) *nativeCommitted = true; // Actual Session commit BEFORE any observer.
    if (committedReplacement) *committedReplacement = replacement;
    if (!managedResult && !nativePrepared && !assistant_->attachProject(target, false)) return false;
    // Attachment itself may close/open another owner, eagerly deleting target.
    // Stop BEFORE assigning this obsolete owner's example/warning metadata.
    if (!current() || project_ != target) return false;
    opened_example_ = example;
    warnings_->setMessages(warnings);
    if (!current() || project_ != target) return false;
    if (project_ != nullptr) {
        connect(project_, &ProjectViewModel::projectEdited, this, [this] {
            if (fresh_result_) result_edited_ = true;
            retireAssistantIntent();
        });
        connect(project_, &ProjectViewModel::refused, this, &Session::setLastError);
        connect(project_, &ProjectViewModel::recalculated, this, &Session::syncCalculationMessages);
        // A load's or a removal's account: each one listed as its own message.
        connect(project_, &ProjectViewModel::message, this, [this](const QString& text) {
            warnings_->post(QStringLiteral("project:%1").arg(++project_messages_), text, QStringLiteral("warning"));
        });
    }
    syncCalculationMessages();  // the new project calculated before it was connected
    if (!current() || project_ != target) return false;
    setLastError({});
    if (!current() || project_ != target) return false;
    if ((previous != nullptr) != (project_ != nullptr)) {
        emit hasProjectChanged();
        if (!current() || project_ != target) return false;
    }
    if (previous_example != opened_example_) {
        emit openedExampleChanged();
        if (!current() || project_ != target) return false;
    }
    emit projectChanged();
    if (!current() || project_ != target) return false;
    emit projectLocationChanged();
    if (!current() || project_ != target) return false;
    emit needsSaveAsChanged();
    if (previous_owner && previous_idle)
        QCoreApplication::sendPostedEvents(previous_owner.data(), QEvent::DeferredDelete);
    return current() && project_ == target;
}

bool Session::commitAssistantCurrentSave(ProjectViewModel* original,quint64 epoch,
    ProjectViewModel::NativeSavedState& prepared) noexcept {
    if(assistant_epoch_exhausted_ || assistant_epoch_!=epoch || !original || project_!=original)return false;
    if(!original->commitNativeSaved(prepared))return false;
    // Same owner, verified new saved directory. Keep the original protected
    // input lease/provenance alive; it no longer requires fresh-result Save As.
    read_only_copy_=false;fresh_result_=false;result_edited_=false;
    result_saved_stamps_.reset();save_intent_.reset();opened_example_.clear();
    return true;
}
bool Session::presentAssistantCurrentSave(ProjectViewModel* original,quint64 epoch) {
    const QPointer<Session> receiver(this);
    const QPointer<ProjectViewModel> target(original);
    const auto token=replacement_generation_;
    const auto current=[&]{return receiver && target && !assistant_epoch_exhausted_ && assistant_epoch_==epoch && project_==target && replacement_generation_==token;};
    if(!current())return false;
    setLastError({});if(!current())return false;
    emit openedExampleChanged();if(!current())return false;
    emit projectLocationChanged();if(!current())return false;
    emit needsSaveAsChanged();if(!current())return false;
    emit projectDirectoryUsed(original->path());return current();
}

void Session::retireExportIntent() noexcept {
    const bool native = save_intent_ && save_intent_->native;
    auto retired = std::move(save_intent_); // Release only this original intent, before external callbacks.
    const QPointer<Session> receiver(this);
    if (native) try { retired->cancelled(); } catch (...) {}
    if (receiver && native) try { emit assistantSaveChanged(); } catch (...) {}
}
void Session::retireAssistantIntent() noexcept {
    if (assistant_epoch_ == UINT64_MAX) assistant_epoch_exhausted_ = true;
    else ++assistant_epoch_;
    retireExportIntent(); // Terminal publication; callers fence any continuation.
}
bool Session::emptyAssistantOwner(quint64 epoch) const noexcept {
    return !assistant_epoch_exhausted_ && assistant_epoch_ == epoch && !project_;
}
bool Session::adoptAssistantResult(std::shared_ptr<ImmutableAssistantResult> result, quint64 epoch,
                                   const std::function<bool()>& current) {
    if (!result || !emptyAssistantOwner(epoch) || !current()) return false;
    // Load only the captured host lease; no runtime writer can change this tree.
    auto project = load_captured_assistant_result(*result);
    project.path.clear(); project.metadata.path.clear(); // The displayed unsaved model never writes into the sealed lease.
    const auto source_stamps = edi::work_stamps(project);
    const auto definition = result_definition(project);
    auto model = std::make_unique<ProjectViewModel>(std::move(project), this);
    const auto& owned = *model->assistantProject();
    const auto saved = edi::work_stamps(owned);
    if (definition != result_definition(*model->assistantProject()) ||
        source_stamps.experiment_inputs != saved.experiment_inputs ||
        source_stamps.structure_inputs != saved.structure_inputs ||
        source_stamps.experiments != saved.experiments || source_stamps.structures != saved.structures ||
        source_stamps.aliases != saved.aliases || source_stamps.constraints != saved.constraints ||
        source_stamps.edits != saved.edits || source_stamps.edits_at != saved.edits_at)
        throw std::runtime_error("Saved result changed during host model preparation");
    if (!emptyAssistantOwner(epoch) || !current()) return false;
    model->setModified(true);
    const QPointer<ProjectViewModel> adopted(model.release());
    const auto release_unattached = [&] {
        // A candidate that became a Session owner is retired/deleted by that
        // replacement, possibly still unwinding a real publication scope.
        if (adopted && project_ != adopted && !adopted->retired_) delete adopted.data();
    };
    try {
        const bool installed = replaceProject(adopted, {}, {}, true, std::move(result), saved);
        if (!installed) release_unattached();
        return installed;
    } catch (...) { release_unattached(); throw; }
}
std::unique_ptr<ProjectViewModel> Session::prepareAssistantNativeModel(edi::Project project, quint64 epoch,
                                                               const std::function<bool()>& current) {
    if (!emptyAssistantOwner(epoch) || !current()) return {};
    project.path.clear(); project.metadata.path.clear();
    // Same semantic-definition boundary as captured result adoption: moving
    // ItemVec generations is initialization, changing science is not.
    const auto definition = result_definition(project);
    const auto source = edi::work_stamps(project);
    auto model = std::make_unique<ProjectViewModel>(std::move(project), this);
    const auto final = edi::work_stamps(*model->assistantProject());
    if (definition != result_definition(*model->assistantProject()) ||
        source.experiment_inputs != final.experiment_inputs || source.structure_inputs != final.structure_inputs ||
        source.experiments != final.experiments || source.structures != final.structures ||
        source.aliases != final.aliases || source.constraints != final.constraints || source.edits != final.edits || source.edits_at != final.edits_at)
        throw std::runtime_error("Native creation changed during host model preparation");
    if (!emptyAssistantOwner(epoch) || !current()) return {};
    model->setModified(true);
    return model;
}
bool Session::commitAssistantNativeModel(std::unique_ptr<ProjectViewModel> model, quint64 epoch,
                                        const std::function<bool()>& current, bool& presentationComplete) {
    presentationComplete = false;
    if (!model || !emptyAssistantOwner(epoch) || !current()) return false;
    const QPointer<ProjectViewModel> adopted(model.get());
    if (replacement_generation_ == UINT64_MAX) throw std::length_error("Session replacement identity is exhausted");
    const auto replacement = replacement_generation_ + 1;
    bool committed = false;
    try {
        const bool published = replaceProject(adopted, {}, {}, false, {}, {}, true, &committed);
        if (!committed) return false; // Still a genuinely local, unexposed candidate.
        model.release(); // May already have been retired/deleted by a later observer.
        presentationComplete = published && adopted && project_ == adopted && replacement_generation_ == replacement;
        return true; // Real adoption, independently of later presentation/current owner.
    } catch (...) {
        if (committed) {
            model.release();
            if (replacement_generation_ == replacement && adopted && project_ == adopted)
                try { setLastError(tr("The native project opened, but some presentation did not complete.")); } catch (...) {}
            return true;
        }
        throw;
    }
}

QString Session::armAssistantSave(const QString& id, ProjectViewModel* original, quint64 epoch, bool fresh,
    const QUrl& parent, const QString& leaf, std::function<bool()> current,
    std::function<bool(const QUrl&, const QString&)> start, std::function<void()> cancelled) {
    if (id.isEmpty() || !original || project_ != original || assistant_epoch_exhausted_ || assistant_epoch_ != epoch ||
        save_intent_ || !current || !start || !cancelled || (fresh && ((!parent.isEmpty() && !parent.isLocalFile()) || leaf.isEmpty()))) return {};
    auto intent = std::make_unique<SaveIntent>();
    intent->id = id;
    intent->project = original; intent->epoch = epoch; // The original task owns its already admitted full stamps.
    intent->result = assistant_result_; intent->fresh = fresh; intent->native = true;
    intent->parent = parent; intent->leaf = leaf; intent->current = std::move(current);
    intent->start = std::move(start); intent->cancelled = std::move(cancelled);
    const QPointer<Session> receiver(this);
    const bool currentIntent = saveIntentCurrent(*intent);
    if (!receiver || !currentIntent || save_intent_ || project_ != original || assistant_epoch_exhausted_ || assistant_epoch_ != epoch) return {};
    const auto token = intent->id;
    save_intent_ = std::move(intent);
    emit assistantSaveChanged();
    return receiver && save_intent_ && save_intent_->id == token ? token : QString();
}
quint64 Session::assistantSaveIntentBytes() noexcept {
    // The adapter separately retains actual text/URL roles. Each original callback
    // capture is compile-time bounded there to two function-wrapper sizes.
    return sizeof(SaveIntent) + 2 * (sizeof(std::function<bool()>) +
        sizeof(std::function<bool(const QUrl&,const QString&)>) + sizeof(std::function<void()>));
}
bool Session::consumeAssistantSave(std::unique_ptr<SaveIntent> intent, bool selectionMatches, const QUrl& parent, const QString& leaf) noexcept {
    const QPointer<Session> receiver(this);
    bool started = false;
    try {
        const bool current = selectionMatches && saveIntentCurrent(*intent);
        if (!receiver) return false;
        if (current) started = intent->start(parent,leaf);
    } catch (...) {} // Worker submission fails before queue admission; no fabricated completion.
    if (!receiver) return started;
    if (!started) try { intent->cancelled(); } catch (...) {}
    if (receiver) try { emit assistantSaveChanged(); } catch (...) {}
    return started;
}
bool Session::assistantSaveReady() const { return save_intent_ && save_intent_->native; }
bool Session::assistantSaveAs() const { return assistantSaveReady() && save_intent_->fresh; }
QUrl Session::saveAsParent(const QString& token) const {
    return save_intent_ && save_intent_->native && save_intent_->fresh && save_intent_->id == token
        ? save_intent_->parent : QUrl();
}
QUrl Session::projectFolderUrl() const {
    return project_ && !project_->path().isEmpty() ? QUrl::fromLocalFile(project_->path()) : QUrl();
}
QString Session::saveAsSuggestion(const QString& token) const {
    return save_intent_ && save_intent_->id==token && save_intent_->native ? save_intent_->leaf : project_ ? project_->name() : QString{};
}
QString Session::beginSaveAs() {
    if (save_intent_ && save_intent_->native) {
        const auto token = save_intent_->id;
        const QPointer<Session> receiver(this);
        bool current = false;
        try { current = save_intent_->fresh && saveIntentCurrent(*save_intent_); } catch (...) {}
        return receiver && current && save_intent_ && save_intent_->id == token ? token : QString();
    }
    save_intent_.reset();
    if (!project_ || assistant_epoch_exhausted_ || project_->fit()->running() || !assistant_->resultSettledReady()) {
        setLastError(tr("Finish the current operation before choosing a Save As destination.")); return {};
    }
    if (fresh_result_ && (result_edited_ || !result_saved_stamps_ ||
        !edi::unchanged_since(*project_->assistantProject(), *result_saved_stamps_))) {
        setLastError(tr("Save the unchanged assistant result before editing. Edited-result export is not available in this first path.")); return {};
    }
    try {
        auto intent = std::make_unique<SaveIntent>();
        intent->id = QUuid::createUuid().toString(QUuid::WithoutBraces);
        intent->project = project_; intent->epoch = assistant_epoch_;
        intent->stamps = edi::work_stamps(*project_->assistantProject());
        intent->result = assistant_result_; intent->fresh = fresh_result_;
        const auto id = intent->id; save_intent_ = std::move(intent); return id;
    } catch (...) { setLastError(tr("Save As could not capture the current project.")); return {}; }
}
void Session::cancelSaveAs(const QString& intent) {
    if (!save_intent_ || save_intent_->id != intent) return;
    auto captured = std::move(save_intent_);
    const QPointer<Session> receiver(this);
    if (captured->native) {
        try { captured->cancelled(); } catch (...) {} // Exact original callback; never recapture a replacement.
        if (receiver) try { emit assistantSaveChanged(); } catch (...) {}
    }
}
bool Session::saveIntentCurrent(const SaveIntent& intent) const {
    if (intent.native) {
        if (assistant_epoch_exhausted_ || intent.epoch != assistant_epoch_ || !intent.project ||
            intent.project != project_ || intent.result != assistant_result_ || project_->fit()->running()) return false;
        const auto current = intent.current; // Reentrant retirement may destroy the stored intent.
        return current(); // External callback is terminal: no member access afterward.
    }
    return !assistant_epoch_exhausted_ && intent.epoch == assistant_epoch_ && intent.project &&
        intent.project == project_ && intent.result == assistant_result_ && intent.fresh == fresh_result_ &&
        !project_->fit()->running() && assistant_->resultSettledReady() &&
        edi::unchanged_since(*project_->assistantProject(), intent.stamps);
}
bool Session::saveAsCurrent(const QString& token) const {
    try { return save_intent_ && save_intent_->id == token && saveIntentCurrent(*save_intent_); }
    catch (...) { return false; }
}
bool Session::completeSaveAs(const QString& token, const QUrl& parent, const QString& leaf) {
    if (!save_intent_ || save_intent_->id != token) {
        setLastError(tr("This Save As request is no longer current; no project was exported.")); return false;
    }
    auto intent = std::move(save_intent_); // One-shot even if preparation refuses.
    const QPointer<Session> receiver(this);
    const auto current = [&] { return receiver && saveIntentCurrent(*intent); };
    if (intent->native) {
        const bool matches = intent->fresh && parent.isLocalFile() &&
            (intent->parent.isEmpty() || parent == intent->parent) && !leaf.isEmpty();
        return consumeAssistantSave(std::move(intent), matches, parent, leaf);
    }
    bool admitted = false;
    try { admitted = parent.isLocalFile() && current(); } catch (...) {}
    if (!receiver) return false;
    if (!admitted) {
        if (project_ == intent->project && assistant_epoch_ == intent->epoch)
            setLastError(tr("Save As was cancelled or its original state could not be verified."));
        return false;
    }
    if (!intent->fresh) {
        // Same initiating-owner guard for the pre-existing native picker path.
        if (!leaf.isEmpty()) { setLastError(tr("This project uses the ordinary directory Save As.")); return false; }
        return saveAs(parent);
    }
    if (!assistant_result_ || result_edited_ || !result_saved_stamps_ ||
        !edi::unchanged_since(*project_->assistantProject(), *result_saved_stamps_)) {
        setLastError(tr("This first export supports the unchanged opened assistant result. Save a fresh result before editing; edited-result export is not yet available.")); return false;
    }
    std::unique_ptr<AssistantResultExport> prepared;
    auto replacement = replacement_generation_;
    try {
        // Copy the exact bounded saved artifact; do not invoke an unbounded scratch writer.
        prepared = std::make_unique<AssistantResultExport>(*assistant_result_, parent.toLocalFile(), leaf);
        // All recovery strings/receipt buffers are allocated BEFORE disk publication.
        QString exported = prepared->destination();
        QJsonArray files = prepared->files();
        prepared->publish(current);
        if (!receiver) return false;
        const bool published_current = current();
        if (!receiver || !published_current) return false; // Committed old files persist; never overwrite a replacement's presentation.
        exported_result_.swap(exported); exported_files_.swap(files); // Nonallocating retention for this exact original owner.
        auto model = std::make_unique<ProjectViewModel>(prepared->reopen(), this);
        const bool reopened_current = current();
        if (!receiver) return false;
        if (!reopened_current) { setLastError(tr("Exported, but not opened: %1").arg(exported_result_)); return false; }
        const QPointer<ProjectViewModel> opened(model.release());
        if (replacement_generation_ == UINT64_MAX) { delete opened.data(); throw std::length_error("Session replacement identity is exhausted"); }
        replacement = replacement_generation_ + 1;
        const auto release_unattached = [&] {
            if (opened && (!receiver || project_ != opened) && !opened->retired_) delete opened.data();
        };
        try {
            if (!replaceProject(opened, {}, {}, true)) {
                release_unattached();
                // Actual export persists even when Clear cancels the managed
                // reopen. Only this same replacement may report that outcome.
                if (receiver && replacement_generation_ == replacement)
                    setLastError(tr("Exported, but not opened: %1").arg(exported_result_));
                return false;
            }
        } catch (...) { release_unattached(); throw; }
        if (!receiver || !opened || project_ != opened) return false;
        emit projectDirectoryUsed(exported_result_);
        return receiver && opened && project_ == opened;
    } catch (...) {
        if (!receiver || replacement_generation_ != replacement) return false;
        if (prepared && prepared->committed()) setLastError(tr("Exported, but not opened: %1").arg(prepared->destination()));
        else setLastError(tr("Save As was refused. Use a fresh folder name in a writable parent; the displayed project and existing destinations are preserved. An unpublished temporary export folder may remain for recovery."));
        return false;
    }
}

void Session::setLastError(const QString& error) {
    if (error != last_error_) {
        last_error_ = error;
        emit lastErrorChanged();
    }
}

}  // namespace edi_app
