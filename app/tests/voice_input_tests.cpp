// SPDX-License-Identifier: BSD-3-Clause
// Voice input (ADR-0107) on the tiny model and a recorded speech, never a real microphone: a model folder named outside
// ASCII, an owner that goes away or releases its recording, a result that lands after a cancel, a microphone that is
// missing, refused or broken, and when a recording counts as speech, quiet or not.
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QRegularExpression>
#include <QScopeGuard>
#include <QSemaphore>
#include <QSignalSpy>
#include <QTemporaryDir>
#include <QThreadPool>
#include <QtTest/QtTest>

#include <algorithm>
#include <cmath>
#include <initializer_list>
#include <memory>
#include <numbers>
#include <utility>
#include <vector>

#include "audio_capture.hpp"
#include "speech_recogniser.hpp"
#include "voice_input.hpp"

namespace edi_app {
namespace {

constexpr int kRecognitionMs = 120000;
constexpr int kRate = SpeechRecogniser::sample_rate;
const QString kFixtures = QStringLiteral(EDI_SOURCE_DIR "/tests/fixtures/assistant_voice");
// A model path with no file: the recogniser refuses it at once, which shows a recording reached it without running
// Whisper.
const QString kAbsentModel = kFixtures + QStringLiteral("/absent-model.bin");
const QString kNoModelMessage = QStringLiteral("The speech model is not installed.");

// CI stages the model before the run (tests/fixtures/assistant_voice/README.md).
QString tinyModel() {
    const auto chosen = qEnvironmentVariable("EDI_VOICE_TEST_MODEL");
    return chosen.isEmpty() ? QStringLiteral(EDI_SOURCE_DIR "/build/voice-models/ggml-tiny-q5_1.bin") : chosen;
}

// The speech detector, staged beside the tiny model (tests/fixtures/assistant_voice/README.md).
QString detectorModel() {
    const auto chosen = qEnvironmentVariable("EDI_VOICE_TEST_DETECTOR");
    return chosen.isEmpty() ? QStringLiteral(EDI_SOURCE_DIR "/build/voice-models/ggml-silero-v6.2.0.bin") : chosen;
}

// Lower-case words, without punctuation.
QStringList words(const QString& text) {
    static const QRegularExpression separators(QStringLiteral("[^\\p{L}]+"));
    return text.toLower().split(separators, Qt::SkipEmptyParts);
}

// Test signals at a known level in dBFS: white noise from a fixed seed, digital silence.
QList<float> noise(double seconds, double db) {
    QList<float> samples(static_cast<qsizetype>(std::lround(seconds * kRate)));
    const double peak = std::pow(10.0, db / 20.0) * std::sqrt(3.0);  // uniform in [-peak, peak]
    quint32 state = 12345U;
    for (auto& sample : samples) {
        state = state * 1664525U + 1013904223U;
        sample = static_cast<float>(peak * (static_cast<double>(state >> 8) / (1 << 23) - 1.0));
    }
    return samples;
}

QList<float> zeros(double seconds) { return QList<float>(static_cast<qsizetype>(std::lround(seconds * kRate)), 0.0F); }

// A 10 ms burst at 2 kHz in three seconds of digital silence.
QList<float> click() {
    auto samples = zeros(3.0);
    for (qsizetype i = 0; i < kRate / 100; ++i)
        samples[kRate + i] = static_cast<float>(0.5 * std::sin(2.0 * std::numbers::pi * 2000.0 * static_cast<double>(i) / kRate));
    return samples;
}

// `a` with `b` added from `at` on.
QList<float> mixed(QList<float> a, const QList<float>& b, qsizetype at = 0) {
    for (qsizetype i = 0; i < b.size() && at + i < a.size(); ++i)
        a[at + i] += b[i];
    return a;
}

QList<float> joined(std::initializer_list<QList<float>> parts) {
    QList<float> all;
    for (const auto& part : parts)
        all.append(part);
    return all;
}

QList<float> scaled(const std::vector<float>& audio, double gain) {
    QList<float> samples;
    samples.reserve(static_cast<qsizetype>(audio.size()));
    for (const float sample : audio)
        samples.append(static_cast<float>(sample * gain));
    return samples;
}

double rms(const std::vector<float>& audio) {
    double energy = 0.0;
    for (const float sample : audio)
        energy += static_cast<double>(sample) * static_cast<double>(sample);
    return std::sqrt(energy / static_cast<double>(audio.size()));
}

// A recording scaled to `db` dBFS over its whole length; with `seconds`, that long, from its start and played again
// from the start if it is shorter.
QList<float> at(const std::vector<float>& audio, double db, double seconds = 0.0) {
    const auto all = scaled(audio, std::pow(10.0, db / 20.0) / rms(audio));
    if (seconds <= 0.0)
        return all;
    QList<float> part(static_cast<qsizetype>(std::lround(seconds * kRate)));
    for (qsizetype i = 0; i < part.size(); ++i)
        part[i] = all[i % all.size()];
    return part;
}

// As a microphone's noise gate and compressor pass it: 30 ms blocks more than 25 dB below the loudest become digital
// silence, and the rest come 4:1 closer to the loudest, so the speech is the only sound and at an even level.
QList<float> gated(QList<float> audio) {
    constexpr qsizetype block = kRate * 30 / 1000;
    std::vector<double> levels;
    for (qsizetype start = 0; start + block <= audio.size(); start += block) {
        double energy = 0.0;
        for (qsizetype i = start; i < start + block; ++i)
            energy += static_cast<double>(audio[i]) * static_cast<double>(audio[i]);
        levels.push_back(10.0 * std::log10(std::max(energy / block, 1e-18)));
    }
    const double top = *std::max_element(levels.begin(), levels.end());
    audio.resize(static_cast<qsizetype>(levels.size()) * block);
    for (std::size_t b = 0; b < levels.size(); ++b) {
        const double gain = levels[b] < top - 25.0 ? 0.0 : std::pow(10.0, ((top - (top - levels[b]) / 4.0) - levels[b]) / 20.0);
        for (qsizetype i = static_cast<qsizetype>(b) * block; i < static_cast<qsizetype>(b + 1) * block; ++i)
            audio[i] = static_cast<float>(audio[i] * gain);
    }
    return audio;
}

// A microphone the test speaks into: it starts on the next turn of the event loop, as a real one answers later.
class FakeCapture final : public AudioCapture {
public:
    using AudioCapture::AudioCapture;
    void start() override {
        QMetaObject::invokeMethod(this, [this, request = ++request_] {
            if (request == request_)
                emit started();
        }, Qt::QueuedConnection);
    }
    void stop() override { ++request_; }
    std::vector<float> finish() override {
        ++finished;
        stop();
        const std::vector<float> end(held.begin(), held.end());
        held.clear();
        return end;
    }
    void play(const std::vector<float>& audio) { emit samples(QList<float>(audio.begin(), audio.end())); }
    void play(const QList<float>& audio) { emit samples(audio); }

