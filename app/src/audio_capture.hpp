// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_AUDIO_CAPTURE_HPP
#define EDI_APP_AUDIO_CAPTURE_HPP

#include <QAudioFormat>
#include <QList>
#include <QObject>
#include <QByteArray>
#include <QPointer>

#include <memory>
#include <span>
#include <vector>

class QAudioSource;
class QIODevice;

namespace edi_app {

/// Converts mono audio at any rate to the 16 kHz voice input records (ADR-0107). Feed it in chunks; it keeps the state
/// between them. Lowering the rate averages the input over each output step first, so speech does not alias.
class MonoResampler {
public:
    explicit MonoResampler(int input_rate, int output_rate = 16000);
    std::vector<float> push(std::span<const float> input);

private:
    double step_;            // input samples per output sample
    int window_;             // the averaging width when lowering the rate
    std::vector<float> recent_;
    double sum_ = 0.0;
    std::size_t next_ = 0;   // the oldest sample in recent_
    std::vector<float> pending_;
    double position_ = 0.0;  // the next output sample's place in pending_
};

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

}  // namespace edi_app

#endif  // EDI_APP_AUDIO_CAPTURE_HPP
