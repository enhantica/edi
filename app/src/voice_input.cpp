// SPDX-License-Identifier: BSD-3-Clause
#include "voice_input.hpp"

#include "background.hpp"
#include "speech_recogniser.hpp"

#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QPointer>
#include <QVariantMap>

#include <cmath>
#include <utility>

#ifndef EDI_VOICE_INSTALL_RELATIVE
#define EDI_VOICE_INSTALL_RELATIVE "../share/edi/voice"
#endif

namespace edi_app {

namespace {

constexpr int rate = SpeechRecogniser::sample_rate;
constexpr auto block = static_cast<std::size_t>(rate * 30 / 1000);  // the silence check reads 30 ms at a time
// Speech is louder than about -34 dBFS in a 30 ms block; a quiet room is well below that.
constexpr float speech_level = 0.02F;
constexpr qint64 manifest_bytes = 4096;

QString refusal_text() {
#if defined(Q_OS_MACOS)
    return QCoreApplication::translate("VoiceInput",
        "EasyDiffraction may not use the microphone. Allow it in System Settings, Privacy & Security, Microphone.");
#elif defined(Q_OS_WIN)
    return QCoreApplication::translate("VoiceInput",
        "EasyDiffraction may not use the microphone. Allow it in Settings, Privacy & security, Microphone.");
#else
    return QCoreApplication::translate("VoiceInput", "EasyDiffraction may not use the microphone.");
#endif
}

QString title_case(const QString& name) {
    QString text = name;
    bool start = true;
    for (auto& c : text) {
        if (start)
            c = c.toUpper();
        start = c == u' ' || c == u'-';
    }
    return text;
}

}  // namespace

VoiceInput::VoiceInput(QObject* parent) : VoiceInput(std::make_unique<QtAudioCapture>(), installedModel(), parent) {}

VoiceInput::VoiceInput(std::unique_ptr<AudioCapture> capture, QString model, QObject* parent)
    : QObject(parent), capture_(std::move(capture)), model_(std::move(model)) {
    connect(capture_.get(), &AudioCapture::started, this, &VoiceInput::captureStarted);
    connect(capture_.get(), &AudioCapture::samples, this, &VoiceInput::captureSamples);
    connect(capture_.get(), &AudioCapture::failed, this, &VoiceInput::captureFailed);
}

VoiceInput::~VoiceInput() {
    if (cancel_)
        cancel_->store(true);
    capture_->disconnect(this);
    capture_->stop();
}

void VoiceInput::setLanguage(const QString& language) {
    if (language == language_)
        return;
    language_ = language;
    emit languageChanged();
}

QVariantList VoiceInput::languages() const {
    QVariantList list{QVariantMap{{QStringLiteral("code"), QStringLiteral("detect")},
                                  {QStringLiteral("name"), tr("Detect")}}};
    for (const auto& language : SpeechRecogniser::languages())
        list.append(QVariantMap{{QStringLiteral("code"), QString::fromStdString(language.code)},
                                {QStringLiteral("name"), title_case(QString::fromStdString(language.name))}});
    return list;
}

void VoiceInput::toggle() {
    switch (state_) {
    case State::Idle:
        if (!available())
            return;
        setMessage({});
        dropRecording();
        setState(State::Starting);
        capture_->start();
        return;
    case State::Listening:
        stop();
        return;
    case State::Starting:
    case State::Recognising:
        cancel();
        return;
    }
}

void VoiceInput::stop() {
    if (state_ != State::Listening)
        return;
    capture_->stop();
    auto recording = std::make_shared<std::vector<float>>(std::exchange(recording_, {}));
    dropRecording();
    setState(State::Recognising);
    const int generation = ++generation_;
    cancel_ = std::make_shared<std::atomic<bool>>(false);
    const QPointer<VoiceInput> receiver(this);
    const auto model = model_.toStdString();
    const auto language = language_ == QStringLiteral("detect") ? std::string() : language_.toStdString();
    run_in_background([receiver, generation, recording, model, language, cancel = cancel_] {
        std::string error;
        SpeechRecogniser::Result result;
        if (auto recogniser = SpeechRecogniser::load(model, error))
            result = recogniser->recognise(*recording, language, cancel.get());
        else
            result.error = error;
        recording->clear();
        recording->shrink_to_fit();
        QMetaObject::invokeMethod(QCoreApplication::instance(), [receiver, generation, result = std::move(result)] {
            if (receiver)
                receiver->finish(generation, QString::fromStdString(result.text), QString::fromStdString(result.error),
                                 result.cancelled);
        }, Qt::QueuedConnection);
    });
}

void VoiceInput::cancel() {
    if (state_ == State::Idle)
        return;
    capture_->stop();
    if (cancel_)
        cancel_->store(true);
    cancel_.reset();
    ++generation_;
    dropRecording();
    setState(State::Idle);
}

void VoiceInput::clearMessage() { setMessage({}); }

void VoiceInput::captureStarted() {
    if (state_ == State::Starting)
        setState(State::Listening);
}

void VoiceInput::captureSamples(const QList<float>& chunk) {
    if (state_ != State::Listening)
        return;
    recording_.insert(recording_.end(), chunk.begin(), chunk.end());
    while (analysed_ + block <= recording_.size()) {
        double energy = 0.0;
        for (std::size_t i = analysed_; i < analysed_ + block; ++i)
            energy += static_cast<double>(recording_[i]) * static_cast<double>(recording_[i]);
        analysed_ += block;
        if (std::sqrt(energy / static_cast<double>(block)) > static_cast<double>(speech_level)) {
            heard_ = true;
            silent_ = 0;
        } else if (heard_) {
            silent_ += block;
        }
    }
    if ((heard_ && silent_ >= static_cast<std::size_t>(silence_seconds * rate)) ||
        recording_.size() >= static_cast<std::size_t>(max_seconds * rate))
        stop();
}

void VoiceInput::captureFailed(AudioCapture::Failure failure) {
    if (state_ != State::Starting && state_ != State::Listening)
        return;
    dropRecording();
    setState(State::Idle);
    switch (failure) {
    case AudioCapture::Failure::NoMicrophone:
        setMessage(tr("No microphone was found. Connect one and try again."));
        return;
    case AudioCapture::Failure::PermissionRefused:
        setMessage(refusal_text());
        return;
    case AudioCapture::Failure::DeviceFailed:
        setMessage(tr("The microphone stopped recording. Try again, or choose another microphone in the system settings."));
        return;
    }
}

void VoiceInput::finish(int generation, const QString& text, const QString& error, bool cancelled) {
    if (generation != generation_ || state_ != State::Recognising)
        return;
    cancel_.reset();
    setState(State::Idle);
    if (cancelled)
        return;
    if (!error.isEmpty())
        setMessage(error);
    else if (text.isEmpty())
        setMessage(tr("No speech was recognised. Try again, closer to the microphone."));
    else
        emit textRecognised(text);
}

void VoiceInput::setState(State state) {
    if (state == state_)
        return;
    state_ = state;
    emit stateChanged();
}

void VoiceInput::setMessage(const QString& message) {
    if (message == message_)
        return;
    message_ = message;
    emit messageChanged();
}

void VoiceInput::dropRecording() {
    recording_.clear();
    recording_.shrink_to_fit();
    analysed_ = 0;
    silent_ = 0;
    heard_ = false;
}

QString VoiceInput::installedModel() {
    if (qEnvironmentVariableIsSet("EDI_VOICE_MODEL")) {
        const QFileInfo file(qEnvironmentVariable("EDI_VOICE_MODEL"));
        return file.isAbsolute() && file.isFile() ? file.absoluteFilePath() : QString();
    }
    const QDir root(QDir(QCoreApplication::applicationDirPath()).absoluteFilePath(QStringLiteral(EDI_VOICE_INSTALL_RELATIVE)));
    QFile manifest(root.absoluteFilePath(QStringLiteral("voice-model.json")));
    if (!manifest.open(QIODevice::ReadOnly) || manifest.size() > manifest_bytes)
        return {};
    QJsonParseError error;
    const auto parsed = QJsonDocument::fromJson(manifest.readAll(), &error);
    if (error.error != QJsonParseError::NoError || !parsed.isObject())
        return {};
    const auto metadata = parsed.object();
    const auto name = metadata.value(QStringLiteral("file")).toString();
    const auto bytes = metadata.value(QStringLiteral("bytes")).toInteger(-1);
    if (metadata.value(QStringLiteral("schema")) != QStringLiteral("edi.voice-model/1") || name.isEmpty() ||
        name.contains(u'/') || name.contains(u'\\') || bytes <= 0)
        return {};
    const QFileInfo model(root.absoluteFilePath(name));
    // The hash was checked when the installer was built and by the installer's payload manifest; the size catches a
    // file cut short without reading 190 MB at every start.
    if (!model.isFile() || model.size() != bytes)
        return {};
    return model.absoluteFilePath();
}

}  // namespace edi_app