    QList<float> held;  // what only `finish` returns, as a real microphone's buffer and resampler hold the end
    int finished = 0;

private:
    int request_ = 0;
};

struct Voice {
    FakeCapture* capture;
    std::unique_ptr<VoiceInput> input;
};

Voice voiceOn(const QString& model) {
    auto capture = std::make_unique<FakeCapture>();
    auto* raw = capture.get();
    return {raw, std::make_unique<VoiceInput>(std::move(capture), model, detectorModel())};
}

// Every recognition `voice` started so far has finished and its result has reached it.
[[nodiscard]] bool settle(VoiceInput& voice) {
    if (!voice.workers().waitForDone(kRecognitionMs))
        return false;
    QCoreApplication::sendPostedEvents();
    QCoreApplication::processEvents();
    return true;
}

}  // namespace

class VoiceInputTests : public QObject {
    Q_OBJECT
    std::vector<float> speech_;   // the fixture at 16 kHz
    std::vector<float> spoken_;   // the fixture and enough silence for the silence check to stop the recording
    std::vector<float> room_;     // a recorded classroom: ventilation and a ceiling light, no speech
    QStringList reference_;

private slots:
    void initTestCase() {
        if (!SpeechRecogniser::cpu_supported())
            QSKIP("This processor cannot run the speech engine; voice input is hidden here");
        QVERIFY2(QFileInfo(tinyModel()).isFile(),
                 qPrintable(QStringLiteral("Stage ggml-tiny-q5_1.bin at %1 (tests/fixtures/assistant_voice/README.md)")
                                .arg(tinyModel())));
        QVERIFY2(QFileInfo(detectorModel()).isFile(),
                 qPrintable(QStringLiteral("Stage ggml-silero-v6.2.0.bin at %1 (tests/fixtures/assistant_voice/README.md)")
                                .arg(detectorModel())));
        room_ = ScriptedAudioCapture::read_wav(kFixtures + QStringLiteral("/classroom-noise.wav"));
        QVERIFY2(room_.size() > static_cast<std::size_t>(7 * SpeechRecogniser::sample_rate),
                 "classroom-noise.wav did not read as about eight seconds of sound");
        speech_ = ScriptedAudioCapture::read_wav(kFixtures + QStringLiteral("/inaugural.wav"));
        QVERIFY2(speech_.size() > static_cast<std::size_t>(10 * SpeechRecogniser::sample_rate),
                 "inaugural.wav did not read as about eleven seconds of speech");
        spoken_ = speech_;
        spoken_.resize(speech_.size() + static_cast<std::size_t>((VoiceInput::silence_seconds + 1) *
                                                                 SpeechRecogniser::sample_rate),
                       0.0F);
        QFile reference(kFixtures + QStringLiteral("/inaugural.txt"));
        QVERIFY(reference.open(QIODevice::ReadOnly));
        reference_ = words(QString::fromUtf8(reference.readAll()));
    }

