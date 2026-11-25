// SPDX-License-Identifier: BSD-3-Clause
#include "range_animation.hpp"

#include <QEasingCurve>
#include <cmath>

namespace edi_app {

RangeAnimation::RangeAnimation(QObject* parent) : QObject(parent) {
    // Qt Charts' series animation easing, as the Pattern chart has moved since easydiffractionbeta.
    animation_.setStartValue(0.0);
    animation_.setEndValue(1.0);
    animation_.setEasingCurve(QEasingCurve::OutQuart);
    connect(&animation_, &QVariantAnimation::valueChanged, this, [this](const QVariant& value) {
        if (animation_.state() != QAbstractAnimation::Running) return;
        const double progress = value.toDouble();
        for (std::size_t i = 0; i < 4; ++i) shown_[i] = from_[i] + (to_[i] - from_[i]) * progress;
        emit rangesChanged();
        emit frame();
    });
    connect(&animation_, &QAbstractAnimation::finished, this, [this] {
        shown_ = to_;
        emit rangesChanged();
        emit runningChanged();
        emit finished();
    });
}

void RangeAnimation::start(const Ranges& from, const Ranges& to) {
    stop();
    if (from == to || duration_ <= 0) return;
    from_ = from;
    to_ = to;
    shown_ = from;
    animation_.setDuration(duration_);
    animation_.start();
    emit runningChanged();
    emit rangesChanged();
    emit frame();
}

void RangeAnimation::stop() {
    if (animation_.state() == QAbstractAnimation::Running) {
        animation_.stop();
        emit runningChanged();
    }
}

RangeAnimation::Ranges RangeAnimation::target() const {
    Ranges out = shown_;
    for (qsizetype i = 0; i < 4; ++i) {
        const double asked = i < zoom_.size() ? zoom_[i] : std::nan("");
        const double own = i < fitted_.size() ? fitted_[i] : std::nan("");
        out[static_cast<std::size_t>(i)] = std::isfinite(asked) ? asked : std::isfinite(own) ? own : out[static_cast<std::size_t>(i)];
    }
    return out;
}

void RangeAnimation::moveTo(const Ranges& to, bool animated) {
    if (animated && placed_ && active_ && duration_ > 0) {
        start(shown_, to);  // from where the view is, mid-move included
        return;
    }
    stop();
    placed_ = true;
    if (to != shown_) {
        shown_ = to;
        emit rangesChanged();
    }
}

void RangeAnimation::setZoom(const QList<double>& zoom) {
    if (zoom == zoom_) return;
    zoom_ = zoom;
    emit zoomChanged();
    moveTo(target(), !immediate_);
}

void RangeAnimation::setFitted(const QList<double>& fitted) {
    if (fitted == fitted_) return;
    fitted_ = fitted;
    emit fittedChanged();
    // New data jumps, but a move already under way ends where it now should.
    if (running()) {
        to_ = target();
    } else {
        moveTo(target(), false);
    }
}

void RangeAnimation::setDuration(int duration) {
    if (duration == duration_) return;
    duration_ = duration;
    emit durationChanged();
}

void RangeAnimation::setImmediate(bool immediate) {
    if (immediate == immediate_) return;
    immediate_ = immediate;
    emit immediateChanged();
}

void RangeAnimation::setActive(bool active) {
    if (active == active_) return;
    active_ = active;
    emit activeChanged();
    if (!active_ && running()) moveTo(to_, false);
}

}  // namespace edi_app
