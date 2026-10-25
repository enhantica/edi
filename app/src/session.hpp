// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_SESSION_HPP
#define EDI_APP_SESSION_HPP

#include <QObject>
#include <QString>
#include <QTemporaryDir>
#include <QUrl>
#include <QtQml/qqmlregistration.h>
#include <memory>
#include <vector>

#include "example_list_model.hpp"
#include "project_view_model.hpp"
#include "row_table_model.hpp"

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
    Q_PROPERTY(edi_app::ProjectViewModel* project READ project NOTIFY projectChanged)
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

   public:
    explicit Session(QObject* parent = nullptr);
    ~Session() override;

    ProjectViewModel* project() const { return project_; }
    bool hasProject() const { return project_ != nullptr; }
    QString lastError() const { return last_error_; }
    ExampleListModel* examples() const { return examples_; }
    WarningListModel* loadWarnings() const { return warnings_; }
    QString openedExample() const { return opened_example_; }
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
    // Write the open project's folder, as last saved and with its reports, as one .zip at `archive` (a `file:` URL),
    // the archive every surface writes (edi ADR-0052). A project with no folder yet is written to a temporary one
    // first. False, with `lastError` saying why, when it cannot be written.
    Q_INVOKABLE bool exportProject(const QUrl& archive);
    // The open project's folder, or the temporary one it was unpacked or exported into, for the browser's download.
    Q_INVOKABLE QString exportFolder();
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
    void replaceProject(ProjectViewModel* project, const QStringList& warnings, const QString& example);
    void setLastError(const QString& error);

    ProjectViewModel* project_ = nullptr;
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
