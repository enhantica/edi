// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_RANGE_ANIMATION_HPP
#define EDI_APP_RANGE_ANIMATION_HPP

#include <QList>
#include <QObject>
#include <QVariantAnimation>
#include <QtQml/qqmlregistration.h>
#include <array>

namespace edi_app {

// A chart's four view ranges, [xMin, xMax, yMin, yMax], moving to new ones as the Pattern chart moves after a box
// zoom, a wheel zoom or a reset (edi ADR-0017 §15): over `duration` ms, easing out (OutQuart). Every chart that zooms
// moves through one of these. The Pattern chart drives it from C++ (start); a QML chart sets `zoom`, the ranges it
// was asked for, and `fitted`, its data's own, and binds its axes to `ranges`. A change of `zoom` moves; a change of
// `fitted` (new data) jumps, as does anything while the chart is not shown.
class RangeAnimation : public QObject {
    Q_OBJECT
    QML_ELEMENT
    // The asked-for ranges: four values, NaN (or an empty list) where the data's own range applies.
    Q_PROPERTY(QList<double> zoom READ zoom WRITE setZoom NOTIFY zoomChanged)
    // The data's own ranges, four values.
    Q_PROPERTY(QList<double> fitted READ fitted WRITE setFitted NOTIFY fittedChanged)
    // The ranges to draw, at this frame.
    Q_PROPERTY(QList<double> ranges READ ranges NOTIFY rangesChanged)
    Q_PROPERTY(int duration READ duration WRITE setDuration NOTIFY durationChanged)
    // A chart not shown moves at once (ADR-0102: no work while hidden).
    Q_PROPERTY(bool active READ active WRITE setActive NOTIFY activeChanged)
    Q_PROPERTY(bool running READ running NOTIFY runningChanged)
    // A pan in progress: zoom changes jump, as the Pattern chart moves with the pointer.
    Q_PROPERTY(bool immediate READ immediate WRITE setImmediate NOTIFY immediateChanged)

   public:
    explicit RangeAnimation(QObject* parent = nullptr);

    QList<double> zoom() const { return zoom_; }
    void setZoom(const QList<double>& zoom);
    QList<double> fitted() const { return fitted_; }
    void setFitted(const QList<double>& fitted);
    QList<double> ranges() const { return {shown_[0], shown_[1], shown_[2], shown_[3]}; }
    int duration() const { return duration_; }
    void setDuration(int duration);
    bool active() const { return active_; }
    void setActive(bool active);
    bool running() const { return animation_.state() == QAbstractAnimation::Running; }
    bool immediate() const { return immediate_; }
    void setImmediate(bool immediate);

    // From C++: moves from `from` to `to`, calling `frame` with each frame's ranges (the first at `from`) and `finished`
    // once at `to`. Equal ends, a duration of 0 or a stopped animation call nothing.
    using Ranges = std::array<double, 4>;
    void start(const Ranges& from, const Ranges& to);
    // Stops where it is; nothing more is called.
    void stop();
    // The ranges at this frame, and where the move ends.
    const Ranges& shown() const { return shown_; }
    const Ranges& end() const { return to_; }

   signals:
    void zoomChanged();
    void fittedChanged();
    void rangesChanged();
    void durationChanged();
    void activeChanged();
    void runningChanged();
    void immediateChanged();
    // Each frame's ranges, then the end.
    void frame();
    void finished();

   private:
    Ranges target() const;
    void moveTo(const Ranges& to, bool animated);
    QVariantAnimation animation_;
    QList<double> zoom_, fitted_;
    Ranges from_{}, to_{}, shown_{0.0, 1.0, 0.0, 1.0};
    int duration_ = 250;
    bool active_ = true;
    bool immediate_ = false;
    bool placed_ = false;  // ranges shown once: the first ones are taken as they are
};

}  // namespace edi_app

#endif  // EDI_APP_RANGE_ANIMATION_HPP