    // A new setting is English, as the preferences' default; Detect stays the list's first choice and can be set.
    void languageDefaultsToEnglish() {
        auto voice = voiceOn(tinyModel());
        QCOMPARE(voice.input->language(), QStringLiteral("en"));
        const auto languages = voice.input->languages();
        QVERIFY(languages.size() > 1);
        QCOMPARE(languages.first().code, QStringLiteral("detect"));
        QCOMPARE(languages.first().name, QStringLiteral("Detect"));
        const auto english = std::find_if(languages.begin(), languages.end(),
                                          [](const SpeechLanguage& language) { return language.code == QStringLiteral("en"); });
        QVERIFY(english != languages.end());
        QCOMPARE(english->name, QStringLiteral("English"));
        for (const auto& language : languages)
            QVERIFY2(!language.name.isEmpty() && language.name.front().isUpper(), qPrintable(language.code));
        QSignalSpy changed(voice.input.get(), &VoiceInput::languageChanged);
        voice.input->setLanguage(QStringLiteral("detect"));
        QCOMPARE(voice.input->language(), QStringLiteral("detect"));
        QCOMPARE(changed.count(), 1);
    }

    // A model installed under a folder named outside ASCII loads and recognises; the text arrives while its owner is
    // still the owner, and the ownership ends with it.
    void recognisesFromUnicodeFolder() {
        QTemporaryDir root;
        QVERIFY(root.isValid());
        const QString folder = root.filePath(QStringLiteral(u"Modèle Ŝpeech 音声"));
        QVERIFY(QDir().mkpath(folder));
        const QString model = QDir(folder).filePath(QStringLiteral("ggml-tiny-q5_1.bin"));
        QVERIFY(QFile::copy(tinyModel(), model));

        auto voice = voiceOn(model);
        QVERIFY(voice.input->available());
        QObject owner;
        QObject* ownerAtText = nullptr;
        QStringList texts;
        connect(voice.input.get(), &VoiceInput::textRecognised, this, [&](const QString& text) {
            texts.append(text);
            ownerAtText = voice.input->owner();
        });
        voice.input->toggle(&owner);
        QCOMPARE(voice.input->owner(), &owner);
        QTRY_COMPARE(voice.input->state(), VoiceInput::State::Listening);
        voice.capture->play(spoken_);
        QCOMPARE(voice.input->state(), VoiceInput::State::Recognising);
        QTRY_COMPARE_WITH_TIMEOUT(texts.size(), 1, kRecognitionMs);
        QCOMPARE(voice.input->state(), VoiceInput::State::Idle);
        QCOMPARE(voice.input->message(), QString());
        QCOMPARE(ownerAtText, &owner);
        QCOMPARE(voice.input->owner(), nullptr);
        const auto heard = words(texts.first());
        for (const auto& word : {QStringLiteral("fellow"), QStringLiteral("americans"), QStringLiteral("country")}) {
            QVERIFY2(reference_.contains(word), qPrintable(word + QStringLiteral(" is not in inaugural.txt")));
            QVERIFY2(heard.contains(word), qPrintable(word + QStringLiteral(" is missing from: ") + texts.first()));
        }
    }

