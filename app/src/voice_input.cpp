// SPDX-License-Identifier: BSD-3-Clause
#include "voice_input.hpp"

#include "speech_recogniser.hpp"

#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QLoggingCategory>
#include <QPointer>

#include <algorithm>
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

// States and timings only, never audio or text: enough to tell from a run log why no text arrived.
Q_LOGGING_CATEGORY(lcVoice, "edi.voice")

constexpr int rate = SpeechRecogniser::sample_rate;
constexpr auto frame = static_cast<std::size_t>(SpeechDetector::frame_samples);  // 32 ms
// The speech detector decides what is speech (ADR-0107 §8), with Silero's own defaults: a frame is speech at a
// probability of 0.5, a recording has speech after 250 ms of such frames, and speech goes on while frames stay above
// 0.35. Measured on the fixture recording and a recorded room (ADR-0107 §8): speech gave 26 frames or more, rooms and
// noise none.
constexpr float speech_probability = 0.5F;
constexpr float voice_probability = 0.35F;
constexpr int speech_frames = 8;
// The detector misses speech for a few seconds after the voice falls 25 dB or more at once, so it hears the recording
// through a gain that brings the loudest recent frame to -20 dBFS: the reference follows a louder frame at once and
// falls 20 dB a second, and the gain only raises, by 40 dB at most. Measured: falls of 25 to 40 dB left gaps of at
// most 1.2 s instead of 3.4 s, and rooms and noise still gave no speech frame. Whisper gets the recording as captured.
constexpr double detector_level_db = -20.0;
constexpr double detector_gain_db = 40.0;
constexpr double detector_fall_db = 20.0 * SpeechDetector::frame_samples / rate;
// The level meter shows -60 to -10 dBFS: a quiet room near the bottom, close speech near the top. It rises at once and
// falls back over a few updates, so it does not flicker between words.
constexpr double meter_floor_db = -60.0;
constexpr double meter_range_db = 50.0;
constexpr double meter_fall = 0.7;
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

// The detector staged beside the test model, where `pixi run voice-models --test` puts both, unless named.
QString app_detector() {
    if (!scripted())
        return VoiceInput::installedDetector();
    if (qEnvironmentVariableIsSet("EDI_TEST_ASSISTANT_VOICE_DETECTOR")) {
        const QFileInfo detector(qEnvironmentVariable("EDI_TEST_ASSISTANT_VOICE_DETECTOR"));
        return detector.isFile() ? detector.absoluteFilePath() : QString();
    }
    const QDir folder = QFileInfo(qEnvironmentVariable("EDI_TEST_ASSISTANT_VOICE_MODEL")).absoluteDir();
    const auto found = folder.entryInfoList({QStringLiteral("ggml-silero-*.bin")}, QDir::Files, QDir::Name);
    return found.isEmpty() ? QString() : found.constFirst().absoluteFilePath();
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

VoiceInput::VoiceInput(QObject* parent) : VoiceInput(app_capture(), app_model(), app_detector(), parent) {}

VoiceInput::VoiceInput(std::unique_ptr<AudioCapture> capture, QString model, QString detector, QObject* parent)
    : QObject(parent), capture_(std::move(capture)), model_(std::move(model)), detectorFile_(std::move(detector)) {
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

bool VoiceInput::available() const { return installed() && SpeechRecogniser::cpu_supported(); }

QString VoiceInput::unavailableReason() const {
    if (!installed())
        return tr("The voice input component is not installed.");
    if (!SpeechRecogniser::cpu_supported())
        return tr("This computer's processor cannot run voice input: it needs AVX2.");
    return {};
}

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
    case State::Idle: {
        if (!available())
            return;
        if (!detector_) {
            std::string error;
            // A native path, as for the model: Windows' 8-bit file names lose characters outside the code page.
            detector_ = SpeechDetector::load(QFileInfo(detectorFile_).filesystemAbsoluteFilePath(), error);
            if (!detector_) {
                qCInfo(lcVoice) << "The speech detector failed to load";
                setMessage(QString::fromStdString(error));
                return;
            }
        }
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
    }
    case State::Listening:
        stop();
        return;
    case State::Starting:
        cancel();
        return;
    case State::Recognising:
        // A press just after the silence stop means "I'm done", not "throw it away"; Cancel and Escape cancel.
        qCInfo(lcVoice) << "Press while recognising ignored";
        return;
    }
}

