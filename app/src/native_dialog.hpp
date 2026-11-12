// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_NATIVE_DIALOG_HPP
#define EDI_NATIVE_DIALOG_HPP
#include <QObject>
#include <QPointer>
#include <QUrl>
#include <QJsonObject>
#include <QTimer>
#include <QtQml/qqmlregistration.h>
#include <QQmlListProperty>

class QProcess;
namespace edi_app {
class NativeDialogs;

/// File chooser whose desktop UI runs in a separate process (ADR-0052).
class NativeFileDialog : public QObject {
    Q_OBJECT
    QML_ELEMENT
    Q_CLASSINFO("DefaultProperty", "data")
    Q_PROPERTY(QQmlListProperty<QObject> data READ data CONSTANT)
    Q_PROPERTY(QString title MEMBER title_ NOTIFY titleChanged)
    Q_PROPERTY(QString acceptLabel MEMBER accept_label_ NOTIFY acceptLabelChanged)
    Q_PROPERTY(QString defaultSuffix MEMBER suffix_ NOTIFY defaultSuffixChanged)
    Q_PROPERTY(QStringList nameFilters MEMBER filters_ NOTIFY nameFiltersChanged)
    Q_PROPERTY(QUrl currentFolder MEMBER folder_ NOTIFY currentFolderChanged)
    Q_PROPERTY(QUrl selectedFile MEMBER selected_file_ NOTIFY selectedFileChanged)
    Q_PROPERTY(QList<QUrl> selectedFiles MEMBER selected_files_ NOTIFY selectedFilesChanged)
    Q_PROPERTY(QUrl selectedFolder MEMBER selected_folder_ NOTIFY selectedFolderChanged)
    Q_PROPERTY(FileMode fileMode MEMBER mode_ NOTIFY fileModeChanged)
    Q_PROPERTY(bool visible READ visible NOTIFY visibleChanged)
public:
    enum FileMode { OpenFile, OpenFiles, SaveFile };
    Q_ENUM(FileMode)
    explicit NativeFileDialog(QObject* parent = nullptr);
    ~NativeFileDialog() override;
    QQmlListProperty<QObject> data() { return {this, &data_}; }
    bool visible() const { return visible_; }
    Q_INVOKABLE void open();
    Q_INVOKABLE void close();
    Q_INVOKABLE void reject();
signals:
    void titleChanged();
    void acceptLabelChanged();
    void defaultSuffixChanged();
    void nameFiltersChanged();
    void currentFolderChanged();
    void selectedFileChanged();
    void selectedFilesChanged();
    void selectedFolderChanged();
    void fileModeChanged();
    void visibleChanged();
    void accepted();
    void rejected();
protected:
    bool directory_ = false;
private:
    friend class NativeDialogs;
    QJsonObject request() const;
    void complete(const QList<QUrl>& files, const QUrl& folder, bool accepted);
    void setVisible(bool visible);
    QString title_, accept_label_, suffix_;
    QStringList filters_;
    QUrl folder_, selected_file_, selected_folder_;
    QList<QUrl> selected_files_;
    FileMode mode_ = OpenFile;
    bool visible_ = false;
    QList<QObject*> data_;
    QPointer<NativeDialogs> broker_;
#ifdef __EMSCRIPTEN__
    QPointer<QObject> fallback_;
private slots:
    void fallbackAccepted();
    void fallbackRejected();
#endif
};

/// A folder chooser with the same process and lifetime rules as NativeFileDialog.
class NativeFolderDialog : public NativeFileDialog {
    Q_OBJECT
    QML_ELEMENT
public:
    explicit NativeFolderDialog(QObject* parent = nullptr) : NativeFileDialog(parent) { directory_ = true; }
};

/// Owns the active desktop chooser; cancellation and process reaping never wait on its UI.
class NativeDialogs : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_SINGLETON
    Q_PROPERTY(bool busy READ busy NOTIFY busyChanged)
    Q_PROPERTY(bool opening READ opening NOTIFY openingChanged)
    Q_PROPERTY(QString title READ title NOTIFY titleChanged)
    Q_PROPERTY(QString error READ error NOTIFY errorChanged)
public:
    explicit NativeDialogs(QObject* parent = nullptr);
    /// Explicit transport and startup deadline, for standalone lifecycle checks.
    NativeDialogs(QString program, QStringList arguments, int startupMilliseconds, QObject* parent = nullptr);
    ~NativeDialogs() override;
    bool busy() const { return process_ != nullptr; }
    bool opening() const { return opening_; }
    QString title() const { return title_; }
    QString error() const { return error_; }
    void open(NativeFileDialog* dialog);
    void retire(NativeFileDialog* dialog);
    Q_INVOKABLE void cancel();
    Q_INVOKABLE void dismissError();
signals:
    void busyChanged();
    void openingChanged();
    void titleChanged();
    void errorChanged();
private:
    friend class NativeFileDialog;
#ifndef __EMSCRIPTEN__
    void readOutput();
    void finish(const QString& error = {}, bool accepted = false);
    QPointer<QProcess> process_;
#else
    QObject* process_ = nullptr;
#endif
    QPointer<NativeFileDialog> owner_;
    QPointer<QObject> session_, original_project_;
    QTimer startup_;
    QString program_, title_, error_;
    QStringList arguments_;
    QByteArray output_;
    QJsonObject result_;
    int startup_ms_ = 30000;
    bool opening_ = false;
    bool had_project_ = false;
};
} // namespace edi_app
#endif
