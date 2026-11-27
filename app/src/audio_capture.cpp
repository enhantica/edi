// SPDX-License-Identifier: BSD-3-Clause
#include "audio_capture.hpp"

#include <QAudioDevice>
#include <QAudioSource>
#include <QCoreApplication>
#include <QFile>
#include <QMediaDevices>
#include <QPermissions>
#include <QtEndian>

#include <algorithm>
#include <cmath>
#include <cstring>
#include <limits>
#include <numbers>
#include <utility>

namespace edi_app {

namespace {

constexpr std::size_t kernel_step = 64;  // kernel points per input sample; linear in between is exact to about -90 dB
constexpr auto kernel_steps = static_cast<double>(kernel_step);

}  // namespace

MonoResampler::MonoResampler(int input_rate, int output_rate)
    : in_(std::max(input_rate, 1)), out_(std::max(output_rate, 1)) {
    if (in_ != out_) {
        // Cut at 15/16 of the lower rate's Nyquist frequency (7.5 kHz for 16 kHz), over 64 samples of the lower rate on
        // each side (4 ms at 16 kHz); the Blackman window then keeps aliases about 70 dB down.
        const double lower = std::min(static_cast<double>(out_) / in_, 1.0);  // the lower rate, in cycles per input sample
        const double cutoff = 0.46875 * lower;
        reach_ = 64.0 / lower;
        kernel_.resize(static_cast<std::size_t>(std::ceil(reach_ * kernel_steps)) + 2);
        for (std::size_t i = 0; i < kernel_.size(); ++i) {
            const double t = static_cast<double>(i) / kernel_steps;
            if (t >= reach_) {
                kernel_[i] = 0.0F;
                continue;
            }
            const double x = 2.0 * cutoff * t;
            const double sinc = x == 0.0 ? 1.0 : std::sin(std::numbers::pi * x) / (std::numbers::pi * x);
            const double w = t / reach_;
            const double window = 0.42 + 0.5 * std::cos(std::numbers::pi * w) + 0.08 * std::cos(2.0 * std::numbers::pi * w);
            kernel_[i] = static_cast<float>(sinc * window);
        }
    }
    reset();
}

void MonoResampler::reset() {
    // Silence before the first sample, so the first output sample sits on the first input sample.
    pending_.assign(static_cast<std::size_t>(std::ceil(reach_)), 0.0F);
    received_ = 0;
    dropped_ = 0;
    emitted_ = 0;
}

std::vector<float> MonoResampler::push(std::span<const float> input) {
    if (reach_ == 0.0)
        return {input.begin(), input.end()};
    pending_.insert(pending_.end(), input.begin(), input.end());
    received_ += static_cast<std::int64_t>(input.size());
    return convert(false);
}

std::vector<float> MonoResampler::flush() {
    if (reach_ == 0.0)
        return {};
    pending_.resize(pending_.size() + static_cast<std::size_t>(std::ceil(reach_)) + 1, 0.0F);
    auto output = convert(true);
    reset();
    return output;
}

std::vector<float> MonoResampler::convert(bool flushing) {
    std::vector<float> output;
    const auto lead = static_cast<std::int64_t>(std::ceil(reach_));
    const auto size = static_cast<double>(pending_.size());
    // Output sample k sits k * in_ / out_ input samples after the first; integers keep that exact over any length.
    const auto place = [&] {
        const std::int64_t at = emitted_ * in_;
        const std::int64_t whole = lead + at / out_ - dropped_;
        return static_cast<double>(whole) + static_cast<double>(at % out_) / out_;
    };
    for (;;) {
        // A flush ends at the last real input sample; otherwise wait for every input sample within reach_.
        if (flushing && emitted_ * in_ >= received_ * out_)
            break;
        const double position = place();
        if (position + reach_ >= size)
            break;
        const auto first = static_cast<std::size_t>(std::ceil(position - reach_));
        const auto last = static_cast<std::size_t>(std::floor(position + reach_));
        const auto middle = static_cast<std::size_t>(std::floor(position));
        double sum = 0.0;
        double total = 0.0;
        // Neighbouring input samples are one kernel step apart and share the offset between kernel points.
        const auto add = [&](double distance, std::size_t from, std::size_t count, bool forward) {
            const double at = distance * kernel_steps;
            auto k = static_cast<std::size_t>(at);
            const double fraction = at - static_cast<double>(k);
            for (std::size_t n = 0; n < count && k + 1 < kernel_.size(); ++n, k += kernel_step) {
                const auto a = static_cast<double>(kernel_[k]);
                const double w = a + (static_cast<double>(kernel_[k + 1]) - a) * fraction;
                sum += w * static_cast<double>(pending_[forward ? from + n : from - n]);
                total += w;
            }
        };
        add(position - static_cast<double>(middle), middle, middle - first + 1, false);
        add(static_cast<double>(middle + 1) - position, middle + 1, last - middle, true);
        // Dividing by the weights keeps the level exact at every offset between input samples.
        output.push_back(total > 0.0 ? static_cast<float>(sum / total) : 0.0F);
        ++emitted_;
    }
    const double reached = std::max(0.0, std::floor(place() - reach_));
    const auto used = std::min(static_cast<std::size_t>(reached), pending_.size());
    pending_.erase(pending_.begin(), pending_.begin() + static_cast<std::ptrdiff_t>(used));
    dropped_ += static_cast<std::int64_t>(used);
    return output;
}

namespace {

template <typename T>
T load(const char* data) {
    T value;
    std::memcpy(&value, data, sizeof value);
    return value;
}

}  // namespace

std::vector<float> mono_samples(const QAudioFormat& format, QByteArrayView bytes) {
    const qsizetype frame = format.bytesPerFrame();
    const qsizetype width = format.bytesPerSample();
    const int channels = format.channelCount();
    if (frame <= 0 || channels <= 0)
        return {};
    const auto decode = [kind = format.sampleFormat()](const char* data) -> float {
        switch (kind) {
        case QAudioFormat::UInt8:
            return static_cast<float>(static_cast<int>(load<quint8>(data)) - 128) / 128.0F;
        case QAudioFormat::Int16:
            return static_cast<float>(load<qint16>(data)) / 32768.0F;
        case QAudioFormat::Int32:
            return static_cast<float>(static_cast<double>(load<qint32>(data)) / 2147483648.0);
        case QAudioFormat::Float:
            return load<float>(data);
        default:
            return 0.0F;
        }
    };
    const qsizetype frames = bytes.size() / frame;
    std::vector<float> mono(static_cast<std::size_t>(frames));
    const char* data = bytes.data();
    for (qsizetype f = 0; f < frames; ++f) {
        float sum = 0.0F;
        for (qsizetype c = 0; c < channels; ++c)
            sum += decode(data + f * frame + c * width);
        mono[static_cast<std::size_t>(f)] = sum / static_cast<float>(channels);
    }
    return mono;
}

QtAudioCapture::~QtAudioCapture() { close(); }

void QtAudioCapture::start() {
    close();
    const int request = ++request_;
#if QT_CONFIG(permissions)
    const QMicrophonePermission permission;
    switch (qApp->checkPermission(permission)) {
    case Qt::PermissionStatus::Granted:
        open();
        return;
    case Qt::PermissionStatus::Denied:
        emit failed(Failure::PermissionRefused);
        return;
    case Qt::PermissionStatus::Undetermined:
        qApp->requestPermission(permission, this, [this, request](const QPermission& answer) {
            if (request != request_)
                return;
            if (answer.status() == Qt::PermissionStatus::Granted)
                open();
            else
                emit failed(Failure::PermissionRefused);
        });
        return;
    }
#endif
    open();
}

void QtAudioCapture::stop() {
    ++request_;
    close();
}

void QtAudioCapture::open() {
    const QAudioDevice input = QMediaDevices::defaultAudioInput();
    if (input.isNull()) {
        emit failed(Failure::NoMicrophone);
        return;
    }
    // Record in the device's own format and convert here. When Qt 6.11 converts the rate itself on macOS it repeats up to a
    // fifth of the audio in short pieces (QTBUG-151918), which garbles speech.
    format_ = input.preferredFormat();
    if (!format_.isValid()) {
        QAudioFormat wanted;
        wanted.setSampleRate(16000);
        wanted.setChannelCount(1);
        wanted.setSampleFormat(QAudioFormat::Float);
        if (input.isFormatSupported(wanted))
            format_ = wanted;
    }
    // The rate bounds the resampler's filter length.
    if (!format_.isValid() || format_.bytesPerFrame() <= 0 || format_.sampleRate() < 8000 || format_.sampleRate() > 384000) {
        emit failed(Failure::DeviceFailed);
        return;
    }
    resampler_ = std::make_unique<MonoResampler>(format_.sampleRate());
    source_ = new QAudioSource(input, format_, this);
    connect(source_, &QAudioSource::stateChanged, this, [this](QtAudio::State) {
        if (source_ && source_->error() != QtAudio::NoError) {
            close();
            emit failed(Failure::DeviceFailed);
        }
    });
    device_ = source_->start();
    if (!device_) {
        close();
        emit failed(Failure::DeviceFailed);
        return;
    }
    connect(device_, &QIODevice::readyRead, this, &QtAudioCapture::read);
    emit started();
}

void QtAudioCapture::read() {
    if (!device_ || !resampler_)
        return;
    carry_.append(device_->readAll());
    const qsizetype frame = format_.bytesPerFrame();
    if (frame <= 0)
        return;
    const qsizetype whole = carry_.size() / frame * frame;
    if (whole == 0)
        return;
    const auto mono = mono_samples(format_, QByteArrayView(carry_).first(whole));
    carry_.remove(0, whole);
    const auto converted = resampler_->push(mono);
    if (!converted.empty())
        emit samples(QList<float>(converted.begin(), converted.end()));
}

void QtAudioCapture::close() {
    if (source_) {
        source_->disconnect(this);
        source_->stop();
        source_->deleteLater();
    }
    source_ = nullptr;
    device_ = nullptr;
    resampler_.reset();
    carry_.clear();
}

ScriptedAudioCapture::ScriptedAudioCapture(QString mode, QString wav, QObject* parent)
    : AudioCapture(parent), mode_(std::move(mode)), wav_(std::move(wav)) {
    // 100 ms of silence every 100 ms, as a quiet room sounds after the recording.
    silence_.setInterval(100);
    connect(&silence_, &QTimer::timeout, this, [this] { emit samples(QList<float>(1600, 0.0F)); });
}

void ScriptedAudioCapture::start() {
    stop();
    const int request = request_;
    // A real microphone answers later, never inside start.
    QMetaObject::invokeMethod(this, [this, request] { play(request); }, Qt::QueuedConnection);
}

void ScriptedAudioCapture::stop() {
    ++request_;
    silence_.stop();
}

void ScriptedAudioCapture::play(int request) {
    if (request != request_)
        return;
    if (mode_ == QStringLiteral("no-device")) {
        emit failed(Failure::NoMicrophone);
        return;
    }
    if (mode_ == QStringLiteral("permission-denied")) {
        emit failed(Failure::PermissionRefused);
        return;
    }
    const auto recording = mode_ == QStringLiteral("available") ? read_wav(wav_) : std::vector<float>();
    if (recording.empty()) {
        emit failed(Failure::DeviceFailed);
        return;
    }
    emit started();
    if (request != request_)
        return;
    emit samples(QList<float>(recording.begin(), recording.end()));
    // The silence check may already have stopped the recording.
    if (request == request_)
        silence_.start();
}

std::vector<float> ScriptedAudioCapture::read_wav(const QString& path) {
    constexpr qint64 most_bytes = qint64{256} * 1024 * 1024;
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly) || file.size() > most_bytes)
        return {};
    const QByteArray bytes = file.readAll();
    const auto* data = reinterpret_cast<const uchar*>(bytes.constData());
    const auto size = static_cast<std::size_t>(bytes.size());
    if (size < 12 || std::memcmp(data, "RIFF", 4) != 0 || std::memcmp(data + 8, "WAVE", 4) != 0)
        return {};
    unsigned format = 0, channels = 0, rate = 0, bits = 0;
    const uchar* payload = nullptr;
    std::size_t payload_bytes = 0;
    for (std::size_t at = 12; at + 8 <= size;) {
        const auto length = static_cast<std::size_t>(qFromLittleEndian<quint32>(data + at + 4));
        const uchar* body = data + at + 8;
        const std::size_t room = size - at - 8;
        if (std::memcmp(data + at, "fmt ", 4) == 0 && length >= 16 && length <= room) {
            format = qFromLittleEndian<quint16>(body);
            channels = qFromLittleEndian<quint16>(body + 2);
            rate = qFromLittleEndian<quint32>(body + 4);
            bits = qFromLittleEndian<quint16>(body + 14);
            // WAVE_FORMAT_EXTENSIBLE keeps the real format in the first two bytes of its sub-format GUID.
            if (format == 0xFFFEU && length >= 40)
                format = qFromLittleEndian<quint16>(body + 24);
        } else if (std::memcmp(data + at, "data", 4) == 0) {
            payload = body;
            payload_bytes = std::min(length, room);
        }
        if (length > room)
            break;
        at += 8 + length + (length & 1U);  // chunks are padded to an even size
    }
    const bool pcm16 = format == 1 && bits == 16;
    const bool float32 = format == 3 && bits == 32;
    // The rate bounds the resampler's filter length.
    if (payload == nullptr || (!pcm16 && !float32) || channels == 0 || rate == 0 || rate > 384000)
        return {};
    const std::size_t width = bits / 8;
    const std::size_t frames = payload_bytes / (width * channels);
    std::vector<float> mono(frames);
    for (std::size_t f = 0; f < frames; ++f) {
        float sum = 0.0F;
        for (std::size_t c = 0; c < channels; ++c) {
            const uchar* sample = payload + (f * channels + c) * width;
            if (pcm16) {
                sum += static_cast<float>(qFromLittleEndian<qint16>(sample)) / 32768.0F;
            } else {
                const quint32 raw = qFromLittleEndian<quint32>(sample);
                float value = 0.0F;
                std::memcpy(&value, &raw, sizeof value);
                sum += value;
            }
        }
        mono[f] = sum / static_cast<float>(channels);
    }
    MonoResampler resampler(static_cast<int>(rate));
    auto converted = resampler.push(mono);
    const auto tail = resampler.flush();
    converted.insert(converted.end(), tail.begin(), tail.end());
    return converted;
}

}  // namespace edi_app