    // The item that started a recording goes away while it listens: the recording is dropped and no text follows.
    void ownerGoneWhileListening() {
        auto voice = voiceOn(tinyModel());
        QSignalSpy text(voice.input.get(), &VoiceInput::textRecognised);
        auto* owner = new QObject;
        voice.input->toggle(owner);
        QTRY_COMPARE(voice.input->state(), VoiceInput::State::Listening);
        // The first three seconds, all speech, so the silence check keeps listening.
        const auto three_seconds = std::ptrdiff_t{3} * SpeechRecogniser::sample_rate;
        voice.capture->play(std::vector<float>(speech_.begin(), speech_.begin() + three_seconds));
        QCOMPARE(voice.input->state(), VoiceInput::State::Listening);
        delete owner;
        QCOMPARE(voice.input->state(), VoiceInput::State::Idle);
        QCOMPARE(voice.input->owner(), nullptr);
        QVERIFY(settle(*voice.input));
        QCOMPARE(text.count(), 0);
    }

    // The same while the recording is being recognised.
    void ownerGoneWhileRecognising() {
        auto voice = voiceOn(tinyModel());
        QSignalSpy text(voice.input.get(), &VoiceInput::textRecognised);
        auto* owner = new QObject;
        voice.input->toggle(owner);
        QTRY_COMPARE(voice.input->state(), VoiceInput::State::Listening);
        voice.capture->play(spoken_);
        QCOMPARE(voice.input->state(), VoiceInput::State::Recognising);
        delete owner;
        QCOMPARE(voice.input->state(), VoiceInput::State::Idle);
        QCOMPARE(voice.input->owner(), nullptr);
        QVERIFY(settle(*voice.input));
        QCOMPARE(text.count(), 0);
        QCOMPARE(voice.input->message(), QString());
    }

    // Only the owner can release a recording.
    void releaseNeedsTheOwner() {
        auto voice = voiceOn(tinyModel());
        QObject owner;
        QObject other;
        QSignalSpy ownerChanged(voice.input.get(), &VoiceInput::ownerChanged);
        voice.input->toggle(&owner);
        QTRY_COMPARE(voice.input->state(), VoiceInput::State::Listening);
        voice.input->release(&other);
        voice.input->release(nullptr);
        QCOMPARE(voice.input->state(), VoiceInput::State::Listening);
        QCOMPARE(voice.input->owner(), &owner);
        voice.input->release(&owner);
        QCOMPARE(voice.input->state(), VoiceInput::State::Idle);
        QCOMPARE(voice.input->owner(), nullptr);
        QCOMPARE(ownerChanged.count(), 2);
    }

    // A recognition cancelled while it runs lands later and is dropped, even with the next recording under way.
    void resultAfterCancelIsDropped() {
        auto voice = voiceOn(tinyModel());
        QSignalSpy text(voice.input.get(), &VoiceInput::textRecognised);
        voice.input->toggle();
        QTRY_COMPARE(voice.input->state(), VoiceInput::State::Listening);
        voice.capture->play(spoken_);
        QCOMPARE(voice.input->state(), VoiceInput::State::Recognising);
        voice.input->cancel();
        QCOMPARE(voice.input->state(), VoiceInput::State::Idle);
        voice.input->toggle();
        QTRY_COMPARE(voice.input->state(), VoiceInput::State::Listening);
        QVERIFY(settle(*voice.input));
        QCOMPARE(voice.input->state(), VoiceInput::State::Listening);
        QCOMPARE(text.count(), 0);
        QCOMPARE(voice.input->message(), QString());
        voice.input->cancel();
    }

