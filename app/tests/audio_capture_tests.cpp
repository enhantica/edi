// SPDX-License-Identifier: BSD-3-Clause
// The microphone's conversion to the 16 kHz mono floats the speech model reads (ADR-0107): sample formats, channel
// mixing, the resampler and the end of a recording, checked against sine waves computed here rather than against the
// code's own output.
#include <QAudioFormat>
#include <QByteArray>
#include <QtTest/QtTest>

#include <cmath>
#include <cstring>
#include <numbers>
#include <vector>

#include "audio_capture.hpp"

namespace edi_app {
namespace {

constexpr int kOutputRate = 16000;

std::vector<float> sine(double frequency, int rate, double seconds, double amplitude = 0.5) {
    std::vector<float> samples(static_cast<std::size_t>(std::lround(seconds * rate)));
    for (std::size_t i = 0; i < samples.size(); ++i)
        samples[i] = static_cast<float>(amplitude * std::sin(2.0 * std::numbers::pi * frequency * static_cast<double>(i) / rate));
    return samples;
}

// Pushes `input` in uneven pieces, the way the microphone delivers it, then flushes.
std::vector<float> resample(const std::vector<float>& input, int rate, unsigned seed) {
    MonoResampler resampler(rate);
    std::vector<float> output;
    unsigned state = seed;
    for (std::size_t at = 0; at < input.size();) {
        state = state * 1664525U + 1013904223U;
        const std::size_t size = std::min<std::size_t>(1 + (state >> 8) % 1500, input.size() - at);
        const auto part = resampler.push(std::span<const float>(input.data() + at, size));
        output.insert(output.end(), part.begin(), part.end());
        at += size;
    }
    const auto tail = resampler.flush();
    output.insert(output.end(), tail.begin(), tail.end());
    return output;
}

// The frequency from the rising zero crossings, away from both ends.
double frequency(const std::vector<float>& samples, int rate) {
    const std::size_t edge = samples.size() / 20;
    double firstTime = -1.0;
    double lastTime = -1.0;
    int crossings = 0;
    for (std::size_t i = edge; i + 1 < samples.size() - edge; ++i) {
        if (samples[i] < 0.0F && samples[i + 1] >= 0.0F) {
            const double t = (static_cast<double>(i) + static_cast<double>(samples[i] / (samples[i] - samples[i + 1]))) / rate;
            if (firstTime < 0.0)
                firstTime = t;
            lastTime = t;
            ++crossings;
        }
    }
    return crossings > 1 ? (crossings - 1) / (lastTime - firstTime) : 0.0;
}

double rms(const std::vector<float>& samples) {
    const std::size_t edge = samples.size() / 20;
    double energy = 0.0;
    for (std::size_t i = edge; i < samples.size() - edge; ++i)
        energy += static_cast<double>(samples[i]) * static_cast<double>(samples[i]);
    return std::sqrt(energy / static_cast<double>(samples.size() - 2 * edge));
}

template <typename T>
void append(QByteArray& bytes, T value) {
    bytes.append(reinterpret_cast<const char*>(&value), sizeof value);
}

QAudioFormat format(QAudioFormat::SampleFormat sampleFormat, int channels) {
    QAudioFormat result;
    result.setSampleRate(48000);
    result.setChannelCount(channels);
    result.setSampleFormat(sampleFormat);
    return result;
}

}  // namespace

class AudioCaptureTests : public QObject {
    Q_OBJECT

private slots:
    void resamplerKeepsPitchLevelAndLength_data() {
        QTest::addColumn<int>("rate");
        QTest::newRow("44.1 kHz") << 44100;
        QTest::newRow("48 kHz") << 48000;
        QTest::newRow("22.05 kHz") << 22050;
        QTest::newRow("8 kHz") << 8000;
    }

    void resamplerKeepsPitchLevelAndLength() {
        QFETCH(int, rate);
        const auto input = sine(440.0, rate, 2.0);
        const auto output = resample(input, rate, 1U);
        const auto expected = static_cast<std::size_t>(std::ceil(static_cast<double>(input.size()) * kOutputRate / rate));
        QCOMPARE(output.size(), expected);
        QVERIFY2(std::abs(frequency(output, kOutputRate) - 440.0) < 0.05, "the pitch moved");
        QVERIFY2(std::abs(rms(output) / (0.5 / std::sqrt(2.0)) - 1.0) < 0.01, "the level changed");
        // The ideal 440 Hz wave at 16 kHz, sample for sample.
        const auto ideal = sine(440.0, kOutputRate, 2.0);
        double worst = 0.0;
        for (std::size_t i = output.size() / 20; i < output.size() - output.size() / 20; ++i)
            worst = std::max(worst, static_cast<double>(std::abs(output[i] - ideal[i])));
        QVERIFY2(worst < 1e-3, qPrintable(QStringLiteral("worst error %1").arg(worst)));
    }

