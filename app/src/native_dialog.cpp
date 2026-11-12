// SPDX-License-Identifier: BSD-3-Clause
#include "native_dialog.hpp"
#include <QCoreApplication>
#include <QDir>
#include <QJsonArray>
#include <QJsonDocument>
#include <QQmlEngine>
#include <QQmlComponent>
#ifndef __EMSCRIPTEN__
#include <QProcess>
#endif

namespace edi_app {
namespace {
#ifndef __EMSCRIPTEN__
constexpr qsizetype maximum_reply = 64 * 1024 * 1024;
void reap(QProcess* process) {
    if (!process) return;
    process->disconnect();
    // QProcess destruction waits; a child killed during shutdown must outlive QObject teardown.
    process->setParent(nullptr);
    if (process->state() == QProcess::NotRunning) process->deleteLater();
    else {
        QObject::connect(process, &QProcess::stateChanged, process, [process](QProcess::ProcessState state) {
            if (state == QProcess::NotRunning) process->deleteLater();
        });
        process->kill();
    }
}
#endif
}
NativeFileDialog::NativeFileDialog(QObject* parent) : QObject(parent) {}
NativeFileDialog::~NativeFileDialog() { if (broker_) broker_->retire(this); }
QJsonObject NativeFileDialog::request() const {
    return {{"schema", 1}, {"directory", directory_}, {"mode", static_cast<int>(mode_)}, {"title", title_},
            {"acceptLabel", accept_label_}, {"defaultSuffix", suffix_}, {"nameFilters", QJsonArray::fromStringList(filters_)},
            {"currentFolder", folder_.toString(QUrl::FullyEncoded)},
            {"selectedFile", (directory_ ? selected_folder_ : selected_file_).toString(QUrl::FullyEncoded)}};
}
void NativeFileDialog::setVisible(bool visible) {
    if (visible_ == visible) return;
    visible_ = visible;
    emit visibleChanged();
}
void NativeFileDialog::complete(const QList<QUrl>& files, const QUrl& folder, bool acceptedResult) {
    const QPointer<NativeFileDialog> self(this);
    if (acceptedResult) {
        selected_files_ = files;
        selected_file_ = files.value(0);
        selected_folder_ = directory_ ? selected_file_ : QUrl();
        folder_ = folder;
        emit selectedFilesChanged(); if (!self) return;
        emit selectedFileChanged(); if (!self) return;
        emit selectedFolderChanged(); if (!self) return;
        emit currentFolderChanged(); if (!self) return;
    }
    setVisible(false); if (!self) return;
    if (acceptedResult) emit accepted(); else emit rejected();
}
void NativeFileDialog::open() {
    if (visible_) return;
#ifdef __EMSCRIPTEN__
    if (!fallback_) {
        auto* engine = qmlEngine(this);
        if (!engine) { emit rejected(); return; }
        QQmlComponent component(engine);
        component.setData(directory_ ? "import QtQuick.Dialogs; FolderDialog {}" : "import QtQuick.Dialogs; FileDialog {}", QUrl());
        fallback_ = component.create(qmlContext(this));
        if (!fallback_) { emit rejected(); return; }
        fallback_->setParent(this);
        connect(fallback_, SIGNAL(accepted()), this, SLOT(fallbackAccepted()));
        connect(fallback_, SIGNAL(rejected()), this, SLOT(fallbackRejected()));
    }
    fallback_->setProperty("title", title_);
    fallback_->setProperty("acceptLabel", accept_label_);
    fallback_->setProperty("currentFolder", folder_);
    if (directory_) fallback_->setProperty("selectedFolder", selected_folder_);
    else {
        fallback_->setProperty("fileMode", static_cast<int>(mode_));
        fallback_->setProperty("defaultSuffix", suffix_);
        fallback_->setProperty("nameFilters", filters_);
        fallback_->setProperty("selectedFile", selected_file_);
    }
    const QPointer<NativeFileDialog> self(this);
    setVisible(true);
    if (self) QMetaObject::invokeMethod(fallback_, "open");
#else
    auto* engine = qmlEngine(this);
    auto* broker = engine ? engine->singletonInstance<NativeDialogs*>("edi.app", "NativeDialogs") : nullptr;
    if (broker) broker->open(this); else emit rejected();
#endif
}
void NativeFileDialog::close() { reject(); }
void NativeFileDialog::reject() {
#ifdef __EMSCRIPTEN__
    if (fallback_ && visible_) QMetaObject::invokeMethod(fallback_, "reject");
#else
    if (broker_ && broker_->owner_ == this) broker_->cancel();
#endif
}
#ifdef __EMSCRIPTEN__
void NativeFileDialog::fallbackAccepted() {
    const auto files = directory_ ? QList<QUrl>{fallback_->property("selectedFolder").toUrl()}
                                  : fallback_->property("selectedFiles").value<QList<QUrl>>();
    complete(files, fallback_->property("currentFolder").toUrl(), true);
}
void NativeFileDialog::fallbackRejected() { complete({}, {}, false); }
#endif

NativeDialogs::NativeDialogs(QObject* parent)
    : NativeDialogs(QCoreApplication::applicationFilePath(), {QStringLiteral("--native-dialog-helper")}, 30000, parent) {}
NativeDialogs::NativeDialogs(QString program, QStringList arguments, int startupMilliseconds, QObject* parent)
    : QObject(parent), program_(std::move(program)), arguments_(std::move(arguments)), startup_ms_(startupMilliseconds) {
    startup_.setSingleShot(true);
#ifndef __EMSCRIPTEN__
    connect(&startup_, &QTimer::timeout, this, [this] {
        finish(tr("The system file chooser did not open. You can try again."));
    });
    connect(QCoreApplication::instance(), &QCoreApplication::aboutToQuit, this, &NativeDialogs::cancel);
#endif
}
NativeDialogs::~NativeDialogs() {
#ifndef __EMSCRIPTEN__
    reap(process_);
#endif
}
void NativeDialogs::dismissError() { if (!error_.isEmpty()) { error_.clear(); emit errorChanged(); } }
void NativeDialogs::retire(NativeFileDialog* dialog) {
    if (owner_ != dialog) return;
    owner_.clear();
    cancel();
}
void NativeDialogs::cancel() {
#ifndef __EMSCRIPTEN__
    if (process_) finish();
#endif
}
void NativeDialogs::open(NativeFileDialog* dialog) {
#ifndef __EMSCRIPTEN__
    if (!dialog) return;
    if (process_) {
        if (owner_ != dialog) dialog->complete({}, {}, false);
        return;
    }
    auto* process = new QProcess(this);
    process_ = process;
    owner_ = dialog;
    auto* engine = qmlEngine(dialog);
    session_ = engine ? engine->singletonInstance<QObject*>("edi.app", "Session") : nullptr;
    original_project_ = session_ ? session_->property("project").value<QObject*>() : nullptr;
    had_project_ = original_project_ != nullptr;
    dialog->broker_ = this;
    output_.clear(); result_ = {};
    error_.clear(); title_ = dialog->title_; opening_ = true;
    const QPointer<NativeDialogs> self(this);
    connect(process, &QProcess::started, this, [this, process, request = dialog->request()] {
        if (process_ != process) return;
        process->write(QJsonDocument(request).toJson(QJsonDocument::Compact) + '\n');
    });
    connect(process, &QProcess::readyReadStandardOutput, this, &NativeDialogs::readOutput);
    connect(process, &QProcess::readyReadStandardError, this, [process] { process->readAllStandardError(); });
    connect(process, &QProcess::errorOccurred, this, [this, process](QProcess::ProcessError) {
        if (process_ == process) finish(tr("The system file chooser could not be opened. You can try again."));
    });
    connect(process, &QProcess::finished, this, [this, process, self](int code, QProcess::ExitStatus status) {
        if (process_ != process) return;
        readOutput();
        if (!self || process_ != process) return;
        const bool valid = code == 0 && status == QProcess::NormalExit && output_.isEmpty() && !result_.isEmpty();
        if (!valid) { finish(tr("The system file chooser closed without a valid answer. You can try again.")); return; }
        finish({}, result_.value("event").toString() == QLatin1String("accepted"));
    });
    startup_.start(startup_ms_);
    process->start(program_, arguments_);
    dialog->setVisible(true);
    if (!self || process_ != process) return;
    emit busyChanged(); if (!self || process_ != process) return;
    emit titleChanged(); if (!self || process_ != process) return;
    emit openingChanged(); if (!self || process_ != process) return;
    emit errorChanged();
#else
    Q_UNUSED(dialog)
#endif
}
#ifndef __EMSCRIPTEN__
void NativeDialogs::readOutput() {
    auto* process = process_.data();
    if (!process) return;
    output_ += process->readAllStandardOutput();
    if (output_.size() > maximum_reply) { finish(tr("The system file chooser returned too much data.")); return; }
    for (;;) {
        const auto newline = output_.indexOf('\n');
        if (newline < 0) break;
        QJsonParseError error;
        const auto document = QJsonDocument::fromJson(output_.left(newline), &error);
        output_.remove(0, newline + 1);
        const auto message = document.object();
        const auto event = message.value("event").toString();
        if (error.error != QJsonParseError::NoError || !document.isObject() || message.value("schema").toInt() != 1 ||
            !result_.isEmpty() || (event != QLatin1String("ready") && event != QLatin1String("accepted") && event != QLatin1String("rejected"))) {
            finish(tr("The system file chooser returned an invalid answer.")); return;
        }
        if (event == QLatin1String("ready")) {
            if (!opening_) { finish(tr("The system file chooser returned an invalid answer.")); return; }
            opening_ = false;
            startup_.stop();
            const QPointer<NativeDialogs> self(this);
            emit openingChanged();
            if (!self || process_ != process) return;
        } else {
            if (opening_) { finish(tr("The system file chooser returned an invalid answer.")); return; }
            if (event == QLatin1String("accepted")) {
                if (!owner_ || !message.value("files").isArray()) { finish(tr("The system file chooser returned an invalid answer.")); return; }
                const auto files = message.value("files").toArray();
                if (files.isEmpty() || ((owner_->directory_ || owner_->mode_ != NativeFileDialog::OpenFiles) && files.size() != 1)) {
                    finish(tr("The system file chooser returned an invalid selection.")); return;
                }
                for (const auto& value : files) {
                    const QUrl url(value.toString(), QUrl::StrictMode);
                    if (!value.isString() || !url.isLocalFile() || url.toLocalFile().contains(QChar::Null) || !QDir::isAbsolutePath(url.toLocalFile())) {
                        finish(tr("The system file chooser returned an invalid selection.")); return;
                    }
                }
                const QUrl folder(message.value("currentFolder").toString(), QUrl::StrictMode);
                if (!folder.isLocalFile() || !QDir::isAbsolutePath(folder.toLocalFile())) {
                    finish(tr("The system file chooser returned an invalid folder.")); return;
                }
            }
            result_ = message;
        }
    }
}
void NativeDialogs::finish(const QString& error, bool acceptedResult) {
    const QPointer<NativeFileDialog> owner = owner_;
    const auto result = result_;
    if ((had_project_ && !original_project_) ||
        (session_ && session_->property("project").value<QObject*>() != original_project_)) acceptedResult = false;
    owner_.clear();
    auto* process = process_.data(); process_.clear();
    startup_.stop(); opening_ = false; title_.clear(); error_ = error;
    output_.clear(); result_ = {};
    reap(process);
    const QPointer<NativeDialogs> self(this);
    emit busyChanged(); if (!self) return;
    emit openingChanged(); if (!self) return;
    emit titleChanged(); if (!self) return;
    emit errorChanged(); if (!self) return;
    if (owner && !process_) {
        QList<QUrl> files;
        if (acceptedResult) for (const auto& value : result.value("files").toArray()) files.append(QUrl(value.toString()));
        owner->complete(files, QUrl(result.value("currentFolder").toString()), acceptedResult);
    }
}
#endif
} // namespace edi_app
