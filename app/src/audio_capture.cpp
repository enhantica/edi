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
#include <utility>

namespace edi_app {

MonoResampler::MonoResampler(int input_rate, int output_rate)
    : step_(static_cast<double>(std::max(input_rate, 1)) / static_cast<double>(std::max(output_rate, 1))),
      window_(std::max(1, static_cast<int>(std::floor(step_)))),
      recent_(static_cast<std::size_t>(window_), 0.0F) {}

std::vector<float> MonoResampler::push(std::span<const float> input) {
    pending_.reserve(pending_.size() + input.size());
    for (const float sample : input) {
        if (window_ > 1) {
            sum_ += static_cast<double>(sample) - static_cast<double>(recent_[next_]);
            recent_[next_] = sample;
            next_ = (next_ + 1) % recent_.size();
            pending_.push_back(static_cast<float>(sum_ / window_));
        } else {
            pending_.push_back(sample);
        }
    }
    std::vector<float> output;
    while (position_ + 1.0 < static_cast<double>(pending_.size())) {
        const auto index = static_cast<std::size_t>(position_);
        const double fraction = position_ - static_cast<double>(index);
        output.push_back(static_cast<float>(static_cast<double>(pending_[index]) * (1.0 - fraction) +
                                            static_cast<double>(pending_[index + 1]) * fraction));
        position_ += step_;
    }
    const auto used = std::min(static_cast<std::size_t>(position_), pending_.size());
    pending_.erase(pending_.begin(), pending_.begin() + static_cast<std::ptrdiff_t>(used));
    position_ -= static_cast<double>(used);
    return output;
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
    QAudioFormat wanted;
    wanted.setSampleRate(16000);
    wanted.setChannelCount(1);
    wanted.setSampleFormat(QAudioFormat::Float);
    format_ = input.isFormatSupported(wanted) ? wanted : input.preferredFormat();
    if (!format_.isValid() || format_.bytesPerFrame() <= 0) {
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
    const int frame = format_.bytesPerFrame();
    const int sample = format_.bytesPerSample();
    const int channels = format_.channelCount();
    const auto frames = carry_.size() / frame;
    if (frames == 0)
        return;
    std::vector<float> mono(static_cast<std::size_t>(frames));
    const char* data = carry_.constData();
    for (qsizetype f = 0; f < frames; ++f) {
        float sum = 0.0F;
        for (int c = 0; c < channels; ++c)
            sum += format_.normalizedSampleValue(data + f * frame + c * sample);
        mono[static_cast<std::size_t>(f)] = sum / static_cast<float>(channels);
    }
    carry_.remove(0, frames * frame);
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
    // The rate bounds the resampler's averaging window.
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
    return resampler.push(mono);
}

}  // namespace edi_app
