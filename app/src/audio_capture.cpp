// SPDX-License-Identifier: BSD-3-Clause
#include "audio_capture.hpp"

#include <QAudioDevice>
#include <QAudioSource>
#include <QCoreApplication>
#include <QMediaDevices>
#include <QPermissions>

#include <algorithm>
#include <cmath>

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

}  // namespace edi_app
