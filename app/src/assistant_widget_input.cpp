// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_widget_input.hpp"
#include "edi/assistant_limits.hpp"
#include <QCoreApplication>
#include <QEvent>
#include <QKeyEvent>
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
constexpr int move_ms = 500, press_ms = 100, click_relaxation_ms = 500, navigation_ms = 100;
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
        const auto original_button = held_button;
        try {
            QTimer::singleShot(0, this, [this, stamp, original_button] {
                if (cleanup_pending != stamp || sequence != stamp) return;
                const QPointer<MouseOwnership> self(this);
                const QPointer<QQuickWindow> target(window);
                bool released = false;
                try {
                    cleanup_delivery = eventStamp(QEvent::MouseButtonRelease);
                    QMouseEvent release(QEvent::MouseButtonRelease, QPointF(-1, -1),
                        target ? target->mapToGlobal(QPointF(-1, -1)) : QPointF(-1, -1),
                        original_button, Qt::NoButton, Qt::NoModifier, &device);
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
    Qt::MouseButton held_button = Qt::LeftButton;
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
void AssistantWidgetInput::pace(int milliseconds) {
    timer_.start(milliseconds); // Original pointer/choice pacing; text has no character clock.
}
AssistantWidgetInput::~AssistantWidgetInput() {
    unwatchChoicePopup();
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
    if(!self || !valid || serial_!=id || request_!=request || !window_ || !request->target)return false;
    if((step_==Step::ChoicePress || step_==Step::ChoiceRelease) && !choice_releasing_ && !choiceRowOwned())return false;
    if((step_==Step::SearchPress || step_==Step::SearchRelease || (step_==Step::Select && request->kind==Kind::SearchChoice)) && !searchEditorOwned())return false;
    return self && (!draft_ || commit_prepared_ || request->target->property("assistantEditing").toBool());
}
bool AssistantWidgetInput::visibleCenter(QQuickItem& item, QPointF& center, bool scrollGutter, bool allowDisabledTarget) const {
    if (!window_ || item.window() != window_ || !window_->isVisible() || item.width() <= 0 || item.height() <= 0) return false;
    QPointF localCenter(scrollGutter ? std::min(1.0, item.width() / 2) : item.width() / 2, item.height() / 2);
    if (!scrollGutter && item.inherits("QQuickTextField")) {
        // FIRST TextField's editable background uses its actual insets. A
        // ParamTextField's title occupies topInset, not the editable box.
        // Read the final scalar properties, not the deferred background item.
        bool leftOk = false, topOk = false, rightOk = false, bottomOk = false;
        const auto left = item.property("leftInset").toDouble(&leftOk);
        const auto top = item.property("topInset").toDouble(&topOk);
        const auto right = item.property("rightInset").toDouble(&rightOk);
        const auto bottom = item.property("bottomInset").toDouble(&bottomOk);
        if (!leftOk || !topOk || !rightOk || !bottomOk || !std::isfinite(left) || !std::isfinite(top) ||
            !std::isfinite(right) || !std::isfinite(bottom)) return false;
        const QRectF box(left, top, item.width() - left - right, item.height() - top - bottom);
        if (!std::isfinite(box.width()) || !std::isfinite(box.height()) || box.width() <= 0 || box.height() <= 0) return false;
        localCenter = box.center();
    }
    if(item.inherits("QQuickTextEdit")) {
        // A multiline editor can grow beyond its unchanged ScrollView. Its
        // actual clipped editor area remains the genuine pointer target.
        auto exposed=item.mapRectToScene(QRectF(0,0,item.width(),item.height()));
        exposed=exposed.intersected(QRectF(0,0,window_->width(),window_->height()));
        for(auto* ancestor=&item;ancestor;ancestor=ancestor->parentItem())
            if(ancestor->clip())exposed=exposed.intersected(ancestor->mapRectToScene(ancestor->clipRect()));
        if(exposed.isEmpty())return false;
        localCenter=item.mapFromScene(exposed.center());
    }
    center = item.mapToScene(localCenter);
    if (!std::isfinite(center.x()) || !std::isfinite(center.y()) || !QRectF(0, 0, window_->width(), window_->height()).contains(center)) return false;
    for (auto* ancestor = &item; ancestor; ancestor = ancestor->parentItem()) {
        if (!ancestor->isVisible() || (!ancestor->isEnabled() && !(allowDisabledTarget && ancestor==&item)) || ancestor->opacity() <= 0) return false;
        if (ancestor->clip() && !ancestor->clipRect().contains(ancestor->mapFromScene(center))) return false;
    }
    return true;
}
bool AssistantWidgetInput::usableTarget(QQuickItem& item, bool visualOnlySave) const {
    QPointF center;
    if(visualOnlySave && item.objectName()!=QStringLiteral("appBar.button.save"))return false;
    return visibleCenter(item, center, false, visualOnlySave);
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
        throw ControlInputRefusal(ControlCause::Unavailable,"A visible input owner is unavailable");
    if(request.visualOnlyDisabledTarget && (request.kind!=Kind::FileLoadCue || request.target->objectName()!=QStringLiteral("appBar.button.save")))
        throw ControlInputRefusal(ControlCause::Unavailable,"Only the existing Save control supports a disabled visual cue");
    const QPointer<AssistantWidgetInput> self(this);
    const auto originalSerial=serial_;
    const bool admitted=request.current();
    if(!self || serial_!=originalSerial || request_)return 0;
    QPointF center;
    if (!admitted || !request.target || !visibleCenter(*request.target, center, request.kind == Kind::Scroll, request.visualOnlyDisabledTarget))
        throw ControlInputRefusal(admitted ? ControlCause::Unavailable : ControlCause::Superseded,"The genuine input control is not visible and current");
    if(!self || serial_!=originalSerial || request_)return 0;
    if(!request.value.isValidUtf16())throw std::invalid_argument("The original control text has invalid Unicode");
    if (request.kind == Kind::Value || request.kind == Kind::Text)
        throw std::invalid_argument("Scientific text uses its ordinary app setter, not draft input");
    if ((request.kind == Kind::ParameterFilter || request.kind == Kind::StagedText || request.kind == Kind::FormText) &&
        (request.value.isEmpty() && request.kind != Kind::FormText))
        throw std::runtime_error("The numeric input spelling is unavailable");
    if(request.kind==Kind::ParameterFilter && request.value.size()>static_cast<qsizetype>(edi::assistant::Limits::id_bytes))
        throw std::invalid_argument("The parameter filter identifier is unavailable");
    if (request.kind == Kind::FormText &&
        (request.value.contains(QChar::Null) || ((request.value.contains('\n') || request.value.contains('\r') || request.value.contains('\t')) &&
            !(request.kind == Kind::FormText && request.target->inherits("QQuickTextEdit")))))
        throw std::invalid_argument("The original single-line field cannot accept control characters");
    // Applies to navigation/free/fit too: their click can commit an unrelated
    // pre-existing manual draft through ordinary focus loss.
    if (manualDraftPresent()) throw ControlInputRefusal(ControlCause::ManualInput,"Finish the current manual input first");
    if (request.kind == Kind::Scroll && request.scrollDirection != 1 && request.scrollDirection != -1)
        throw std::runtime_error("The bounded viewport scroll is unavailable");
    original_text_ = request.kind == Kind::StagedText ? request.target->property("editText").toString() : QString{};
    if ((request.kind == Kind::Choose || request.kind == Kind::SearchChoice) && (request.option < 0 || request.option >= request.target->property("count").toInt() ||
        (request.kind == Kind::SearchChoice && (!request.target->property("searchable").toBool() || request.value.isEmpty() || request.value.size() > static_cast<qsizetype>(edi::assistant::Limits::id_bytes)))))
        throw std::runtime_error("The actual ComboBox option is unavailable");
    QString optionText;
    if((request.kind==Kind::Choose || request.kind==Kind::SearchChoice) &&
        !QMetaObject::invokeMethod(request.target,"textAt",Qt::DirectConnection,Q_RETURN_ARG(QString,optionText),Q_ARG(int,request.option)))
        throw ControlInputRefusal(ControlCause::Unavailable,"The original offered choice text is unavailable");
    if(!self || serial_!=originalSerial || request_)return 0;
    if(request.kind==Kind::SearchChoice && optionText!=request.value)
        throw ControlInputRefusal(ControlCause::Unavailable,"The exact search text does not match the original offered option");
    if(!request.current())throw ControlInputRefusal(ControlCause::Superseded,"The original offered choice changed");
    if(!self || serial_!=originalSerial || request_)return 0;
    request.failure=ControlCause::None;
    auto prepared = std::make_shared<Request>(std::move(request)); // All job/callback allocation precedes visibility.
    if (!mouse_owner_) throw ControlInputRefusal(ControlCause::Unavailable,"The visible mouse window is unavailable");
    mouse_stamp_ = mouse_owner_->begin(*this);
    request_ = std::move(prepared);
    const auto original = request_;
    const auto id = ++serial_;
    choice_popup_.clear(); choice_content_.clear(); choice_row_.clear(); search_header_.clear(); search_editor_.clear(); choice_text_=std::move(optionText);
    center_ = center; step_ = Step::Move; draft_ = false; commit_prepared_ = false;
    emit activeChanged(true);
    if (!self) return id;
    const bool ready = self->current(id);
    if (!self) return id;
    if (!ready) { if (serial_ == id && request_ == original) self->fail(original,id,ControlCause::Superseded, QT_TR_NOOP("Visible input ownership changed"), false); return id; }
    emit pointerShown();
    if (!self) return id;
    const bool shown = self->current(id);
    if (!self) return id;
    if (!shown) { if (serial_ == id && request_ == original) self->fail(original,id,ControlCause::Superseded, QT_TR_NOOP("Visible input ownership changed"), false); return id; }
    timer_.start(0);
    return id;
}
bool AssistantWidgetInput::mouse(QEvent::Type type, Qt::MouseButton button) {
    if (!window_ || !request_ || !mouse_owner_ || (!window_->isActive() && !cleanup_release_)) return false;
    const QPointer<AssistantWidgetInput> self(this);
    const QPointer<QQuickWindow> window(window_);
    const auto original = request_; const auto id = serial_;
    const auto original_stamp = mouse_stamp_;
    const bool old = injecting_; injecting_ = true;
    const auto release = qScopeGuard([self, old] { if (self) self->injecting_ = old; });
    const auto buttons = type == QEvent::MouseButtonRelease ? Qt::NoButton : button;
    QMouseEvent event(type, center_, window->mapToGlobal(center_), button, buttons, Qt::NoModifier, &mouse_owner_->device);
    if (type == QEvent::MouseButtonPress) mouse_owner_->held_button = button;
    event.setTimestamp(mouse_owner_->eventStamp(type));
    QCoreApplication::sendEvent(window, &event);
    if (self && mouse_owner_ && type == QEvent::MouseButtonRelease) mouse_owner_->releaseFinished(*this, original_stamp);
    return self && window && serial_ == id && request_ == original;
}
bool AssistantWidgetInput::scroll() {
    if (!window_ || !window_->isActive() || !request_ || !mouse_owner_ || !request_->scrollDirection) return false;
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
bool AssistantWidgetInput::conflictsWith(const QQuickItem* item) const noexcept {
    if (!request_ || !item || !window_ || item->window() != window_) return false;
    const auto* target = request_->target.data();
    return (target && (target == item || target->isAncestorOf(item))) ||
        (choice_content_ && (choice_content_ == item || choice_content_->isAncestorOf(item)));
}
void AssistantWidgetInput::unwatchChoicePopup() noexcept {
    for(const auto& connection:{choice_hiding_,choice_closed_connection_,choice_reopening_,choice_destroyed_})QObject::disconnect(connection);
    choice_hiding_={};choice_closed_connection_={};choice_reopening_={};choice_destroyed_={};
    choice_observation_=0;choice_closing_=false;choice_closed_=false;
}
bool AssistantWidgetInput::watchChoicePopup() {
    unwatchChoicePopup();
    if(!request_ || !choice_popup_)return false;
    choice_observation_=serial_;
    choice_hiding_=QObject::connect(choice_popup_,SIGNAL(aboutToHide()),this,SLOT(choiceAboutToHide()),Qt::DirectConnection);
    choice_closed_connection_=QObject::connect(choice_popup_,SIGNAL(closed()),this,SLOT(choiceClosed()),Qt::DirectConnection);
    choice_reopening_=QObject::connect(choice_popup_,SIGNAL(aboutToShow()),this,SLOT(choiceReopened()),Qt::DirectConnection);
    const QPointer<AssistantWidgetInput> self(this);const auto original=request_;const auto id=serial_;
    choice_destroyed_=QObject::connect(choice_popup_,&QObject::destroyed,this,[self,original,id] {
        if(self && self->request_==original && self->serial_==id)
            self->fail(original,id,ControlCause::Unavailable,QT_TR_NOOP("The original popup was destroyed before its close was confirmed"),false);
    });
    if(!choice_hiding_ || !choice_closed_connection_ || !choice_reopening_ || !choice_destroyed_){unwatchChoicePopup();return false;}
    return true;
}
void AssistantWidgetInput::choiceAboutToHide() {
    if(request_ && choice_observation_==serial_ && sender()==choice_popup_)choice_closing_=true;
}
void AssistantWidgetInput::choiceClosed() {
    if(!request_ || choice_observation_!=serial_ || sender()!=choice_popup_)return;
    choice_closed_=true;
    if(step_==Step::ChoiceSettle)timer_.start(0);
}
void AssistantWidgetInput::choiceReopened() {
    if(request_ && choice_observation_==serial_ && sender()==choice_popup_)
        fail(request_,serial_,ControlCause::Superseded,QT_TR_NOOP("The original choice popup was reopened before settlement"),false);
}
void AssistantWidgetInput::settleChoice(const std::shared_ptr<Request>& original,std::uint64_t id) {
    const QPointer<AssistantWidgetInput> self(this);
    if(!original || request_!=original || serial_!=id)return;
    step_=Step::ChoiceSettle;
    // No further device event belongs to this completed press/release. Refuse
    // delayed private clones while the original native exit transition runs.
    if(mouse_owner_)mouse_owner_->retire(*this,mouse_stamp_);
    const bool owned=current(id);
    if(!self || request_!=original || serial_!=id)return;
    if(!owned || !choice_popup_ || !original->target ||
        original->target->property(original->kind==Kind::DismissMenu?"contextMenu":"popup").value<QObject*>()!=choice_popup_) {
        fail(original,id,ControlCause::Superseded,QT_TR_NOOP("The original popup owner changed during choice settlement"),false);return;
    }
    const bool selected=original->kind==Kind::DismissMenu || original->target->property("currentIndex").toInt()==original->option;
    if(!selected){fail(original,id,ControlCause::Commit,QT_TR_NOOP("The actual popup click did not select the original offered option"),false);return;}
    if(choice_closed_ || !choice_popup_->property("visible").toBool()) {stop(original,id,true,{},false);return;}
    if(choice_closing_)return; // Only this exact popup's closed signal continues.
    fail(original,id,ControlCause::Commit,QT_TR_NOOP("The actual popup choice did not begin closing its original popup"),false);
}
bool AssistantWidgetInput::choicePopupOwned() const {
    if(choice_closing_ || !request_ || !window_ || !request_->target || !choice_popup_ || !choice_content_ ||
        request_->option<0 || request_->option>=request_->target->property("count").toInt() ||
        request_->target->property("popup").value<QObject*>()!=choice_popup_ || !choice_popup_->property("visible").toBool() ||
        choice_popup_->property("contentItem").value<QQuickItem*>()!=choice_content_ || choice_content_->window()!=window_)return false;
    const QPointer<const AssistantWidgetInput> self(this);const auto request=request_;const auto serial=serial_;
    QString text;
    const bool read=QMetaObject::invokeMethod(request->target,"textAt",Qt::DirectConnection,Q_RETURN_ARG(QString,text),Q_ARG(int,request->option));
    return self && request_==request && serial_==serial && read && text==choice_text_;
}
bool AssistantWidgetInput::choiceRowOwned() const {
    if(!choicePopupOwned() || !choice_row_)return false;
    const QPointer<const AssistantWidgetInput> self(this);const auto request=request_;const auto serial=serial_;
    const QPointer<QQuickItem> list(choice_content_),row(choice_row_);QQuickItem* actual=nullptr;
    const bool read=QMetaObject::invokeMethod(list,"itemAtIndex",Qt::DirectConnection,Q_RETURN_ARG(QQuickItem*,actual),Q_ARG(int,request->option));
    if(!self || request_!=request || serial_!=serial || !list || !row || list!=choice_content_ || row!=choice_row_ ||
        !read || actual!=row || row->window()!=window_ || !list->isAncestorOf(row))return false;
    QPointF center;if(!visibleCenter(*row,center))return false;
    // The original searchable list uses an overlay header; an option behind
    // that real editor is not an exposed choice even when its delegate exists.
    const QPointer<QQuickItem> header(list->property("headerItem").value<QQuickItem*>());
    return !header || !header->isVisible() || header->opacity()<=0 ||
        !header->mapRectToScene(QRectF(0,0,header->width(),header->height())).contains(center);
}
bool AssistantWidgetInput::revealChoice() {
    if(!choicePopupOwned())return false;
    const QPointer<AssistantWidgetInput> self(this);const auto request=request_;const auto serial=serial_;
    const QPointer<QQuickItem> list(choice_content_);
    const auto owned=[&] {return self && request_==request && serial_==serial && current(serial) && list && list==choice_content_ && choicePopupOwned();};
    if(!owned())return false;
    list->ensurePolished();if(!owned())return false;
    if(!QMetaObject::invokeMethod(list,"forceLayout",Qt::DirectConnection) || !owned())return false;
    // Public ListView.Center (Qt's QML position mode), not a guessed row coordinate.
    if(!QMetaObject::invokeMethod(list,"positionViewAtIndex",Qt::DirectConnection,Q_ARG(int,request->option),Q_ARG(int,1)) || !owned())return false;
    if(!QMetaObject::invokeMethod(list,"forceLayout",Qt::DirectConnection) || !owned())return false;
    QQuickItem* row=nullptr;
    if(!QMetaObject::invokeMethod(list,"itemAtIndex",Qt::DirectConnection,Q_RETURN_ARG(QQuickItem*,row),Q_ARG(int,request->option)) || !owned() || !row)return false;
    const QPointer<QQuickItem> actual(row);choice_row_=actual;
    return choiceRowOwned() && actual && visibleCenter(*actual,center_);
}
bool AssistantWidgetInput::searchEditorOwned() const {
    if(!choicePopupOwned() || !request_ || request_->kind!=Kind::SearchChoice || !search_header_ || !search_editor_)return false;
    const QPointer<const AssistantWidgetInput> self(this);const auto request=request_;const auto serial=serial_;
    const QPointer<QQuickItem> list(choice_content_),header(search_header_),editor(search_editor_);
    if(list->property("headerItem").value<QQuickItem*>()!=header || !list->isAncestorOf(header) || !header->isAncestorOf(editor) ||
        editor->window()!=window_ || editor->objectName()!=QStringLiteral("comboBox.search") ||
        (!editor->inherits("QQuickTextInput") && !editor->inherits("QQuickTextEdit")))return false;
    QQuickItem* actual=nullptr;
    for(auto* child:header->childItems())if(child->objectName()==QStringLiteral("comboBox.search")) {
        if(actual)return false;
        actual=child;
    }
    QPointF center;
    return self && request_==request && serial_==serial && actual==editor && visibleCenter(*editor,center);
}
bool AssistantWidgetInput::revealSearchEditor() {
    if(!choicePopupOwned() || !request_ || request_->kind!=Kind::SearchChoice)return false;
    const QPointer<AssistantWidgetInput> self(this);const auto request=request_;const auto serial=serial_;
    const QPointer<QQuickItem> list(choice_content_);
    const auto owned=[&]{return self && request_==request && serial_==serial && current(serial) && list && list==choice_content_ && choicePopupOwned();};
    list->ensurePolished();if(!owned())return false;
    if(!QMetaObject::invokeMethod(list,"forceLayout",Qt::DirectConnection) || !owned())return false;
    const QPointer<QQuickItem> header(list->property("headerItem").value<QQuickItem*>());
    if(!header || !list->isAncestorOf(header))return false;
    header->ensurePolished();if(!owned() || !header || list->property("headerItem").value<QQuickItem*>()!=header)return false;
    QPointer<QQuickItem> editor;
    for(auto* child:header->childItems())if(child->objectName()==QStringLiteral("comboBox.search")) {
        if(editor)return false;
        editor=child;
    }
    if(!editor)return false;
    editor->ensurePolished();if(!owned() || !header || !editor)return false;
    search_header_=header;search_editor_=editor;
    return searchEditorOwned() && visibleCenter(*editor,center_);
}
bool AssistantWidgetInput::choiceKeyboardOwned() const {
    if (!window_ || !request_ || !request_->target) return false;
    if (request_->kind != Kind::SearchChoice && request_->kind != Kind::DismissMenu && request_->target->hasActiveFocus()) return true;
    if ((request_->kind != Kind::Choose && request_->kind != Kind::SearchChoice && request_->kind != Kind::DismissMenu) || !choice_popup_ || !choice_popup_->property("visible").toBool() ||
        request_->target->property(request_->kind == Kind::DismissMenu ? "contextMenu" : "popup").value<QObject*>() != choice_popup_) return false;
    const auto* content = choice_popup_->property("contentItem").value<QQuickItem*>();
    const auto* focus = window_->activeFocusItem();
    if (request_->kind == Kind::SearchChoice && (!focus || focus->objectName() != "comboBox.search")) return false;
    for (auto* item = focus; item; item = item->parentItem()) if (item == content) return content->window() == window_;
    return false;
}
bool AssistantWidgetInput::key(int code, Qt::KeyboardModifiers modifiers, const QString& text) {
    const bool delivered = [&]() {
        if (!window_ || !window_->isActive() || !request_ || !request_->target || !choiceKeyboardOwned()) return false;
        const QPointer<AssistantWidgetInput> self(this);
        const QPointer<QQuickWindow> window(window_);
        const auto original = request_; const auto id = serial_;
        const bool old = injecting_; injecting_ = true;
        const auto release = qScopeGuard([self, old] { if (self) self->injecting_ = old; });
        // Only a prepared original menu/filter/choice commit may drop focus.
        // Its balancing release stays on the original surviving control.
        const bool terminal = (code == Qt::Key_Escape && original->kind == Kind::DismissMenu && commit_prepared_) ||
            (code == Qt::Key_Return && commit_prepared_ &&
            ((step_ == Step::Commit && (original->kind == Kind::ParameterFilter || original->kind == Kind::SearchChoice)) ||
             (step_ == Step::ChooseCommit && original->kind == Kind::Choose)));
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
        const bool retained = self && window && serial_ == id && request_ == original &&
            (!terminal || (target && request_->target == target && window_ == window && target->window() == window));
        return retained;
    }();
    return delivered;
}
void AssistantWidgetInput::advance() noexcept {
    const auto id = serial_;
    const auto request = request_; // Strong original callback/target scope for this tick.
    const QPointer<AssistantWidgetInput> self(this);
    try {
        const bool valid = current(id);
        if (!self) return;
        const bool rowStep=step_==Step::ChoicePress || step_==Step::ChoiceRelease;
        const bool searchStep=step_==Step::SearchPress || step_==Step::SearchRelease;
        const auto geometryTarget=rowStep?choice_row_:searchStep?search_editor_:request?request->target:QPointer<QQuickItem>{};
        if (!valid || !request || !request->target || (rowStep && !choiceRowOwned()) || !geometryTarget || !visibleCenter(*geometryTarget, center_, request->kind == Kind::Scroll, request->visualOnlyDisabledTarget)) { if (self && serial_ == id && request_ == request) self->fail(request,id,valid ? ControlCause::Unavailable : ControlCause::Superseded, QT_TR_NOOP("Visible action target changed or is unavailable"), true); return; }
        // Keep the same step and original authority while another application
        // is active. Never request activation or inject into an inactive window.
        if (!window_->isActive()) { timer_.start(navigation_ms); return; }
        if ((step_ == Step::Move || step_ == Step::Press) && manualDraftPresent()) {
            if(self)self->stop(request,id,false, interrupted_, false, ControlCause::ManualInput); return;
        }
        switch (step_) {
        case Step::Move:
            emit pointerMoved(center_);
            if (!self) return;
            { const bool valid = self->current(id); if (!self) return;
              if (!valid) { if (self && serial_ == id && request_ == request) self->fail(request,id,ControlCause::Superseded, QT_TR_NOOP("Visible action ownership changed"), true); return; } }
            step_ = Step::Press; pace(move_ms); return;
        case Step::Press:
            if (request->kind == Kind::FileLoadCue) {
                // Presentation only: no device event, focus change or button handler.
                emit pointerPressed();
                if (!self || serial_ != id || request_ != request) return;
                const bool valid = current(id);
                if (!self || serial_ != id || request_ != request) return;
                if (!valid) { if(self)self->fail(request,id,ControlCause::Superseded, QT_TR_NOOP("Visible file cue ownership changed"), false); return; }
                step_ = Step::Release; pace(press_ms); return;
            }
            if (request->kind == Kind::DismissMenu) {
                choice_popup_ = request->target->property("contextMenu").value<QObject*>();
                choice_content_ = choice_popup_ ? choice_popup_->property("contentItem").value<QQuickItem*>() : nullptr;
                if (!choice_popup_ || !choice_popup_->property("visible").toBool() || !choiceKeyboardOwned() || !watchChoicePopup()) { if(self)self->fail(request,id,ControlCause::Delivery, QT_TR_NOOP("The original parameter menu lost keyboard ownership"), false); return; }
                step_ = Step::ChooseCommit; timer_.start(0); return;
            }
            if (request->kind == Kind::Scroll) {
                // Wheel movement changes only the actual existing viewport; it
                // never focuses/blurs an editor or synthesizes a button click.
                if (!scroll()) { if (self && serial_ == id && request_ == request) self->fail(request,id,ControlCause::Delivery, QT_TR_NOOP("The viewport did not receive its wheel input"), false); return; }
                if (self && serial_ == id && request_ == request) self->stop(request,id,true, {}, false);
                return;
            }
            if (!mouse(QEvent::MouseMove, Qt::NoButton)) { if (self && serial_ == id && request_ == request) self->fail(request,id,ControlCause::Delivery, QT_TR_NOOP("The target did not receive pointer movement"), false); return; }
            if (!self) return;
            { const bool valid = self->current(id); if (!self) return;
              if (!valid) { if (self && serial_ == id && request_ == request) self->fail(request,id,ControlCause::Superseded, QT_TR_NOOP("Visible action ownership changed"), true); return; } }
            emit pointerPressed();
            if (!self) return;
            { const bool valid = self->current(id); if (!self) return;
              if (!valid) { if (self && serial_ == id && request_ == request) self->fail(request,id,ControlCause::Superseded, QT_TR_NOOP("Visible action ownership changed"), true); return; } }
            pressed_ = true; // Own a balancing release even if the press reenters retirement.
            if (!mouse(QEvent::MouseButtonPress, request->kind == Kind::ContextMenu ? Qt::RightButton : Qt::LeftButton)) { if (self && serial_ == id && request_ == request) self->fail(request,id,ControlCause::Delivery, QT_TR_NOOP("The real control did not receive its press"), true); return; }
            if (!self || serial_ != id || request_ != request) return;
            step_ = Step::Release; pace(press_ms); return;
        case Step::Release:
            if (request->kind == Kind::FileLoadCue) { if(self)self->stop(request,id,true, {}, false); return; }
            if (request->kind != Kind::ParameterFilter && request->kind != Kind::StagedText && request->kind != Kind::Choose && request->kind != Kind::SearchChoice && request->kind != Kind::FormText) {
                commit_prepared_ = true; // Exact finish is owed even if preparation reenters/cancels.
                if (!request->prepareCommit()) { if (self && serial_ == id && request_ == request) self->fail(request,id,ControlCause::Commit, QT_TR_NOOP("The native input could not be prepared"), false); return; }
                if (!self) return;
            { const bool valid = self->current(id); if (!self) return;
              if (!valid) { if (self && serial_ == id && request_ == request) self->fail(request,id,ControlCause::Superseded, QT_TR_NOOP("Visible action ownership changed"), true); return; } }
            }
            pressed_ = false;
            if (!mouse(QEvent::MouseButtonRelease, request->kind == Kind::ContextMenu ? Qt::RightButton : Qt::LeftButton)) { if (self && serial_ == id && request_ == request) self->fail(request,id,ControlCause::Delivery, QT_TR_NOOP("The real control did not receive its release"), true); return; }
            if (!self || serial_ != id || request_ != request) return;
            if (request_->kind == Kind::Choose || request_->kind == Kind::SearchChoice) {
                choice_popup_ = request_->target->property("popup").value<QObject*>();
                choice_content_ = choice_popup_ ? choice_popup_->property("contentItem").value<QQuickItem*>() : nullptr;
                if (!choice_popup_ || !choice_popup_->property("visible").toBool() || !watchChoicePopup()) { if(self)self->fail(request,id,ControlCause::Commit, QT_TR_NOOP("The genuine ComboBox popup did not open with its original completion owner"), false); return; }
                step_ = request_->kind == Kind::SearchChoice ? Step::SearchReveal : Step::ChoiceReveal;
                pace(click_relaxation_ms); return;
            }
            if (request_->kind != Kind::ParameterFilter && request_->kind != Kind::StagedText && request_->kind != Kind::Choose && request_->kind != Kind::SearchChoice && request_->kind != Kind::FormText) { if(self)self->stop(request,id,true, {}, false); return; }
            step_ = Step::Select; pace(click_relaxation_ms); return;
        case Step::SearchReveal: {
            if(!revealSearchEditor()) {if(self && serial_==id && request_==request)self->fail(request,id,ControlCause::Unavailable,QT_TR_NOOP("The original popup search editor could not be revealed"),false);return;}
            if(!self || serial_!=id || request_!=request)return;
            const bool composing=search_editor_->property("inputMethodComposing").toBool();
            const bool manual=manualDraftPresent();
            if(!self || serial_!=id || request_!=request)return;
            if(composing || manual) {
                self->fail(request,id,ControlCause::ManualInput,QT_TR_NOOP("Finish the current manual input before focusing the original popup search"),false);return;
            }
            if(window_->activeFocusItem()==search_editor_ && choiceKeyboardOwned()) {step_=Step::Select;timer_.start(0);return;}
            // An open popup may legitimately own focus at its scope item. Focus
            // this exact visible original editor by its ordinary physical click,
            // not forceActiveFocus or an assumption about onOpened timing.
            emit pointerMoved(center_);
            if(self && serial_==id && request_==request){step_=Step::SearchPress;pace(move_ms);}return;
        }
        case Step::SearchPress: {
            if(!searchEditorOwned()){if(self && serial_==id && request_==request)self->fail(request,id,ControlCause::Unavailable,QT_TR_NOOP("The original popup search editor changed before pointer movement"),false);return;}
            const bool manual=manualDraftPresent();
            if(!self || serial_!=id || request_!=request)return;
            if(manual){self->fail(request,id,ControlCause::ManualInput,QT_TR_NOOP("Finish the current manual input before focusing the original popup search"),false);return;}
            if(!mouse(QEvent::MouseMove,Qt::NoButton)) {if(self && serial_==id && request_==request)self->fail(request,id,ControlCause::Delivery,QT_TR_NOOP("The original popup search editor did not receive pointer movement"),false);return;}
            if(!self || serial_!=id || request_!=request)return;
            if(!current(id) || !searchEditorOwned()){if(self && serial_==id && request_==request)self->fail(request,id,ControlCause::Superseded,QT_TR_NOOP("The original popup search editor changed before its press"),false);return;}
            emit pointerPressed();
            if(!self || serial_!=id || request_!=request)return;
            if(!current(id) || !searchEditorOwned()){if(self && serial_==id && request_==request)self->fail(request,id,ControlCause::Superseded,QT_TR_NOOP("The original popup search editor changed during its cue"),false);return;}
            pressed_=true;
            if(!mouse(QEvent::MouseButtonPress,Qt::LeftButton)){if(self && serial_==id && request_==request)self->fail(request,id,ControlCause::Delivery,QT_TR_NOOP("The original popup search editor did not receive its press"),false);return;}
            if(self && serial_==id && request_==request){step_=Step::SearchRelease;pace(press_ms);}return;
        }
        case Step::SearchRelease:
            pressed_=false;
            if(!mouse(QEvent::MouseButtonRelease,Qt::LeftButton)){if(self && serial_==id && request_==request)self->fail(request,id,ControlCause::Delivery,QT_TR_NOOP("The original popup search editor did not receive its release"),false);return;}
            if(!self || serial_!=id || request_!=request)return;
            if(!searchEditorOwned() || window_->activeFocusItem()!=search_editor_ || !choiceKeyboardOwned()) {if(self && serial_==id && request_==request)self->fail(request,id,ControlCause::Delivery,QT_TR_NOOP("The original popup search editor did not receive keyboard focus"),false);return;}
            step_=Step::Select;timer_.start(0);return;
        case Step::ChoiceReveal:
            if(!revealChoice()) {if(self && serial_==id && request_==request)self->fail(request,id,ControlCause::Unavailable,QT_TR_NOOP("The exact offered popup row could not be revealed"),false);return;}
            if(!self || serial_!=id || request_!=request)return;
            emit pointerMoved(center_);
            if(!self || serial_!=id || request_!=request)return;
            step_=Step::ChoicePress;pace(move_ms);return;
        case Step::ChoicePress:
            if(!choiceRowOwned() || !mouse(QEvent::MouseMove,Qt::NoButton)) {if(self && serial_==id && request_==request)self->fail(request,id,ControlCause::Delivery,QT_TR_NOOP("The offered popup row did not receive pointer movement"),false);return;}
            if(!self || serial_!=id || request_!=request)return;
            if(!current(id) || !choiceRowOwned()){if(self && serial_==id && request_==request)self->fail(request,id,ControlCause::Superseded,QT_TR_NOOP("The original offered row changed before its press"),false);return;}
            emit pointerPressed();
            if(!self || serial_!=id || request_!=request)return;
            if(!current(id) || !choiceRowOwned()){if(self && serial_==id && request_==request)self->fail(request,id,ControlCause::Superseded,QT_TR_NOOP("The original offered row changed during its cue"),false);return;}
            pressed_=true;
            if(!mouse(QEvent::MouseButtonPress,Qt::LeftButton)) {if(self && serial_==id && request_==request)self->fail(request,id,ControlCause::Delivery,QT_TR_NOOP("The original popup choice did not receive its press"),false);return;}
            if(self && serial_==id && request_==request){step_=Step::ChoiceRelease;pace(press_ms);}return;
        case Step::ChoiceRelease:
            commit_prepared_=true;
            if(!request->prepareCommit()) {if(self && serial_==id && request_==request)self->fail(request,id,ControlCause::Commit,QT_TR_NOOP("The original popup choice could not admit its ordinary commit"),false);return;}
            if(!self || serial_!=id || request_!=request)return;
            if(!current(id) || !choiceRowOwned()) {if(self && serial_==id && request_==request)self->fail(request,id,ControlCause::Superseded,QT_TR_NOOP("The prepared original popup choice changed"),false);return;}
            pressed_=false;
            {
                choice_releasing_=true;
                const auto release=qScopeGuard([self]{if(self)self->choice_releasing_=false;});
                if(!mouse(QEvent::MouseButtonRelease,Qt::LeftButton)) {if(self && serial_==id && request_==request)self->fail(request,id,ControlCause::Delivery,QT_TR_NOOP("The original popup choice did not receive its release"),false);return;}
            }
            if(self && serial_==id && request_==request)settleChoice(request,id);
            return;
        case Step::ChoiceSettle:
            settleChoice(request,id);return;
        case Step::ChooseCommit:
            commit_prepared_ = true;
            if (!request->prepareCommit()) { if (self && serial_ == id && request_ == request) self->fail(request,id,ControlCause::Commit, QT_TR_NOOP("The original ComboBox choice was retired"), false); return; }
            if (!self || serial_ != id || request_ != request) return;
            { const bool owned=current(id);
            if (!owned || !key(request->kind == Kind::DismissMenu ? Qt::Key_Escape : Qt::Key_Return)) { if (self && serial_ == id && request_ == request) self->fail(request,id,owned ? ControlCause::Delivery : ControlCause::Superseded, QT_TR_NOOP("The actual menu key could not be delivered"), false); return; } }
            if (self && serial_ == id && request_ == request)settleChoice(request,id);
            return;
        case Step::Select: {
            if (request->kind == Kind::StagedText) {
                if (!QMetaObject::invokeMethod(request->target, "beginAssistantEdit", Qt::DirectConnection)) { if(self)self->fail(request,id,ControlCause::Commit, QT_TR_NOOP("The original staged draft has no safe owner"), false); return; }
                if (!self || serial_ != id || request_ != request) return;
                if (!request->target || !request->target->property("assistantEditing").toBool()) { if(self)self->fail(request,id,ControlCause::Commit, QT_TR_NOOP("The original staged draft was not admitted"), false); return; }
                draft_ = true;
            }
            // Only genuine form/filter/staged drafts are edited here. Scientific
            // declarations use the adapter's original ordinary model methods.
            // Search stays on the actual popup editor; the offered result is
            // revealed and clicked below without a second acceptance handler.
            const QPointer<QQuickItem> editor(request->kind == Kind::SearchChoice ? search_editor_.data() : request->target.data());
            if (!editor || (!editor->inherits("QQuickTextInput") && !editor->inherits("QQuickTextEdit")) ||
                !choiceKeyboardOwned() || (request->kind==Kind::SearchChoice && window_->activeFocusItem()!=editor) || editor->property("inputMethodComposing").toBool()) { if(self)self->fail(request,id,ControlCause::Delivery, QT_TR_NOOP("The original draft lost keyboard ownership"), true); return; }
            if (!self || serial_ != id || request_ != request || !editor) return;
            const auto old = injecting_; injecting_ = true;
            {
                const auto release = qScopeGuard([self,old] { if (self) self->injecting_ = old; });
                if (editor->property("text").toString() != request->value && !editor->setProperty("text", request->value)) {
                    if (self && serial_ == id && request_ == request) self->fail(request,id,ControlCause::Commit, QT_TR_NOOP("The original draft refused its text"), true);
                    return;
                }
            }
            if (!self || serial_ != id || request_ != request) return;
            const bool valid = current(id);
            if (!self || serial_ != id || request_ != request) return;
            if (!valid || !editor || !choiceKeyboardOwned() ||
                (request->kind == Kind::SearchChoice && window_->activeFocusItem() != editor) ||
                editor->property("text").toString() != request->value) {
                if(self)self->fail(request,id,ControlCause::Superseded, QT_TR_NOOP("The original draft owner or text changed"), true); return;
            }
            emit inputProgress();
            if (!self || serial_ != id || request_ != request) return;
            step_ = request->kind==Kind::SearchChoice?Step::ChoiceReveal:Step::Commit; timer_.start(0); return;
        }
        case Step::Commit:
            commit_prepared_ = true;
            if (!request->prepareCommit()) { if (self && serial_ == id && request_ == request) self->fail(request,id,ControlCause::Commit, QT_TR_NOOP("The recorded native input could not be prepared"), true); return; }
            if (!self) return;
            { const bool valid = self->current(id); if (!self) return;
              if (!valid) { if (self && serial_ == id && request_ == request) self->fail(request,id,ControlCause::Superseded, QT_TR_NOOP("Visible action ownership changed"), true); return; } }
            if ((request->kind == Kind::StagedText) && !QMetaObject::invokeMethod(request->target, "allowAssistantCommit", Qt::DirectConnection)) { if(self)self->fail(request,id,ControlCause::Commit, QT_TR_NOOP("The numeric control could not admit its final key"), true); return; }
            if (!self || serial_ != id || request_ != request) return;
            // Staged/form drafts have no scientific blur/Return commit. Their
            // original Apply/Create/Save action remains the sole final commit.
            if (request->kind != Kind::StagedText && request->kind != Kind::FormText && !key(Qt::Key_Return)) { if (self && serial_ == id && request_ == request) self->fail(request,id,ControlCause::Delivery, QT_TR_NOOP("The numeric input commit was not confirmed"), true); return; }
            if (self && serial_ == id && request_ == request) {
                draft_ = false;
                const bool selected = request->kind != Kind::SearchChoice || (request->target && request->target->property("currentIndex").toInt() == request->option);
                if(self)self->stop(request,id,selected, {}, false, selected ? ControlCause::None : ControlCause::Commit);
            }
            return;
        }
    } catch (...) { if (self && serial_ == id && request_ == request) self->stop(request,id,false, failed_, true); }
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
void AssistantWidgetInput::fail(const std::shared_ptr<Request>& expected, std::uint64_t expectedId,
                                ControlCause cause, const char* diagnostic, bool restore) {
    // Translation is a virtual callback boundary. Capture the original before it.
    const QPointer<AssistantWidgetInput> self(this);
    const auto original=expected;
    if(!original || request_!=original || serial_!=expectedId)return;
    if(original->failure==ControlCause::None)original->failure=cause;
    const auto translated=tr(diagnostic);
    if(!self || self->request_!=original || self->serial_!=expectedId)return;
    self->stop(original,expectedId,false,translated,restore,cause);
}
void AssistantWidgetInput::stop(const std::shared_ptr<Request>& expected, std::uint64_t expectedId,
                                bool delivered, const QString& diagnostic, bool restore, ControlCause cause) noexcept {
    const QPointer<AssistantWidgetInput> self(this);
    if(!expected || request_!=expected || serial_!=expectedId)return;
    const auto id = expectedId;
    const auto original = expected;
    const auto settled_diagnostic = diagnostic; // Own the original fallback across completion reentry.
    if(!delivered){
        if(original->failure==ControlCause::None)original->failure=cause;
        cause=original->failure;
    }else cause=ControlCause::None;
    try { timer_.stop(); } catch (...) { delivered = false; }
    if (mouse_owner_) mouse_owner_->retire(*this, mouse_stamp_);
    if (pressed_ || (mouse_owner_ && mouse_owner_->heldBy(*this, mouse_stamp_))) {
        // Retire first; balancing release must not replay an old delayed press.
        pressed_ = false;
        center_ = QPointF(-1, -1);
        cleanup_release_ = true;
        const auto release_cleanup = qScopeGuard([self] { if (self) self->cleanup_release_ = false; });
        try { (void)mouse(QEvent::MouseButtonRelease, original->kind == Kind::ContextMenu ? Qt::RightButton : Qt::LeftButton); }
        catch (...) {
            delivered = false;
            if (self && mouse_owner_) mouse_owner_->deferHeldCleanup(mouse_stamp_);
        } // Still owe draft/editor/completion cleanup.
    }
    if (!self || request_ != original || serial_ != id) return;
    if (restore) restoreDraft();
    if (!self || request_ != original || serial_ != id) return;
    unwatchChoicePopup();
    request_.reset();
    const bool prepared = commit_prepared_; commit_prepared_ = false; draft_ = false; original_text_.clear(); choice_popup_.clear(); choice_content_.clear(); choice_row_.clear(); search_header_.clear(); search_editor_.clear(); choice_text_.clear();
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
    try { original->completed(delivered, settled_diagnostic, cause); } catch (...) {}
}
void AssistantWidgetInput::cancel() {
    const QPointer<AssistantWidgetInput> self(this);
    const auto original=request_;
    const auto id=serial_;
    if(self)self->stop(original,id,false,interrupted_,true,ControlCause::Superseded);
}
bool AssistantWidgetInput::eventFilter(QObject* watched, QEvent* event) {
    // The retained application filter separately consumes stale own events, even
    // when this helper is inactive/replaced. Genuine devices remain manual.
    if (ownMouseEvent(event)) return rejectOwnEvent(watched, event);
    // The owning VM classifies genuine project input at its actual receiver.
    // This helper must not convert ordinary hover/chat/navigation or Cmd-Tab
    // into a second blanket cancellation path.
    if (watched == window_ && request_ && !injecting_ &&
        (event->type() == QEvent::Hide || event->type() == QEvent::Close)) {
        const QPointer<QObject> original_target(watched);
        cancel();
        return !original_target;
    }
    return false;
}
}
