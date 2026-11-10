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
#include <QPair>
#include <QPointer>
#include <QUuid>
#include <algorithm>
#include <memory>
#include <cmath>
#include <exception>
#include <string>
#include <utility>
#include <filesystem>
#if !defined(_WIN32)
#include <sys/stat.h>
#endif

#include "app_info.hpp"
#include "web_files.hpp"
#include "web_storage.hpp"
#include "edi/display.hpp"
#include "edi/io.hpp"
#include "edi/project_archive.hpp"
#include "edi/parameter_walk.hpp"
#include "edi/scan.hpp"
#include "run_log.hpp"

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
    online_sources_ = new OnlineSourcesModel(this);
    online_search_ = new OnlineSearch(online_sources_, this);
    // The example projects come from the collections (ADR-0068); the bundled catalogue alone lists them.
    collection_examples_ = new CollectionExamples(online_sources_, this);
    connect(collection_examples_, &CollectionExamples::noticeChanged, this, &Session::examplesNoticeChanged);
#if EDI_APP_ASSISTANT
    assistant_ = new AssistantViewModel(this, options);
#endif
    initializeSession();
}
#if EDI_APP_ASSISTANT && !defined(__EMSCRIPTEN__)
Session::Session(edi::assistant::native::NativeDependencies dependencies,QObject* parent,AssistantWorkReportOptions options)
    : QObject(parent),work_report_options_(options),examples_(new ExampleListModel(this)),warnings_(new WarningListModel(this)) {
    online_sources_ = new OnlineSourcesModel(this);
    online_search_ = new OnlineSearch(online_sources_, this);
    // The example projects come from the collections (ADR-0068); the bundled catalogue alone lists them.
    collection_examples_ = new CollectionExamples(online_sources_, this);
    connect(collection_examples_, &CollectionExamples::noticeChanged, this, &Session::examplesNoticeChanged);
    assistant_=new AssistantViewModel(std::move(dependencies),this,options);
    initializeSession();
}
#endif
void Session::initializeSession() {
#if EDI_APP_ASSISTANT
    connect(assistant_, &AssistantViewModel::conversationRetired, this, &Session::retireAssistantIntent);
    connect(this, &Session::projectDirectoryUsed, assistant_, &AssistantViewModel::projectSaved);
#endif
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
    // every fallible initialization step (ADR-0057).
#if EDI_APP_ASSISTANT
    assistant_->finishHistoryInitialization();
#endif
}

#if EDI_APP_ASSISTANT
bool Session::assistantRetainsProject(ProjectViewModel* project) const { return assistant_->retainsSessionProject(project); }
bool Session::assistantPrepareRestore(ProjectViewModel* project, const QString& source, const std::function<bool()>& commit) {
    return assistant_->prepareSessionProjectRestore(project, source, commit);
}
bool Session::assistantSaveNotified(ProjectViewModel* project) const { return assistant_->ordinarySaveNotification(project); }
#else
bool Session::assistantRetainsProject(ProjectViewModel*) const { return false; }
bool Session::assistantPrepareRestore(ProjectViewModel*, const QString&, const std::function<bool()>&) { return true; }
bool Session::assistantSaveNotified(ProjectViewModel*) const { return false; }
#endif

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
        if(aside_) {  // a project a tutorial set aside still owns its folders
            if(aside_->project)addModel(aside_->project);
            add(aside_->temporary_folder);add(aside_->web_copy);add(aside_->archive_location);
            if(aside_->read_only_copy)add(aside_->read_only_source);
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
    if (openProjectAt(location)) {
        qCInfo(lcApp, "project opened");
        return true;
    }
#if EDI_APP_ASSISTANT
    if(receiver && assistant_->sessionProjectRestorePending())return false;
#endif
    // A stale outer Open neither reports its successor's error as its own nor
    // decorates that successor. False does not imply no partial adoption.
    if(!receiver || replacement_generation_!=binding || project_!=before)return false;
    const auto message=last_error_.isEmpty()?tr("The project at %1 could not be opened").arg(location.toLocalFile().isEmpty()?location.toString():location.toLocalFile()):last_error_;
    if(!receiver || replacement_generation_!=binding || project_!=before)return false;
    emit loadFailed(message);
    return false;
}

bool Session::openExample(const QString& exampleId) {
    const QPointer<Session> receiver(this);
    const QPointer<ProjectViewModel> before(project_);
    const auto binding=replacement_generation_;
    if (openExampleNamed(exampleId)) {
        qCInfo(lcApp, "example requested: %s", qPrintable(exampleId));
        return true;
    }
    // A stale outer Open neither reports its successor's error as its own nor
    // decorates that successor. False does not imply no partial adoption.
    if(!receiver || replacement_generation_!=binding || project_!=before)return false;
    const auto message=last_error_.isEmpty()?tr("The example %1 could not be opened").arg(exampleId):last_error_;
    if(!receiver || replacement_generation_!=binding || project_!=before)return false;
    emit loadFailed(message);
    return false;
}