void VoiceInput::stop() {
    if (state_ != State::Listening)
        return;
    // The end of the recording that the microphone and its resampler still hold.
    analyse(capture_->finish());
    // Whisper makes up text for a recording without speech, so such a recording is never recognised.
    if (!heard_) {
        qCInfo(lcVoice) << "Nothing was heard; the recording is dropped";
        dropRecording();
        setState(State::Idle);
        setMessage(tr("Nothing was heard."));
        dropOwner();
        return;
    }
    qCInfo(lcVoice).nospace() << "Recognising " << static_cast<double>(recording_.size()) / rate << " s of audio";
    recognising_.start();
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
    qCInfo(lcVoice) << "Cancelled while" << state_;
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
    if (state_ != State::Idle && owner != nullptr && owner == owner_) {
        qCInfo(lcVoice) << "Released by its owner";
        cancel();
    }
}

void VoiceInput::clearMessage() { setMessage({}); }

void VoiceInput::captureStarted() {
    if (state_ == State::Starting) {
        qCInfo(lcVoice) << "Listening";
        setState(State::Listening);
    }
}

void VoiceInput::captureSamples(const QList<float>& chunk) {
    if (state_ != State::Listening)
        return;
    analyse(std::span<const float>(chunk.constData(), static_cast<std::size_t>(chunk.size())));
    if (!levelShown_.isValid() || levelShown_.elapsed() >= level_ms) {
        const double db = 20.0 * std::log10(std::max(loudest_, 1e-6));
        setLevel(std::max(std::clamp((db - meter_floor_db) / meter_range_db, 0.0, 1.0), level_ * meter_fall));
        loudest_ = 0.0;
        levelShown_.start();
    }
    const bool pause =
        heard_ && silent_ >= static_cast<std::size_t>(silence_seconds) * static_cast<std::size_t>(rate);
    if (pause || recording_.size() >= static_cast<std::size_t>(max_seconds) * static_cast<std::size_t>(rate)) {
        qCInfo(lcVoice) << (pause ? "Silence stops the recording" : "Time limit stops the recording");
        stop();
    }
}

void VoiceInput::analyse(std::span<const float> chunk) {
    recording_.insert(recording_.end(), chunk.begin(), chunk.end());
    const std::size_t whole = (recording_.size() - analysed_) / frame * frame;
    if (whole == 0 || !detector_)
        return;
    std::vector<float> levelled(recording_.begin() + static_cast<std::ptrdiff_t>(analysed_),
                                recording_.begin() + static_cast<std::ptrdiff_t>(analysed_ + whole));
    for (std::size_t at = 0; at < whole; at += frame) {
        double energy = 0.0;
        for (std::size_t i = at; i < at + frame; ++i)
            energy += static_cast<double>(levelled[i]) * static_cast<double>(levelled[i]);
        const double rms = std::sqrt(energy / static_cast<double>(frame));
        loudest_ = std::max(loudest_, rms);
        reference_db_ = std::max(20.0 * std::log10(std::max(rms, 1e-10)), reference_db_ - detector_fall_db);
        const double gain_db = std::clamp(detector_level_db - reference_db_, 0.0, detector_gain_db);
        const auto gain = static_cast<float>(std::pow(10.0, gain_db / 20.0));
        for (std::size_t i = at; i < at + frame; ++i)
            levelled[i] = std::clamp(levelled[i] * gain, -1.0F, 1.0F);
    }
    const auto probabilities = detector_->probabilities(levelled);
    analysed_ += whole;
    for (const float probability : probabilities) {
        if (probability >= speech_probability)
            ++speechFrames_;
        if (speechFrames_ > 0 && probability >= voice_probability)
            lastVoice_ = framesRead_;
        ++framesRead_;
    }
    heard_ = heard_ || speechFrames_ >= speech_frames;
    silent_ = heard_ ? static_cast<std::size_t>(framesRead_ - 1 - lastVoice_) * frame : 0;
}

