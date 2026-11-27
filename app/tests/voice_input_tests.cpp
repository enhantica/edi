// SPDX-License-Identifier: BSD-3-Clause
// Voice input (ADR-0107) on the tiny model and a recorded speech, never a real microphone: a model folder named outside
// ASCII, an owner that goes away or releases its recording, a result that lands after a cancel, and a microphone that
// is missing, refused or broken.
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QRegularExpression>
#include <QSignalSpy>
#include <QTemporaryDir>
#include <QThreadPool>
#include <QtTest/QtTest>

#include <memory>
#include <utility>
#include <vector>

#include "audio_capture.hpp"
#include "speech_recogniser.hpp"
#include "voice_input.hpp"

namespace edi_app {
namespace {

constexpr int kRecognitionMs = 120000;
const QString kFixtures = QStringLiteral(EDI_SOURCE_DIR "/tests/fixtures/assistant_voice");

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
    void play(const std::vector<float>& audio) { emit samples(QList<float>(audio.begin(), audio.end())); }

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

// Every recognition started so far has finished and its result has reached the voice input.
[[nodiscard]] bool settle() {
    if (!QThreadPool::globalInstance()->waitForDone(kRecognitionMs))
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
        voice.capture->play(std::vector<float>(speech_.begin(), speech_.begin() + 3 * SpeechRecogniser::sample_rate));
        QCOMPARE(voice.input->state(), VoiceInput::State::Listening);
        delete owner;
        QCOMPARE(voice.input->state(), VoiceInput::State::Idle);
        QCOMPARE(voice.input->owner(), nullptr);
        QVERIFY(settle());
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
        QVERIFY(settle());
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
        QVERIFY(settle());
        QCOMPARE(voice.input->state(), VoiceInput::State::Listening);
        QCOMPARE(text.count(), 0);
        QCOMPARE(voice.input->message(), QString());
        voice.input->cancel();
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
