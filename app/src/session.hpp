// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_SESSION_HPP
#define EDI_APP_SESSION_HPP

#include <QObject>
#include <QJsonArray>
#include "edi/calculation.hpp"
#include <optional>
#include <QString>
#include <QTemporaryDir>
#include <QUrl>
#include <QtQml/qqmlregistration.h>
#include <memory>
#include <functional>
#include <vector>

#include "example_list_model.hpp"
#include "project_view_model.hpp"
#include "row_table_model.hpp"
#include "assistant_view_model.hpp"

class QQmlEngine;
class QJSEngine;

namespace edi_app {
struct ImmutableAssistantResult;

// The app's one list of messages (edi ADR-0017 §14): the warnings the last open reported and the errors the
// views used to show in red — a calculation refusal, one row per distinct refusal. Roles `message` and
// `severity` ("warning" or "error"). The one source of the status bar's warnings item and its popup.
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
    Q_PROPERTY(edi_app::ProjectViewModel* project READ project NOTIFY projectChanged)
    Q_PROPERTY(edi_app::AssistantViewModel* assistant READ assistant CONSTANT)
    Q_PROPERTY(bool hasProject READ hasProject NOTIFY hasProjectChanged)
    Q_PROPERTY(QString lastError READ lastError NOTIFY lastErrorChanged)
    Q_PROPERTY(edi_app::ExampleListModel* examples READ examples CONSTANT)
    Q_PROPERTY(edi_app::WarningListModel* loadWarnings READ loadWarnings CONSTANT)
    // The bundled example the open project came from, empty for a project opened from its directory
    // or created (its extracted location is a temporary directory, not the user's).
    Q_PROPERTY(QString openedExample READ openedExample NOTIFY openedExampleChanged)
    // Where the open project is, as the Description tab shows it: its directory, for an example the working
    // copy a save writes (edi ADR-0017 §9). The demo shows the working copy's temporary root as
    // "<temporary>", so its images do not change with the run's directory.
    Q_PROPERTY(QString projectLocation READ projectLocation NOTIFY projectLocationChanged)
    // Whether Save must ask where (edi ADR-0017 §13): a project with no directory yet, or a bundled example's
    // temporary working copy, is saved as.
    Q_PROPERTY(bool needsSaveAs READ needsSaveAs NOTIFY needsSaveAsChanged)
    Q_PROPERTY(bool needsFreshSaveAs READ needsFreshSaveAs NOTIFY needsSaveAsChanged)

   public:
    explicit Session(QObject* parent);
    static Session* create(QQmlEngine* engine, QJSEngine* script_engine);
#ifndef __EMSCRIPTEN__
    Session(edi::assistant::native::NativeDependencies dependencies, QObject* parent = nullptr);
#endif
    ~Session() override;

    ProjectViewModel* project() const { return project_; }
    AssistantViewModel* assistant() const { return assistant_; }
    bool hasProject() const { return project_ != nullptr; }
    QString lastError() const { return last_error_; }
    ExampleListModel* examples() const { return examples_; }
    WarningListModel* loadWarnings() const { return warnings_; }
    QString openedExample() const { return opened_example_; }
    QString projectLocation() const;
    bool needsSaveAs() const;
    bool needsFreshSaveAs() const { return fresh_result_; }
    Q_INVOKABLE QString beginSaveAs();
    Q_INVOKABLE bool saveAsCurrent(const QString& intent) const;
    Q_INVOKABLE bool completeSaveAs(const QString& intent, const QUrl& parent, const QString& leaf);
    Q_INVOKABLE void cancelSaveAs(const QString& intent);

