// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_widget_input.hpp"
#include "edi/assistant_limits.hpp"
#include <QCoreApplication>
#include <QEvent>
#include <QKeyEvent>
#include <QKeySequence>
#include <QMouseEvent>
#include <QWheelEvent>
#include <QPointingDevice>
#include <QElapsedTimer>
#include <array>
#include <algorithm>
#include <QScopeGuard>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace edi_app {
namespace {
// Actual matched RemotePointer/RemoteController prior art, not blocking waits.
constexpr int move_ms = 500, press_ms = 100, click_relaxation_ms = 500, character_ms = 100;
}
// One exact device/filter for the application lifetime, including old-window clones.
// Qt's delayed press clone retains device()/timestamp(); no event pointer map,
// clock grace period, private Qt API or platform-wide input exemption is used.
struct AssistantWidgetInput::MouseOwnership final : QObject {
    static qint64 deviceId() {
        static qint64 next = -1; // Construction is confined to the GUI thread.
        if (next == std::numeric_limits<qint64>::min()) throw std::runtime_error("Visible mouse identity exhausted");
        return next--;
    }
    explicit MouseOwnership(QCoreApplication& application)
        : QObject(&application), device(QStringLiteral("EDI assistant input"), deviceId(),
          QInputDevice::DeviceType::Mouse, QPointingDevice::PointerType::Generic,
          QInputDevice::Capability::Position, 1, 3) { application.installEventFilter(this); }
    bool recognizes(const QEvent* event) const noexcept {
        switch (event->type()) {
        case QEvent::MouseMove: case QEvent::MouseButtonPress: case QEvent::MouseButtonRelease: case QEvent::MouseButtonDblClick:
            return static_cast<const QMouseEvent*>(event)->pointingDevice() == &device;
        case QEvent::Wheel: return static_cast<const QWheelEvent*>(event)->pointingDevice() == &device;
        default: return false;
        }
    }
    quint64 begin(AssistantWidgetInput& input) {
        if (cleanup_pending || held || (owner && owner != &input && owner->request_) || sequence == std::numeric_limits<quint64>::max())
            throw std::runtime_error("Visible mouse input owner is unavailable");
        owner = &input; window = input.window_; accepting = true; stamps.fill(0);
        return ++sequence;
    }
    static int eventIndex(QEvent::Type type) noexcept {
        switch (type) {
        case QEvent::MouseMove: return 0;
        case QEvent::MouseButtonPress: return 1;
        case QEvent::MouseButtonRelease: return 2;
        case QEvent::Wheel: return 3;
        default: return -1;
        }
    }
    quint64 eventStamp(QEvent::Type type) {
        const int index = eventIndex(type);
        if (index < 0 || last_event_stamp == std::numeric_limits<quint64>::max())
            throw std::runtime_error("Visible mouse event identity exhausted");
        QElapsedTimer clock; clock.start();
        const auto tick = clock.msecsSinceReference();
        last_event_stamp = std::max(last_event_stamp + 1, tick > 0 ? static_cast<quint64>(tick) : quint64(1));
        stamps[static_cast<std::size_t>(index)] = last_event_stamp;
        if (type == QEvent::MouseButtonPress) held = true;
        return last_event_stamp;
    }
    bool heldBy(AssistantWidgetInput& input, quint64 stamp) const noexcept {
        return owner == &input && sequence == stamp && held;
    }
    void releaseFinished(AssistantWidgetInput& input, quint64 stamp) noexcept {
        if (owner == &input && sequence == stamp) held = false;
    }
    void retire(AssistantWidgetInput& input, quint64 stamp) noexcept {
        if (owner == &input && sequence == stamp) accepting = false;
    }
    void deferHeldCleanup(quint64 stamp) noexcept {
        if (sequence != stamp || cleanup_pending) return;
        cleanup_pending = stamp; accepting = false;
        try {
            QTimer::singleShot(0, this, [this, stamp] {
                if (cleanup_pending != stamp || sequence != stamp) return;
                const QPointer<MouseOwnership> self(this);
                const QPointer<QQuickWindow> target(window);
                bool released = false;
                try {
                    cleanup_delivery = eventStamp(QEvent::MouseButtonRelease);
                    QMouseEvent release(QEvent::MouseButtonRelease, QPointF(-1, -1),
                        target ? target->mapToGlobal(QPointF(-1, -1)) : QPointF(-1, -1),
                        Qt::LeftButton, Qt::NoButton, Qt::NoModifier, &device);
                    release.setTimestamp(cleanup_delivery);
                    if (target) QCoreApplication::sendEvent(target, &release);
                    else {
                        // No old window exists to receive a balancing release.
                        // Public device-point ungrab also clears a delayed
                        // Flickable grab if its item moved to another window.
                        release.setExclusivePointGrabber(nullptr);
                        if (!self) return;
                        release.clearPassiveGrabbers(release.point(0));
                    }
                    released = true;
                } catch (...) {} // Retain the authority fence; never send an old click.
                if (self && sequence == stamp && cleanup_pending == stamp) {
                    cleanup_delivery = 0;
                    if (released) { cleanup_pending = 0; held = false; }
                }
            });
        } catch (...) {} // No queued cleanup: begin remains fenced until window retirement.
    }
    bool rejectDelivery(QObject* watched, QEvent::Type type, quint64 timestamp, const QPointF& scene) const noexcept {
        const QPointer<QObject> receiver(watched);
        const auto receiverWindow = [&]() -> QQuickWindow* {
            if (auto* item = qobject_cast<QQuickItem*>(receiver.data())) return item->window();
            return qobject_cast<QQuickWindow*>(receiver.data());
        };
        auto* delivered_window = receiverWindow();
        if (!delivered_window || delivered_window != window) return true;
        const bool outside_release = type == QEvent::MouseButtonRelease && scene == QPointF(-1, -1);
        if (cleanup_delivery && timestamp == cleanup_delivery && outside_release) return false;
        const auto input = owner;
        const QPointer<const MouseOwnership> self(this);
        const auto stamp = sequence;
        const int index = eventIndex(type);
        if (!input || input->window_ != window || input->mouse_stamp_ != stamp || index < 0 ||
            !stamps[static_cast<std::size_t>(index)] || timestamp != stamps[static_cast<std::size_t>(index)]) return true;
        // Qt localizes item position; stable scene coordinates identify the
        // original balancing release throughout its real delivery chain.
        if (input->injecting_ && input->cleanup_release_ && outside_release) return false;
        if (!accepting || !input->request_) return true;
        const auto serial = input->serial_;
        bool current = false;
        try { current = input->current(serial); } catch (...) {}
        return !self || !input || !receiver || !current || owner != input || sequence != stamp || !accepting ||
            receiverWindow() != window || input->window_ != window || input->mouse_stamp_ != stamp || input->serial_ != serial || !input->request_;
    }
    bool reject(QObject* watched, const QEvent* event) const noexcept {
        if (!recognizes(event)) return false;
        // A window check cannot authorize a later item recipient after a
        // synchronous retirement/replacement. Recheck at every real receiver.
        const auto* input = static_cast<const QInputEvent*>(event);
        const auto scene = event->type() == QEvent::Wheel ? static_cast<const QWheelEvent*>(event)->position()
            : static_cast<const QMouseEvent*>(event)->scenePosition();
        return rejectDelivery(watched, event->type(), input->timestamp(), scene);
    }
    bool rejectPoint(QObject* receiver, const QEventPoint& point) const noexcept {
        // The actual handler supplies its grab/release point before action.
        // No event is fabricated/redelivered. Foreign devices never enter this
        // private predicate; unknown/late own points fail closed.
        const auto type = point.state() == QEventPoint::State::Pressed ? QEvent::MouseButtonPress
            : point.state() == QEventPoint::State::Released ? QEvent::MouseButtonRelease : QEvent::None;
        return type == QEvent::None || rejectDelivery(receiver, type, point.timestamp(), point.scenePosition());
    }
    bool eventFilter(QObject* watched, QEvent* event) override {
        return reject(watched, event); // Stale private input is consumed, never manual.
    }
    QPointer<QQuickWindow> window;
    QPointingDevice device;
    QPointer<AssistantWidgetInput> owner;
    quint64 sequence = 0, cleanup_pending = 0, cleanup_delivery = 0, last_event_stamp = 0;
    std::array<quint64, 4> stamps{};
    bool accepting = false, held = false;
};
bool AssistantWidgetInput::ownMouseEvent(const QEvent* event) const noexcept {
    return mouse_owner_ && mouse_owner_->recognizes(event);
}
bool AssistantWidgetInput::rejectOwnEvent(QObject* receiver, QEvent* event) const noexcept {
    const QPointer<MouseOwnership> retained(mouse_owner_);
    return !retained || retained->reject(receiver, event);
}
std::optional<bool> AssistantWidgetInput::rejectOwnedPoint(QObject* receiver, const QEventPoint& point) noexcept {
    if (auto* application = QCoreApplication::instance()) {
        // Same application-lifetime owner discovery as helper construction.
        // It survives helper/window teardown to consume their late points.
        for (auto* child : application->children()) {
            if (auto* retained = dynamic_cast<MouseOwnership*>(child); retained && point.device() == &retained->device)
                return retained->rejectPoint(receiver, point);
        }
    }
    return std::nullopt;
}
AssistantWidgetInput::AssistantWidgetInput(QQuickWindow& window, QObject* parent)
    : QObject(parent), window_(&window) {
    auto* application = QCoreApplication::instance();
    if (!application) throw std::runtime_error("The application input owner is unavailable");
    for (auto* child : application->children())
        if (auto* retained = dynamic_cast<MouseOwnership*>(child)) { mouse_owner_ = retained; break; }
    if (!mouse_owner_) mouse_owner_ = new MouseOwnership(*application);
    timer_.setSingleShot(true);
    connect(&timer_, &QTimer::timeout, this, &AssistantWidgetInput::advance);
    // Cocoa/IBus can send text events straight to the current focus object.
    // The existing filter observes application delivery, scoped below to this
    // exact owned window or its actual current text-event receiver.
    application->installEventFilter(this);
}
AssistantWidgetInput::~AssistantWidgetInput() {
    if (auto* application = QCoreApplication::instance()) application->removeEventFilter(this);
    timer_.stop();
    if (mouse_owner_) {
        mouse_owner_->retire(*this, mouse_stamp_);
        if (pressed_ || mouse_owner_->heldBy(*this, mouse_stamp_)) mouse_owner_->deferHeldCleanup(mouse_stamp_);
    }
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
bool AssistantWidgetInput::visibleCenter(QQuickItem& item, QPointF& center, bool scrollGutter) const {
    if (!window_ || item.window() != window_ || !window_->isVisible() || item.width() <= 0 || item.height() <= 0) return false;
    center = item.mapToScene(QPointF(scrollGutter ? std::min(1.0, item.width() / 2) : item.width() / 2, item.height() / 2));
    if (!std::isfinite(center.x()) || !std::isfinite(center.y()) || !QRectF(0, 0, window_->width(), window_->height()).contains(center)) return false;
    for (auto* ancestor = &item; ancestor; ancestor = ancestor->parentItem()) {
        if (!ancestor->isVisible() || !ancestor->isEnabled() || ancestor->opacity() <= 0) return false;
        if (ancestor->clip() && !ancestor->clipRect().contains(ancestor->mapFromScene(center))) return false;
    }
    return true;
}
bool AssistantWidgetInput::usableTarget(QQuickItem& item) const {
    QPointF center;
    return visibleCenter(item, center);
}
bool AssistantWidgetInput::manualDraftPresent() const {
    if (!window_) return false;
    // TextInput may be a visual child of an app-owned editor. The common
    // value/text editors expose their exact pre-commit display comparison;
    // parameter editors retain their existing assistant-owned draft rules.
    for (auto* item = window_->activeFocusItem(); item; item = item->parentItem()) {
        const auto manual = item->property("assistantManualDraft");
        if (manual.isValid()) return manual.toBool();
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
    if (!request.current() || !visibleCenter(*request.target, center, request.kind == Kind::Scroll))
        throw std::runtime_error("The genuine input control is not visible and current");
    const qsizetype text_limit = request.kind == Kind::StagedText
        ? static_cast<qsizetype>(edi::assistant::Limits::context_bytes) : 256;
    if ((request.kind == Kind::Value || request.kind == Kind::ParameterFilter || request.kind == Kind::StagedText) &&
        (request.value.isEmpty() || request.value.size() > text_limit))
        throw std::runtime_error("The numeric input spelling is unavailable");
    // Applies to navigation/free/fit too: their click can commit an unrelated
    // pre-existing manual draft through ordinary focus loss.
    if (manualDraftPresent()) throw std::runtime_error("Finish the current manual input first");
    if (request.kind == Kind::Scroll && request.scrollDirection != 1 && request.scrollDirection != -1)
        throw std::runtime_error("The bounded viewport scroll is unavailable");
    original_text_ = (request.kind == Kind::Value || request.kind == Kind::StagedText) ? request.target->property("editText").toString() : QString{};
    if (original_text_.size() > text_limit) throw std::runtime_error("The original numeric draft exceeds the visible input bound");
    if (request.kind == Kind::Choose && (request.option < 0 || request.option >= request.target->property("count").toInt() ||
        request.target->property("count").toInt() > static_cast<int>(edi::assistant::Limits::stream_items)))
        throw std::runtime_error("The actual ComboBox option is unavailable");
    auto prepared = std::make_shared<Request>(std::move(request)); // All job/callback allocation precedes visibility.
    if (!mouse_owner_) throw std::runtime_error("The visible mouse window is unavailable");
    mouse_stamp_ = mouse_owner_->begin(*this);
    request_ = std::move(prepared);
    const auto original = request_;
    const auto id = ++serial_;
    choice_popup_.clear(); option_step_ = 0;
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
    if (!window_ || !request_ || !mouse_owner_) return false;
    const QPointer<AssistantWidgetInput> self(this);
    const QPointer<QQuickWindow> window(window_);
    const auto original = request_; const auto id = serial_;
    const auto original_stamp = mouse_stamp_;
    const bool old = injecting_; injecting_ = true;
    const auto release = qScopeGuard([self, old] { if (self) self->injecting_ = old; });
    const auto buttons = type == QEvent::MouseButtonRelease ? Qt::NoButton : button;
    QMouseEvent event(type, center_, window->mapToGlobal(center_), button, buttons, Qt::NoModifier, &mouse_owner_->device);
    event.setTimestamp(mouse_owner_->eventStamp(type));
    QCoreApplication::sendEvent(window, &event);
    if (self && mouse_owner_ && type == QEvent::MouseButtonRelease) mouse_owner_->releaseFinished(*this, original_stamp);
    return self && window && serial_ == id && request_ == original;
}
bool AssistantWidgetInput::scroll() {
    if (!window_ || !request_ || !mouse_owner_ || !request_->scrollDirection) return false;
    const QPointer<AssistantWidgetInput> self(this);
    const QPointer<QQuickWindow> window(window_);
    const auto original = request_; const auto id = serial_;
    const bool old = injecting_; injecting_ = true;
    const auto release = qScopeGuard([self, old] { if (self) self->injecting_ = old; });
    QWheelEvent event(center_, window->mapToGlobal(center_), QPoint(),
        QPoint(0, 120 * original->scrollDirection), Qt::NoButton, Qt::NoModifier, Qt::NoScrollPhase, false,
        Qt::MouseEventNotSynthesized, &mouse_owner_->device);
    event.setTimestamp(mouse_owner_->eventStamp(QEvent::Wheel));
    QCoreApplication::sendEvent(window, &event);
    return self && window && serial_ == id && request_ == original;
}
bool AssistantWidgetInput::choiceKeyboardOwned() const {
    if (!window_ || !request_ || !request_->target) return false;
    if (request_->target->hasActiveFocus()) return true;
    if (request_->kind != Kind::Choose || !choice_popup_ || !choice_popup_->property("visible").toBool()) return false;
    const auto* content = choice_popup_->property("contentItem").value<QQuickItem*>();
    for (auto* item = window_->activeFocusItem(); item; item = item->parentItem()) if (item == content) return content->window() == window_;
    return false;
}
bool AssistantWidgetInput::key(int code, Qt::KeyboardModifiers modifiers, const QString& text) {
    if (!window_ || !request_ || !request_->target || !choiceKeyboardOwned()) return false;
    const QPointer<AssistantWidgetInput> self(this);
    const QPointer<QQuickWindow> window(window_);
    const auto original = request_; const auto id = serial_;
    const bool old = injecting_; injecting_ = true;
    const auto release = qScopeGuard([self, old] { if (self) self->injecting_ = old; });
    // Accepted numeric controls deliberately drop focus. Only the prepared
    // final Return permits that transition; ordinary typing stays focus-bound.
    const bool terminal = code == Qt::Key_Return && commit_prepared_ &&
        ((step_ == Step::Commit && (original->kind == Kind::Value || original->kind == Kind::ParameterFilter || original->kind == Kind::StagedText)) ||
         (step_ == Step::ChooseCommit && original->kind == Kind::Choose));
    const QPointer<QQuickItem> target(original->target);
    if (terminal && target->window() != window) return false;
    QKeyEvent press(QEvent::KeyPress, code, modifiers, text);
    QCoreApplication::sendEvent(window, &press);
    if (!self || !window || serial_ != id || request_ != original || !request_->target) return false;
    if (terminal) {
        if (!target || request_->target != target || window_ != window || target->window() != window) return false;
    } else if (!choiceKeyboardOwned()) return false;
    QKeyEvent release_event(QEvent::KeyRelease, code, modifiers, text);
    // Never route an accepted Return's release into a newly focused editor.
    // The same original surviving item receives its real balancing key event.
    QCoreApplication::sendEvent(terminal ? static_cast<QObject*>(target.data()) : static_cast<QObject*>(window.data()), &release_event);
    return self && window && serial_ == id && request_ == original &&
        (!terminal || (target && request_->target == target && window_ == window && target->window() == window));
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
        if (!valid || !request || !request->target || !visibleCenter(*request->target, center_, request->kind == Kind::Scroll)) { if (serial_ == id && request_ == request) stop(false, tr("Visible action target changed or is unavailable"), true); return; }
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
            if (request->kind == Kind::Scroll) {
                // Wheel movement changes only the actual existing viewport; it
                // never focuses/blurs an editor or synthesizes a button click.
                if (!scroll()) { if (self && serial_ == id && request_ == request) stop(false, tr("The viewport did not receive its wheel input"), false); return; }
                if (self && serial_ == id && request_ == request) stop(true, {}, false);
                return;
            }
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
            if (request->kind != Kind::Value && request->kind != Kind::ParameterFilter && request->kind != Kind::StagedText && request->kind != Kind::Choose) {
                commit_prepared_ = true; // Exact finish is owed even if preparation reenters/cancels.
                if (!request->prepareCommit()) { if (self && serial_ == id && request_ == request) stop(false, tr("The native input could not be prepared"), false); return; }
                if (!self) return;
            { const bool valid = self->current(id); if (!self) return;
              if (!valid) { if (serial_ == id && request_ == request) stop(false, tr("Visible action ownership changed"), true); return; } }
            }
            pressed_ = false;
            if (!mouse(QEvent::MouseButtonRelease, Qt::LeftButton)) { if (self && serial_ == id && request_ == request) stop(false, tr("The real control did not receive its release"), true); return; }
            if (!self || serial_ != id || request_ != request) return;
            if (request_->kind == Kind::Choose) {
                choice_popup_ = request_->target->property("popup").value<QObject*>();
                if (!choice_popup_ || !choice_popup_->property("visible").toBool()) { stop(false, tr("The genuine ComboBox popup did not open"), false); return; }
                step_ = Step::ChooseHome; timer_.start(click_relaxation_ms); return;
            }
            if (request_->kind != Kind::Value && request_->kind != Kind::ParameterFilter && request_->kind != Kind::StagedText && request_->kind != Kind::Choose) { stop(true, {}, false); return; }
            step_ = Step::Select; timer_.start(click_relaxation_ms); return;
        case Step::ChooseHome:
            if (!key(Qt::Key_Home)) { if (self && serial_ == id && request_ == request) stop(false, tr("The original ComboBox lost keyboard ownership"), false); return; }
            if (self && serial_ == id && request_ == request) { step_ = Step::ChooseDown; timer_.start(character_ms); }
            return;
        case Step::ChooseDown:
            if (option_step_ < request->option) {
                if (!key(Qt::Key_Down)) { if (self && serial_ == id && request_ == request) stop(false, tr("The original ComboBox lost keyboard ownership"), false); return; }
                if (self && serial_ == id && request_ == request) { ++option_step_; timer_.start(character_ms); }
                return;
            }
            step_ = Step::ChooseCommit; timer_.start(0); return;
        case Step::ChooseCommit:
            commit_prepared_ = true;
            if (!request->prepareCommit()) { if (self && serial_ == id && request_ == request) stop(false, tr("The original ComboBox choice was retired"), false); return; }
            if (!self || serial_ != id || request_ != request) return;
            if (!current(id) || !key(Qt::Key_Return)) { if (self && serial_ == id && request_ == request) stop(false, tr("The actual ComboBox choice could not be delivered"), false); return; }
            if (self && serial_ == id && request_ == request)
                stop(request->target && request->target->property("currentIndex").toInt() == request->option, {}, false);
            return;
        case Step::Select:
            if ((request->kind == Kind::Value || request->kind == Kind::StagedText) && !QMetaObject::invokeMethod(request->target, "beginAssistantEdit", Qt::DirectConnection)) { stop(false, tr("The numeric control has no safe draft owner"), true); return; }
            if (!self || serial_ != id || request_ != request) return;
            draft_ = request->kind == Kind::Value || request->kind == Kind::StagedText;
            if (!selectAll()) { if (self && serial_ == id && request_ == request) stop(false, tr("The numeric input did not acquire focus"), true); return; }
            if (!self || serial_ != id || request_ != request) return;
            step_ = Step::Delete; timer_.start(character_ms); return;
        case Step::Delete:
            // A filter's text is immediate presentation state, not a deferred
            // scientific edit. Never restore/reflow it before a manual event.
            draft_ = request->kind == Kind::Value || request->kind == Kind::StagedText;
            if (!key(Qt::Key_Backspace)) { if (self && serial_ == id && request_ == request) stop(false, tr("The numeric input changed focus"), true); return; }
            if (!self || serial_ != id || request_ != request) return;
            step_ = Step::Type; timer_.start(character_ms); return;
        case Step::Type:
            if (character_ < request_->value.size()) {
                const auto width = request_->value.at(character_).isHighSurrogate() &&
                    character_ + 1 < request_->value.size() && request_->value.at(character_ + 1).isLowSurrogate() ? 2 : 1;
                const QString character = request_->value.mid(character_, width); character_ += width;
                const int code = request->kind == Kind::StagedText && character == QStringLiteral("\n") ? Qt::Key_Return :
                    request->kind == Kind::StagedText && character == QStringLiteral("\t") ? Qt::Key_Tab : 0;
                if (!key(code, Qt::NoModifier, character)) { if (self && serial_ == id && request_ == request) stop(false, tr("The numeric input changed focus"), true); return; }
                if (!self || serial_ != id || request_ != request) return;
                emit inputProgress();
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
            if ((request->kind == Kind::Value || request->kind == Kind::StagedText) && !QMetaObject::invokeMethod(request->target, "allowAssistantCommit", Qt::DirectConnection)) { stop(false, tr("The numeric control could not admit its final key"), true); return; }
            if (!self || serial_ != id || request_ != request) return;
            // Staged fields publish presentation text on each real key. They
            // have no scientific blur/Return commit; an extra Return would
            // append a newline to a genuine multiline expression. Only Apply
            // below owns the prearmed scientific batch.
            if (request->kind != Kind::StagedText && !key(Qt::Key_Return)) { if (self && serial_ == id && request_ == request) stop(false, tr("The numeric input commit was not confirmed"), true); return; }
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
    if (mouse_owner_) mouse_owner_->retire(*this, mouse_stamp_);
    if (pressed_ || (mouse_owner_ && mouse_owner_->heldBy(*this, mouse_stamp_))) {
        // Retire first; balancing release must not replay an old delayed press.
        pressed_ = false;
        center_ = QPointF(-1, -1);
        cleanup_release_ = true;
        const auto release_cleanup = qScopeGuard([self] { if (self) self->cleanup_release_ = false; });
        try { (void)mouse(QEvent::MouseButtonRelease, Qt::LeftButton); }
        catch (...) {
            delivered = false;
            if (self && mouse_owner_) mouse_owner_->deferHeldCleanup(mouse_stamp_);
        } // Still owe draft/editor/completion cleanup.
    }
    if (!self || request_ != original || serial_ != id) return;
    if (restore) restoreDraft();
    if (!self || request_ != original || serial_ != id) return;
    request_.reset();
    const bool prepared = commit_prepared_; commit_prepared_ = false; draft_ = false; original_text_.clear(); choice_popup_.clear();
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
    // The retained application filter separately consumes stale own events, even
    // when this helper is inactive/replaced. Genuine devices remain manual.
    if (ownMouseEvent(event)) return rejectOwnEvent(watched, event);
    const bool owned_window = watched == window_;
    const bool focus_text = window_ && watched == window_->focusObject() &&
        (event->type() == QEvent::InputMethod || event->type() == QEvent::KeyPress ||
         event->type() == QEvent::KeyRelease || event->type() == QEvent::ShortcutOverride);
    if ((owned_window || focus_text) && request_ && !injecting_) {
        switch (event->type()) {
        case QEvent::MouseButtonPress: case QEvent::MouseButtonRelease: case QEvent::MouseMove:
        case QEvent::Wheel: case QEvent::KeyPress: case QEvent::KeyRelease: case QEvent::ShortcutOverride: case QEvent::TouchBegin: case QEvent::InputMethod: {
            const QPointer<QObject> original_target(watched);
            const QPointer<AssistantWidgetInput> self(this);
            const auto original = request_; const auto id = serial_;
            try { emit manualInput(); } catch (...) {}
            // A synchronous observer may have retired/replaced the old input.
            if (self && request_ == original && serial_ == id) cancel();
            // Never redeliver to a deleted receiver. A surviving original
            // receiver receives this same event only after exact cleanup.
            return !original_target;
        }
        case QEvent::WindowDeactivate: case QEvent::Hide: case QEvent::Close: {
            const QPointer<QObject> original_target(watched);
            cancel(); return !original_target;
        }
        default: break;
        }
    }
    return false;
}
}
