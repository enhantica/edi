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

#include "project_view_model.hpp"
#include "row_table_model.hpp"

namespace edi_app {

// The Examples list: every project of edi's CLI registry, in registry order, then the app's X-ray
// example — bundled in the app's resources. Roles `exampleId`, `name` (sample, instrument and
// variant from the id) and `description` (the technique the id encodes).
class ExampleListModel : public RowTableModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to the session")

   public:
    explicit ExampleListModel(QObject* parent);
    // The ids in list order, from the bundle's index.
    static QStringList bundledIds();
};

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

    // Open a project directory; only `file:` URLs (seam row 13).
    Q_INVOKABLE bool openProject(const QUrl& directory);
    // Open a bundled example: extracted to this session's temporary directory, then opened whole.
    Q_INVOKABLE bool openExample(const QString& exampleId);
    Q_INVOKABLE bool createProject(const QString& name, const QString& description);
    Q_INVOKABLE void closeProject();
    // The open project's calculation refusals into the message list, after each recalculation (§14).
    void syncCalculationMessages();
    // Save the open project to its directory, or into `directory` (a `file:` URL), which then is its
    // directory. False, with `lastError` the core's message, when the write is refused; `save` refuses
    // when the project must be saved as.
    Q_INVOKABLE bool save();
    Q_INVOKABLE bool saveAs(const QUrl& directory);
    Q_INVOKABLE void clearError();

   signals:
    void projectChanged();
    void hasProjectChanged();
    void openedExampleChanged();
    void projectLocationChanged();
    void needsSaveAsChanged();
    void lastErrorChanged();

   private:
    bool open(const QString& directory, const QString& example);
    // Opens `source` from a writable copy at `target` (an example, a read-only folder): the project and its results
    // are copied, a scan's data directory is not (the copy reads it in place, Project::scan_data_root).
    bool openCopy(const QString& source, const QString& target, const QString& example);
    void replaceProject(ProjectViewModel* project, const QStringList& warnings, const QString& example);
    void setLastError(const QString& error);

    ProjectViewModel* project_ = nullptr;
    QString last_error_;
    ExampleListModel* examples_;
    WarningListModel* warnings_;
    std::unique_ptr<QTemporaryDir> extracted_;
    QString opened_example_;
    // The open project is a temporary copy of a folder this user may not write: Save As is its way out.
    bool read_only_copy_ = false;
    // Copies every file under `source` to `target` but those under `skip` (none when empty), writable by the owner.
    bool copyTree(const QString& source, const QString& target, const QString& skip);
};

}  // namespace edi_app

#endif  // EDI_APP_SESSION_HPP
