// SPDX-License-Identifier: BSD-3-Clause
#include "load_attempt.hpp"

#include <QFile>
#include <QFileInfo>
#include <utility>

#include "edi/io.hpp"

namespace edi_app {
namespace {
thread_local LoadFrame* top = nullptr;

QString existing(const QString& path) { return !path.isEmpty() && QFileInfo(path).isFile() ? path : QString(); }
}  // namespace

// The core's record so far belongs to the frame that was innermost until `frame` started: kept when that is an
// attempt, dropped otherwise (an announcement's listeners record nothing for anyone).
void LoadAttempt::absorbBelow(const LoadFrame* frame) {
    const QString core = QString::fromStdString(edi::take_failed_file());
    if (frame->outer_ && !frame->outer_->announcing_ && !core.isEmpty())
        static_cast<LoadAttempt*>(frame->outer_)->recorded_ = core;
}

LoadFrame::LoadFrame(const QObject* owner, bool announcing) : owner_(owner), outer_(top), announcing_(announcing) {
    top = this;
}

LoadFrame::~LoadFrame() { top = outer_; }

LoadFrame* LoadFrame::innermost(const QObject* owner) {
    for (LoadFrame* frame = top; frame; frame = frame->outer_)
        if (frame->owner_ == owner) return frame;
    return nullptr;
}

LoadAttempt::LoadAttempt(const QObject* owner) : LoadFrame(owner, false) { absorbBelow(this); }

LoadAttempt::~LoadAttempt() { edi::take_failed_file(); }

LoadAttempt* LoadAttempt::current(const QObject* owner) {
    LoadFrame* frame = innermost(owner);
    return frame && !frame->announcing_ ? static_cast<LoadAttempt*>(frame) : nullptr;
}

void LoadAttempt::collect() {
    if (this != top) return;  // the core's record is the innermost frame's
    const QString core = QString::fromStdString(edi::take_failed_file());
    if (!core.isEmpty()) recorded_ = core;
}

QString LoadAttempt::failed() {
    collect();
    return existing(!recorded_.isEmpty() ? recorded_ : reading_);
}

void LoadAttempt::keep() {
    const QString path = failed();
    if (path.isEmpty() || (copy_ && path.startsWith(copy_->path()))) return;
    auto kept = std::make_unique<QTemporaryDir>();
    const QString copy = kept->isValid() ? kept->filePath(QFileInfo(path).fileName()) : QString();
    if (copy.isEmpty() || !QFile::copy(path, copy)) return;
    copy_ = std::move(kept);
    recorded_ = copy;
    reading_.clear();
}

QString LoadAttempt::release(std::unique_ptr<QTemporaryDir>& copy) {
    const QString path = failed();
    copy = std::move(copy_);
    recorded_.clear();
    reading_.clear();
    return path;
}

RefusalAnnouncement::RefusalAnnouncement(const QObject* owner) : LoadFrame(owner, true) {
    LoadAttempt::absorbBelow(this);
    // The owner's frame below: its load's failed file, or none when no load (or another announcement) is there.
    LoadFrame* frame = outer_;
    while (frame && frame->owner_ != owner) frame = frame->outer_;
    if (frame && !frame->announcing_) {
        const auto* attempt = static_cast<const LoadAttempt*>(frame);
        file_ = existing(!attempt->recorded_.isEmpty() ? attempt->recorded_ : attempt->reading_);
    }
}

RefusalAnnouncement::~RefusalAnnouncement() { edi::take_failed_file(); }

QString RefusalAnnouncement::file(const QObject* owner) {
    LoadFrame* frame = innermost(owner);
    return frame && frame->announcing_ ? existing(static_cast<RefusalAnnouncement*>(frame)->file_) : QString();
}

}  // namespace edi_app