    // A press that lands just after the silence stop keeps the recording: the text still arrives for its owner.
    void pressWhileRecognisingKeepsTheText() {
        auto voice = voiceOn(tinyModel());
        QSignalSpy text(voice.input.get(), &VoiceInput::textRecognised);
        QObject owner;
        voice.input->toggle(&owner);
        QTRY_COMPARE(voice.input->state(), VoiceInput::State::Listening);
        voice.capture->play(spoken_);
        QCOMPARE(voice.input->state(), VoiceInput::State::Recognising);
        voice.input->toggle(&owner);
        QCOMPARE(voice.input->state(), VoiceInput::State::Recognising);
        QCOMPARE(voice.input->owner(), &owner);
        QTRY_COMPARE_WITH_TIMEOUT(text.count(), 1, kRecognitionMs);
        QVERIFY2(words(text.first().first().toString()).contains(QStringLiteral("country")),
                 qPrintable(text.first().first().toString()));
        QCOMPARE(voice.input->state(), VoiceInput::State::Idle);
    }

    // Recognitions cancelled before the worker gets to them open no model and give no text, and they run one at a time.
    void cancelBeforeTheWorkerStartsOpensNoModel() {
        auto voice = voiceOn(tinyModel());
        QCOMPARE(voice.input->workers().maxThreadCount(), 1);
        QSignalSpy text(voice.input.get(), &VoiceInput::textRecognised);
        // Hold the one worker thread, so the jobs below wait as they would behind a slow load. The job shares the gate,
        // so it outlives this test however it ends.
        auto gate = std::make_shared<QSemaphore>();
        voice.input->workers().start([gate] { gate->acquire(); });
        auto open = qScopeGuard([gate] { gate->release(); });
        const int loads = SpeechRecogniser::loads();
        for (int round = 0; round < 2; ++round) {
            voice.input->toggle();
            QTRY_COMPARE(voice.input->state(), VoiceInput::State::Listening);
            voice.capture->play(spoken_);
            QCOMPARE(voice.input->state(), VoiceInput::State::Recognising);
            voice.input->cancel();
            QCOMPARE(voice.input->state(), VoiceInput::State::Idle);
        }
        open.dismiss();
        gate->release();
        QVERIFY(settle(*voice.input));
        QCOMPARE(SpeechRecogniser::loads(), loads);
        QCOMPARE(text.count(), 0);
        QCOMPARE(voice.input->message(), QString());
    }

    // A recording without speech is never recognised, since Whisper makes up text from silence (ADR-0107 §8): digital
    // silence, a quiet or a noisy room, a microphone that starts with digital silence, a click. The silence stop waits
    // for speech, and a press says nothing was heard.
    void nothingHeardWithoutSpeech_data() {
        QTest::addColumn<QList<float>>("recording");
        QTest::newRow("digital silence") << zeros(3.0);
        QTest::newRow("a recorded room as recorded") << at(room_, -22.0);
        QTest::newRow("a recorded room at -40 dBFS") << at(room_, -40.0);
        QTest::newRow("a recorded room at -55 dBFS") << at(room_, -55.0);
        QTest::newRow("a room, then digital silence") << joined({at(room_, -40.0), zeros(1.5)});
        QTest::newRow("silence, a room, silence") << joined({zeros(0.5), at(room_, -40.0, 3.0), zeros(1.5)});
        QTest::newRow("a room a gate let through") << joined({zeros(0.5), at(room_, -45.0, 1.5), zeros(2.5)});
        QTest::newRow("digital silence, then white noise") << joined({zeros(0.5), noise(3.0, -50.0)});
        QTest::newRow("white noise at -45 dBFS") << noise(3.0, -45.0);
        QTest::newRow("white noise at -70 dBFS") << noise(3.0, -70.0);
        QTest::newRow("a click") << click();
        QList<float> typing;
        for (int key = 0; key < 6; ++key)
            typing = joined({typing, zeros(0.3), noise(0.02, -30.0)});
        QTest::newRow("keys typed behind a gate") << joined({typing, zeros(1.0)});
    }
    void nothingHeardWithoutSpeech() {
        QFETCH(QList<float>, recording);
        auto voice = voiceOn(kAbsentModel);
        QVERIFY(voice.input->available());
        voice.input->toggle();
        QTRY_COMPARE(voice.input->state(), VoiceInput::State::Listening);
        voice.capture->play(recording);
        QCOMPARE(voice.input->state(), VoiceInput::State::Listening);
        voice.input->toggle();
        QCOMPARE(voice.input->state(), VoiceInput::State::Idle);
        QCOMPARE(voice.input->message(), QStringLiteral("Nothing was heard."));
        QVERIFY(settle(*voice.input));
        QCOMPARE(voice.input->message(), QStringLiteral("Nothing was heard."));
    }

