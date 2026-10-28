// SPDX-License-Identifier: BSD-3-Clause
#include "session.hpp"
#include "assistant_result.hpp"
#include "../../core/src/canonical_encoding.hpp"
#include <limits>
#include <tuple>
#include <bit>
#include <QScopeGuard>

#include <QCoreApplication>
#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QFileInfo>
#include <QStandardPaths>
#include <QPointer>
#include <QUuid>
#include <algorithm>
#include <cmath>
#include <exception>
#include <string>
#include <utility>
#include <filesystem>

#include "app_info.hpp"
#include "web_files.hpp"
#include "web_storage.hpp"
#include "edi/display.hpp"
#include "edi/io.hpp"
#include "edi/project_archive.hpp"
#include "edi/parameter_walk.hpp"
#include "edi/scan.hpp"

namespace edi_app {
namespace {
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

struct Session::PendingOpenSource {
    QPointer<Session> owner;
    QString path;
    PendingOpenSource(Session& session,const QString& source):owner(&session),path(source) {
        if(!path.isEmpty())session.pending_open_sources_.append(path);
    }
    PendingOpenSource(const PendingOpenSource&)=delete;
    PendingOpenSource& operator=(const PendingOpenSource&)=delete;
    ~PendingOpenSource() {
        if(owner && !path.isEmpty()) {
            owner->pending_open_sources_.removeOne(path);
            owner->releaseTemporaryRoots({});
        }
    }
};

Session::Session(QObject* parent, AssistantWorkReportOptions options)
    : QObject(parent), work_report_options_(options), examples_(new ExampleListModel(this)), warnings_(new WarningListModel(this)) {
    assistant_ = new AssistantViewModel(this, options);
    initializeSession();
}
#ifndef __EMSCRIPTEN__
Session::Session(edi::assistant::native::NativeDependencies dependencies,QObject* parent,AssistantWorkReportOptions options)
    : QObject(parent),work_report_options_(options),examples_(new ExampleListModel(this)),warnings_(new WarningListModel(this)) {
    assistant_=new AssistantViewModel(std::move(dependencies),this,options);
    initializeSession();
}
#endif
void Session::initializeSession() {
    connect(assistant_, &AssistantViewModel::conversationRetired, this, &Session::retireAssistantIntent);
    // crysta's warnings reach Messages, never only the terminal (the owner, 2026-10-23).
    edi::collect_engine_warnings();
    // What a crash left in the temporary directory (edi ADR-0052).
    edi::remove_stale_archive_directories();
    // The web app keeps a project's unsaved state a few seconds after its last edit (edi ADR-0052 §9).
    keep_timer_ = new QTimer(this);
    keep_timer_->setSingleShot(true);
    keep_timer_->setInterval(3000);
    connect(keep_timer_, &QTimer::timeout, this, &Session::keepChanges);
    if (WebFiles::available()) {
        connect(WebStorage::instance(), &WebStorage::usableChanged, this, &Session::locationTextChanged);
    }
    // Commit the shared history lease only after this actual owner finished
    // every fallible initialization step (ADR-0056).
    assistant_->finishHistoryInitialization();
}

Session::~Session() {
    delete assistant_;assistant_=nullptr;
    // QObject normally deletes children after members. The workers/models must
    // stop before archive roots remove their files.
    project_=nullptr;
    while(auto* model=findChild<ProjectViewModel*>(QString{},Qt::FindDirectChildrenOnly)) {
        disconnect(model,nullptr,this,nullptr);model->blockSignals(true);delete model;
    }
    releaseTemporaryRoots({std::exchange(temporary_folder_,QString{}),std::exchange(web_copy_,QString{})});
}

void Session::releaseTemporaryFolder() {
    releaseTemporaryRoots({std::exchange(temporary_folder_,QString{})});
}

QString Session::prepareCopyRoot(const char* kind) {
    const auto root=QString::fromStdString(edi::fresh_archive_directory(kind));
    try { retainTemporaryRoots({root}); }
    catch(...) { edi::remove_archive_directory(root.toStdString());throw; }
    return root;
}

void Session::retainTemporaryRoots(const QStringList& candidates) {
    for(const auto& candidate:candidates)if(!candidate.isEmpty()) {
        const auto root=QString::fromStdString(edi::detail::archive_directory_root(candidate.toStdString()));
        if(!root.isEmpty() && !retained_temporary_roots_.contains(root))retained_temporary_roots_.append(root);
    }
}

void Session::releaseTemporaryRoots(const QStringList& candidates,const QString& openedFrom) noexcept {
    const QPointer<Session> receiver(this);const QPointer<ProjectViewModel> target(project_);
    const auto binding=replacement_generation_;
    const auto current=[&]{return receiver && project_==target && replacement_generation_==binding;};
    try {
        retainTemporaryRoots(candidates);
        if(retained_temporary_roots_.isEmpty())return;
        QStringList closure;
        const auto add=[&](const QString& path){if(!path.isEmpty() && !closure.contains(path))closure.append(path);};
        add(openedFrom);
        for(const auto& source:pending_open_sources_)add(source);
        const auto addModel=[&](ProjectViewModel* owner) {
            const auto& model=owner->project();
            add(owner->path());add(QString::fromStdString(model.metadata.path));
            add(QString::fromStdString(model.scan_data_root));add(QString::fromStdString(model.archive));
            if(model.sequential_fit.declared()) {
                const auto scan=edi::scan_datasets(model);add(QString::fromStdString(scan.directory));
                for(const auto& file:scan.files)add(QDir(QString::fromStdString(scan.directory)).filePath(QString::fromStdString(file)));
            }
            if(const auto& staged=owner->retired_result_) {
                add(staged->directory);add(staged->recovery_directory);
                if(staged->lease)add(staged->lease->path());
            }
            // The ordinary archive owner supplies the actual file/link closure.
            for(const auto& folder:{owner->path(),QString::fromStdString(model.scan_data_root)})if(!folder.isEmpty())
                for(const auto& file:edi::project_archive_members(folder.toStdString()))add(QDir(folder).filePath(QString::fromStdString(file)));
        };
        if(target) {
            addModel(target);
            add(archive_location_);if(read_only_copy_)add(read_only_source_);
            add(temporary_folder_);add(web_copy_);add(web_source_path_);
        }
        // Retirement cancels delivery, but an in-flight worker joins only in
        // the model's destructor. Every live child still owns its backing data.
        for(QObject* child:children())if(auto* held=qobject_cast<ProjectViewModel*>(child))
            if(held!=target)addModel(held);
        const auto physical=[](const QString& path) {
            std::error_code error;
            auto result=std::filesystem::weakly_canonical(QFileInfo(path).filesystemFilePath(),error);
            if(error)throw std::runtime_error("Temporary backing-root independence is unavailable");
            return result;
        };
        const auto used=[&](const QString& root) {
            const auto directory=physical(root);
            std::error_code error;
            const bool exists=std::filesystem::exists(directory,error);
            if(error)return true;
            for(const auto& path:closure) {
                auto cursor=physical(path);
                // Canonical ancestors plus filesystem equivalence cover aliases,
                // directory mounts, descendant paths and not-yet-written leaves.
                for(;;) {
                    if(exists && std::filesystem::exists(cursor,error)) {
                        if(std::filesystem::equivalent(directory,cursor,error))return true;
                        if(error)return true;
                    } else if(error)return true;
                    if(!exists) {
                        const auto [inside,outside]=std::mismatch(directory.begin(),directory.end(),cursor.begin(),cursor.end());
                        if(inside==directory.end())return true;
                    }
                    const auto parent=cursor.parent_path();if(parent==cursor || parent.empty())break;cursor=parent;
                }
            }
            return false;
        };
        for(qsizetype i=0;i<retained_temporary_roots_.size();) {
            if(!current())return;
            const auto root=retained_temporary_roots_.at(i);
            if(used(root)){++i;continue;}
            if(!current())return;
            edi::remove_archive_directory(root.toStdString());
            retained_temporary_roots_.removeAt(i);
        }
    }catch(...) {} // Unproved independence keeps the existing registered owner.
}

bool Session::openProject(const QUrl& location) {
    const QPointer<Session> receiver(this);
    const QPointer<ProjectViewModel> before(project_);
    const auto binding=replacement_generation_;
    if (openProjectAt(location)) return true;
    if(receiver && assistant_->sessionProjectRestorePending())return false;
    // A stale outer Open neither reports its successor's error as its own nor
    // decorates that successor. False does not imply no partial adoption.
    if(!receiver || replacement_generation_!=binding || project_!=before)return false;
    const auto message=last_error_.isEmpty()?tr("The project could not be opened"):last_error_;
    if(!receiver || replacement_generation_!=binding || project_!=before)return false;
    emit loadFailed(message);
    return false;
}

bool Session::openExample(const QString& exampleId) {
    const QPointer<Session> receiver(this);
    const QPointer<ProjectViewModel> before(project_);
    const auto binding=replacement_generation_;
    if (openExampleNamed(exampleId)) return true;
    // A stale outer Open neither reports its successor's error as its own nor
    // decorates that successor. False does not imply no partial adoption.
    if(!receiver || replacement_generation_!=binding || project_!=before)return false;
    const auto message=last_error_.isEmpty()?tr("The project could not be opened"):last_error_;
    if(!receiver || replacement_generation_!=binding || project_!=before)return false;
    emit loadFailed(message);
    return false;
}

bool Session::openProjectAt(const QUrl& location) {
    if (!location.isLocalFile()) {
        setLastError(QStringLiteral("cannot open %1: only local projects (file: URLs) can be opened")
                         .arg(location.toString()));
        return false;
    }
    QString source = location.toLocalFile();
    const PendingOpenSource pending(*this,source);
    // edi ADR-0052: a project record opens its folder; an archive is unpacked by the core into a temporary folder and
    // opens unsaved, so its first Save asks where to keep it.
    const QFileInfo given(source);
    if (given.isFile() && given.fileName() == QStringLiteral("project.edi")) {
        source = given.absolutePath();
    } else if (given.isFile() && edi::is_project_archive(source.toStdString())) {
        return open(source,{},[this,given] {
        const QPointer<Session> receiver(this);const QPointer<ProjectViewModel> target(project_);
        const auto binding=replacement_generation_;auto pathBinding=path_generation_;
        const auto current=[&]{return receiver && target && project_==target && replacement_generation_==binding && pathBinding!=UINT64_MAX && path_generation_==pathBinding;};
        temporary_folder_ = QString::fromStdString(target->project().scan_data_root);
        // The archive is the project's location and Save rewrites it, unless it cannot be written back: a read-only
        // file or folder, or the browser's uploaded copy (owner, 2026-10-25).
        const QFileInfo folder(given.absolutePath());
        if (!WebFiles::available() && given.isWritable() && folder.isWritable()) {
            if(pathBinding==UINT64_MAX)return false;
            ++pathBinding; // This Open's actual workIn owns one path notification.
            target->workIn(QString::fromStdString(target->project().scan_data_root));
            if(!current())return false;
            archive_location_ = given.absoluteFilePath();
            emit projectLocationChanged();if(!current())return false;
            emit needsSaveAsChanged();if(!current())return false;
            emit locationTextChanged();if(!current())return false;
            emit projectDirectoryUsed(archive_location_);if(!current())return false;
        } else {
            setOpenedArchive(given.fileName());
        }
        if(!current())return false;
        releaseTemporaryRoots({});
        return current();
        });
    }
    // A project in a folder this user may not write (a read-only tree) runs in a temporary copy, as an example does,
    // so a fit never writes into it; Save As writes the project where the user chooses.
    const QFileInfo folder(source), analysis(source + QStringLiteral("/analysis"));
    if (folder.isDir() && (!folder.isWritable() || (analysis.exists() && !analysis.isWritable()))) {
        QString copyRoot;
        try { copyRoot=prepareCopyRoot("read-only"); }
        catch(const std::exception& error) { setLastError(QString::fromUtf8(error.what()));return false; }
        const QPointer<Session> copyOwner(this);
        const auto cleanup=qScopeGuard([copyOwner,copyRoot]{if(copyOwner)copyOwner->releaseTemporaryRoots({copyRoot});});
        const QString target=QDir(copyRoot).filePath(folder.fileName());
        return openCopy(source,target,{},[this,folder] {
        const QPointer<Session> receiver(this);const QPointer<ProjectViewModel> openedOwner(project_);
        const auto binding=replacement_generation_;const auto pathBinding=path_generation_;
        const auto current=[&]{return receiver && openedOwner && project_==openedOwner && replacement_generation_==binding && pathBinding!=UINT64_MAX && path_generation_==pathBinding;};
        read_only_copy_ = true;
        read_only_source_ = folder.absoluteFilePath();
        emit needsSaveAsChanged();if(!current())return false;
        emit locationTextChanged();if(!current())return false;
        emit projectDirectoryUsed(folder.absoluteFilePath());if(!current())return false;
        if(!current())return false;
        releaseTemporaryRoots({});
        return current();
        });
    }
    return open(source,{},[this,folder] {
        const QPointer<Session> receiver(this);const QPointer<ProjectViewModel> target(project_);
        const auto binding=replacement_generation_;const auto pathBinding=path_generation_;
        emit projectDirectoryUsed(folder.absoluteFilePath());
        return receiver && target && project_==target && replacement_generation_==binding && pathBinding!=UINT64_MAX && path_generation_==pathBinding;
    });
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
    if (ApplicationInfo::demoIdentity() && !opened_example_.isEmpty()) {
        const auto root=QString::fromStdString(edi::detail::archive_directory_root(location.toStdString()));
        if(!root.isEmpty())location.replace(0,root.size(),QStringLiteral("<temporary>"));
    }
    return location;
}

QString Session::locationText() const {
    if (project_ == nullptr) {
        return {};
    }
    // The web app (edi ADR-0052 §9): the disk's folder or .zip by its name, else the browser's own storage, or the tab
    // alone where the browser keeps nothing (a private window may not).
    if (WebFiles::available()) {
        if (!webPlaceInBrowser()) {
            return web_place_.name;
        }
        return WebStorage::instance()->usable() ? tr("In this browser only")
                                                : tr("Only in this tab: this browser keeps nothing, use Save project as…");
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
        // Where the browser keeps nothing, nothing is saved: the project stays unsaved and the window says why
        // (owner, 2026-10-25).
        if (webPlaceInBrowser() && !WebStorage::instance()->usable()) {
            setLastError({});
            emit webStorageUnavailable();
            return false;
        }
        if (web_writing_) {
            setLastError(tr("The project is still being saved: save again once it is written."));
            return false;
        }
        // What the Save writes is staged on a copy and written to the place; the open project takes that snapshot only
        // once the place holds it (webSaveFinished says when).
        const QString name = project_->path().isEmpty() ? folderNameFor(project_->name())
                                                        : QFileInfo(project_->path()).fileName();
        Staged staged;
        if (!stageCopy("web", name, staged)) {
            return false;
        }
        const WebPlace place = web_place_;
        const QPointer<ProjectViewModel> saving = project_;
        const quint64 revision = project_->revision();
        web_writing_ = true;
        writeWebPlace(place, staged.folder, [this, saving, revision, staged, place](bool written) {
            web_writing_ = false;
            if (saving.isNull() || saving != project_) {
                QDir(staged.root).removeRecursively();
                return;
            }
            if (!written) {
                QDir(staged.root).removeRecursively();
                emit webSaveFinished(false);
                return;
            }
            const bool saved = takeWebSave(staged, revision);
            if (!saved) {
                QDir(staged.root).removeRecursively();
            } else {
                // Saved, the changes kept for a reload are no longer needed.
                WebStorage::instance()->dropRecovery(place.key);
                emit webSaved(place.kind);
            }
            emit webSaveFinished(saved);
        });
        return true;
    }
    if (project_ == nullptr || needsSaveAs()) {
        setLastError(QStringLiteral("this project has no directory of its own yet: save it as"));
        return false;
    }
    if (!archive_location_.isEmpty()) {
        // The archive is written from a staged copy, and the open project then takes that snapshot and works in its
        // folder: a refused archive leaves the project as it was.
        Staged staged;
        if (!stageCopy("saved", {}, staged) || !publishArchive(staged, archive_location_)) {
            return false;
        }
        emit projectDirectoryUsed(archive_location_);
        return true;
    }
    const QString error = project_->saveTo(project_->path());
    setLastError(error);
    if (!error.isEmpty()) {
        return false;
    }
    emit projectDirectoryUsed(QFileInfo(project_->path()).absoluteFilePath());
    return true;
}

QString Session::writeBackReports() {
    if (project_ == nullptr || archive_location_.isEmpty()) {
        return {};
    }
    try {
        edi::write_project_archive(project_->path().toStdString(), archive_location_.toStdString());
    } catch (const std::exception& refusal) {
        return tr("The reports were written, but %1 could not be rewritten: %2")
            .arg(archive_location_, QString::fromUtf8(refusal.what()));
    }
    return {};
}

bool Session::saveAs(const QUrl& directory) {
    if(directory.isLocalFile()) {
        const QFileInfo target(directory.toLocalFile());
        if(!target.exists() && !target.isSymLink())return saveProjectAsFresh(directory,false,false);
    }
    if (project_ == nullptr) {
        return false;
    }
    if (!directory.isLocalFile()) {
        setLastError(QStringLiteral("cannot save to %1: only local directories (file: URLs)").arg(directory.toString()));
        return false;
    }
    // A save refused before its write leaves the project where it was; one refused after it (reading it back) leaves it
    // working where it was written, unsaved, and the place follows it.
    const QString before = project_->path();
    const bool saved = saveInto(directory.toLocalFile());
    if (!saved && project_->path() == before) {
        return false;
    }
    archive_location_.clear();
    leaveTemporaryOrigin();
    releaseTemporaryFolder();
    emit projectLocationChanged();
    emit needsSaveAsChanged();
    emit locationTextChanged();
    emit projectDirectoryUsed(QFileInfo(directory.toLocalFile()).absoluteFilePath());
    return saved;
}

bool Session::saveInto(const QString& folder) {
    // A refused save leaves the project where it worked, unsaved (the core moves it only once written).
    const QString error = project_->saveTo(folder);
    setLastError(error);
    return error.isEmpty();
}

void Session::leaveTemporaryOrigin() {
    // Saved where the user chose, the project is no longer the example's, the archive's or the read-only tree's
    // temporary copy.
    read_only_copy_ = false;
    setOpenedArchive({});
    if (!opened_example_.isEmpty()) {
        opened_example_.clear();
        emit openedExampleChanged();
    }
}

// Same original staged native save/adopt owner; only fresh publication differs.
bool Session::saveProjectAsFresh(const QUrl& destination,bool zip,bool copy,bool notify) {
    const QPointer<Session> receiver(this);
    const QPointer<ProjectViewModel> target(project_);
    const auto replacement=replacement_generation_;
    const auto current=[&]{return receiver && target && receiver->project_==target &&
        receiver->replacement_generation_==replacement && !target->retired_;};
    if(!current())return false;
    if(!destination.isLocalFile() || destination.toLocalFile().isEmpty()) {
        setLastError(tr("A fresh project destination must be a local file or folder."));return false;
    }
    const QFileInfo requested(QDir::cleanPath(destination.toLocalFile()));
    if(requested.exists() || requested.isSymLink()) {
        setLastError(tr("The fresh project destination already exists; nothing was replaced."));return false;
    }
    if(const auto refusal=target->criticalEditRefusal();!refusal.isEmpty()){setLastError(refusal);return false;}
    bool editingSet=false;
    const auto editing=qScopeGuard([target,&editingSet]{if(editingSet && target) {
        target->editing_=false;
        if(target->retired_ && !target->publication_depth_)target->deleteLater();
    }});
    if(!copy) {
        const auto origin=std::exchange(target->assistant_save_origin_,0);
        target->notifyProjectEdited(origin);if(!current())return false;
        if(const auto refusal=target->saveRefusal();!refusal.isEmpty()){setLastError(refusal);return false;}
        target->editing_=true;editingSet=true;
        target->notifyProjectEdited(origin);
    }
    if(!current())return false;
    const auto revision=target->revision();
    Staged staged;
    if(!stageCopy(copy?"copy":"saved",QStringLiteral("project"),staged,requested.absolutePath()))return false;
    const auto release=qScopeGuard([receiver,root=staged.root]{if(receiver)receiver->releaseTemporaryRoots({root});});
    if(!current() || target->revision()!=revision)return false;
    const auto parent=QDir(requested.absolutePath()).canonicalPath();
    if(parent.isEmpty() || requested.fileName().isEmpty()) {
        if(current())setLastError(tr("The original fresh save parent is unavailable."));return false;
    }
    const auto where=parent+QLatin1Char('/')+requested.fileName();
    const PendingOpenSource pendingOrigin(*this,where);
    try {
        if(zip)edi::detail::write_project_archive_fresh(staged.folder.toStdString(),where.toStdString());
        else {
            staged.project->path=where.toStdString();staged.project->metadata.path=staged.project->path;
            if(staged.scan.listing)staged.scan.listing->relocate(staged.project,staged.folder,where);
            if(!current() || target->revision()!=revision)return false;
            edi::detail::publish_fresh_project_path(staged.folder.toStdString(),where.toStdString());
        }
    }catch(const std::exception& refusal) {if(current())setLastError(QString::fromUtf8(refusal.what()));return false;}
    if(!current())return false; // The file commit is real; never decorate a successor.
    if(copy){setLastError({});return current();}
    target->takeStaged(zip?staged.folder:where,*staged.project,staged.scan);
    if(!current())return false;
    leaveTemporaryOrigin();if(!current())return false;
    if(zip) {
        releaseTemporaryFolder();if(!current())return false;
        temporary_folder_=staged.root;archive_location_=where;
    }else {
        archive_location_.clear();releaseTemporaryFolder();if(!current())return false;
    }
    setLastError({});if(!current())return false;
    if(notify) {
        emit projectLocationChanged();if(!current())return false;
        emit needsSaveAsChanged();if(!current())return false;
        emit locationTextChanged();if(!current())return false;
        emit projectDirectoryUsed(where);
    }
    return current();
}

bool Session::saveProjectAs(const QUrl& target, bool zip, bool copy) {
    if(target.isLocalFile()) {
        const QFileInfo destination(target.toLocalFile());
        if(!destination.exists() && !destination.isSymLink())return saveProjectAsFresh(target,zip,copy);
    }
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
    // A project saved as a .zip works in a folder of its own and every Save rewrites the archive from it. The
    // archive is written from a staged copy before the project moves to it: a refused archive leaves the open project
    // where and as it was.
    Staged staged;
    if (!stageCopy("saved", {}, staged) || !publishArchive(staged, where)) {
        return false;
    }
    leaveTemporaryOrigin();
    archive_location_ = where;
    emit projectLocationChanged();
    emit needsSaveAsChanged();
    emit locationTextChanged();
    emit projectDirectoryUsed(where);
    return true;
}

bool Session::publishArchive(const Staged& staged, const QString& archive) {
    try {
        edi::write_project_archive(staged.folder.toStdString(), archive.toStdString());
    } catch (const std::exception& refusal) {
        edi::remove_archive_directory(staged.root.toStdString());
        setLastError(QString::fromUtf8(refusal.what()));
        return false;
    }
    // The archive holds the staged snapshot: the open project takes it and works in its folder from now on.
    project_->takeStaged(staged.folder, *staged.project, staged.scan);
    releaseTemporaryFolder();
    temporary_folder_ = staged.root;
    return true;
}

bool Session::takeWebSave(const Staged& staged, quint64 revision) {
    // The place holds the staged snapshot. The open project takes it and works in its folder, unless it was edited
    // meanwhile (the newer edits stay unsaved) or a fit started (the fit owns where it works).
    if (project_->revision() != revision) {
        emit webSaveFailed(tr("The project was written to its place, but it stays unsaved here: it changed while it was "
                              "written. Save again to keep the changes."));
        return false;
    }
    if (const QString refusal = project_->saveRefusal(); !refusal.isEmpty()) {
        emit webSaveFailed(tr("The project was written to its place, but it stays unsaved here: %1").arg(refusal));
        return false;
    }
    project_->takeStaged(staged.folder, *staged.project, staged.scan);
    releaseTemporaryFolder();
    const auto previousWeb=std::exchange(web_copy_,staged.root);
    web_source_path_=staged.folder;
    releaseTemporaryRoots({previousWeb});
    return true;
}

bool Session::stageCopy(const char* purpose, const QString& name, Staged& staged,const QString& parent) {
    // What a Save writes (round, adopt, recalculate, write), done on a copy in a folder of its own, once the project
    // may be saved at all: the open project is left as it is.
    if (const QString refusal = project_->saveRefusal(); !refusal.isEmpty()) {
        setLastError(refusal);
        return false;
    }
    try {
        staged.root = QString::fromStdString(parent.isEmpty()?edi::fresh_archive_directory(purpose):
            edi::detail::fresh_archive_directory_at(purpose,parent.toStdString()));
        staged.folder = name.isEmpty() ? staged.root : staged.root + QLatin1Char('/') + name;
        auto copy = std::make_shared<edi::Project>(project_->savedModel());
        QString copiedScratch;
        if(!parent.isEmpty() && !copy->path.empty()) {
            const auto source=QFileInfo(QString::fromStdString(copy->path)).canonicalFilePath();
            if(!source.isEmpty()) {
                copy->path=source.toStdString();copy->metadata.path=copy->path;
                const auto relative=QDir(source).relativeFilePath(staged.root);
                if(relative!=QStringLiteral("..") && !relative.startsWith(QStringLiteral("../")) && !QDir::isAbsolutePath(relative))
                    copiedScratch=QDir(staged.folder).filePath(relative);
            }
        }
        edi::save_project_as(*copy, staged.folder.toStdString());
        if(!copiedScratch.isEmpty() && QFileInfo::exists(copiedScratch) && !QDir().rmdir(copiedScratch))
            throw edi::IoError("cannot remove the native save's copied empty staging directory");
        edi::adopt_saved_project(*copy, staged.folder.toStdString());
        staged.project = std::move(copy);
    } catch (const std::exception& refusal) {
        if (!staged.root.isEmpty()) {
            edi::remove_archive_directory(staged.root.toStdString());
        }
        setLastError(QString::fromUtf8(refusal.what()));
        return false;
    }
    // Everything that can refuse happens before the save is published: a scan's results and its listing too.
    if (const QString refusal = project_->stageScan(staged.folder, *staged.project, staged.scan); !refusal.isEmpty()) {
        edi::remove_archive_directory(staged.root.toStdString());
        setLastError(refusal);
        return false;
    }
    return true;
}

bool Session::saveCopy(const QString& target, bool zip) {
    // What a Save writes (round, adopt, recalculate, write), done on a copy of the project: the open project keeps its
    // own location and values. A running fit owns where the project works, which a copy may name: it refuses first.
    if (const QString refusal = project_->saveRefusal(); !refusal.isEmpty()) {
        setLastError(refusal);
        return false;
    }
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
    QString copyRoot;
    try { copyRoot=prepareCopyRoot("example"); }
    catch(const std::exception& error) { setLastError(QString::fromUtf8(error.what()));return false; }
    const QPointer<Session> copyOwner(this);
    const auto cleanup=qScopeGuard([copyOwner,copyRoot]{if(copyOwner)copyOwner->releaseTemporaryRoots({copyRoot});});
    // Resource files are copied into an independent native folder for each Open.
    const QString target=QDir(copyRoot).filePath(exampleId+QStringLiteral("/project"));
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
    bool saved = false;
    QString path;
};
bool Session::createProject(const QString& name, const QString& description, const QString& location,
                            const QString& suRule, const QString& title, const QString& authors,
                            bool reportLibraries, const QString& assistantIntent) {
    return createProjectWithOutcome(name,description,location,suRule,title,authors,reportLibraries,assistantIntent).value("success").toBool();
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
    const QVariantMap result{{"success", success}, {"current", current}, {"error", outcome.error}, {"saved", outcome.saved}, {"path", outcome.path},
        {"owner", QVariant::fromValue(static_cast<QObject*>(outcome.owner.data()))},
        {"has_owner", outcome.has_owner}, {"replacement", QString::number(outcome.replacement)}};
    assistant_->finishOrdinaryProjectCreationOutcome(assistantIntent,result);
    return result;
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
        if (assistantCreation && !assistant_->prepareOrdinaryProjectCreation(created, assistantIntent, location)) {
            if (originalCreated) originalCreated->deleteLater();
            return false;
        }
    } catch (const std::exception& refusal) {
        // Retain this original preparation's factual reason in its local outcome,
        // never a replacement Session's mutable lastError.
        if (outcome) outcome->error=QString::fromUtf8(refusal.what());
        if (originalCreated) originalCreated->deleteLater();
        return false;
    }
    if (!receiver || !originalCreated) return false;
    bool committed = false;
    quint64 committedReplacement = 0;
    const bool presented = replaceProject(created, {}, {}, assistantCreation, &committed, &committedReplacement, !assistantCreation && project_==nullptr);
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
    const bool saved=saveProjectAsFresh(QUrl::fromLocalFile(location),false,false,false);
    const QString error=current()?(saved?QString{}:last_error_):QStringLiteral("The original Create save owner changed");
    if (outcome) { outcome->error = error; outcome->saved = error.isEmpty(); outcome->path = originalCreated ? originalCreated->path() : QString{}; }
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
    // A recent project is a folder or a .zip it was saved as (edi ADR-0052).
    return !path.isEmpty() && (QFileInfo(path).isDir() || edi::is_project_archive(path.toStdString()));
}

QUrl Session::projectDirectoryUrl(const QString& path) const {
    return path.isEmpty() ? QUrl() : QUrl::fromLocalFile(path);
}

void Session::clearError() { setLastError({}); }

QUrl Session::suggestedSaveTarget(bool zip) const {
    if (project_ == nullptr) {
        return {};
    }
    // A place of the user's own: the .zip the project saves to, or its folder; never a temporary copy.
    QString place = archive_location_;
    if (place.isEmpty() && opened_example_.isEmpty() && !read_only_copy_ && temporary_folder_.isEmpty()) {
        place = project_->path();
    }
    if (place.isEmpty() && read_only_copy_) {
        place = read_only_source_;
    }
    const QFileInfo info(place);
    const QString folder = !place.isEmpty() ? info.absolutePath()
                                            : QStandardPaths::writableLocation(QStandardPaths::DocumentsLocation);
    QString name = !place.isEmpty() ? info.completeBaseName() : folderNameFor(project_->name());
    if (!place.isEmpty() && info.suffix().compare(QStringLiteral("zip"), Qt::CaseInsensitive) != 0) {
        name = info.fileName();  // a folder's whole name, dots and all
    }
    return QUrl::fromLocalFile(QDir(folder).filePath(zip ? name + QStringLiteral(".zip") : name));
}

bool Session::open(const QString& directory,const QString& example,const std::function<bool()>& afterOpen) {
    const PendingOpenSource pending(*this,directory);
    const QPointer<Session> receiver(this);const QPointer<ProjectViewModel> before(project_);
    const auto binding=replacement_generation_;const auto pathBinding=path_generation_;
    const auto preparing=[&]{return receiver && project_==before && replacement_generation_==binding && pathBinding!=UINT64_MAX && path_generation_==pathBinding;};
    QStringList warnings;
    QPointer<ProjectViewModel> opened;
    auto adopted=std::make_shared<bool>(false);
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
        if(preparing())setLastError(QString::fromUtf8(refusal.what())); // Never overwrite a successor's error.
        return false;
    }
    if(!preparing()) {
        if(receiver && opened && project_!=opened)opened->deleteLater();
        return false;
    }
    const auto cleanup=qScopeGuard([&] {
        if(!*adopted && receiver && opened && project_!=opened && !assistant_->retainsSessionProject(opened))opened->deleteLater();
    });
    retainTemporaryRoots({QString::fromStdString(opened->project().scan_data_root)});
    connect(opened,&QObject::destroyed,this,[this]{releaseTemporaryRoots({});},Qt::QueuedConnection);
    const auto commit=[receiver,before,binding,pathBinding,opened,warnings,example,source=directory,afterOpen,adopted] {
        if(!receiver || !opened || receiver->project_!=before || receiver->replacement_generation_!=binding ||
            pathBinding==UINT64_MAX || receiver->path_generation_!=pathBinding)return false;
        const PendingOpenSource pending(*receiver,source);
        if(!receiver->replaceProject(opened,warnings,example,false,adopted.get(),nullptr,false,source))return false;
        return !afterOpen || afterOpen();
    };
    if(!assistant_->prepareSessionProjectRestore(opened,directory,commit))return false;
    return commit();
}

