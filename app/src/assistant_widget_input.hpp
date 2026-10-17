// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <QObject>
#include <QEvent>
#include <QEventPoint>
#include <memory>
#include <QPointer>
#include <QPointF>
#include <QQuickItem>
#include <QQuickWindow>
#include <QTimer>
#include <QString>
#include <functional>
#include <optional>
#include <cstdint>

namespace edi_app {
// App-private real input sequencer. No Q_INVOKABLE, script commands, model
// setters or provider-selected QObject targets. The native adapter supplies an
// already validated exact current widget and original-call ownership checks.
class AssistantWidgetInput final : public QObject {
    Q_OBJECT
 public:
    enum class Kind { Value, Text, Free, Fit, Navigate, ParameterFilter, StagedText, Scroll, Choose, SearchChoice, ContextMenu, DismissMenu, FileLocation, FilePath, FormText };
    struct Request {
        Kind kind;
        QPointer<QQuickItem> target;
        // Only the original Qt FileDialog breadcrumb field, captured through
        // its actual dialog link before the genuine Ctrl+L focus transition.
        QPointer<QQuickItem> locationField;
        int scrollDirection = 0; // One ordinary wheel detent (+1/-1), only at the sidebar gutter.
        int option = -1; // Actual finite ComboBox option.
        QString value; // Actual numeric spelling, declaration text or popup search; never executable input.
        std::function<bool()> current;
        std::function<bool()> restoreCurrent; // Same exact widget/owner; independent of retired mutation authority.
        // These narrowly wrap the genuine final input event. The adapter must
        // own recorded edit/real FitReport delivery before this returns true.
        std::function<bool()> prepareCommit;
        std::function<void()> finishCommit;
        std::function<void(bool delivered, const QString& diagnostic)> completed;
    };
    explicit AssistantWidgetInput(QQuickWindow& window, QObject* parent = nullptr);
    ~AssistantWidgetInput() override;
    std::uint64_t start(Request request); // Not exposed to QML/provider tools.
    void cancel();
    bool injecting() const noexcept { return injecting_; }
    // Exact private mouse device, including Qt clones; not a synthetic-event heuristic.
    bool ownMouseEvent(const QEvent* event) const noexcept;
    // Recognition is not admission: every window/item delivery rechecks the
    // retained original device/window/sequence/stamp, including direct clones.
    bool rejectOwnEvent(QObject* receiver, QEvent* event) const noexcept;
    // Actual QML handler pre-action boundary, also after helper destruction.
    // nullopt means genuine other-device input; true consumes stale own input.
    static std::optional<bool> rejectOwnedPoint(QObject* receiver, const QEventPoint& point) noexcept;
    bool active() const noexcept { return static_cast<bool>(request_); }
    bool usableTarget(QQuickItem& item) const; // Same actual window/clip check used immediately before input.
    bool manualDraftPresent() const; // App-private current-focus preflight, never a provider selector.
 signals:
    void activeChanged(bool active);
    void inputProgress(); // A real delivered character; no text/payload.
    void manualInput(); // Keep the manual target exposed before yielding its original event.
    void pointerShown();
    void pointerMoved(const QPointF& position);
    void pointerPressed();
    void pointerHidden();
 protected:
    bool eventFilter(QObject* watched, QEvent* event) override;
 private:
    struct MouseOwnership;
    enum class Step { Move, Press, Release, Select, Delete, Type, Commit, ChooseHome, ChooseDown, ChooseCommit };
    void advance() noexcept;
    bool current(std::uint64_t id) const;
    bool visibleCenter(QQuickItem& item, QPointF& center, bool scrollGutter = false) const;
    bool mouse(QEvent::Type type, Qt::MouseButton button);
    bool scroll();
    bool selectAll();
    bool key(int code, Qt::KeyboardModifiers modifiers = Qt::NoModifier, const QString& text = {});
    void stop(bool delivered, const QString& diagnostic, bool restoreDraft) noexcept;
    void restoreDraft() noexcept;
    QPointer<QQuickWindow> window_;
    QPointer<MouseOwnership> mouse_owner_; // Application-owned: rejects old replays across helper/window teardown.
    quint64 mouse_stamp_ = 0;
    QTimer timer_;
    std::shared_ptr<Request> request_;
    std::uint64_t serial_ = 0;
    Step step_ = Step::Move;
    qsizetype character_ = 0;
    QString original_text_;
    QPointer<QObject> choice_popup_;
    int option_step_ = 0;
    bool choiceKeyboardOwned() const;
    const QString failed_ = QStringLiteral("The visible action could not be completed; inspect the current project");
    const QString interrupted_ = QStringLiteral("Visible action interrupted");
    QPointF center_;
    bool cleanup_release_ = false;
    bool injecting_ = false, draft_ = false, commit_prepared_ = false, pressed_ = false;
};
}
