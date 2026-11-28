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

// Lower-case words, without punctuation.
QStringList words(const QString& text) {
    static const QRegularExpression separators(QStringLiteral("[^\\p{L}]+"));
    return text.toLower().split(separators, Qt::SkipEmptyParts);
}

// Test signals at a known level in dBFS: white noise from a fixed seed for a room, a 220 Hz tone for a voice.
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

QList<float> tone(double seconds, double db) {
    QList<float> samples(static_cast<qsizetype>(std::lround(seconds * kRate)));
    const double peak = std::pow(10.0, db / 20.0) * std::sqrt(2.0);
    const double step = 2.0 * std::numbers::pi * 220.0 / kRate;
    for (qsizetype i = 0; i < samples.size(); ++i)
        samples[i] = static_cast<float>(peak * std::sin(step * static_cast<double>(i)));
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
    return {raw, std::make_unique<VoiceInput>(std::move(capture), model)};
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
    QStringList reference_;

private slots:
    void initTestCase() {
        if (!SpeechRecogniser::cpu_supported())
            QSKIP("This processor cannot run the speech engine; voice input is hidden here");
        QVERIFY2(QFileInfo(tinyModel()).isFile(),
                 qPrintable(QStringLiteral("Stage ggml-tiny-q5_1.bin at %1 (tests/fixtures/assistant_voice/README.md)")
                                .arg(tinyModel())));
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
        QTest::newRow("digital silence") << QList<float>(3 * kRate, 0.0F);
        QTest::newRow("quiet room") << noise(3.0, -70.0);
        QTest::newRow("noisy room") << noise(3.0, -45.0);
        QTest::newRow("digital silence, then a room") << joined({QList<float>(kRate / 2, 0.0F), noise(3.0, -50.0)});
        QTest::newRow("a click") << mixed(noise(3.0, -60.0), tone(0.01, -10.0), kRate);
        // An open microphone in a room whose capture then falls to digital silence: the room is no gated sound.
        QTest::newRow("a room, then digital silence") << joined({noise(3.0, -50.0), QList<float>(kRate, 0.0F)});
        // Keys typed behind a noise gate: each passes for 20 ms, shorter than any syllable.
        QList<float> typing;
        for (int key = 0; key < 6; ++key)
            typing = joined({typing, QList<float>(kRate * 3 / 10, 0.0F), noise(0.02, -30.0)});
        QTest::newRow("keys typed behind a gate") << joined({typing, QList<float>(kRate, 0.0F)});
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

    // Speech from a microphone set low, the fixture at -45 dBFS (28 dB down, no 30 ms block above -36 dBFS), is heard:
    // the silence after it stops the recording, and so does a press. The recogniser's refusal of the absent model
    // shows the recording reached it.
    void quietSpeechIsHeard_data() {
        QTest::addColumn<bool>("pressed");
        QTest::newRow("stopped by the silence") << false;
        QTest::newRow("stopped by a press") << true;
    }
    void quietSpeechIsHeard() {
        QFETCH(bool, pressed);
        const double gain = std::pow(10.0, -45.0 / 20.0) / rms(speech_);
        const auto three_seconds = std::ptrdiff_t{3} * kRate;
        const auto recording =
            pressed ? scaled(std::vector<float>(speech_.begin(), speech_.begin() + three_seconds), gain)
                    : scaled(spoken_, gain);
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

    // A quiet continuation after a loud syllable is still speech, so the silence stop waits for real silence: a room at
    // -60 dBFS, a syllable at -20 dBFS, then three seconds at -40 dBFS.
    void quietContinuationKeepsListening() {
        auto voice = voiceOn(kAbsentModel);
        voice.input->toggle();
        QTRY_COMPARE(voice.input->state(), VoiceInput::State::Listening);
        voice.capture->play(noise(0.5, -60.0));
        voice.capture->play(mixed(noise(0.3, -60.0), tone(0.3, -20.0)));
        voice.capture->play(mixed(noise(3.0, -60.0), tone(3.0, -40.0)));
        QCOMPARE(voice.input->state(), VoiceInput::State::Listening);
        voice.capture->play(noise(2.5, -60.0));
        QCOMPARE(voice.input->state(), VoiceInput::State::Recognising);
        QVERIFY(settle(*voice.input));
        QCOMPARE(voice.input->message(), kNoModelMessage);
    }

    // A microphone with a noise gate sends digital silence instead of the room, so its speech can be the only sound and
    // at an even level: a phrase at -45 to -46 dBFS. It is heard when the gate closes between words, when it closes only
    // after the phrase just before a press, and when the silence after the phrase stops the recording by itself. Zeros
    // only at the start are a microphone starting (nothingHeardWithoutSpeech).
    void gatedEvenSpeechIsHeard_data() {
        QTest::addColumn<QList<float>>("recording");
        QTest::addColumn<bool>("pressed");
        const QList<float> start(kRate / 2, 0.0F);
        const QList<float> gap(kRate * 3 / 20, 0.0F);
        QTest::newRow("gaps between words")
            << joined({start, tone(0.5, -45.0), gap, tone(0.5, -46.0), gap, tone(0.5, -45.0), gap}) << true;
        QTest::newRow("gate closes after the phrase")
            << joined({start, tone(1.5, -45.0), QList<float>(kRate * 3 / 10, 0.0F)}) << true;
        QTest::newRow("the silence after the phrase stops it")
            << joined({start, tone(1.5, -45.0), QList<float>(kRate * 5 / 2, 0.0F)}) << false;
    }
    void gatedEvenSpeechIsHeard() {
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
        QCOMPARE(voice.input->message(), kNoModelMessage);
    }

    // A press takes the end of the recording the microphone still holds, here its only speech; a cancel drops it.
    void stopTakesTheHeldEndAndCancelDropsIt() {
        auto voice = voiceOn(kAbsentModel);
        voice.input->toggle();
        QTRY_COMPARE(voice.input->state(), VoiceInput::State::Listening);
        voice.capture->play(noise(2.0, -60.0));
        voice.capture->held = mixed(noise(1.0, -60.0), tone(1.0, -30.0));
        voice.input->toggle();
        QCOMPARE(voice.capture->finished, 1);
        QVERIFY(voice.capture->held.isEmpty());
        QCOMPARE(voice.input->state(), VoiceInput::State::Recognising);
        QVERIFY(settle(*voice.input));
        QCOMPARE(voice.input->message(), kNoModelMessage);

        voice.input->toggle();
        QTRY_COMPARE(voice.input->state(), VoiceInput::State::Listening);
        voice.capture->play(noise(2.0, -60.0));
        voice.capture->held = mixed(noise(1.0, -60.0), tone(1.0, -30.0));
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
        VoiceInput voice(std::make_unique<ScriptedAudioCapture>(mode, wav), tinyModel());
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
                         tinyModel());
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