bool Session::openCopy(const QString& source,const QString& target,const QString& example,const std::function<bool()>& afterOpen) {
    const PendingOpenSource pending(*this,source);
    const QPointer<Session> receiver(this);const QPointer<ProjectViewModel> before(project_);
    const auto binding=replacement_generation_;const auto pathBinding=path_generation_;
    const auto preparing=[&]{return receiver && project_==before && replacement_generation_==binding && pathBinding!=UINT64_MAX && path_generation_==pathBinding;};
    QStringList warnings;
    QPointer<ProjectViewModel> opened;
    auto adopted=std::make_shared<bool>(false);
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
        if(QFileInfo::exists(target))throw std::runtime_error("The independent temporary copy target already exists");
        std::error_code pathError;
        auto cursor=std::filesystem::weakly_canonical(QFileInfo(target).filesystemFilePath(),pathError);
        if(pathError)throw std::runtime_error("The temporary copy target cannot be resolved independently");
        const auto original=QFileInfo(source).filesystemFilePath();
        for(;;) {
            if(std::filesystem::exists(cursor,pathError) && std::filesystem::equivalent(cursor,original,pathError))
                throw std::runtime_error("The temporary copy target must be outside its source folder");
            if(pathError)throw std::runtime_error("The temporary copy target independence cannot be proved");
            const auto parent=cursor.parent_path();if(parent.empty() || parent==cursor)break;cursor=parent;
        }
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
        if(preparing())setLastError(QString::fromUtf8(refusal.what())); // Never overwrite a successor's error.
        return false;
    }
    if(!preparing()) {
        if(receiver && opened && project_!=opened)opened->deleteLater();
        return false;
    }
    const auto cleanup=qScopeGuard([&] {
        if(!*adopted && receiver && opened && project_!=opened && !assistant_->retainsSessionProject(opened))opened->deleteLater();
    });
    retainTemporaryRoots({QString::fromStdString(opened->project().scan_data_root)});
    connect(opened,&QObject::destroyed,this,[this]{releaseTemporaryRoots({});},Qt::QueuedConnection);
    const auto commit=[receiver,before,binding,pathBinding,opened,warnings,example,source=source,afterOpen,adopted] {
        if(!receiver || !opened || receiver->project_!=before || receiver->replacement_generation_!=binding ||
            pathBinding==UINT64_MAX || receiver->path_generation_!=pathBinding)return false;
        const PendingOpenSource pending(*receiver,source);
        if(!receiver->replaceProject(opened,warnings,example,false,adopted.get(),nullptr,false,source))return false;
        return !afterOpen || afterOpen();
    };
    if(!assistant_->prepareSessionProjectRestore(opened,source,commit))return false;
    return commit();
}