    // Recorded speech that must reach the recogniser, whose refusal of the absent model shows it did: quiet, from the
    // first sample behind a noise gate, and in a recorded room. `pressed` rows stop with a press while listening; the
    // others are stopped by the silence after the speech.
    void speechIsHeard_data() {
        QTest::addColumn<QList<float>>("recording");
        QTest::addColumn<bool>("pressed");
        QTest::newRow("quiet, -45 dBFS, silence stops it") << joined({at(speech_, -45.0), zeros(3.0)}) << false;
        QTest::newRow("quiet, -55 dBFS, silence stops it") << joined({at(speech_, -55.0), zeros(3.0)}) << false;
        QTest::newRow("quiet, -45 dBFS, pressed") << at(speech_, -45.0, 3.0) << true;
        QTest::newRow("a short phrase from the first sample behind a gate, pressed")
            << gated(at(speech_, -45.0, 1.5)) << true;
        QTest::newRow("a short phrase from the first sample behind a gate, silence stops it")
            << joined({gated(at(speech_, -45.0, 1.5)), zeros(2.5)}) << false;
        QTest::newRow("all of it from the first sample behind a gate, silence stops it")
            << joined({gated(at(speech_, -45.0)), zeros(2.5)}) << false;
        QTest::newRow("in a recorded room 10 dB below it, pressed")
            << mixed(at(speech_, -45.0), at(room_, -55.0, 11.0)) << true;
        QTest::newRow("in a recorded room 5 dB below it, pressed")
            << mixed(at(speech_, -35.0), at(room_, -40.0, 11.0)) << true;
    }
    void speechIsHeard() {
        QFETCH(QList<float>, recording);
        QFETCH(bool, pressed);
        auto voice = voiceOn(kAbsentModel);
        voice.input->toggle();
        QTRY_COMPARE(voice.input->state(), VoiceInput::State::Listening);
        voice.capture->play(recording);
        if (pressed) {
            QCOMPARE(voice.input->state(), VoiceInput::State::Listening);
            voice.input->toggle();
        }
        QCOMPARE(voice.input->state(), VoiceInput::State::Recognising);
        QVERIFY(settle(*voice.input));
        QCOMPARE(voice.input->state(), VoiceInput::State::Idle);
        QCOMPARE(voice.input->message(), kNoModelMessage);
    }

    // Speech that falls sharply after two seconds keeps the recording going until the silence after it. Without the
    // detector's levelling gain a fall of 25 dB left a 3.4 s gap and the silence stop came during the quiet part;
    // with it the longest gap measured 1.2 s for falls of 25 to 40 dB.
    void quietContinuationKeepsListening_data() {
        QTest::addColumn<double>("loud");
        QTest::addColumn<double>("quiet");
        QTest::newRow("falls 25 dB") << -20.0 << -45.0;
        QTest::newRow("falls 30 dB") << -20.0 << -50.0;
        QTest::newRow("falls 40 dB") << -15.0 << -55.0;
    }
    void quietContinuationKeepsListening() {
        QFETCH(double, loud);
        QFETCH(double, quiet);
        auto voice = voiceOn(kAbsentModel);
        voice.input->toggle();
        QTRY_COMPARE(voice.input->state(), VoiceInput::State::Listening);
        voice.capture->play(at(speech_, loud).first(2 * kRate));
        voice.capture->play(at(speech_, quiet).sliced(2 * kRate));
        QCOMPARE(voice.input->state(), VoiceInput::State::Listening);
        voice.capture->play(zeros(2.5));
        QCOMPARE(voice.input->state(), VoiceInput::State::Recognising);
        QVERIFY(settle(*voice.input));
        QCOMPARE(voice.input->message(), kNoModelMessage);
    }

