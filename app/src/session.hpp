// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_SESSION_HPP
#define EDI_APP_SESSION_HPP

#include <QObject>
#include <QPointer>
#include <QString>
#include <QStringList>
#include <QTimer>
#include <QUrl>
#include <QtQml/qqmlregistration.h>
#include <functional>
#include <memory>
#include <vector>

#include "example_list_model.hpp"
#include "project_view_model.hpp"
#include "row_table_model.hpp"
#include "assistant_view_model.hpp"

class QQmlEngine;
class QJSEngine;
#include "web_storage.hpp"

namespace edi_app {

// The app's one list of messages (edi ADR-0017 §14): the warnings the last open reported and the errors the
// views used to show in red — a calculation refusal, one row per distinct refusal — and information entries (why an
// estimate subtracted or ignored the calculated peaks). Roles `message` and `severity` ("warning", "error" or
// "information"). The one source of the status bar's warnings item and its popup.
class WarningListModel : public RowTableModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to the session")
    // How many of the listed messages have not been viewed yet (the status bar's Messages item; edi
    // ADR-0017 §14): all of a fresh open's, none once the Messages dialog has shown them, and a message
    // raised later again. Each message carries its own viewed state and the count is derived from them, so
    // removing one (a dismissal, a withdrawn refusal) takes away exactly its own share.
    Q_PROPERTY(int unviewedCount READ unviewedCount NOTIFY unviewedCountChanged)

   public:
    explicit WarningListModel(QObject* parent);
    // Replace every message with the open's warnings (a new open).
    void setMessages(const QStringList& messages);
    // List a message under `key` unless one is listed there already (a dismissed one is listed again);
    // withdraw the one under `key`; the keys listed that start with `prefix`.
    void post(const QString& key, const QString& text, const QString& severity);
    void withdraw(const QString& key);
    QStringList keys(const QString& prefix) const;
    int unviewedCount() const { return unviewed_; }
    Q_INVOKABLE void markViewed();
    // Remove one warning (by its row) or all of them.
    Q_INVOKABLE void dismiss(int row);
    Q_INVOKABLE void dismissAll();

   signals:
    void unviewedCountChanged();

   private:
    struct Message {
        int id = 0;  // the row's key while it is listed
        QString key;
        QString text;
        QString severity;
        bool viewed = false;
    };
    // After any change of the list: its rows to the table, then the count.
    void changed();
    void publish();
    void recount();
    std::vector<Message> messages_;
    int next_id_ = 1;
    int unviewed_ = 0;
};

// The app's one session: opens, creates and closes the project. The project is replaced only by
// those three calls (I5); a refused open leaves the open project untouched and names the refusal
// in `lastError`.
class Session : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_SINGLETON
    Q_PROPERTY(edi_app::AssistantViewModel* assistant READ assistant CONSTANT)
    Q_PROPERTY(bool assistantWorkReportsAutomatic READ assistantWorkReportsAutomatic CONSTANT)
    Q_PROPERTY(edi_app::ProjectViewModel* project READ project NOTIFY projectChanged)
    Q_PROPERTY(bool hasProject READ hasProject NOTIFY hasProjectChanged)
    Q_PROPERTY(QString lastError READ lastError NOTIFY lastErrorChanged)
    Q_PROPERTY(edi_app::ExampleListModel* examples READ examples CONSTANT)
    Q_PROPERTY(edi_app::WarningListModel* loadWarnings READ loadWarnings CONSTANT)
    // The bundled example the open project came from, empty for a project opened from its directory
    // or created (its extracted location is a temporary directory, not the user's).
    Q_PROPERTY(QString openedExample READ openedExample NOTIFY openedExampleChanged)
    // The .zip the open project was unpacked from, by file name, until it is saved somewhere (edi ADR-0052).
    Q_PROPERTY(QString openedArchive READ openedArchive NOTIFY openedArchiveChanged)
    // Where the project is, as the Project page shows it (edi ADR-0052): its folder or .zip, or, when it has none of
    // its own yet, what it came from ("Not saved yet: …"); never an internal temporary path.
    Q_PROPERTY(QString locationText READ locationText NOTIFY locationTextChanged)
    // Where the open project is, as the Description tab shows it: its directory, for an example the working
    // copy a save writes (edi ADR-0017 §9). The demo shows the working copy's temporary root as
    // "<temporary>", so its images do not change with the run's directory.
    Q_PROPERTY(QString projectLocation READ projectLocation NOTIFY projectLocationChanged)
    // Whether Save must ask where (edi ADR-0017 §13): a project with no directory yet, or a bundled example's
    // temporary working copy, is saved as.
    Q_PROPERTY(bool needsSaveAs READ needsSaveAs NOTIFY needsSaveAsChanged)

   public:
    explicit Session(QObject* parent, AssistantWorkReportOptions options = {});
    static Session* create(QQmlEngine* engine, QJSEngine* script_engine);
    AssistantViewModel* assistant() const { return assistant_; }
    bool assistantWorkReportsAutomatic() const { return work_report_options_.automatic; }