bool Session::openProjectAt(const QUrl& location, const QString& example) {
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
        return open(source,example,[this,given] {
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

bool Session::locationExists(const QString& path) const {
    if (path.isEmpty()) return false;
    const QFileInfo info(QDir::cleanPath(path));
    return info.exists() || info.isSymLink();
}

QString Session::existingParentFolder(const QString& path) const {
    if (path.isEmpty()) return {};
    const QFileInfo parent(QFileInfo(path).absolutePath());
    return parent.isDir() ? parent.absoluteFilePath() : QString{};
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
    if (project_ == nullptr) return false;
    const bool web = WebFiles::available();
    if (web) {
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
    } else if (needsSaveAs()) {
        setLastError(QStringLiteral("this project has no directory of its own yet: save it as"));
        return false;
    }
    // A Save into the project's folder writes its texts; a .zip or a browser place is written whole (edi ADR-0069).
    const auto operation = beginSave(web || !archive_location_.isEmpty(), web || !archive_location_.isEmpty(),
                                     [this](const SaveOperation& answered) { saveWith(answered); },
                                     [this] { return save(); });
    return operation && saveWith(*operation);
}

bool Session::saveWith(const SaveOperation& operation) {
    const auto logged = [](const char* line) {
        qCInfo(lcApp, "%s", line);
        return true;
    };
    if (!owns(operation)) return false;
    // A Save moves the open project to what it writes: changed since the plan, it is planned again (edi ADR-0069).
    if (!planned(operation)) return queueReplan(operation), false;
    if (WebFiles::available()) {
        if (web_writing_) {
            setLastError(tr("The project is still being saved: save again once it is written."));
            return false;
        }
        // What the Save writes is staged on a copy and written to the place; the open project takes that snapshot only
        // once the place holds it (webSaveFinished says when).
        const QString name = project_->path().isEmpty() ? folderNameFor(project_->name())
                                                        : QFileInfo(project_->path()).fileName();
        Staged staged;
        if (!stageCopy(operation, "web", name, staged) || !readyToWrite(operation, staged)) {
            return false;
        }
        const WebPlace place = web_place_;
        const QPointer<ProjectViewModel> saving = project_;
        const quint64 revision = project_->revision();
        web_writing_ = true;
        writeWebPlace(place, staged.folder, [this, saving, revision, staged, place, held = operation.hold](bool written) {
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
        return logged("project saved");
    }
    if (needsSaveAs()) {
        setLastError(QStringLiteral("this project has no directory of its own yet: save it as"));
        return false;
    }
    if (!archive_location_.isEmpty()) {
        // The archive is written from a staged copy, and the open project then takes that snapshot and works in its
        // folder: a refused archive leaves the project as it was.
        Staged staged;
        if (!stageCopy(operation, "saved", {}, staged) || !readyToWrite(operation, staged) ||
            !publishArchive(staged, archive_location_)) {
            return false;
        }
        emit projectDirectoryUsed(archive_location_);
        return logged("project saved");
    }
    // The folder Save writes the open project itself: changed since the plan, it is planned again. It is staged whole
    // beside the folder, checked in full, and put in the folder's place, as Save as into an existing folder is, so a
    // refusal leaves the folder as it was (edi ADR-0069).
    if (!planned(operation)) return queueReplan(operation), false;
    return saveAsWith(operation, QUrl::fromLocalFile(project_->path()));
}

std::optional<Session::SaveOperation> Session::beginSave(bool wholeTree, bool stores, SaveContinuation again,
                                                        std::function<bool()> replan) {
    if (project_ == nullptr) return std::nullopt;
    // A save starts only on a project nothing else is changing: no edit still publishing, no failed presentation and
    // no other save (edi ADR-0069). It then holds the project before reading anything from it.
    if (const QString refusal = project_->criticalEditRefusal(); !refusal.isEmpty()) {
        setLastError(refusal);
        return std::nullopt;
    }
    // Nor while a fit runs or is still publishing its end: the save would plan from a project about to change.
    if (const QString refusal = project_->saveRefusal(); !refusal.isEmpty()) {
        setLastError(refusal);
        return std::nullopt;
    }
    SaveOperation operation;
    operation.id = ++save_operations_;
    operation.project = project_;
    operation.replacement = replacement_generation_;
    operation.hold = std::make_shared<ProjectViewModel::OperationHold>(*project_);
    // One snapshot the decision, the plan and the writer all read (edi ADR-0069): a drag held back is settled first,
    // the project kept alive through what that announces, and the save goes on only for the project it began for.
    {
        const ProjectViewModel::PublicationScope publication(*project_);
        project_->settleHeld();
    }
    if (!owns(operation) || operation.project->retired_) return std::nullopt;
    operation.snapshot = std::make_shared<const edi::Project>(project_->savedModel());
    operation.revision = project_->revision();
    operation.wholeTree = wholeTree;
    operation.replan = std::move(replan);
    // Every save is staged whole and published by renaming the checked stage, the project's own folder included: its
    // plan counts every file it carries and its receipt covers each of them. Only a save that moves the project asks
    // for its size alone; one into the project's own folder asks when it would copy linked data (edi ADR-0069).
    operation.stores = stores;
    operation.plan = project_->saveDataPlan(wholeTree, true, stores);
    const SaveDataPlan& plan = operation.plan;
    const bool linked = plan.value(QStringLiteral("linked")).toBool();
    operation.treeReceipt = true;
    operation.inputs = project_->linkedInputsKey(operation.treeReceipt);
    if (plan.value(QStringLiteral("ask")).toBool()) {
        if (assistant_save_origin_ != 0 || project_->assistant_save_origin_ != 0) {
            // A question nobody answers would leave the assistant's save neither done nor refused.
            setLastError(tr("This save asks first what to do with the project's data: save from the window to answer."));
            return std::nullopt;
        }
        save_question_ = SaveQuestion{++save_questions_, operation, std::move(again)};
        save_question_->operation.hold.reset();  // the user may take their time: the answer holds it again
        const qint64 bytes = plan.value(QStringLiteral("bytes")).toLongLong();
        qCInfo(lcApp, "save asks first: %lld bytes in %d files, linked data %s", static_cast<long long>(bytes),
               plan.value(QStringLiteral("files")).toInt(), linked ? "yes" : "no");
        emit saveDataChoiceNeeded(save_question_->request, bytes, plan.value(QStringLiteral("files")).toInt(),
                                  plan.value(QStringLiteral("large")).toBool(), linked);
        return std::nullopt;  // asked, not refused: no message
    }
    operation.include = linked && plan.value(QStringLiteral("mode")).toString() == QLatin1String("all");
    // Including data that is not here cannot be done: refused before anything is written, never saved still linked.
    if (operation.include) {
        if (const QString why = project_->linkedDataUnavailable(); !why.isEmpty()) {
            setLastError(why);
            return std::nullopt;
        }
    }
    return operation;
}

void Session::queueReplan(const SaveOperation& operation) {
    // Planned again once the current call has unwound, and only for the project and replacement it was planned for: a
    // project opened or created meanwhile is never saved under the earlier request.
    if (!operation.replan) return;
    QMetaObject::invokeMethod(
        this,
        [receiver = QPointer<Session>(this), project = operation.project, replacement = operation.replacement,
         replan = operation.replan] {
            if (!receiver || project.isNull() || receiver->project_ != project ||
                receiver->replacement_generation_ != replacement)
                return;
            replan();
        },
        Qt::QueuedConnection);
}

bool Session::owns(const SaveOperation& operation) const {
    return !operation.project.isNull() && operation.project == project_ && operation.replacement == replacement_generation_;
}

bool Session::hold(SaveOperation& operation) {
    if (!owns(operation)) {
        setLastError(tr("The project changed before the save could go on: nothing was saved."));
        return false;
    }
    if (operation.hold) return true;
    if (const QString refusal = project_->criticalEditRefusal(); !refusal.isEmpty()) {
        setLastError(refusal);
        return false;
    }
    operation.hold = std::make_shared<ProjectViewModel::OperationHold>(*project_);
    return true;
}

QString Session::replacementRefusal() const {
    return project_ != nullptr ? project_->operationRefusal() : QString();
}

bool Session::sameInputs(const SaveOperation& operation) const {
    return owns(operation) && project_->linkedInputsKey(operation.treeReceipt) == operation.inputs;
}

bool Session::planned(const SaveOperation& operation) const {
    return sameInputs(operation) && project_->revision() == operation.revision;
}

void Session::answerSaveData(int request, const QString& choice) {
    // Only the question asked last is answered, and only for the project it was asked for: the answer completes that
    // question's own save operation, and no other save sees it.
    if (!save_question_ || save_question_->request != request) return;
    SaveQuestion question = std::move(*save_question_);
    save_question_.reset();
    if (choice != QLatin1String("copy") && choice != QLatin1String("linked")) return;  // cancelled: nothing is saved
    if (!owns(question.operation)) {
        setLastError(tr("The project changed before the save could go on: nothing was saved."));
        return;
    }
    if (!hold(question.operation)) return;
    question.operation.include =
        question.operation.plan.value(QStringLiteral("linked")).toBool() && choice == QLatin1String("copy");
    if (question.operation.include) {
        if (const QString why = project_->linkedDataUnavailable(); !why.isEmpty()) {
            setLastError(why);
            return;
        }
    }
    if (question.again) question.again(question.operation);
}

QString Session::writeBackReports() {
    if (project_ == nullptr || archive_location_.isEmpty()) {
        return {};
    }
    const QString failed = tr("The reports were written, but %1 could not be rewritten: %2");
    // Rewriting the .zip is an operation like a save's (edi ADR-0069): not while a save waits for its answer or holds
    // the project, an edit is still being published or a fit is running or finishing. It holds the project, copies
    // its folder into a stage checked against a receipt of every file, stores what its links reach as a save to a
    // .zip does, and writes the .zip from that stage only.
    if (save_question_) return failed.arg(archive_location_, tr("a save is waiting for an answer"));
    if (const QString refusal = project_->criticalEditRefusal(); !refusal.isEmpty())
        return failed.arg(archive_location_, refusal);
    if (const QString refusal = project_->saveRefusal(); !refusal.isEmpty()) return failed.arg(archive_location_, refusal);
    const auto hold = std::make_shared<ProjectViewModel::OperationHold>(*project_);
    const QString receipt = project_->linkedInputsKey(true);
    QString root;
    const auto release = qScopeGuard([&root] {
        if (!root.isEmpty()) edi::remove_archive_directory(root.toStdString());
    });
    try {
        root = QString::fromStdString(edi::fresh_archive_directory("reports"));
        const QString folder = root + QStringLiteral("/project");
        if (const QString refused = project_->copyFolderAs(project_->path(), folder); !refused.isEmpty())
            return failed.arg(archive_location_, refused);
        if (const QString changed = project_->carriedBytesDiffer(receipt, folder, {}, true); !changed.isEmpty())
            return failed.arg(archive_location_, changed);
        if (const QString refused = project_->freezeLinks(receipt, folder); !refused.isEmpty())
            return failed.arg(archive_location_, refused);
        edi::write_project_archive(folder.toStdString(), archive_location_.toStdString());
    } catch (const std::exception& refusal) {
        return failed.arg(archive_location_, QString::fromUtf8(refusal.what()));
    }
    return {};
}

bool Session::saveAs(const QUrl& directory) {
    const auto operation =
        beginSave(true, false, [this, directory](const SaveOperation& answered) { saveAsWith(answered, directory); },
                  [this, directory] { return saveAs(directory); });
    return operation && saveAsWith(*operation, directory);
}

bool Session::saveAsWith(const SaveOperation& operation, const QUrl& directory) {
    if (!owns(operation)) return false;
    if (!planned(operation)) return queueReplan(operation), false;
    if(directory.isLocalFile()) {
        const QFileInfo target(directory.toLocalFile());
        if(!target.exists() && !target.isSymLink())return saveProjectAsFreshWith(operation,directory,false,false,true);
    }
    if (!directory.isLocalFile()) {
        setLastError(QStringLiteral("cannot save to %1: only local directories (file: URLs)").arg(directory.toString()));
        return false;
    }
    // Into an existing folder: staged beside it, checked against the save's receipt, checked again right before it is
    // published, then put in the folder's place by renaming, so what was checked is what the folder holds; the project
    // then takes the staged snapshot (edi ADR-0069).
    QString folder = QFileInfo(directory.toLocalFile()).absoluteFilePath();
    if (const QString canonical = QFileInfo(folder).canonicalFilePath(); !canonical.isEmpty()) folder = canonical;
    // The save announces itself as an edit of the project, with the assistant's origin when it asked for it, as every
    // moving save does; nothing a listener does meanwhile can change the held project.
    {
        const QPointer<ProjectViewModel> target(project_);
        const auto origin = std::exchange(project_->assistant_save_origin_, 0);
        target->notifyProjectEdited(origin);
        if (!target || !owns(operation)) return false;
    }
    if (!planned(operation)) return queueReplan(operation), false;
    Staged staged;
    if (!stageCopy(operation, "saved", {}, staged, QFileInfo(folder).absolutePath())) return false;
    const auto release = qScopeGuard([root = staged.root] { edi::remove_archive_directory(root.toStdString()); });
    if (!readyToWrite(operation, staged) || !publishStaged(staged.folder, folder, true)) return false;
    edi::Project published = *staged.project;
    edi::adopt_save_location(published, folder.toStdString());
    if (staged.scan.listing)
        staged.scan.listing->relocate(std::make_shared<const edi::Project>(published), staged.folder, folder);
    project_->takeStaged(folder, published, staged.scan);
    archive_location_.clear();
    leaveTemporaryOrigin();
    releaseTemporaryFolder();
    emit projectLocationChanged();
    emit needsSaveAsChanged();
    emit locationTextChanged();
    emit projectDirectoryUsed(folder);
    qCInfo(lcApp, "project saved");
    return true;
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
    const auto operation=beginSave(true,zip,[this,destination,zip,copy,notify](const SaveOperation& answered) {
        saveProjectAsFreshWith(answered,destination,zip,copy,notify);},
        [this,destination,zip,copy,notify]{return saveProjectAsFresh(destination,zip,copy,notify);});
    return operation && saveProjectAsFreshWith(*operation,destination,zip,copy,notify);
}

bool Session::saveProjectAsFreshWith(const SaveOperation& operation,const QUrl& destination,bool zip,bool copy,
                                     bool notify) {
    if(!owns(operation))return false;
    if(!copy && !planned(operation))return queueReplan(operation),false;
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
    if(const auto refusal=target->criticalEditRefusal(false,false,true);!refusal.isEmpty()){setLastError(refusal);return false;}
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
    if(!editingSet) { target->editing_=true; editingSet=true; }
    if(!current())return false;
    // An edit made while the save notified (above) is not in its snapshot: the save is planned again once this one
    // has unwound, and the project adopts only what the snapshot's own revision wrote.
    if(!copy && !planned(operation)) {
        queueReplan(operation);
        return false;
    }
    const auto revision=operation.revision;
    Staged staged;
    // A folder is staged beside the destination at its own depth, so a linked folder declared relative to the stage is
    // declared the same for the destination; a .zip is archived from a folder inside its stage.
    if(!stageCopy(operation,copy?"copy":"saved",zip?QStringLiteral("project"):QString(),staged,requested.absolutePath(),true))return false;
    const auto release=qScopeGuard([receiver,root=staged.root]{if(receiver)receiver->releaseTemporaryRoots({root});});
    if(!current() || target->revision()!=revision)return false;
    const auto parent=QDir(requested.absolutePath()).canonicalPath();
    if(parent.isEmpty() || requested.fileName().isEmpty()) {
        if(current())setLastError(tr("The original fresh save parent is unavailable."));return false;
    }
    const auto where=parent+QLatin1Char('/')+requested.fileName();
    const PendingOpenSource pendingOrigin(*this,where);
    try {
        if(zip) {
            if(!readyToWrite(operation,staged))return false;
            edi::detail::write_project_archive_fresh(staged.folder.toStdString(),where.toStdString());
        } else {
            // What the stage declares must read the same from the destination, before anything is published: nothing
            // is rewritten after the folder is in place.
            edi::Project placed=*staged.project;
            placed.path=staged.folder.toStdString();placed.scan_data_root.clear();
            edi::adopt_save_location(placed,where.toStdString());
            bool moved=placed.sequential_fit.data_dir!=staged.project->sequential_fit.data_dir;
            for(std::size_t i=0;i<placed.experiments.size();++i)
                moved=moved || placed.experiments[i]->data_path!=staged.project->experiments[i]->data_path;
            if(moved) {
                setLastError(tr("The project's linked data could not be declared for %1: nothing was written").arg(where));
                return false;
            }
            if(!current() || target->revision()!=revision)return false;
            if(!readyToWrite(operation,staged) || !publishStaged(staged.folder,where,false))return false;
            staged.project->path=where.toStdString();staged.project->metadata.path=staged.project->path;
            if(staged.scan.listing)staged.scan.listing->relocate(staged.project,staged.folder,where);
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
    const auto operation = beginSave(
        true, zip, [this, target, zip, copy](const SaveOperation& answered) { saveProjectAsWith(answered, target, zip, copy); },
        [this, target, zip, copy] { return saveProjectAs(target, zip, copy); });
    return operation && saveProjectAsWith(*operation, target, zip, copy);
}

bool Session::saveProjectAsWith(const SaveOperation& operation, const QUrl& target, bool zip, bool copy) {
    if (!owns(operation)) return false;
    // A moving save is planned again for a changed project; a copy writes the snapshot it planned.
    if (!copy && !planned(operation)) return queueReplan(operation), false;
    if(target.isLocalFile()) {
        const QFileInfo destination(target.toLocalFile());
        if(!destination.exists() && !destination.isSymLink())return saveProjectAsFreshWith(operation,target,zip,copy,true);
    }
    const auto logged = [](const char* line) {
        qCInfo(lcApp, "%s", line);
        return true;
    };
    if (project_ == nullptr) {
        return false;
    }
    if (!target.isLocalFile()) {
        setLastError(QStringLiteral("cannot save to %1: only local files and folders (file: URLs)").arg(target.toString()));
        return false;
    }
    const QString where = target.toLocalFile();
    if (copy) {
        return saveCopy(operation, where, zip);
    }
    if (!zip) {
        return saveAsWith(operation, target);
    }
    // A project saved as a .zip works in a folder of its own and every Save rewrites the archive from it. The
    // archive is written from a staged copy before the project moves to it: a refused archive leaves the open project
    // where and as it was.
    Staged staged;
    if (!stageCopy(operation, "saved", {}, staged) || !readyToWrite(operation, staged) || !publishArchive(staged, where)) {
        return false;
    }
    leaveTemporaryOrigin();
    archive_location_ = where;
    emit projectLocationChanged();
    emit needsSaveAsChanged();
    emit locationTextChanged();
    emit projectDirectoryUsed(where);
    return logged("project saved");
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

bool Session::stageCopy(const SaveOperation& operation, const char* purpose, const QString& name, Staged& staged,
                        const QString& parent, bool admitted) {
    if (!owns(operation)) return false;
    // The snapshot the save planned is what it writes; linked inputs changed since cannot be the ones it planned.
    if (!sameInputs(operation)) {
        setLastError(tr("The project's linked data changed while the save waited: save again."));
        return false;
    }
    // What a Save writes (round, adopt, recalculate, write), done on a copy in a folder of its own, once the project
    // may be saved at all: the open project is left as it is.
    if (const QString refusal = project_->saveRefusal(admitted); !refusal.isEmpty()) {
        setLastError(refusal);
        return false;
    }
    QString included;
    bool includedAny = false;
    try {
        staged.root = QString::fromStdString(parent.isEmpty()?edi::fresh_archive_directory(purpose):
            edi::detail::fresh_archive_directory_at(purpose,parent.toStdString()));
        staged.folder = name.isEmpty() ? staged.root : staged.root + QLatin1Char('/') + name;
        auto copy = std::make_shared<edi::Project>(*operation.snapshot);
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
        // Linked data the save includes goes into the staged copy only (edi ADR-0069).
        if (operation.include) {
            if (const QString refusal =
                    project_->includeDataInto(*copy, staged.folder, &included, &includedAny, &operation.inputs);
                !refusal.isEmpty())
                throw edi::IoError(refusal.toStdString());
        }
        edi::adopt_saved_project(*copy, staged.folder.toStdString());
        staged.project = std::move(copy);
    } catch (const std::exception& refusal) {
        if (!staged.root.isEmpty()) {
            edi::remove_archive_directory(staged.root.toStdString());
        }
        setLastError(QString::fromUtf8(refusal.what()));
        return false;
    }
    // The carried files are the bytes the save planned (its receipt), checked in the staged copy before it is published.
    // What the save wrote itself (a linked scan copied into scans/<name>) is not a carried file.
    QStringList written;
    if (!included.isEmpty() && staged.project) written << QString::fromStdString(staged.project->sequential_fit.data_dir);
    if (const QString changed = project_->carriedBytesDiffer(operation.inputs, staged.folder, written);
        !changed.isEmpty()) {
        edi::remove_archive_directory(staged.root.toStdString());
        setLastError(changed);
        return false;
    }
    // Everything that can refuse happens before the save is published: a scan's results and its listing too.
    if (const QString refusal = project_->stageScan(staged.folder, *staged.project, staged.scan); !refusal.isEmpty()) {
        edi::remove_archive_directory(staged.root.toStdString());
        setLastError(refusal);
        return false;
    }
    staged.scan.included = included;
    staged.scan.includedData = includedAny;
    staged.written = written;
    return true;
}

bool Session::sealed(const SaveOperation& operation, const Staged& staged) {
    if (const QString changed = project_ != nullptr && owns(operation)
                                    ? project_->carriedBytesDiffer(operation.inputs, staged.folder, staged.written)
                                    : tr("The project changed before the save could go on: nothing was saved.");
        !changed.isEmpty()) {
        edi::remove_archive_directory(staged.root.toStdString());
        setLastError(changed);
        return false;
    }
    return true;
}

bool Session::readyToWrite(const SaveOperation& operation, const Staged& staged) {
    if (!sealed(operation, staged)) return false;
    if (!operation.stores) return true;
    // A writer that stores what links reach reads only the stage's own bytes: each link is replaced by the bytes it
    // reaches, checked against the receipt as they are written.
    if (const QString refused = project_->freezeLinks(operation.inputs, staged.folder); !refused.isEmpty()) {
        edi::remove_archive_directory(staged.root.toStdString());
        setLastError(refused);
        return false;
    }
    return true;
}

bool Session::publishStaged(const QString& stage, const QString& destination, bool replace) {
    namespace fs = std::filesystem;
    std::error_code error;
    const fs::path to(destination.toStdString());
    const fs::file_status status = fs::symlink_status(to, error);
    // The folder keeps the permissions of the one it replaces, and a fresh one gets the usual ones, not the stage's
    // private ones.
    fs::perms wanted = fs::perms::all;
#if !defined(_WIN32)
    const mode_t mask = ::umask(0);
    ::umask(mask);
    wanted = static_cast<fs::perms>(0777 & ~mask);
#endif
    if (fs::is_directory(status)) wanted = status.permissions();
    fs::permissions(stage.toStdString(), wanted, fs::perm_options::replace, error);
    // Every rename refuses to replace what is there, so nothing made at the destination meanwhile is lost: a fresh
    // destination refuses anything existing, and an existing folder is moved aside, then the stage takes its name.
    const auto move = [](const std::string& from, const std::string& into) -> QString {
        try {
            edi::detail::rename_directory_no_replace(from, into);
        } catch (const std::exception& refusal) {
            return QString::fromUtf8(refusal.what());
        }
        return {};
    };
    if (!replace || !fs::exists(status)) {
        if (const QString refused = move(stage.toStdString(), to.string()); !refused.isEmpty()) {
            setLastError(replace ? tr("%1 could not be written: %2").arg(destination, refused)
                                 : tr("The fresh project destination already exists; nothing was replaced."));
            return false;
        }
        return true;
    }
    if (!fs::is_directory(status)) {
        setLastError(tr("%1 is not a folder; nothing was replaced.").arg(destination));
        return false;
    }
    fs::path aside = to;
    aside += ".edi-replaced";
    for (int n = 2; fs::exists(fs::symlink_status(aside, error)); ++n) {
        aside = to;
        aside += ".edi-replaced-" + std::to_string(n);
    }
    if (const QString refused = move(to.string(), aside.string()); !refused.isEmpty()) {
        setLastError(tr("%1 could not be replaced: %2").arg(destination, refused));
        return false;
    }
    if (const QString refused = move(stage.toStdString(), to.string()); !refused.isEmpty()) {
        if (!move(aside.string(), to.string()).isEmpty())
            setLastError(tr("%1 could not be replaced, and the folder it held is now %2: %3")
                             .arg(destination, QString::fromStdString(aside.string()), refused));
        else
            setLastError(tr("%1 could not be replaced: %2").arg(destination, refused));
        return false;
    }
    fs::remove_all(aside, error);
    if (error) qCWarning(lcApp, "the replaced folder %s was left behind: %s", aside.string().c_str(), error.message().c_str());
    return true;
}

bool Session::saveCopy(const SaveOperation& operation, const QString& target, bool zip) {
    if (!owns(operation)) return false;
    // What a Save writes (round, adopt, recalculate, write), staged from the snapshot the save planned and checked as a
    // Save's stage is, then published by its last writer only after one more check: the open project keeps its own
    // location and values. A running fit owns where the project works, which a copy may name: stageCopy refuses first.
    Staged staged;
    if (zip) {
        if (!stageCopy(operation, "copy", QStringLiteral("project"), staged)) return false;
        const auto release = qScopeGuard([root = staged.root] { edi::remove_archive_directory(root.toStdString()); });
        if (!readyToWrite(operation, staged)) return false;
        try {
            edi::write_project_archive(staged.folder.toStdString(), target.toStdString());
        } catch (const std::exception& refusal) {
            setLastError(QString::fromUtf8(refusal.what()));
            return false;
        }
        setLastError({});
        return true;
    }
    // Into a folder: staged beside it and put in its place by renaming, so a refusal leaves it as it was.
    QString folder = QFileInfo(target).absoluteFilePath();
    if (const QString canonical = QFileInfo(folder).canonicalFilePath(); !canonical.isEmpty()) folder = canonical;
    if (!stageCopy(operation, "copy", {}, staged, QFileInfo(folder).absolutePath())) return false;
    const auto release = qScopeGuard([root = staged.root] { edi::remove_archive_directory(root.toStdString()); });
    if (!readyToWrite(operation, staged) || !publishStaged(staged.folder, folder, true)) return false;
    setLastError({});
    return true;
}

QString Session::examplesNotice() const { return collection_examples_->notice(); }

bool Session::openExampleNamed(const QString& exampleId) {
    // An example's project comes from the collections (ADR-0068): once the sources are read (again, after an
    // outage), its zip is downloaded, checked and opened as any archive. The request keeps what it was made
    // with: a tutorial's aside intent, and the project it was made against, so a later request, Close, Create
    // or Open makes an older reply inert. The outcome arrives through loadFailed and exampleOpenFinished.
    // An example is a catalogue case; a collection project the catalogue does not list is not one.
    if (!ExampleListModel::bundledIds().contains(exampleId)) {
        setLastError(QStringLiteral("no example named '%1'").arg(exampleId));
        return false;
    }
    const QPointer<Session> receiver(this);
    const bool aside = aside_next_;
    const quint64 request = ++example_request_;
    const auto binding = replacement_generation_;
    const QPointer<ProjectViewModel> before(project_);
    opening_example_ = true;
    example_download_received_ = 0;
    example_download_total_ = -1;
    emit openingExampleChanged();
    if (!receiver || receiver->example_request_ != request) return true;
    emit exampleDownloadReceivedChanged();
    if (!receiver || receiver->example_request_ != request) return true;
    emit exampleDownloadTotalChanged();
    if (!receiver || receiver->example_request_ != request) return true;
    emit exampleDownloadProgressChanged();
    if (!receiver || receiver->example_request_ != request) return true;
    const auto finish = [receiver, exampleId, request](bool opened, const QString& message) {
        if (!receiver || receiver->example_request_ != request || !receiver->opening_example_) return;
        receiver->opening_example_ = false;
        emit receiver->openingExampleChanged();
        if (!receiver || receiver->example_request_ != request) return;
        if (!opened && !message.isEmpty()) {
            receiver->setLastError(message);
            if (!receiver || receiver->example_request_ != request) return;
            emit receiver->loadFailed(message);
            if (!receiver || receiver->example_request_ != request) return;
        }
        emit receiver->exampleOpenFinished(exampleId, opened);
    };
    // Still this request, against the project it was made for: a newer example request owns the outcome, and a
    // project replaced in between is not replaced again.
    const auto current = [receiver, request, binding, before] {
        return receiver && receiver->example_request_ == request && receiver->replacement_generation_ == binding &&
               receiver->project_ == before;
    };
    collection_examples_->whenRead(exampleId, [receiver, exampleId, aside, request, binding, before, finish, current] {
        if (!receiver || receiver->example_request_ != request) return;
        if (!current()) {
            qCInfo(lcApp, "example %s not opened: the project changed meanwhile", qPrintable(exampleId));
            finish(false, {});
            return;
        }
        if (!receiver->collection_examples_->knows(exampleId)) {
            const QString notice = receiver->collection_examples_->notice();
            finish(false, !notice.isEmpty() ? notice : tr("No online source that answered holds the example '%1'").arg(exampleId));
            return;
        }
        receiver->collection_examples_->fetchProject(exampleId, [receiver, exampleId, aside, request, finish, current](const QUrl& archive, const QString& error) {
            if (!receiver || receiver->example_request_ != request) return;
            if (!current()) {
                qCInfo(lcApp, "example %s not opened: the project changed meanwhile", qPrintable(exampleId));
                finish(false, {});
                return;
            }
            if (!error.isEmpty()) {
                qCWarning(lcApp, "example %s not fetched: %s", qPrintable(exampleId), qPrintable(error));
                finish(false, error);
                return;
            }
            if (aside && receiver->aside_) {
                finish(false, QStringLiteral("a tutorial already holds a project aside"));
                return;
            }
            receiver->aside_next_ = aside;
            const bool opened = receiver->openProjectAt(archive, exampleId);
            receiver->aside_next_ = false;
            if (opened) qCInfo(lcApp, "example opened: %s", qPrintable(exampleId));
            else qCWarning(lcApp, "example %s: %s could not be opened: %s", qPrintable(exampleId), qPrintable(archive.toLocalFile()), qPrintable(receiver->last_error_));
            finish(opened, opened ? QString()
                   : tr("The example %1, downloaded to %2, could not be opened%3")
                         .arg(exampleId, archive.toLocalFile(), receiver->last_error_.isEmpty() ? QString() : QStringLiteral(": ") + receiver->last_error_));
        }, [receiver, request, current](qint64 received, qint64 total) {
            if (!receiver || receiver->example_request_ != request || !current()) return;
            receiver->example_download_received_ = std::max<qint64>(0, received);
            receiver->example_download_total_ = total;
            emit receiver->exampleDownloadReceivedChanged();
            if (!receiver || receiver->example_request_ != request) return;
            emit receiver->exampleDownloadTotalChanged();
            if (!receiver || receiver->example_request_ != request) return;
            emit receiver->exampleDownloadProgressChanged();
        });
    });
    return true;
}

namespace {
// The tutorials' two inputs, by their ids in the collection and the names the tutorial text gives them.
const QList<QPair<QString, QString>> kTutorialFiles{{QStringLiteral("tutorial-lbco"), QStringLiteral("lbco.cif")},
                                                    {QStringLiteral("tutorial-hrpt"), QStringLiteral("hrpt.xye")}};
}  // namespace

// Downloads the tutorials' files one after the other; `done` gets every (name, bytes) pair or the first error.
void Session::fetchTutorialFiles(std::function<void(const QList<QPair<QString, QByteArray>>&, const QString&)> done) {
    const QPointer<Session> receiver(this);
    auto fetched = std::make_shared<QList<QPair<QString, QByteArray>>>();
    auto step = std::make_shared<std::function<void(int)>>();
    *step = [receiver, fetched, step, done](int index) {
        if (!receiver) return;
        if (index == kTutorialFiles.size()) {
            done(*fetched, {});
            return;
        }
        const QString id = kTutorialFiles[index].first, name = kTutorialFiles[index].second;
        receiver->collection_examples_->whenRead(id, [receiver, fetched, step, done, index, id, name] {
            if (!receiver) return;
            receiver->collection_examples_->fetchBytes(id, [receiver, fetched, step, done, index, name](const QByteArray& bytes, const QString& error) {
                if (!receiver) return;
                if (!error.isEmpty()) {
                    done({}, tr("%1 could not be fetched: %2").arg(name, error));
                    return;
                }
                fetched->append({name, bytes});
                (*step)(index + 1);
            });
        });
    };
    (*step)(0);
}

int Session::stageTutorialFiles() {
    // Each request stages into a folder of its own, written only while it is the current request: a late reply to an
    // earlier one can neither overwrite the files a newer one staged nor answer (edi ADR-0069 operations).
    auto operation = std::make_shared<TutorialFilesOperation>();
    operation->request = ++tutorial_files_request_;
    operation->folder = QDir(QStandardPaths::writableLocation(QStandardPaths::TempLocation))
                            .filePath(QStringLiteral("easydiffraction-tutorial-%1-%2")
                                          .arg(QCoreApplication::applicationPid())
                                          .arg(operation->request));
    tutorial_staging_ = operation;
    // The reply always arrives after this returns, so the caller holds the request before any answer naming it.
    fetchTutorialFiles([this, operation](const QList<QPair<QString, QByteArray>>& fetched, const QString& failure) {
        QMetaObject::invokeMethod(
            this,
            [this, operation, files = fetched, error = failure] {
                if (tutorial_staging_ != operation) return;  // cancelled or superseded: nothing written or said
                const int request = operation->request;
                const QString& folder = operation->folder;
                if (!error.isEmpty()) {
                    tutorial_staging_.reset();
                    emit tutorialFilesFailed(request, error);
                    return;
                }
                if (!QDir().mkpath(folder)) {
                    tutorial_staging_.reset();
                    emit tutorialFilesFailed(request, tr("The folder %1 could not be made").arg(folder));
                    return;
                }
                for (const auto& [name, bytes] : files) {
                    QFile written(QDir(folder).filePath(name));
                    if (!written.open(QIODevice::WriteOnly | QIODevice::Truncate) || written.write(bytes) != bytes.size()) {
                        tutorial_staging_.reset();
                        emit tutorialFilesFailed(request, tr("%1 could not be written").arg(written.fileName()));
                        return;
                    }
                }
                tutorial_staging_.reset();
                emit tutorialFilesStaged(request, QUrl::fromLocalFile(folder));
            },
            Qt::QueuedConnection);
    });
    return operation->request;
}

int Session::saveTutorialFiles(const QUrl& folder) {
    auto operation = std::make_shared<TutorialFilesOperation>();
    operation->request = ++tutorial_files_request_;
    operation->folder = folder.toLocalFile();
    tutorial_saving_ = operation;
    const bool download = edi_app::WebFiles::available();
    fetchTutorialFiles([this, download, operation](const QList<QPair<QString, QByteArray>>& fetched,
                                                   const QString& failure) {
        QMetaObject::invokeMethod(
            this,
            [this, download, operation, files = fetched, error = failure] {
                if (tutorial_saving_ != operation) return;  // cancelled or superseded: nothing written or said
                tutorial_saving_.reset();
                const int request = operation->request;
                const QString& target = operation->folder;
                if (!error.isEmpty()) {
                    emit tutorialFilesFailed(request, error);
                    return;
                }
                if (!download && !QDir().mkpath(target)) {
                    emit tutorialFilesFailed(request, tr("The folder %1 could not be made").arg(target));
                    return;
                }
                for (const auto& [name, bytes] : files) {
                    if (download) {
                        if (!edi_app::WebFiles::download(bytes, name)) {
                            emit tutorialFilesFailed(request, tr("%1 could not be downloaded").arg(name));
                            return;
                        }
                        continue;
                    }
                    QFile written(QDir(target).filePath(name));
                    if (!written.open(QIODevice::WriteOnly | QIODevice::Truncate) || written.write(bytes) != bytes.size()) {
                        emit tutorialFilesFailed(request, tr("%1 could not be written").arg(written.fileName()));
                        return;
                    }
                }
                emit tutorialFilesSaved(request);
            },
            Qt::QueuedConnection);
    });
    return operation->request;
}

void Session::cancelTutorialFiles() {
    tutorial_staging_.reset();
    tutorial_saving_.reset();
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
                            bool reportLibraries, const QString& assistantIntent, bool replace) {
    return createProjectWithOutcome(name,description,location,suRule,title,authors,reportLibraries,assistantIntent,replace).success;
}
edi_app::ProjectCreationResult Session::createProjectWithOutcome(const QString& name, const QString& description, const QString& location,
                            const QString& suRule, const QString& title, const QString& authors,
                            bool reportLibraries, const QString& assistantIntent, bool replace) {
    const QPointer<Session> receiver(this);
    ProjectCreationOutcome outcome;
    const bool success = createProjectImpl(name, description, location, suRule, title, authors,
                                          reportLibraries, assistantIntent, &outcome, replace);
    if (!receiver) return {};
    const bool current = (!outcome.has_owner || outcome.owner) && project_ == outcome.owner &&
        replacement_generation_ == outcome.replacement;
    edi_app::ProjectCreationResult result;
    result.success = success; result.current = current; result.error = outcome.error; result.saved = outcome.saved;
    result.path = outcome.path; result.owner = outcome.owner.data(); result.has_owner = outcome.has_owner;
    result.replacement = QString::number(outcome.replacement);
#if EDI_APP_ASSISTANT
    assistant_->finishOrdinaryProjectCreationOutcome(assistantIntent,result);
#endif
    return result;
}
bool Session::creationOutcomeCurrent(const edi_app::ProjectCreationResult& outcome) const {
    const auto* original = outcome.owner.data();
    return (!outcome.has_owner || original) && project_ == original &&
        outcome.replacement == QString::number(replacement_generation_);
}
bool Session::createProjectImpl(const QString& name, const QString& description, const QString& location,
                            const QString& suRule, const QString& title, const QString& authors,
                            bool reportLibraries, const QString& assistantIntent, ProjectCreationOutcome* outcome, bool replace) {
    const QPointer<Session> receiver(this);
    if (outcome) { outcome->owner = project_; outcome->has_owner = project_ != nullptr; outcome->replacement = replacement_generation_; }
    if (const QString refusal = replacementRefusal(); !refusal.isEmpty()) {
        setLastError(refusal);
        if (outcome) outcome->error = refusal;
        return false;
    }
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
        created = new ProjectViewModel(std::move(project), this, colour_scheme_);
    } catch (const std::exception& refusal) {
        const auto failure = QString::fromUtf8(refusal.what());
        if (outcome) outcome->error = failure;
        if (receiver) setLastError(failure);
        return false;
    }
    const QPointer<ProjectViewModel> originalCreated(created);
    const bool assistantCreation = !assistantIntent.isEmpty();
#if EDI_APP_ASSISTANT
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
#endif
    if (!receiver || !originalCreated) return false;
    bool committed = false;
    quint64 committedReplacement = 0;
    const bool presented = replaceProject(created, {}, {}, assistantCreation, &committed, &committedReplacement, !assistantCreation && project_==nullptr);
    if (outcome && committed) {
        outcome->owner = originalCreated; outcome->has_owner = true; outcome->replacement = committedReplacement;
    }
#if EDI_APP_ASSISTANT
    if (receiver && assistantCreation) assistant_->finishOrdinaryProjectCreation(originalCreated, assistantIntent, committed);
#endif
    const auto current = [&] { return receiver && originalCreated && project_ == originalCreated &&
        committed && replacement_generation_ == committedReplacement; };
    if (!presented || !current()) return false;
    qCInfo(lcApp, "%s", location.isEmpty() ? "project created, unsaved" : "project created");
    if (location.isEmpty()) {
        return true;
    }
    // Over a project folder already at the location, once the user chose Replace: the ordinary save writes into
    // it, so a refused write leaves the old project as it was (the owner, 2026-11-04).
    const QFileInfo existing(location);
    const bool replacing = replace && (existing.exists() || existing.isSymLink());
    bool saved = false;
    if (!replacing) saved = saveProjectAsFresh(QUrl::fromLocalFile(location),false,false,false);
    else if (!existing.isDir() || !QFileInfo::exists(existing.absoluteFilePath() + QStringLiteral("/project.edi")))
        setLastError(tr("%1 exists and is not a project folder; nothing was replaced.").arg(existing.absoluteFilePath()));
    else {
        // Nothing of the old project survives (the owner, 2026-11-04): it moves aside, the new one is saved fresh in
        // its place, and only then is the old one removed; a refused save puts it back as it was.
        const QString place = existing.absoluteFilePath();
        QString aside = place + QStringLiteral(".edi-replaced");
        for (int n = 2; QFileInfo::exists(aside); ++n) aside = place + QStringLiteral(".edi-replaced-%1").arg(n);
        if (!QDir().rename(place, aside)) {
            setLastError(tr("The project %1 could not be replaced: it could not be moved aside").arg(existing.fileName()));
        } else {
            saved = saveProjectAsFresh(QUrl::fromLocalFile(place), false, false, false);
            if (saved) {
                QDir(aside).removeRecursively();
            } else {
                const QString why = last_error_;
                QDir(place).removeRecursively();
                QDir().rename(aside, place);
                if (current()) setLastError(tr("The project %1 could not be replaced: %2").arg(existing.fileName(), why));
            }
        }
    }
    const QString error=current()?(saved?QString{}:last_error_):QStringLiteral("The original Create save owner changed");
    if (outcome) { outcome->error = error; outcome->saved = error.isEmpty(); outcome->path = originalCreated ? originalCreated->path() : QString{}; }
    if (!current()) return false;
    setLastError(error);
    if (!current() || !error.isEmpty()) return false;
    emit projectLocationChanged();
    if (!current()) return false;
    emit needsSaveAsChanged();
    if (!current()) return false;
    // The Project tab's location line reads locationText: a project the assistant creates is shown before this save,
    // so without the signal the line kept the empty location it had then.
    emit locationTextChanged();
    if (!current()) return false;
    emit projectDirectoryUsed(QFileInfo(location).absoluteFilePath());
    return true;
}

void Session::closeProject() {
    if (const QString refusal = replacementRefusal(); !refusal.isEmpty()) {
        setLastError(refusal);
        return;
    }
    const QPointer<Session> receiver(this);const QPointer<ProjectViewModel> original(project_);
    const auto binding=replacement_generation_;
#if EDI_APP_ASSISTANT
    auto pending=assistant_->prepareProjectResetInputs();
    if(!receiver || !pending || project_!=original || replacement_generation_!=binding)return;
#else
    const std::shared_ptr<SessionResetInputs> pending;
    if(!receiver || project_!=original || replacement_generation_!=binding)return;
#endif
    replaceProject(nullptr, {}, {}, false, nullptr, nullptr, false, {}, pending);
}

bool Session::openExampleAside(const QString& exampleId) {
    if (aside_) {
        setLastError(QStringLiteral("a tutorial already holds a project aside"));
        return false;  // never a second one: the first would be lost
    }
    // Started, not done: the download lands later, and the project is set aside as the example's opens
    // (exampleOpenFinished tells, hasProjectSetAside then holds).
    aside_next_ = true;
    const bool started = openExample(exampleId);
    aside_next_ = false;
    return started;
}

bool Session::createProjectAside(const QString& name, const QString& description) {
    if (aside_) {
        setLastError(QStringLiteral("a tutorial already holds a project aside"));
        return false;
    }
    aside_next_ = true;
    const bool created = createProject(name, description);
    aside_next_ = false;
    return created && aside_.has_value();
}

bool Session::setProjectAside() {
    if (const QString refusal = replacementRefusal(); !refusal.isEmpty()) {
        setLastError(refusal);
        return false;
    }
    if (aside_) {
        setLastError(QStringLiteral("a tutorial already holds a project aside"));
        return false;
    }
    aside_next_ = true;
    replaceProject(nullptr, {}, {});
    return aside_.has_value();
}

void Session::restoreProjectSetAside() {
    if (!aside_) {
        return;
    }
    if (const QString refusal = replacementRefusal(); !refusal.isEmpty()) {
        setLastError(refusal);
        return;
    }
    SetAside aside = *std::move(aside_);
    aside_.reset();
    replaceProject(aside.project.data(), {}, aside.example);
    temporary_folder_ = aside.temporary_folder;
    archive_location_ = aside.archive_location;
    setOpenedArchive(aside.opened_archive);
    read_only_source_ = aside.read_only_source;
    read_only_copy_ = aside.read_only_copy;
    web_copy_ = aside.web_copy;
    web_from_file_ = aside.web_from_file;
    setWebPlace(aside.web_place);
    emit projectLocationChanged();
    emit locationTextChanged();
    emit needsSaveAsChanged();
    emit projectSetAsideChanged();
    emit projectSetAsideNameChanged();
    emit projectSetAsideModifiedChanged();
}

void Session::dropProjectSetAside() {
    if (!aside_) {
        return;
    }
    SetAside aside = *std::move(aside_);
    aside_.reset();
    // Its folders go once the project itself is gone and nothing else uses them.
    retainTemporaryRoots({aside.temporary_folder, aside.web_copy});
    if (!aside.project.isNull()) {
        connect(aside.project, &QObject::destroyed, this, [this] { releaseTemporaryRoots({}); }, Qt::QueuedConnection);
        aside.project->retire();
        aside.project->deleteLater();
    } else {
        releaseTemporaryRoots({});
    }
    emit projectSetAsideChanged();
    emit projectSetAsideNameChanged();
    emit projectSetAsideModifiedChanged();
}

QString Session::projectSetAsideName() const {
    return aside_ && !aside_->project.isNull() ? aside_->project->name() : QString();
}

bool Session::projectSetAsideModified() const {
    return aside_ && !aside_->project.isNull() && aside_->project->modified();
}

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
        edi::Project project = edi::load_project(directory.toStdString(), edi::ProjectLoadMode::Construction, [&warnings](const std::string& message) {
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
        opened = new ProjectViewModel(std::move(project), this, colour_scheme_);
    } catch (const std::exception& refusal) {
        if(preparing())setLastError(QString::fromUtf8(refusal.what())); // Never overwrite a successor's error.
        return false;
    }
    if(!preparing()) {
        if(receiver && opened && project_!=opened)opened->deleteLater();
        return false;
    }
    const auto cleanup=qScopeGuard([&] {
        if(!*adopted && receiver && opened && project_!=opened && !assistantRetainsProject(opened))opened->deleteLater();
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
    if(!assistantPrepareRestore(opened,directory,commit))return false;
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
        edi::Project project = edi::load_project(source.toStdString(), edi::ProjectLoadMode::Construction, [&warnings](const std::string& message) {
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
        opened = new ProjectViewModel(std::move(project), this, colour_scheme_);
    } catch (const std::exception& refusal) {
        if(preparing())setLastError(QString::fromUtf8(refusal.what())); // Never overwrite a successor's error.
        return false;
    }
    if(!preparing()) {
        if(receiver && opened && project_!=opened)opened->deleteLater();
        return false;
    }
    const auto cleanup=qScopeGuard([&] {
        if(!*adopted && receiver && opened && project_!=opened && !assistantRetainsProject(opened))opened->deleteLater();
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
    if(!assistantPrepareRestore(opened,source,commit))return false;
    return commit();
}

void Session::setColourScheme(const QString& scheme) {
    if (scheme != colour_scheme_) {
        colour_scheme_ = scheme;
        emit colourSchemeChanged();
    }
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

bool Session::replaceProject(ProjectViewModel* project, const QStringList& warnings, const QString& example, bool nativePrepared, bool* committed, quint64* committedReplacement, bool ordinaryEmptyCreate, const QString& openedFrom, const std::shared_ptr<SessionResetInputs>& resetInputs) {
    // A save holding the open project finishes first (edi ADR-0069): nothing replaces or closes it meanwhile.
    if (const QString refusal = replacementRefusal(); !refusal.isEmpty()) {
        setLastError(refusal);
        return false;
    }
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
    // A tutorial's project sets the open one aside instead of closing it (edi ADR-0064): kept alive and connected to
    // nothing here, with its own temporary folders, until it is restored or dropped.
    std::optional<SetAside> keep;
    if (std::exchange(aside_next_, false)) {
        keep = SetAside{project_,         opened_example_,  temporary_folder_, archive_location_,
                        opened_archive_,  read_only_source_, read_only_copy_,  web_copy_,
                        web_place_,       web_from_file_};
    }
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
        if(!keep) {
            connect(previous,&QObject::destroyed,this,[this]{releaseTemporaryRoots({});},Qt::QueuedConnection);
            previous->retire();
        }
    }
    if(!current())return false;
    if(!nativePrepared){emit projectAboutToChange();if(!current())return false;}
#if EDI_APP_ASSISTANT
    if(nativePrepared && !assistant_->commitNativeProject(target))return false;
#endif
    if(target)connect(target,&ProjectViewModel::pathChanged,this,[this,target] {
        if(target && project_==target && path_generation_!=UINT64_MAX)++path_generation_;
    });
    project_ = target;
    if(committed)*committed=true;
    if(committedReplacement)*committedReplacement=replacement;
#if EDI_APP_ASSISTANT
    if(!nativePrepared && !assistant_->attachProject(target,false,ordinaryEmptyCreate && previous==nullptr,resetInputs))return false;
#endif
    if(!current() || project_!=target)return false;
    opened_example_ = example;
    if (example.isEmpty() && opening_example_) {
        opening_example_ = false;
        emit openingExampleChanged();
        if (!current() || project_ != target) return false;
    }
    warnings_->setMessages(warnings);
    if(!current() || project_!=target)return false;
    if (project_ != nullptr) {
        // Collection-linked data is fetched through the collections the app reads (edi ADR-0069).
        project_->setCollectionFetcher([examples = QPointer<CollectionExamples>(collection_examples_)](
                                           const QString& id, std::function<void(const QByteArray&, const QString&)> done) {
            if (examples.isNull()) {
                done({}, tr("The data collections are not available"));
                return;
            }
            examples->whenRead(id, [examples, id, done] {
                if (examples.isNull()) return done({}, tr("The data collections are not available"));
                if (!examples->knows(id)) return done({}, tr("No data collection holds %1").arg(id));
                examples->fetchBytes(id, done);
            });
        });
        connect(project_, &ProjectViewModel::projectEdited, this, [this] {
            auto* source=qobject_cast<ProjectViewModel*>(sender());
            if(source!=project_ || assistantSaveNotified(source))return;
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
    if (keep) {
        aside_ = std::move(keep);
        emit projectSetAsideChanged();
        emit projectSetAsideNameChanged();
        emit projectSetAsideModifiedChanged();
    } else if (previous != nullptr && previous_idle) {
        previous->deleteLater();
        // Release this retired model graph now; unrelated deferred objects may still be inside
        // their own callbacks and must wait for their event-loop turn (ADR-0052).
        QCoreApplication::sendPostedEvents(previous.data(), QEvent::DeferredDelete);
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
    const auto operation = beginSave(
        true, true, [this, kind, copy](const SaveOperation& answered) { saveWebProjectAsWith(answered, kind, copy); },
        [this, kind, copy] {
            saveWebProjectAs(kind, copy);
            return true;
        });
    if (!operation) {
        if (!last_error_.isEmpty()) emit webSaveFailed(last_error_);
        return;
    }
    saveWebProjectAsWith(*operation, kind, copy);
}

void Session::saveWebProjectAsWith(const SaveOperation& operation, const QString& kind, bool copy) {
    if (!owns(operation)) return;
    const QString busy = tr("The project is still being saved: save again once it is written.");
    const QPointer<ProjectViewModel> before = project_;
    // The picker waits on the user: the project is not held meanwhile, and the answer holds it again before the save
    // checks its plan.
    SaveOperation waiting = operation;
    waiting.hold.reset();
    WebStorage::instance()->pickSave(kind, downloadName(), web_place_.key, [this, before, kind, copy, busy, waiting](
                                                                               const WebStorageAnswer& answer) mutable {
        SaveOperation operation = std::move(waiting);
        if (answer.ok && owns(operation) && !hold(operation)) {
            emit webSaveFailed(last_error_);
            return;
        }
        if (!copy && answer.ok && owns(operation) && !planned(operation)) {
            queueReplan(operation);  // the project changed while the place was picked
            return;
        }
        if (before != project_ || project_ == nullptr || !answer.ok || !owns(operation)) {
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
        if (!stageCopy(operation, copy ? "copy" : "web",
                       folderNameFor(kind == QStringLiteral("zip") ? project_->name() : place.name), staged) ||
            !readyToWrite(operation, staged)) {
            emit webSaveFailed(last_error_);
            return;
        }
        const QPointer<ProjectViewModel> saving = project_;
        const quint64 revision = project_->revision();
        web_writing_ = true;
        writeWebPlace(place, staged.folder, [this, saving, revision, staged, place, copy, held = operation.hold](bool written) {
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
    const auto operation =
        beginSave(true, true, [this](const SaveOperation& answered) { downloadWebProjectWith(answered); }, [this] {
            downloadWebProject();
            return true;
        });
    if (!operation) {
        if (!last_error_.isEmpty()) emit webSaveFailed(last_error_);
        return;
    }
    downloadWebProjectWith(*operation);
}

void Session::downloadWebProjectWith(const SaveOperation& operation) {
    if (!owns(operation)) return;
    // The copy a Save writes, staged and checked as a Save's stage is, checked once more as the archive is made.
    Staged staged;
    if (!stageCopy(operation, "download", {}, staged) || !readyToWrite(operation, staged)) {
        emit webSaveFailed(last_error_);
        return;
    }
    const std::string folder = staged.root.toStdString();
    QByteArray archive;
    try {
        const std::string bytes = edi::project_archive_bytes(staged.folder.toStdString());
        archive = QByteArray(bytes.data(), static_cast<qsizetype>(bytes.size()));
    } catch (const std::exception& refusal) {
        edi::remove_archive_directory(folder);
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
        qCWarning(lcCrysta, "dictionary: %s", error.what());
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

QUrl Session::documentationUrl(const QString& uid) const {
    // Only dictionary identities may become links; no user-provided URL or fragment.
    if (!edi::has_item(uid.toStdString())) return {};
    QString anchor = uid;
    anchor.replace('_', '-');
    anchor.replace('.', '-');
    return QUrl(QStringLiteral("https://enhantica.github.io/edi/physics/parameters/#") + anchor);
}

QString Session::categoryTitle(const QString& id) const {
    return from_bridge([&] { return edi::category_label(id.toStdString()); });
}

QString Session::categoryIcon(const QString& id) const {
    return from_bridge([&] { return edi::category_icon(id.toStdString()); });
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
        qCWarning(lcCrysta, "dictionary: %s", error.what());
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
