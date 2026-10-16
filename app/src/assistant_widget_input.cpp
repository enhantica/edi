// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_widget_input.hpp"
#include <QCoreApplication>
#include <QEvent>
#include <QKeyEvent>
#include <QKeySequence>
#include <QMouseEvent>
#include <QScopeGuard>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace edi_app {
namespace {
// Actual matched RemotePointer/RemoteController prior art, not blocking waits.
constexpr int move_ms = 500, press_ms = 100, click_relaxation_ms = 500, character_ms = 100;
}
AssistantWidgetInput::AssistantWidgetInput(QQuickWindow& window, QObject* parent)
    : QObject(parent), window_(&window) {
    timer_.setSingleShot(true);
    connect(&timer_, &QTimer::timeout, this, &AssistantWidgetInput::advance);
    window.installEventFilter(this);
}
AssistantWidgetInput::~AssistantWidgetInput() {
    timer_.stop();
    if (window_) window_->removeEventFilter(this);
    // Owning native adapter retires its original call/worker independently;
    // destruction never invokes callbacks into a partially destroyed owner.
}
bool AssistantWidgetInput::current(std::uint64_t id) const {
    const QPointer<const AssistantWidgetInput> self(this);
    const auto request = request_; // Keep callback ownership through reentrant retirement.
    if (serial_ != id || !request || !window_ || !request->target || !request->current) return false;
    const bool valid = request->current();
    return self && valid && serial_ == id && request_ == request && window_ && request->target;
}
bool AssistantWidgetInput::visibleCenter(QQuickItem& item, QPointF& center) const {
    if (!window_ || item.window() != window_ || !window_->isVisible() || item.width() <= 0 || item.height() <= 0) return false;
    center = item.mapToScene(QPointF(item.width() / 2, item.height() / 2));
    if (!std::isfinite(center.x()) || !std::isfinite(center.y()) || !QRectF(0, 0, window_->width(), window_->height()).contains(center)) return false;
    for (auto* ancestor = &item; ancestor; ancestor = ancestor->parentItem()) {
        if (!ancestor->isVisible() || !ancestor->isEnabled() || ancestor->opacity() <= 0) return false;
        if (ancestor->clip() && !ancestor->boundingRect().contains(ancestor->mapFromScene(center))) return false;
    }
    return true;
}
bool AssistantWidgetInput::usableTarget(QQuickItem& item) const {
    QPointF center;
    return visibleCenter(item, center);
}
bool AssistantWidgetInput::manualDraftPresent() const {
    if (!window_) return false;
    // TextInput may be a visual child of the actual field. Check its real
    // ParameterField/ParameterCell ancestor, not just the requested target.
    for (auto* item = window_->activeFocusItem(); item; item = item->parentItem()) {
        if (!item->property("assistantEditing").isValid()) continue;
        if (draft_ && request_ && request_->target == item && item->property("assistantEditing").toBool()) return false;
        const auto text = item->property("text").toString();
        return text != item->property("value").toString() && text != item->property("editText").toString();
    }
    return false;
}
std::uint64_t AssistantWidgetInput::start(Request request) {
    if (request_ || !window_ || !request.target || !request.current || !request.prepareCommit ||
        !request.finishCommit || !request.completed || serial_ == UINT64_MAX)
        throw std::runtime_error("A visible input owner is unavailable");
    QPointF center;
    if (!request.current() || !visibleCenter(*request.target, center))
        throw std::runtime_error("The genuine input control is not visible and current");
    if (request.kind == Kind::Value && (request.value.isEmpty() || request.value.size() > 256))
        throw std::runtime_error("The numeric input spelling is unavailable");
    // Applies to navigation/free/fit too: their click can commit an unrelated
    // pre-existing manual draft through ordinary focus loss.
    if (manualDraftPresent()) throw std::runtime_error("Finish the current manual input first");
    original_text_ = request.kind == Kind::Value ? request.target->property("editText").toString() : QString{};
    if (original_text_.size() > 256) throw std::runtime_error("The original numeric draft exceeds the visible input bound");
    auto prepared = std::make_shared<Request>(std::move(request)); // All job/callback allocation precedes visibility.
    request_ = std::move(prepared);
    const auto original = request_;
    const auto id = ++serial_;
    center_ = center; step_ = Step::Move; character_ = 0; draft_ = false; commit_prepared_ = false;
    QPointer<AssistantWidgetInput> self(this);
    emit activeChanged(true);
    if (!self) return id;
    const bool ready = self->current(id);
    if (!self) return id;
    if (!ready) { if (serial_ == id && request_ == original) stop(false, tr("Visible input ownership changed"), false); return id; }
    emit pointerShown();
    if (!self) return id;
    const bool shown = self->current(id);
    if (!self) return id;
    if (!shown) { if (serial_ == id && request_ == original) stop(false, tr("Visible input ownership changed"), false); return id; }
    timer_.start(0);
    return id;
}
bool AssistantWidgetInput::mouse(QEvent::Type type, Qt::MouseButton button) {
    if (!window_ || !request_) return false;
    const QPointer<AssistantWidgetInput> self(this);
    const QPointer<QQuickWindow> window(window_);
    const auto original = request_; const auto id = serial_;
    const bool old = injecting_; injecting_ = true;
    const auto release = qScopeGuard([self, old] { if (self) self->injecting_ = old; });
    const auto buttons = type == QEvent::MouseButtonRelease ? Qt::NoButton : button;
    QMouseEvent event(type, center_, window->mapToGlobal(center_), button, buttons, Qt::NoModifier);
    QCoreApplication::sendEvent(window, &event);
    return self && window && serial_ == id && request_ == original;
}
bool AssistantWidgetInput::key(int code, Qt::KeyboardModifiers modifiers, const QString& text) {
    if (!window_ || !request_ || !request_->target || !request_->target->hasActiveFocus()) return false;
    const QPointer<AssistantWidgetInput> self(this);
    const QPointer<QQuickWindow> window(window_);
    const auto original = request_; const auto id = serial_;
    const bool old = injecting_; injecting_ = true;
    const auto release = qScopeGuard([self, old] { if (self) self->injecting_ = old; });
    QKeyEvent press(QEvent::KeyPress, code, modifiers, text);
    QCoreApplication::sendEvent(window, &press);
    if (!self || !window || serial_ != id || request_ != original || !request_->target || !request_->target->hasActiveFocus()) return false;
    QKeyEvent release_event(QEvent::KeyRelease, code, modifiers, text);
    QCoreApplication::sendEvent(window, &release_event);
    return self && window && serial_ == id && request_ == original;
}
bool AssistantWidgetInput::selectAll() {
    const auto bindings = QKeySequence::keyBindings(QKeySequence::SelectAll);
    if (bindings.isEmpty()) return false;
    const auto combination = bindings.front()[0];
    return key(combination.key(), combination.keyboardModifiers());
}
void AssistantWidgetInput::advance() noexcept {
    const auto id = serial_;
    const auto request = request_; // Strong original callback/target scope for this tick.
    const QPointer<AssistantWidgetInput> self(this);
    try {
        const bool valid = current(id);
        if (!self) return;
        if (!valid || !request || !request->target || !visibleCenter(*request->target, center_)) { if (serial_ == id && request_ == request) stop(false, tr("Visible action target changed or is unavailable"), true); return; }
        if ((step_ == Step::Move || step_ == Step::Press) && manualDraftPresent()) {
            stop(false, interrupted_, false); return;
        }
        switch (step_) {
        case Step::Move:
            emit pointerMoved(center_);
            if (!self) return;
            { const bool valid = self->current(id); if (!self) return;
              if (!valid) { if (serial_ == id && request_ == request) stop(false, tr("Visible action ownership changed"), true); return; } }
            step_ = Step::Press; timer_.start(move_ms); return;
        case Step::Press:
            if (!mouse(QEvent::MouseMove, Qt::NoButton)) { if (self && serial_ == id && request_ == request) stop(false, tr("The target did not receive pointer movement"), false); return; }
            if (!self) return;
            { const bool valid = self->current(id); if (!self) return;
              if (!valid) { if (serial_ == id && request_ == request) stop(false, tr("Visible action ownership changed"), true); return; } }
            emit pointerPressed();
            if (!self) return;
            { const bool valid = self->current(id); if (!self) return;
              if (!valid) { if (serial_ == id && request_ == request) stop(false, tr("Visible action ownership changed"), true); return; } }
            pressed_ = true; // Own a balancing release even if the press reenters retirement.
            if (!mouse(QEvent::MouseButtonPress, Qt::LeftButton)) { if (self && serial_ == id && request_ == request) stop(false, tr("The real control did not receive its press"), true); return; }
            if (!self || serial_ != id || request_ != request) return;
            step_ = Step::Release; timer_.start(press_ms); return;
        case Step::Release:
            if (request->kind != Kind::Value) {
                commit_prepared_ = true; // Exact finish is owed even if preparation reenters/cancels.
                if (!request->prepareCommit()) { if (self && serial_ == id && request_ == request) stop(false, tr("The native input could not be prepared"), false); return; }
                if (!self) return;
            { const bool valid = self->current(id); if (!self) return;
              if (!valid) { if (serial_ == id && request_ == request) stop(false, tr("Visible action ownership changed"), true); return; } }
            }
            pressed_ = false;
            if (!mouse(QEvent::MouseButtonRelease, Qt::LeftButton)) { if (self && serial_ == id && request_ == request) stop(false, tr("The real control did not receive its release"), true); return; }
            if (!self || serial_ != id || request_ != request) return;
            if (request_->kind != Kind::Value) { stop(true, {}, false); return; }
            step_ = Step::Select; timer_.start(click_relaxation_ms); return;
        case Step::Select:
            if (!QMetaObject::invokeMethod(request->target, "beginAssistantEdit", Qt::DirectConnection)) { stop(false, tr("The numeric control has no safe draft owner"), true); return; }
            if (!self || serial_ != id || request_ != request) return;
            draft_ = true;
            if (!selectAll()) { if (self && serial_ == id && request_ == request) stop(false, tr("The numeric input did not acquire focus"), true); return; }
            if (!self || serial_ != id || request_ != request) return;
            step_ = Step::Delete; timer_.start(character_ms); return;
        case Step::Delete:
            draft_ = true; // Own cancellation restoration before the first destructive key.
            if (!key(Qt::Key_Backspace)) { if (self && serial_ == id && request_ == request) stop(false, tr("The numeric input changed focus"), true); return; }
            if (!self || serial_ != id || request_ != request) return;
            step_ = Step::Type; timer_.start(character_ms); return;
        case Step::Type:
            if (character_ < request_->value.size()) {
                const QString character = request_->value.mid(character_++, 1);
                if (!key(0, Qt::NoModifier, character)) { if (self && serial_ == id && request_ == request) stop(false, tr("The numeric input changed focus"), true); return; }
                if (!self || serial_ != id || request_ != request) return;
                timer_.start(character_ms); return;
            }
            step_ = Step::Commit; timer_.start(0); return;
        case Step::Commit:
            commit_prepared_ = true;
            if (!request->prepareCommit()) { if (self && serial_ == id && request_ == request) stop(false, tr("The recorded native input could not be prepared"), true); return; }
            if (!self) return;
            { const bool valid = self->current(id); if (!self) return;
              if (!valid) { if (serial_ == id && request_ == request) stop(false, tr("Visible action ownership changed"), true); return; } }
            if (!QMetaObject::invokeMethod(request->target, "allowAssistantCommit", Qt::DirectConnection)) { stop(false, tr("The numeric control could not admit its final key"), true); return; }
            if (!self || serial_ != id || request_ != request) return;
            if (!key(Qt::Key_Return)) { if (self && serial_ == id && request_ == request) stop(false, tr("The numeric input commit was not confirmed"), true); return; }
            if (self && serial_ == id && request_ == request) { draft_ = false; stop(true, {}, false); }
            return;
        }
    } catch (...) { if (self && serial_ == id && request_ == request) stop(false, failed_, true); }
}
void AssistantWidgetInput::restoreDraft() noexcept {
    if (!draft_ || !request_ || !request_->target) return;
    const QPointer<AssistantWidgetInput> self(this);
    const auto request = request_;
    try {
        if (!request->restoreCurrent || !request->restoreCurrent() || !self || request_ != request || !request->target) return;
        // Real ParameterField/ParameterCell own this view-only cancel door. It
        // restores the CURRENT committed binding, without a scientific write,
        // stale-number rollback or partial text left for editingFinished.
        QMetaObject::invokeMethod(request->target, "cancelAssistantEdit", Qt::DirectConnection);
        if (self && request_ == request) draft_ = false;
    } catch (...) {}
}
void AssistantWidgetInput::stop(bool delivered, const QString& diagnostic, bool restore) noexcept {
    if (!request_) return;
    const QPointer<AssistantWidgetInput> self(this);
    const auto id = serial_;
    const auto original = request_;
    try { timer_.stop(); } catch (...) { delivered = false; }
    if (pressed_) {
        // Cancel a real grab with an outside release, never a successful click.
        pressed_ = false;
        center_ = QPointF(-1, -1);
        try { (void)mouse(QEvent::MouseButtonRelease, Qt::LeftButton); }
        catch (...) { delivered = false; } // Still owe draft/editor/completion cleanup.
    }
    if (!self || request_ != original || serial_ != id) return;
    if (restore) restoreDraft();
    if (!self || request_ != original || serial_ != id) return;
    request_.reset();
    const bool prepared = commit_prepared_; commit_prepared_ = false; draft_ = false; original_text_.clear();
    if (prepared) try { original->finishCommit(); } catch (...) { delivered = false; }
    if (!self) return;
    if (serial_ == id && !request_) {
        try { emit pointerHidden(); } catch (...) { delivered = false; }
        if (!self) return;
        if (serial_ == id && !request_) try { emit activeChanged(false); } catch (...) { delivered = false; }
    }
    if (!self) return;
    // Never alter a replacement's UI. The old completion still carries only
    // its original native record; its adapter must independently fence that ID.
    try { original->completed(delivered, diagnostic); } catch (...) {}
}
void AssistantWidgetInput::cancel() { stop(false, interrupted_, true); }
bool AssistantWidgetInput::eventFilter(QObject* watched, QEvent* event) {
    if (watched == window_ && request_ && !injecting_) {
        switch (event->type()) {
        case QEvent::MouseButtonPress: case QEvent::MouseButtonRelease: case QEvent::MouseMove:
        case QEvent::Wheel: case QEvent::KeyPress: case QEvent::ShortcutOverride: case QEvent::TouchBegin: {
            const QPointer<AssistantWidgetInput> self(this);
            const auto original = request_; const auto id = serial_;
            try { emit manualInput(); } catch (...) {}
            // A synchronous observer may have retired/replaced the old input.
            if (self && request_ == original && serial_ == id) cancel();
            break; // Keep manual controls exposed and yield the very same event.
        }
        case QEvent::WindowDeactivate: case QEvent::Hide: case QEvent::Close:
            cancel(); break;
        default: break;
        }
    }
    return false;
}
}