    void resamplerOutputDoesNotDependOnTheSplit() {
        const auto input = sine(1234.0, 44100, 1.0);
        const auto a = resample(input, 44100, 1U);
        const auto b = resample(input, 44100, 99U);
        QCOMPARE(a.size(), b.size());
        for (std::size_t i = 0; i < a.size(); ++i)
            QCOMPARE(a[i], b[i]);
    }

    void resamplerKeepsHighSoundsOutOfTheSpeechBand() {
        // A 12 kHz hiss at 48 kHz would land at 4 kHz.
        const auto output = resample(sine(12000.0, 48000, 1.0), 48000, 3U);
        QVERIFY2(rms(output) < 0.5 / std::sqrt(2.0) * 1e-3, "the hiss came through");
        // Speech up to 7 kHz passes.
        const auto speech = resample(sine(7000.0, 48000, 1.0), 48000, 3U);
        QVERIFY2(std::abs(rms(speech) / (0.5 / std::sqrt(2.0)) - 1.0) < 0.01, "7 kHz was cut");
    }

    void resamplerPassesTheTargetRateThrough() {
        const auto input = sine(440.0, kOutputRate, 0.5);
        MonoResampler resampler(kOutputRate);
        const auto output = resampler.push(input);
        QCOMPARE(output.size(), input.size());
        QVERIFY(std::memcmp(output.data(), input.data(), input.size() * sizeof(float)) == 0);
        QVERIFY(resampler.flush().empty());
    }

    void monoSamplesDecodeEveryFormat() {
        QByteArray uint8;
        append<quint8>(uint8, 192);
        append<quint8>(uint8, 64);
        QCOMPARE(mono_samples(format(QAudioFormat::UInt8, 1), uint8), (std::vector<float>{0.5F, -0.5F}));

        QByteArray int16;
        append<qint16>(int16, 16384);
        append<qint16>(int16, -32768);
        QCOMPARE(mono_samples(format(QAudioFormat::Int16, 1), int16), (std::vector<float>{0.5F, -1.0F}));

        QByteArray int32;
        append<qint32>(int32, 1073741824);
        QCOMPARE(mono_samples(format(QAudioFormat::Int32, 1), int32), (std::vector<float>{0.5F}));

        QByteArray float32;
        append<float>(float32, 0.25F);
        QCOMPARE(mono_samples(format(QAudioFormat::Float, 1), float32), (std::vector<float>{0.25F}));
    }

    void monoSamplesAverageTheChannelsOfWholeFrames() {
        QByteArray stereo;
        append<float>(stereo, 0.5F);
        append<float>(stereo, 0.25F);
        append<float>(stereo, -1.0F);
        append<float>(stereo, 0.0F);
        append<float>(stereo, 0.75F);  // half a frame, kept back by the caller until the rest arrives
        QCOMPARE(mono_samples(format(QAudioFormat::Float, 2), stereo), (std::vector<float>{0.375F, -0.5F}));
    }

    // A stop must finish the microphone's converter: the resampler holds the last samples back until it knows what
    // follows. Bytes in uneven pieces, partial frames included, then the finish give the whole recording at 16 kHz.
    void converterFinishReleasesTheEnd() {
        const auto stereo = format(QAudioFormat::Int16, 2);
        const auto wave = sine(440.0, 48000, 0.5);
        QByteArray bytes;
        for (const float sample : wave) {
            const auto value = static_cast<qint16>(std::lround(static_cast<double>(sample) * 32767.0));
            append<qint16>(bytes, value);
            append<qint16>(bytes, value);
        }
        CaptureConverter converter(stereo);
        std::vector<float> output;
        qsizetype size = 1;
        for (qsizetype at = 0; at < bytes.size(); at += size, size = size * 3 % 1999 + 1) {
            const auto part = converter.push(QByteArrayView(bytes).sliced(at, std::min(size, bytes.size() - at)));
            output.insert(output.end(), part.begin(), part.end());
        }
        const auto expected =
            static_cast<std::size_t>(std::ceil(static_cast<double>(wave.size()) * kOutputRate / 48000));
        QVERIFY2(output.size() < expected, "nothing was held back for the finish");
        const auto end = converter.finish();
        output.insert(output.end(), end.begin(), end.end());
        QCOMPARE(output.size(), expected);
        // The ideal 440 Hz wave at 16 kHz, away from both ends.
        const auto ideal = sine(440.0, kOutputRate, 0.5);
        double worst = 0.0;
        for (std::size_t i = output.size() / 20; i < output.size() - output.size() / 20; ++i)
            worst = std::max(worst, static_cast<double>(std::abs(output[i] - ideal[i])));
        QVERIFY2(worst < 1e-3, qPrintable(QStringLiteral("worst error %1").arg(worst)));
    }
};

}  // namespace edi_app

QTEST_GUILESS_MAIN(edi_app::AudioCaptureTests)
#include "audio_capture_tests.moc"