    // A press takes the end of the recording the microphone still holds, here its only speech; a cancel drops it.
    void stopTakesTheHeldEndAndCancelDropsIt() {
        auto voice = voiceOn(kAbsentModel);
        voice.input->toggle();
        QTRY_COMPARE(voice.input->state(), VoiceInput::State::Listening);
        voice.capture->play(zeros(2.0));
        voice.capture->held = at(speech_, -30.0, 1.5);
        voice.input->toggle();
        QCOMPARE(voice.capture->finished, 1);
        QVERIFY(voice.capture->held.isEmpty());
        QCOMPARE(voice.input->state(), VoiceInput::State::Recognising);
        QVERIFY(settle(*voice.input));
        QCOMPARE(voice.input->message(), kNoModelMessage);

        voice.input->toggle();
        QTRY_COMPARE(voice.input->state(), VoiceInput::State::Listening);
        voice.capture->play(zeros(2.0));
        voice.capture->held = at(speech_, -30.0, 1.5);
        voice.input->cancel();
        QCOMPARE(voice.capture->finished, 1);
        QCOMPARE(voice.input->state(), VoiceInput::State::Idle);
        QVERIFY(settle(*voice.input));
        QCOMPARE(voice.input->message(), QString());
    }

    // The test microphone of the app's pytest runs: a missing or refused microphone, or a recording it cannot read,
    // ends in Idle with a message that names the microphone.
    void microphoneUnavailable_data() {
        QTest::addColumn<QString>("mode");
        QTest::addColumn<QString>("wav");
        QTest::newRow("no device") << QStringLiteral("no-device") << QString();
        QTest::newRow("permission refused") << QStringLiteral("permission-denied") << QString();
        QTest::newRow("unreadable recording") << QStringLiteral("available") << kFixtures + QStringLiteral("/absent.wav");
    }
    void microphoneUnavailable() {
        QFETCH(QString, mode);
        QFETCH(QString, wav);
        QObject owner;
        VoiceInput voice(std::make_unique<ScriptedAudioCapture>(mode, wav), tinyModel(), detectorModel());
        voice.toggle(&owner);
        QCOMPARE(voice.state(), VoiceInput::State::Starting);
        QTRY_COMPARE(voice.state(), VoiceInput::State::Idle);
        QVERIFY2(voice.message().contains(QStringLiteral("microphone"), Qt::CaseInsensitive), qPrintable(voice.message()));
        QCOMPARE(voice.owner(), nullptr);
    }

    // The same test microphone playing the fixture: its silence afterwards ends the recording, as a user's pause does.
    void scriptedRecordingStopsOnSilence() {
        VoiceInput voice(std::make_unique<ScriptedAudioCapture>(QStringLiteral("available"),
                                                                kFixtures + QStringLiteral("/inaugural.wav")),
                         tinyModel(), detectorModel());
        QSignalSpy text(&voice, &VoiceInput::textRecognised);
        voice.toggle();
        QTRY_COMPARE_WITH_TIMEOUT(text.count(), 1, kRecognitionMs);
        QVERIFY2(words(text.first().first().toString()).contains(QStringLiteral("country")),
                 qPrintable(text.first().first().toString()));
        QCOMPARE(voice.state(), VoiceInput::State::Idle);
    }
};

}  // namespace edi_app

QTEST_GUILESS_MAIN(edi_app::VoiceInputTests)
#include "voice_input_tests.moc"
