// SPDX-License-Identifier: BSD-3-Clause
#include "voice_input.hpp"

#include "speech_recogniser.hpp"

#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QPointer>

#include <cmath>
#include <filesystem>
#include <mutex>
#include <new>
#include <stdexcept>
#include <utility>

#ifndef EDI_VOICE_INSTALL_RELATIVE
#define EDI_VOICE_INSTALL_RELATIVE "../share/edi/voice"
#endif

namespace edi_app {

// A recording handed to the worker. A cancel sets `cancelled` and drops the audio; a worker that has not started yet then
// never opens the model.
struct RecognitionJob {
    std::mutex mutex;              // guards `recording` between the cancel and the worker taking it
    std::vector<float> recording;
    std::atomic<bool> cancelled{false};
};

namespace {

constexpr int rate = SpeechRecogniser::sample_rate;
constexpr auto block = static_cast<std::size_t>(rate * 30 / 1000);  // the silence check reads 30 ms at a time
// Speech is louder than about -34 dBFS in a 30 ms block; a quiet room is well below that.
constexpr float speech_level = 0.02F;
constexpr qint64 manifest_bytes = 4096;

QString refusal_text() {
    const QString refused = QCoreApplication::translate("VoiceInput", "Permission to use the microphone was refused.");
#if defined(Q_OS_MACOS)
    return refused + u' ' +
           QCoreApplication::translate("VoiceInput",
                                       "Allow EasyDiffraction in System Settings, Privacy & Security, Microphone.");
#elif defined(Q_OS_WIN)
    return refused + u' ' +
           QCoreApplication::translate("VoiceInput", "Allow EasyDiffraction in Settings, Privacy & security, Microphone.");
#else
    return refused + u' ' +
           QCoreApplication::translate("VoiceInput",
                                       "Allow EasyDiffraction to use the microphone in the system settings.");
#endif
}

// Inside a pytest run the app may take a recording, a model and a microphone outcome from the environment
// (tests/fixtures/assistant_voice/README.md); a user's run never does.
bool scripted() {
    return !qEnvironmentVariableIsEmpty("PYTEST_CURRENT_TEST") &&
           !qEnvironmentVariableIsEmpty("EDI_TEST_ASSISTANT_VOICE_CAPTURE");
}

std::unique_ptr<AudioCapture> app_capture() {
    if (scripted())
        return std::make_unique<ScriptedAudioCapture>(qEnvironmentVariable("EDI_TEST_ASSISTANT_VOICE_CAPTURE"),
                                                      qEnvironmentVariable("EDI_TEST_ASSISTANT_VOICE_WAV"));
    return std::make_unique<QtAudioCapture>();
}

QString app_model() {
    if (!scripted())
        return VoiceInput::installedModel();
    // A missing file stands for a computer without the model.
    const QFileInfo model(qEnvironmentVariable("EDI_TEST_ASSISTANT_VOICE_MODEL"));
    return model.isFile() ? model.absoluteFilePath() : QString();
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

VoiceInput::VoiceInput(QObject* parent) : VoiceInput(app_capture(), app_model(), parent) {}

VoiceInput::VoiceInput(std::unique_ptr<AudioCapture> capture, QString model, QObject* parent)
    : QObject(parent), capture_(std::move(capture)), model_(std::move(model)) {
    connect(capture_.get(), &AudioCapture::started, this, &VoiceInput::captureStarted);
    connect(capture_.get(), &AudioCapture::samples, this, &VoiceInput::captureSamples);
    connect(capture_.get(), &AudioCapture::failed, this, &VoiceInput::captureFailed);
    workers_.setMaxThreadCount(1);
}

VoiceInput::~VoiceInput() {
    if (job_)
        job_->cancelled.store(true);
    capture_->disconnect(this);
    capture_->stop();
}

bool VoiceInput::available() const { return !model_.isEmpty() && SpeechRecogniser::cpu_supported(); }

void VoiceInput::setLanguage(const QString& language) {
    if (language == language_)
        return;
    language_ = language;
    emit languageChanged();
}

QList<SpeechLanguage> VoiceInput::languages() const {
    QList<SpeechLanguage> list{{QStringLiteral("detect"), tr("Detect")}};
    for (const auto& language : SpeechRecogniser::languages())
        list.append({QString::fromStdString(language.code), title_case(QString::fromStdString(language.name))});
    return list;
}

void VoiceInput::toggle(QObject* owner) {
    switch (state_) {
    case State::Idle:
        if (!available())
            return;
        setMessage({});
        dropRecording();
        dropOwner();
        if (owner != nullptr) {
            owner_ = owner;
            owned_ = true;
            ownerGone_ = connect(owner, &QObject::destroyed, this, &VoiceInput::cancel);
            emit ownerChanged();
        }
        setState(State::Starting);
        capture_->start();
        return;
    case State::Listening:
        stop();
        return;
    case State::Starting:
        cancel();
        return;
    case State::Recognising:
        // A press just after the silence stop means "I'm done", not "throw it away"; Cancel and Escape cancel.
        return;
    }
}

void VoiceInput::stop() {
    if (state_ != State::Listening)
        return;
    capture_->stop();
    auto job = std::make_shared<RecognitionJob>();
    job->recording = std::exchange(recording_, {});
    dropRecording();
    setState(State::Recognising);
    const int generation = ++generation_;
    job_ = job;
    const QPointer<VoiceInput> receiver(this);
    // The native path, so a model folder outside the ANSI code page still opens on Windows.
    const std::filesystem::path model = QFileInfo(model_).filesystemAbsoluteFilePath();
    const auto language = language_ == QStringLiteral("detect") ? std::string() : language_.toStdString();
    // NOLINTNEXTLINE(bugprone-exception-escape): only libc++'s container growth past max_size() raises length_error here
    workers_.start([receiver, generation, job, model, language] {
        std::vector<float> recording;
        {
            const std::lock_guard lock(job->mutex);
            recording.swap(job->recording);
        }
        SpeechRecogniser::Result result;
        // The pool rethrows what a job throws, which would end the app, so a failure here becomes the message.
        try {
            std::string error;
            // Cancelled before this job started, or while the model loaded: no model is opened, or no inference runs.
            if (job->cancelled.load()) {
                result.cancelled = true;
            } else if (auto recogniser = SpeechRecogniser::load(model, error)) {
                if (job->cancelled.load())
                    result.cancelled = true;
                else
                    result = recogniser->recognise(recording, language, &job->cancelled);
            } else {
                result.error = error;
            }
        } catch (const std::bad_alloc&) {
            result = {};
            result.error = "There is not enough free memory to recognise the speech.";
        } catch (const std::exception&) {
            result = {};
            result.error = "The speech could not be recognised.";
        }
        std::vector<float>().swap(recording);
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
    if (job_) {
        job_->cancelled.store(true);
        const std::lock_guard lock(job_->mutex);
        std::vector<float>().swap(job_->recording);  // the audio goes now, not when the worker gets to the job
    }
    job_.reset();
    ++generation_;
    dropRecording();
    setState(State::Idle);
    dropOwner();
}

void VoiceInput::release(QObject* owner) {
    if (state_ != State::Idle && owner != nullptr && owner == owner_)
        cancel();
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
    if ((heard_ && silent_ >= static_cast<std::size_t>(silence_seconds) * static_cast<std::size_t>(rate)) ||
        recording_.size() >= static_cast<std::size_t>(max_seconds) * static_cast<std::size_t>(rate))
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
        break;
    case AudioCapture::Failure::PermissionRefused:
        setMessage(refusal_text());
        break;
    case AudioCapture::Failure::DeviceFailed:
        setMessage(tr("The microphone stopped recording. Try again, or choose another microphone in the system settings."));
        break;
    }
    dropOwner();
}

void VoiceInput::finish(int generation, const QString& text, const QString& error, bool cancelled) {
    if (generation != generation_ || state_ != State::Recognising)
        return;
    job_.reset();
    setState(State::Idle);
    if (cancelled) {
        dropOwner();
        return;
    }
    if (!error.isEmpty())
        setMessage(error);
    else if (text.isEmpty())
        setMessage(tr("No speech was recognised. Try again, closer to the microphone."));
    else
        emit textRecognised(text);  // with the owner still set, so only its message box takes the text
    // A handler may have started the next recording, which keeps its own owner.
    if (state_ == State::Idle)
        dropOwner();
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

void VoiceInput::dropOwner() {
    if (!owned_)
        return;
    disconnect(ownerGone_);
    ownerGone_ = {};
    owner_ = nullptr;
    owned_ = false;
    emit ownerChanged();
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