#ifndef __EMSCRIPTEN__
    Session(edi::assistant::native::NativeDependencies, QObject* parent=nullptr, AssistantWorkReportOptions options={});
#endif
    ~Session() override;

    ProjectViewModel* project() const { return project_; }
    bool hasProject() const { return project_ != nullptr; }
    QString lastError() const { return last_error_; }
    ExampleListModel* examples() const { return examples_; }
    WarningListModel* loadWarnings() const { return warnings_; }
    QString openedExample() const { return opened_example_; }
    QString openedArchive() const { return opened_archive_; }
    QString locationText() const;
    QString projectLocation() const;
    bool needsSaveAs() const;

    // Open a project from its folder, its project.edi or a .zip of the folder; only `file:` URLs (edi ADR-0052). An
    // archive unpacks into a temporary folder: the project has no folder of its own until Save asks where to keep it.
    Q_INVOKABLE bool openProject(const QUrl& location);
    // Open a bundled example: extracted to this session's temporary directory, then opened whole.
    Q_INVOKABLE bool openExample(const QString& exampleId);
    // A new empty project; with a `location` it is saved there at once, so it is that folder's project from the start
    // and Save writes in place (the owner, 2026-10-08). A refused save keeps the project, unsaved, and says why.
    // `suRule` is the preference's rule for standard uncertainties, "iucr_19" or "iucr_99". A title
    // and authors go into `_metadata` as the Project page writes them; an empty title keeps the default one.
    // `reportLibraries` is the preference for whether its saved HTML reports embed their chart libraries, written into
    // the new project's `_report.html_offline` (ADR-0036 §7); no other project takes the preference.
    Q_INVOKABLE bool createProject(const QString& name, const QString& description, const QString& location = QString(),
                                   const QString& suRule = QStringLiteral("iucr_99"), const QString& title = QString(),
                                   const QString& authors = QString(), bool reportLibraries = false, const QString& assistantIntent = QString());
    Q_INVOKABLE QVariantMap createProjectWithOutcome(const QString&,const QString&,const QString&,const QString&,const QString&,const QString&,bool,const QString&);
    Q_INVOKABLE bool creationOutcomeCurrent(const QVariantMap&) const;
    Q_INVOKABLE void closeProject();
    // The open project's calculation refusals into the message list, after each recalculation (§14).
    void syncCalculationMessages();
    // Save the open project to its directory, or into `directory` (a `file:` URL), which then is its
    // directory. False, with `lastError` the core's message, when the write is refused; `save` refuses
    // when the project must be saved as.
    Q_INVOKABLE bool save();
    Q_INVOKABLE bool saveAs(const QUrl& directory);
    // Save as (edi ADR-0052): into the folder or the .zip `target` (a `file:` URL), as `zip` says. A project saved as a
    // .zip keeps the archive as its location and every later Save rewrites it. With `copy` the project is written
    // there as it stands and stays where it is: a copy. False, with `lastError` saying why, when it cannot be written.
    Q_INVOKABLE bool saveProjectAs(const QUrl& target, bool zip, bool copy);
    // A project opened from or saved as a .zip keeps its reports inside it: after Save report wrote them into the folder
    // the project works in, the archive is rewritten from that folder (the owner, 2026-10-27). Nothing to do for a
    // folder project. An empty string, else why the archive could not be written.
    Q_INVOKABLE QString writeBackReports();
    Q_INVOKABLE void clearError();
    // Where Save project as starts, with the name filled in (owner, 2026-10-25): the project's own folder or .zip
    // name (the project's name for one with neither), `.zip` for an archive, in the folder the project is in, else in
    // the user's documents.
    Q_INVOKABLE QUrl suggestedSaveTarget(bool zip) const;
    Q_INVOKABLE bool assistantSaveAsCurrent(const QString& token) const;
    Q_INVOKABLE QUrl assistantSaveAsTarget(const QString& token, bool zip) const;
    Q_INVOKABLE bool completeAssistantSaveAs(const QString& token, const QUrl& target, bool zip, bool copy);
    Q_INVOKABLE void cancelAssistantSaveAs(const QString& token);

    // The web app (edi ADR-0052 §9). Every project there has a place: the browser's own storage, or in Chrome and Edge
    // a folder or a .zip on the disk; Save writes into it, never a download.
    // Asks for a project "folder" or "zip" and opens it: from the disk where the browser can write it back, else as a
    // copy kept in the browser.
    Q_INVOKABLE void openWebProject(const QString& kind);
    // Reopens a stored place, or the unsaved state kept for it (`recovery`).
    Q_INVOKABLE void openStoredProject(const QString& key, bool recovery);
    // Save as onto the disk, where the browser can write it: a "folder" or a "zip" the user picks becomes the
    // project's place, or with `copy` only receives a copy.
    Q_INVOKABLE void saveWebProjectAs(const QString& kind, bool copy);
    // Save as where the browser cannot write the disk: a copy of the project, as saved, handed to the browser as a
    // .zip; the project and the browser's storage are left as they are.
    Q_INVOKABLE void downloadWebProject();
    // The unsaved state kept for the open project is no longer wanted (its changes were discarded).
    Q_INVOKABLE void discardKeptChanges();
    /// Whether a saved project directory is present on disk.
    Q_INVOKABLE bool projectDirectoryExists(const QString& path) const;
    /// Turn a native directory path into the file URL accepted by openProject.
    Q_INVOKABLE QUrl projectDirectoryUrl(const QString& path) const;

    // Every name and number a page shows, from crysta's dictionary through the core's display bridge: an item's
    // label, units and tooltip (the label and the `.edi` name it labels), a selector option's name, a category's
    // title, and a value in the item's display format. `uid` is `category.name`; `variant` the token its label or
    // format depends on (an ADP's type). An item the dictionary lacks shows its uid, so the page still reads.
    Q_INVOKABLE QString label(const QString& uid, const QString& variant = QString()) const;
    Q_INVOKABLE QString units(const QString& uid, const QString& variant = QString()) const;
    Q_INVOKABLE QString tooltip(const QString& uid, const QString& variant = QString()) const;
    Q_INVOKABLE QString optionLabel(const QString& uid, const QString& token) const;
    Q_INVOKABLE QString optionTooltip(const QString& uid, const QString& token) const;
    Q_INVOKABLE QString categoryTitle(const QString& id) const;
    // A value of item `uid` as a save writes it, for an input field or an editable cell (edi ADR-0051).
    Q_INVOKABLE QString written(const QString& uid, double value) const;
    Q_INVOKABLE QString display(const QString& uid, double value, const QString& variant = QString()) const;
    // A read-only value of item `uid` and its s.u. as a table shows them apart: rounded by the s.u. under the project's
    // rule (edi::fitted_text), or without one by the item's display format, the s.u. then empty.
    Q_INVOKABLE QString valueText(const QString& uid, double value, double su) const;
    Q_INVOKABLE QString suText(const QString& uid, double value, double su) const;

   signals:
    // Just before the open project is replaced (or closed): the pages let go of it first (edi ADR-0052).
    void projectAboutToChange();
    void projectChanged();
    void assistantSaveAsRequested(const QString& token);
    void projectDirectoryUsed(const QString& path);
    void hasProjectChanged();
    void openedExampleChanged();
    void openedArchiveChanged();
    void locationTextChanged();
    void projectLocationChanged();
    void needsSaveAsChanged();
    void lastErrorChanged();
    // A project or an example could not be opened: every refused open says why (the window shows it), never a silent
    // no-op.
    void loadFailed(const QString& message);
    // The web app wrote the project into its place (`kind`: "browser", "folder" or "zip"), or downloaded it as `name`.
    void webSaved(const QString& kind);
    // `fromFile`: the project came from a file the user may want to replace.
    void webDownloaded(const QString& name, bool fromFile);
    // Save found that the browser keeps nothing for the app (a private window may not): nothing was saved.
    void webStorageUnavailable();
    // A write to the project's place, or a download, failed: why.
    void webSaveFailed(const QString& message);
    // A Save or a moving Save as in the web app finished: `saved` once its place holds the project. A replacement
    // or a quit waiting on the Save goes on only then.
    void webSaveFinished(bool saved);

   private:
    bool openProjectAt(const QUrl& directory);
    bool openExampleNamed(const QString& exampleId);
    bool open(const QString& directory,const QString& example,const std::function<bool()>& afterOpen = {});
    // Opens `source` (a read-only folder) from a writable copy at `target`: the project and its results are copied, and
    // a scan's data files linked, not duplicated.
    bool openCopy(const QString& source,const QString& target,const QString& example,const std::function<bool()>& afterOpen = {});
    bool replaceProject(ProjectViewModel* project, const QStringList& warnings, const QString& example, bool nativePrepared=false, bool* committed=nullptr, quint64* committedReplacement=nullptr, bool ordinaryEmptyCreate=false, const QString& openedFrom={}, const std::shared_ptr<AssistantViewModel::ProjectResetInputs>& resetInputs={});
    void setLastError(const QString& error);
    void setOpenedArchive(const QString& name);
    bool saveInto(const QString& folder);
    // After a Save as: the project is no longer an example's, an archive's or a read-only tree's temporary copy.
    void leaveTemporaryOrigin();
    bool saveCopy(const QString& target, bool zip);
    bool saveProjectAsFresh(const QUrl& target,bool zip,bool copy,bool notify = true);

    const AssistantWorkReportOptions work_report_options_;
    void initializeSession();
    struct ProjectCreationOutcome;
    bool createProjectImpl(const QString&,const QString&,const QString&,const QString&,const QString&,const QString&,bool,const QString&,ProjectCreationOutcome*);
    friend class AssistantViewModel;
    quint64 assistantEpoch() const noexcept { return assistant_epoch_; }
    bool assistantOwner(quint64 epoch,ProjectViewModel* expected) const noexcept;
    bool emptyAssistantOwner(quint64 epoch) const noexcept;
    void retireAssistantIntent() noexcept;
    std::unique_ptr<ProjectViewModel> prepareAssistantNativeModel(edi::Project, quint64, const std::function<bool()>&);
    bool commitAssistantNativeModel(std::unique_ptr<ProjectViewModel>, quint64, const std::function<bool()>&, bool&);
    quint64 assistant_epoch_=0, replacement_generation_=0;
    bool assistant_epoch_exhausted_=false;
    std::uint64_t assistant_save_origin_=0;
    struct AssistantSaveChoice {
        QString token, suggestion;
        QPointer<ProjectViewModel> owner;
        quint64 epoch=0;
        std::function<bool()> current;
        std::function<bool(const QUrl&,bool,bool)> accepted;
        std::function<void()> cancelled;
    };
    std::unique_ptr<AssistantSaveChoice> assistant_save_choice_;
    bool requestAssistantSaveAs(const QString&, const QString&, ProjectViewModel*, quint64,
        std::function<bool()>, std::function<bool(const QUrl&,bool,bool)>, std::function<void()>);
    friend void configure_engine(QQmlEngine&, std::unique_ptr<Session>);
    bool engine_bound_ = false;
    AssistantViewModel* assistant_ = nullptr;
    ProjectViewModel* project_ = nullptr;
    QString last_error_;
    ExampleListModel* examples_;
    WarningListModel* warnings_;
    int project_messages_ = 0;  // the keys of the project's messages
    QString opened_example_;
    QString opened_archive_;
    // The .zip the project was saved as: its location, rewritten by every Save from the working folder.
    QString archive_location_;
    // The read-only folder a temporary working copy was made from.
    QString read_only_source_;
    // The temporary folder the project works in (an unpacked archive), removed when it is no longer the project's.
    QString temporary_folder_;
    void releaseTemporaryFolder();
    // Cleanup authority only: never an inherited origin/Save destination.
    QStringList retained_temporary_roots_;
    QString prepareCopyRoot(const char* kind);
    void retainTemporaryRoots(const QStringList& candidates);
    struct PendingOpenSource;
    QStringList pending_open_sources_;
    quint64 path_generation_=0;
    void releaseTemporaryRoots(const QStringList& candidates, const QString& openedFrom = {}) noexcept;
    // The open project is a temporary copy of a folder this user may not write: Save As is its way out.
    bool read_only_copy_ = false;
    // Copies every file under `source` to `target`, writable by the owner; those under `linked` are hard links.
    bool copyTree(const QString& source, const QString& target, const QString& linked);

    // The web app's place of the open project: its key in the browser's records, its kind and its name.
    struct WebPlace {
        QString key;
        QString kind;
        QString name;
    };
    WebPlace web_place_;
    // The open project's place is the browser's own storage until a Save as onto the disk.
    void setWebPlace(const WebPlace& place);
    // The answer to a browser chooser that copied a project into `root` in memory: opens it there.
    WebStorage::Answer webOpenAnswer(const QString& root, bool fromFile = true, bool recovery = false);
    // Opens the project folder or archive the browser copied into memory at `path`, from the place `place`.
    bool openWebCopy(const QString& path, const WebPlace& place);
    // Writes `folder` into `place`; `done` hears whether it was written.
    void writeWebPlace(const WebPlace& place, const QString& folder, const std::function<void(bool)>& done);
    // A browser Save, Save as or copy is being written to a place: another waits until it is, whatever project is open
    // by then. Only the write's own completion releases it.
    bool web_writing_ = false;
    // A save staged on a copy: its folder inside a new `root` and the metadata it wrote.
    struct Staged {
        QString root;
        QString folder;
        std::shared_ptr<edi::Project> project;  // the staged copy: what the open project takes once published
        ProjectViewModel::StagedScan scan;             // what a scan project reads there, read before publication
    };
    // What a Save writes (round, adopt, recalculate, write), done on a copy in `name` inside a new folder (the folder
    // itself for an empty name), once the project may be saved; the open project is left as it is.
    bool stageCopy(const char* purpose, const QString& name, Staged& staged, const QString& parent = {});
    // Writes the staged snapshot into the .zip `archive`, then the project takes it and works in its folder.
    bool publishArchive(const Staged& staged, const QString& archive);
    // The browser's place holds the staged snapshot: the project takes it and works in its folder, unless it was
    // edited since `revision` or a fit started. Whether it did.
    bool takeWebSave(const Staged& staged, quint64 revision);
    // A web open request: its answer replaces the project only if no later request or open came meanwhile, and the
    // project was not edited while it was read.
    std::function<bool(const WebStorageAnswer&)> openRequest(const QString& root);
    quint64 open_request_ = 0;
    // The name a .zip of the project is offered under: the place's own name, or the project's.
    QString downloadName() const;
    // Whether the project's place is the browser's own storage (not a folder or .zip on the disk).
    bool webPlaceInBrowser() const;
    // The open project was uploaded from a file or folder on the disk.
    bool web_from_file_ = false;
    // Keeps the open project's unsaved state in the browser, a few seconds after its last edit.
    void keepChanges();
    QTimer* keep_timer_ = nullptr;
    // The memory folder the browser copied the open project into, released with it.
    QString web_copy_;
    QString web_source_path_; // Current Open/staged input dependency, never a displayed origin.
};

}  // namespace edi_app

#endif  // EDI_APP_SESSION_HPP
