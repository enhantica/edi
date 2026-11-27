// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_AUDIO_CAPTURE_HPP
#define EDI_APP_AUDIO_CAPTURE_HPP

#include <QAudioFormat>
#include <QList>
#include <QObject>
#include <QByteArray>
#include <QByteArrayView>
#include <QPointer>
#include <QString>
#include <QTimer>

#include <cstdint>
#include <memory>
#include <span>
#include <vector>

class QAudioSource;
class QIODevice;

namespace edi_app {

/// Converts mono audio at any rate to the 16 kHz voice input records (ADR-0107). Feed it in chunks; it keeps the state
/// between them, so the output does not depend on how the input was split. A windowed-sinc low-pass filter keeps
/// everything above 7.5 kHz out of the result, so fricatives do not fold back into the speech band. Equal rates pass the
/// samples through unchanged.
class MonoResampler {
public:
    explicit MonoResampler(int input_rate, int output_rate = 16000);
    std::vector<float> push(std::span<const float> input);
    /// The samples still waiting for later input, as if silence followed; the resampler then starts afresh.
    std::vector<float> flush();

private:
    std::vector<float> convert(bool flushing);
    void reset();

    int in_;
    int out_;
    double reach_ = 0.0;         // the filter's half width in input samples; 0 when the rates match
    std::vector<float> kernel_;  // the filter from 0 to reach_, sampled finely
    std::vector<float> pending_; // input samples some later output still needs
    std::int64_t received_ = 0;  // input samples pushed since the start
    std::int64_t dropped_ = 0;   // input samples no longer in pending_
    std::int64_t emitted_ = 0;   // output samples so far
};

/// Whole frames of `bytes` in `format`, each frame's channels averaged into one float in [-1, 1].
std::vector<float> mono_samples(const QAudioFormat& format, QByteArrayView bytes);

/// A microphone for voice input: 16 kHz mono floats in [-1, 1], in memory only. Tests inject their own source.
class AudioCapture : public QObject {
    Q_OBJECT
public:
    enum class Failure { NoMicrophone, PermissionRefused, DeviceFailed };
    Q_ENUM(Failure)

    using QObject::QObject;

    /// Asks for the microphone permission when the system has not been asked yet, then records. Answers with
    /// `started` or `failed`, possibly before returning.
    virtual void start() = 0;
    /// Stops recording; no `samples` follow.
    virtual void stop() = 0;

signals:
    void started();
    void samples(const QList<float>& chunk);
    void failed(edi_app::AudioCapture::Failure failure);
};

/// The default microphone through Qt Multimedia, with Qt's microphone permission.
class QtAudioCapture final : public AudioCapture {
    Q_OBJECT
public:
    using AudioCapture::AudioCapture;
    ~QtAudioCapture() override;

    void start() override;
    void stop() override;

private:
    void open();
    void read();
    void close();

    QPointer<QAudioSource> source_;
    QPointer<QIODevice> device_;
    QAudioFormat format_;
    std::unique_ptr<MonoResampler> resampler_;
    QByteArray carry_;  // a partial frame left from the last read
    int request_ = 0;  // a stop or a later start makes an earlier permission answer stale
};

/// A microphone that plays a recording, for the app's own pytest runs (tests/fixtures/assistant_voice/README.md).
/// `mode` is "available", "no-device" or "permission-denied". When available, `start` plays the recording at once and
/// then real-time silence until `stop`, so the silence check ends the recording as it would after the user stops.
class ScriptedAudioCapture final : public AudioCapture {
    Q_OBJECT
public:
    ScriptedAudioCapture(QString mode, QString wav, QObject* parent = nullptr);

    void start() override;
    void stop() override;

    /// A RIFF WAV file of 16-bit PCM or 32-bit float samples, at any rate and channel count, as 16 kHz mono; empty
    /// when the file cannot be read.
    static std::vector<float> read_wav(const QString& path);

private:
    void play(int request);

    QString mode_;
    QString wav_;
    QTimer silence_;
    int request_ = 0;  // a stop or a later start makes an earlier queued start stale
};

}  // namespace edi_app

#endif  // EDI_APP_AUDIO_CAPTURE_HPP