void Session::setOpenedArchive(const QString& name) {
    const QPointer<Session> receiver(this);const QPointer<ProjectViewModel> target(project_);
    const auto binding=replacement_generation_;const auto pathBinding=path_generation_;
    if (name != opened_archive_) {
        opened_archive_ = name;
        emit openedArchiveChanged();
        if(!receiver || project_!=target || replacement_generation_!=binding || pathBinding==UINT64_MAX || path_generation_!=pathBinding)return;
        emit locationTextChanged();
    }
}

bool Session::replaceProject(ProjectViewModel* project, const QStringList& warnings, const QString& example, bool nativePrepared, bool* committed, quint64* committedReplacement, bool ordinaryEmptyCreate, const QString& openedFrom) {
    const QPointer<Session> receiver(this); const QPointer<ProjectViewModel> target(project);
    const bool hasTarget=project!=nullptr;
    const QPointer<ProjectViewModel> previous(project_);
    const QString previous_example=opened_example_;
    const bool previous_idle=!previous || (previous->publication_depth_==0 && !previous->editing_);
    const auto retire_previous=qScopeGuard([receiver,previous] {
        if(receiver && previous && receiver->project_!=previous && previous->retired_ && previous->publication_depth_==0 && !previous->editing_)previous->deleteLater();
    });
    // Keep both original cleanup obligations before any publication can reenter.
    retainTemporaryRoots({temporary_folder_,web_copy_});
    if(replacement_generation_==UINT64_MAX)throw std::length_error("Session replacement identity is exhausted");
    const auto replacement=++replacement_generation_;
    const auto pathBinding=path_generation_;
    auto current=[&]{return receiver && replacement_generation_==replacement && pathBinding!=UINT64_MAX && path_generation_==pathBinding && (!hasTarget || target);};
    retireAssistantIntent(); if(!current())return false;
    keep_timer_->stop();
    // A web open still being read no longer replaces anything.
    ++open_request_;
    const QString previous_web_copy = std::exchange(web_copy_, QString());
    // In the web app a project starts in the browser's own storage; an open from the disk or from a stored place
    // names its place once it is open.
    web_place_ = {};
    web_from_file_ = false;web_source_path_.clear();
    if (project != nullptr && WebFiles::available()) {
        web_place_ = {newWebKey(), QStringLiteral("browser"), folderNameFor(project->name())};
        connect(project, &ProjectViewModel::edited, keep_timer_, qOverload<>(&QTimer::start));
    }
    read_only_copy_ = false;
    read_only_source_.clear();
    archive_location_.clear();
    setOpenedArchive({});
    if(!current())return false;
    // Every piece of the session's state — the project, its load warnings, the example it came from,
    // the cleared error — is in place before any consumer is told, so a handler of one signal reads
    // the new state of the others; then each property signals only if it changed.
    if(previous) {
        disconnect(previous,nullptr,this,nullptr);
        connect(previous,&QObject::destroyed,this,[this]{releaseTemporaryRoots({});},Qt::QueuedConnection);
        previous->retire();
    }
    if(!current())return false;
    if(!nativePrepared){emit projectAboutToChange();if(!current())return false;}
    if(nativePrepared && !assistant_->commitNativeProject(target))return false;
    if(target)connect(target,&ProjectViewModel::pathChanged,this,[this,target] {
        if(target && project_==target && path_generation_!=UINT64_MAX)++path_generation_;
    });
    project_ = target;
    if(committed)*committed=true;
    if(committedReplacement)*committedReplacement=replacement;
    if(!nativePrepared && !assistant_->attachProject(target,false,ordinaryEmptyCreate && previous==nullptr))return false;
    if(!current() || project_!=target)return false;
    opened_example_ = example;
    warnings_->setMessages(warnings);
    if(!current() || project_!=target)return false;
    if (project_ != nullptr) {
        connect(project_, &ProjectViewModel::projectEdited, this, [this] {
            auto* source=qobject_cast<ProjectViewModel*>(sender());
            if(source!=project_ || assistant_->ordinarySaveNotification(source))return;
            retireAssistantIntent();
        });
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
    if(!current() || project_!=target)return false;
    setLastError({});
    if(!current() || project_!=target)return false;
    if ((previous != nullptr) != (project_ != nullptr)) {
        emit hasProjectChanged();
    }
    if (previous_example != opened_example_) {
        emit openedExampleChanged();
    }
    emit projectChanged();
    if(!current() || project_!=target)return false;
    emit projectLocationChanged();
    if(!current() || project_!=target)return false;
    emit locationTextChanged();
    if(!current() || project_!=target)return false;
    emit needsSaveAsChanged();
    if(!current() || project_!=target)return false;
    // The replaced project's temporary folder goes with it, once it is gone.
    const QString previous_folder = std::exchange(temporary_folder_, QString());
    if (previous != nullptr && previous_idle) {
        previous->deleteLater();
        // Free the replaced project's view-models, and the page items the views released for them,
        // now rather than at the next event-loop turn: projects opened back to back (a script, a
        // test) must hold one project's pages, not every one opened so far.
        QCoreApplication::sendPostedEvents(nullptr, QEvent::DeferredDelete);
    }
    if(!current() || project_!=target)return false;
    releaseTemporaryRoots({previous_folder,previous_web_copy},openedFrom);
    return current() && project_==target;
}

// ---- The web app's places (edi ADR-0052 §9) ---------------------------------------------------------

void Session::setWebPlace(const WebPlace& place) {
    const QPointer<Session> receiver(this);const QPointer<ProjectViewModel> target(project_);
    const auto binding=replacement_generation_;const auto pathBinding=path_generation_;
    web_place_ = place;
    emit locationTextChanged();
    if(!receiver || project_!=target || replacement_generation_!=binding || pathBinding==UINT64_MAX || path_generation_!=pathBinding)return;
    emit projectLocationChanged();
}

bool Session::openWebCopy(const QString& path, const WebPlace& place) {
    const PendingOpenSource pending(*this,path);
    const QPointer<Session> receiver(this);const QPointer<ProjectViewModel> before(project_);
    const auto initial=replacement_generation_;const auto initialPath=path_generation_;
    const auto preparing=[&]{return receiver && project_==before && replacement_generation_==initial && initialPath!=UINT64_MAX && path_generation_==initialPath;};
    const QFileInfo given(path);
    if (given.isFile() && edi::is_project_archive(path.toStdString())) {
        if (!open(path, {}))return false;
        const QPointer<ProjectViewModel> target(project_);const auto binding=replacement_generation_;auto pathBinding=path_generation_;
        const auto current=[&]{return receiver && target && project_==target && replacement_generation_==binding && pathBinding!=UINT64_MAX && path_generation_==pathBinding;};
        const QString unpacked=QString::fromStdString(target->project().scan_data_root);
        if(pathBinding==UINT64_MAX)return false;
        ++pathBinding; // This Open's actual workIn owns one path notification.
        target->workIn(unpacked);
        if(!current())return false;
        temporary_folder_=unpacked;
        setWebPlace({place.key.isEmpty()?newWebKey():place.key,place.kind,place.name});
        return current();
    }
    QString error;
    const QString folder=WebFiles::projectIn(path,error);
    if(!preparing())return false;
    if(folder.isEmpty()) {
        setLastError(QStringLiteral("cannot open %1: %2").arg(given.fileName(),error));
        return false;
    }
    if(!open(folder,{}))return false;
    const QPointer<ProjectViewModel> target(project_);const auto binding=replacement_generation_;const auto pathBinding=path_generation_;
    setWebPlace({place.key.isEmpty()?newWebKey():place.key,place.kind,place.name});
    return receiver && target && project_==target && replacement_generation_==binding && pathBinding!=UINT64_MAX && path_generation_==pathBinding;
}

void Session::openWebProject(const QString& kind) {
    const QPointer<Session> receiver(this);const QPointer<ProjectViewModel> before(project_);
    const auto binding=replacement_generation_;
    const auto current=[&]{return receiver && project_==before && replacement_generation_==binding;};
    QString root;
    try {
        root = QString::fromStdString(edi::fresh_archive_directory("web"));
    } catch (const std::exception& refusal) {
        if(!current())return;
        setLastError(QString::fromUtf8(refusal.what()));
        if(current())emit loadFailed(last_error_);
        return;
    }
    WebStorage::instance()->pickOpen(kind, root, webOpenAnswer(root));
}

std::function<bool(const WebStorageAnswer&)> Session::openRequest(const QString& root) {
    // A stale/duplicate answer cannot clean up a root a replacement may now own.
    const QPointer<Session> receiver(this);
    const quint64 request=++open_request_;
    const QPointer<ProjectViewModel> before=project_;
    const quint64 revision=project_!=nullptr?project_->revision():0;
    return [this,receiver,root,request,before,revision](const WebStorageAnswer& answer) {
        const auto current=[&]{return receiver && request==open_request_ && before==project_;};
        if(!current())return false;
        if(!answer.ok) {
            if(web_copy_!=root)QDir(root).removeRecursively();
            if(!current())return false;
            if(!answer.cancelled) {
                setLastError(answer.message);
                if(current())emit loadFailed(last_error_);
            }
            return false;
        }
        if(project_ && project_->modified() && project_->revision()!=revision) {
            if(web_copy_!=root)QDir(root).removeRecursively();
            if(!current())return false;
            const auto message=tr("%1 was not opened: the open project was changed while it was read. Open it again to replace the project.").arg(answer.name);
            if(!current())return false;
            setLastError(message);
            if(current())emit loadFailed(last_error_);
            return false;
        }
        return true;
    };
}

WebStorage::Answer Session::webOpenAnswer(const QString& root, bool fromFile, bool recovery) {
    const QPointer<Session> receiver(this);
    return [this,receiver,root,fromFile,recovery,current=openRequest(root)](const WebStorageAnswer& answer) {
        if(!receiver || !current(answer))return;
        const PendingOpenSource pending(*this,answer.path);
        const QPointer<ProjectViewModel> before(project_);const auto beforeBinding=replacement_generation_;
        const WebPlace place{answer.key,answer.kind,answer.name};
        if(!openWebCopy(answer.path,place)) {
            if(!receiver || project_!=before || replacement_generation_!=beforeBinding)return;
            // A failed parse owns no replacement. A false publication after
            // adoption retains its original staging, never rolls back live data.
            if(web_copy_!=root)QDir(root).removeRecursively();
            if(!receiver || project_!=before || replacement_generation_!=beforeBinding)return;
            const auto message=last_error_;
            emit loadFailed(message);
            return;
        }
        const QPointer<ProjectViewModel> target(project_);const auto binding=replacement_generation_;const auto pathBinding=path_generation_;
        const auto owned=[&]{return receiver && target && project_==target && replacement_generation_==binding && pathBinding!=UINT64_MAX && path_generation_==pathBinding;};
        web_copy_=root;web_from_file_=fromFile;web_source_path_=answer.path;
        if(recovery) {
            target->markUnsaved();
            if(!owned())return;
        }
        releaseTemporaryRoots({});
        if(!owned())return;
        if(!fromFile)return; // Stored/recovery places already own their backing record.
        const bool persist=web_place_.kind==QStringLiteral("browser") && WebStorage::instance()->usable();
        if(!owned())return;
        if(persist)writeWebPlace(web_place_,target->path(),nullptr);
    };
}

void Session::openStoredProject(const QString& key, bool recovery) {
    const QPointer<Session> receiver(this);const QPointer<ProjectViewModel> before(project_);
    const auto binding=replacement_generation_;
    const auto current=[&]{return receiver && project_==before && replacement_generation_==binding;};
    QString root;
    try {
        root=QString::fromStdString(edi::fresh_archive_directory("web"));
    }catch(const std::exception& refusal) {
        if(!current())return;
        setLastError(QString::fromUtf8(refusal.what()));
        if(current())emit loadFailed(last_error_);
        return;
    }
    WebStorage::instance()->load(key,recovery,root,webOpenAnswer(root,false,recovery));
}

bool Session::webPlaceInBrowser() const {
    return web_place_.kind != QStringLiteral("folder") && web_place_.kind != QStringLiteral("zip");
}

void Session::writeWebPlace(const WebPlace& place, const QString& folder, const std::function<void(bool)>& done) {
    keep_timer_->stop();
    // The page writes one place's jobs in the order they are sent, so a later keep or discard is never overtaken.
    const QPointer<ProjectViewModel> project = project_;
    WebStorage::instance()->write(
        place.key, place.kind, place.name, folder, false, [this, place, project, done](const WebStorageAnswer& answer) {
            if (!answer.ok) {
                // The browser's own words ("UnknownError", "QuotaExceededError") say nothing to the user: the place
                // is named instead.
                if (place.kind == QStringLiteral("browser")) {
                    WebStorage::instance()->markUnusable();
                    emit webSaveFailed(tr("This browser would not keep the project: its storage is not available here "
                                          "(a private window, for example) or is full. Use Save project as… to "
                                          "download it."));
                } else {
                    emit webSaveFailed(
                        tr("The project could not be written to %1: %2").arg(place.name, answer.message));
                }
                if (!project.isNull() && project == project_) {
                    keepChanges();
                }
            }
            if (done) {
                done(answer.ok);
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
    // One browser write to a place at a time, a copy's too: a picked place may be the one the project works for, and
    // its new key proves nothing else. A second waits until the first is written.
    const QString busy = tr("The project is still being saved: save again once it is written.");
    if (web_writing_) {
        emit webSaveFailed(busy);
        return;
    }
    // A running fit owns where the project works, which the picked place may name: refused before any picker.
    if (const QString refusal = project_->saveRefusal(); !refusal.isEmpty()) {
        setLastError(refusal);
        emit webSaveFailed(refusal);
        return;
    }
    const QPointer<ProjectViewModel> before = project_;
    WebStorage::instance()->pickSave(kind, downloadName(), web_place_.key, [this, before, kind, copy, busy](
                                                                               const WebStorageAnswer& answer) {
        if (before != project_ || project_ == nullptr || !answer.ok) {
            if (before == project_ && !answer.cancelled) {
                emit webSaveFailed(answer.message);
            }
            return;
        }
        if (web_writing_) {
            emit webSaveFailed(busy);
            return;
        }
        const WebPlace place{answer.key, kind,
                             answer.name};
        // What a Save writes, staged on a copy of the project in a memory folder of its own.
        Staged staged;
        if (!stageCopy(copy ? "copy" : "web",
                       folderNameFor(kind == QStringLiteral("zip") ? project_->name() : place.name), staged)) {
            emit webSaveFailed(last_error_);
            return;
        }
        const QPointer<ProjectViewModel> saving = project_;
        const quint64 revision = project_->revision();
        web_writing_ = true;
        writeWebPlace(place, staged.folder, [this, saving, revision, staged, place, copy](bool written) {
            web_writing_ = false;
            if (saving.isNull() || saving != project_) {
                QDir(staged.root).removeRecursively();
                return;
            }
            // A copy leaves the project where it is; a moving Save as moves it only if it takes the written snapshot.
            if (copy || !written || !takeWebSave(staged, revision)) {
                QDir(staged.root).removeRecursively();
                if (copy && written) {
                    // The copy holds the snapshot taken before a fit that started meanwhile; the project stays
                    // unsaved here either way, and says so while the fit runs.
                    if (const QString refusal = project_->saveRefusal(); !refusal.isEmpty()) {
                        emit webSaveFailed(
                            tr("The project was written to its place, but it stays unsaved here: %1").arg(refusal));
                    } else {
                        emit webSaved(place.kind);
                    }
                }
                if (!copy) {
                    emit webSaveFinished(false);
                }
                return;
            }
            leaveTemporaryOrigin();
            setWebPlace(place);
            emit webSaved(place.kind);
            emit webSaveFinished(true);
        });
    });
}

void Session::downloadWebProject() {
    if (project_ == nullptr) {
        return;
    }
    // A copy, as a Save writes it, handed to the browser as a .zip: the project and the browser's storage are left as
    // they are (owner, 2026-10-25).
    QByteArray archive;
    std::string folder;
    try {
        folder = edi::fresh_archive_directory("download");
        edi::Project copy = project_->project();
        edi::save_project(copy, folder);
        edi::adopt_saved_project(copy, folder);
        const std::string bytes = edi::project_archive_bytes(folder);
        archive = QByteArray(bytes.data(), static_cast<qsizetype>(bytes.size()));
    } catch (const std::exception& refusal) {
        if (!folder.empty()) {
            edi::remove_archive_directory(folder);
        }
        emit webSaveFailed(QString::fromUtf8(refusal.what()));
        return;
    }
    edi::remove_archive_directory(folder);
    const QString name = downloadName();
    if (!WebFiles::download(archive, name)) {
        emit webSaveFailed(tr("The browser could not download %1").arg(name));
        return;
    }
    emit webDownloaded(name, web_from_file_);
}

void Session::discardKeptChanges() {
    keep_timer_->stop();
    if (WebFiles::available() && !web_place_.key.isEmpty()) {
        WebStorage::instance()->dropRecovery(web_place_.key);
    }
}

void Session::keepChanges() {
    if (!WebFiles::available() || project_ == nullptr || !project_->modified() || !WebStorage::instance()->usable()) {
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
                                  [root](const WebStorageAnswer&) { QDir(root).removeRecursively(); });
}

void Session::setLastError(const QString& error) {
    if (error != last_error_) {
        last_error_ = error;
        emit lastErrorChanged();
    }
}

namespace {

// A bridge answer as text. A page asking for an item the dictionary lacks is a defect of the page: it is reported as
// a warning, which fails every warning-strict test, and shows nothing, or the stored token for a selector, rather than
// a plausible stand-in.
template <typename Call>
QString from_bridge(Call&& call, const QString& fallback = QString()) {
    try {
        return QString::fromStdString(call());
    } catch (const std::exception& error) {
        qWarning("dictionary: %s", error.what());
        return fallback;
    }
}

}  // namespace

QString Session::label(const QString& uid, const QString& variant) const {
    return from_bridge([&] { return edi::label(uid.toStdString(), variant.toStdString()); });
}

QString Session::units(const QString& uid, const QString& variant) const {
    return from_bridge([&] { return edi::units_label(uid.toStdString(), variant.toStdString()); });
}

QString Session::tooltip(const QString& uid, const QString& variant) const {
    return from_bridge([&] { return edi::tooltip(uid.toStdString(), variant.toStdString()); });
}

QString Session::optionLabel(const QString& uid, const QString& token) const {
    return from_bridge([&] { return edi::option_label(uid.toStdString(), token.toStdString()); }, token);
}

QString Session::optionTooltip(const QString& uid, const QString& token) const {
    return from_bridge([&] { return edi::option_tooltip(uid.toStdString(), token.toStdString()); });
}

QString Session::categoryTitle(const QString& id) const {
    return from_bridge([&] { return edi::category_label(id.toStdString()); });
}

// A number that is not finite (an excluded row's computed value, an empty range) has no spelling: it shows nothing.
QString Session::written(const QString& uid, double value) const {
    if (!std::isfinite(value)) {
        return {};
    }
    return from_bridge([&] { return edi::file_text(uid.toStdString(), value); });
}

QString Session::display(const QString& uid, double value, const QString& variant) const {
    if (!std::isfinite(value)) {
        return {};
    }
    return from_bridge([&] { return edi::display_text(uid.toStdString(), value, variant.toStdString()); });
}

namespace {

// A value with an s.u., rounded by it under `rule`, as a fitted value shows (edi::fitted_text); empty for a bad item.
edi::FileText fitted(const QString& uid, double value, double su, const std::string& rule) {
    try {
        return edi::fitted_text(uid.toStdString(), value, su, rule);
    } catch (const std::exception& error) {
        qWarning("dictionary: %s", error.what());
        return {};
    }
}

bool has_su(double value, double su) { return std::isfinite(su) && su > 0.0 && std::isfinite(value); }

}  // namespace

QString Session::valueText(const QString& uid, double value, double su) const {
    // Without an s.u., the value by its item's display format.
    if (!has_su(value, su)) {
        return display(uid, value);
    }
    const std::string rule = project_ != nullptr ? project_->suRule().toStdString() : std::string(edi::kDefaultSuRule);
    return QString::fromStdString(fitted(uid, value, su, rule).value);
}

QString Session::suText(const QString& uid, double value, double su) const {
    if (!has_su(value, su)) {
        return {};
    }
    const std::string rule = project_ != nullptr ? project_->suRule().toStdString() : std::string(edi::kDefaultSuRule);
    return QString::fromStdString(fitted(uid, value, su, rule).su);
}

}  // namespace edi_app

void edi_app::Session::retireAssistantIntent() noexcept {
    if(assistant_epoch_==UINT64_MAX)assistant_epoch_exhausted_=true;else ++assistant_epoch_;
    if(assistant_save_choice_){const auto token=assistant_save_choice_->token;try{cancelAssistantSaveAs(token);}catch(...) {}}
}
bool edi_app::Session::assistantOwner(quint64 epoch,ProjectViewModel* expected) const noexcept {
    return !assistant_epoch_exhausted_ && assistant_epoch_==epoch && project_==expected;
}
bool edi_app::Session::emptyAssistantOwner(quint64 epoch) const noexcept {
    return assistantOwner(epoch,nullptr);
}
namespace edi_app {
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
        const bool published = replaceProject(adopted, {}, {}, true, &committed);
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

}

namespace edi_app {
bool Session::assistantSaveAsCurrent(const QString& token) const {
    const auto* choice=assistant_save_choice_.get();
    return choice && choice->token==token && choice->owner && choice->owner==project_ &&
        choice->epoch==assistant_epoch_ && !assistant_epoch_exhausted_ && choice->current && choice->current();
}
QUrl Session::assistantSaveAsTarget(const QString& token,bool zip) const {
    const auto ordinary=suggestedSaveTarget(zip);
    if(!assistantSaveAsCurrent(token) || assistant_save_choice_->suggestion.isEmpty())return ordinary;
    return QUrl::fromLocalFile(QFileInfo(ordinary.toLocalFile()).dir().filePath(assistant_save_choice_->suggestion+(zip?QStringLiteral(".zip"):QString())));
}
bool Session::requestAssistantSaveAs(const QString& token,const QString& name,ProjectViewModel* owner,quint64 epoch,
    std::function<bool()> current,std::function<bool(const QUrl&,bool,bool)> accepted,std::function<void()> cancelled) {
    if(token.isEmpty() || assistant_save_choice_ || !owner || project_!=owner || assistant_epoch_exhausted_ || assistant_epoch_!=epoch || !current || !current())return false;
    auto choice=std::make_unique<AssistantSaveChoice>();choice->token=token;choice->suggestion=name;choice->owner=owner;choice->epoch=epoch;
    choice->current=std::move(current);choice->accepted=std::move(accepted);choice->cancelled=std::move(cancelled);assistant_save_choice_=std::move(choice);
    emit assistantSaveAsRequested(token);return true;
}
void Session::cancelAssistantSaveAs(const QString& token) {
    if(!assistant_save_choice_ || assistant_save_choice_->token!=token)return;
    auto choice=std::move(assistant_save_choice_);
    if(choice->cancelled)choice->cancelled();
}
bool Session::completeAssistantSaveAs(const QString& token,const QUrl& target,bool zip,bool copy) {
    if(!assistantSaveAsCurrent(token))return false;
    auto choice=std::move(assistant_save_choice_);
    return choice->accepted && choice->accepted(target,zip,copy);
}
}