    // Open a project directory; only `file:` URLs (seam row 13).
    Q_INVOKABLE bool openProject(const QUrl& directory);
    // Open a bundled example: extracted to this session's temporary directory, then opened whole.
    Q_INVOKABLE bool openExample(const QString& exampleId);
    // A new empty project; with a `location` it is saved there at once, so it is that folder's project from the start
    // and Save writes in place (the owner, 2026-10-08). A refused save keeps the project, unsaved, and says why.
    // `suRule` is the preference's rule for standard uncertainties, "iucr_19" or "iucr_99". A title
    // and authors go into `_metadata` as the Project page writes them; an empty title keeps the default one.
    // `reportLibraries` is the preference for whether its saved HTML reports embed their chart libraries, written into
    // the new project's `_report.html_offline` (ADR-0036 §7); no other project takes the preference.
    Q_INVOKABLE bool createProject(const QString& name, const QString& description, const QString& location = QString(),
                                   const QString& suRule = QStringLiteral("iucr_19"), const QString& title = QString(),
                                   const QString& authors = QString(), bool reportLibraries = false);
    Q_INVOKABLE void closeProject();
    // The open project's calculation refusals into the message list, after each recalculation (§14).
    void syncCalculationMessages();
    // Save the open project to its directory, or into `directory` (a `file:` URL), which then is its
    // directory. False, with `lastError` the core's message, when the write is refused; `save` refuses
    // when the project must be saved as.
    Q_INVOKABLE bool save();
    Q_INVOKABLE bool saveAs(const QUrl& directory);
    Q_INVOKABLE void clearError();
    /// Whether a saved project directory is present on disk.
    Q_INVOKABLE bool projectDirectoryExists(const QString& path) const;
    /// Turn a native directory path into the file URL accepted by openProject.
    Q_INVOKABLE QUrl projectDirectoryUrl(const QString& path) const;

   signals:
    void projectChanged();
    void projectDirectoryUsed(const QString& path);
    void hasProjectChanged();
    void openedExampleChanged();
    void projectLocationChanged();
    void needsSaveAsChanged();
    void lastErrorChanged();
    // A project or an example could not be opened: every refused open says why (the window shows it), never a silent
    // no-op.
    void loadFailed(const QString& message);

   private:
    bool openProjectAt(const QUrl& directory);
    bool openExampleNamed(const QString& exampleId);
    bool open(const QString& directory, const QString& example);
    // Opens `source` (a read-only folder) from a writable copy at `target`: the project and its results are copied, and
    // a scan's data files linked, not duplicated.
    bool openCopy(const QString& source, const QString& target, const QString& example);
    bool replaceProject(ProjectViewModel* project, const QStringList& warnings, const QString& example,
                        bool managedResult = false, std::shared_ptr<ImmutableAssistantResult> result = {},
                        std::optional<edi::WorkStamps> resultStamps = {});
    friend class AssistantViewModel;
    quint64 assistantEpoch() const noexcept { return assistant_epoch_; }
    bool emptyAssistantOwner(quint64 epoch) const noexcept;
    void retireAssistantIntent() noexcept;
    void retireExportIntent() noexcept;
    bool adoptAssistantResult(std::shared_ptr<ImmutableAssistantResult> result, quint64 epoch, const std::function<bool()>& current);
    struct SaveIntent;
    bool saveIntentCurrent(const SaveIntent& intent) const;
    std::unique_ptr<SaveIntent> save_intent_;
    std::shared_ptr<ImmutableAssistantResult> assistant_result_;
    quint64 assistant_epoch_ = 0;
    quint64 replacement_generation_ = 0; // Private exact synchronous attachment owner.
    bool assistant_epoch_exhausted_ = false, fresh_result_ = false, result_edited_ = false;
    std::optional<edi::WorkStamps> result_saved_stamps_;
    QString exported_result_;
    QJsonArray exported_files_;
    void setLastError(const QString& error);

    ProjectViewModel* project_ = nullptr;
    friend void configure_engine(QQmlEngine&, std::unique_ptr<Session>);
    bool engine_bound_ = false;
    AssistantViewModel* assistant_ = nullptr;
    QString last_error_;
    ExampleListModel* examples_;
    WarningListModel* warnings_;
    int project_messages_ = 0;  // the keys of the project's messages
    std::unique_ptr<QTemporaryDir> extracted_;
    QString opened_example_;
    // The open project is a temporary copy of a folder this user may not write: Save As is its way out.
    bool read_only_copy_ = false;
    // Copies every file under `source` to `target`, writable by the owner; those under `linked` are hard links.
    bool copyTree(const QString& source, const QString& target, const QString& linked);
};

}  // namespace edi_app

#endif  // EDI_APP_SESSION_HPP