void VoiceInput::captureFailed(AudioCapture::Failure failure) {
    if (state_ != State::Starting && state_ != State::Listening)
        return;
    qCInfo(lcVoice) << "Microphone failed:" << failure;
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
    const char* outcome = cancelled ? "cancelled" : !error.isEmpty() ? "failed" : text.isEmpty() ? "no speech" : "text";
    qCInfo(lcVoice).nospace() << "Recognition took " << recognising_.elapsed() << " ms: " << outcome
                              << (owner_ ? "" : ", no owner");
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

void VoiceInput::setLevel(double level) {
    if (level == level_)
        return;
    level_ = level;
    emit levelChanged();
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
    framesRead_ = 0;
    speechFrames_ = 0;
    lastVoice_ = -1;
    reference_db_ = -200.0;
    if (detector_)
        detector_->reset();
    loudest_ = 0.0;
    levelShown_.invalidate();
    setLevel(0.0);
}

namespace {

// The installed voice folder and its manifest (voice-model.json), or an empty object.
QJsonObject voice_manifest(QDir& root) {
    root = QDir(QDir(QCoreApplication::applicationDirPath()).absoluteFilePath(QStringLiteral(EDI_VOICE_INSTALL_RELATIVE)));
    QFile manifest(root.absoluteFilePath(QStringLiteral("voice-model.json")));
    if (!manifest.open(QIODevice::ReadOnly) || manifest.size() > manifest_bytes)
        return {};
    QJsonParseError error;
    const auto parsed = QJsonDocument::fromJson(manifest.readAll(), &error);
    if (error.error != QJsonParseError::NoError || !parsed.isObject() ||
        parsed.object().value(QStringLiteral("schema")) != QStringLiteral("edi.voice-model/1"))
        return {};
    return parsed.object();
}

// The file a manifest entry names in `root`, if it is there at its stated size. The hash was checked when the installer
// was built and by the installer's payload manifest; the size catches a file cut short without reading 190 MB at every
// start.
QString listed_file(const QDir& root, const QJsonObject& entry) {
    const auto name = entry.value(QStringLiteral("file")).toString();
    const auto bytes = entry.value(QStringLiteral("bytes")).toInteger(-1);
    if (name.isEmpty() || name.contains(u'/') || name.contains(u'\\') || bytes <= 0)
        return {};
    const QFileInfo file(root.absoluteFilePath(name));
    return file.isFile() && file.size() == bytes ? file.absoluteFilePath() : QString();
}

}  // namespace

QString VoiceInput::installedModel() {
    if (qEnvironmentVariableIsSet("EDI_VOICE_MODEL")) {
        const QFileInfo file(qEnvironmentVariable("EDI_VOICE_MODEL"));
        return file.isAbsolute() && file.isFile() ? file.absoluteFilePath() : QString();
    }
    QDir root;
    return listed_file(root, voice_manifest(root));
}

QString VoiceInput::installedDetector() {
    if (qEnvironmentVariableIsSet("EDI_VOICE_MODEL")) {
        // Beside the model named for development, as the installer puts it.
        const QFileInfo model(qEnvironmentVariable("EDI_VOICE_MODEL"));
        const auto found =
            model.absoluteDir().entryInfoList({QStringLiteral("ggml-silero-*.bin")}, QDir::Files, QDir::Name);
        return model.isAbsolute() && !found.isEmpty() ? found.constFirst().absoluteFilePath() : QString();
    }
    QDir root;
    return listed_file(root, voice_manifest(root).value(QStringLiteral("vad")).toObject());
}

}  // namespace edi_app
