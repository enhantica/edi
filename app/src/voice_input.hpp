// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_VOICE_INPUT_HPP
#define EDI_APP_VOICE_INPUT_HPP

#include "audio_capture.hpp"

#include <QObject>
#include <QPointer>
#include <QString>
#include <QVariantList>
#include <QtQml/qqmlregistration.h>

#include <atomic>
#include <memory>
#include <vector>

namespace edi_app {

/// Voice input for the assistant's message box (ADR-0107): records from the microphone, then turns the recording into
/// text on this computer and hands it to the message box. Nothing is written to disk or sent anywhere.
///
/// The states run Idle → Starting (asking for the microphone) → Listening → Recognising → Idle. `toggle` starts and
/// stops; `cancel` drops the recording or its recognition from any state. A failure returns to Idle with `message`.
/// The item that started a recording is its `owner` until the text arrives; only that item inserts it, and the
/// recording is dropped when the owner goes away.
class VoiceInput : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_SINGLETON
    /// The speech model is installed and this processor can run it: otherwise the message box shows no microphone
    /// button.
    Q_PROPERTY(bool available READ available CONSTANT)
    Q_PROPERTY(State state READ state NOTIFY stateChanged)
    /// The item that started the current recording or recognition; null when idle or started without one.
    Q_PROPERTY(QObject* owner READ owner NOTIFY ownerChanged)
    /// Why the last recording gave no text, in plain words; empty otherwise.
    Q_PROPERTY(QString message READ message NOTIFY messageChanged)
    /// "detect", or a language code from `languages`.
    Q_PROPERTY(QString language READ language WRITE setLanguage NOTIFY languageChanged)
    /// The choices for the language setting: maps with `code` and `name`, "detect" first.
    Q_PROPERTY(QVariantList languages READ languages CONSTANT)

public:
    enum class State { Idle, Starting, Listening, Recognising };
    Q_ENUM(State)

    static constexpr int max_seconds = 120;
    static constexpr int silence_seconds = 2;

    /// The app's voice input: the default microphone and the installed model.
    explicit VoiceInput(QObject* parent = nullptr);
    /// A voice input on `capture` (owned) and the model at `model`; an empty `model` means not installed.
    VoiceInput(std::unique_ptr<AudioCapture> capture, QString model, QObject* parent = nullptr);
    ~VoiceInput() override;

    bool available() const;
    State state() const { return state_; }
    QObject* owner() const { return owner_; }
    QString message() const { return message_; }
    QString language() const { return language_; }
    void setLanguage(const QString& language);
    QVariantList languages() const;

    /// Starts listening when idle, stops and recognises when listening, cancels while starting or recognising.
    /// `owner` becomes the owner of a recording this starts.
    Q_INVOKABLE void toggle(QObject* owner = nullptr);
    /// Stops listening and recognises what was recorded.
    Q_INVOKABLE void stop();
    /// Drops the recording or its recognition; no text follows.
    Q_INVOKABLE void cancel();
    /// Cancels the current recording or recognition if `owner` started it.
    Q_INVOKABLE void release(QObject* owner);
    Q_INVOKABLE void clearMessage();

    /// The installed model's file, checked against its manifest, or empty. `EDI_VOICE_MODEL` names a model file
    /// directly for development and tests.
    static QString installedModel();

signals:
    void stateChanged();
    void ownerChanged();
    void messageChanged();
    void languageChanged();
    /// The recognised text, to insert at the cursor in the message box. It is never sent by itself.
    void textRecognised(const QString& text);

private:
    void captureStarted();
    void captureSamples(const QList<float>& chunk);
    void captureFailed(AudioCapture::Failure failure);
    void finish(int generation, const QString& text, const QString& error, bool cancelled);
    void setState(State state);
    void setMessage(const QString& message);
    void dropRecording();
    void dropOwner();

    std::unique_ptr<AudioCapture> capture_;
    QString model_;
    State state_ = State::Idle;
    QPointer<QObject> owner_;
    QMetaObject::Connection ownerGone_;  // the owner's destroyed() to cancel()
    bool owned_ = false;                 // owner_ was set; it reads null once the owner is being destroyed
    QString message_;
    QString language_ = QStringLiteral("detect");
    std::vector<float> recording_;
    std::size_t analysed_ = 0;  // samples of recording_ the silence check has read
    std::size_t silent_ = 0;    // samples of silence since the last speech
    bool heard_ = false;        // speech has been heard in this recording
    int generation_ = 0;        // a cancel or a new recording makes an earlier recognition's result stale
    std::shared_ptr<std::atomic<bool>> cancel_;
};

}  // namespace edi_app

#endif  // EDI_APP_VOICE_INPUT_HPP
