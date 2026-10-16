// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <QObject>
#include <QEvent>
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
    enum class Kind { Value, Free, Fit, Navigate };
    struct Request {
        Kind kind;
        QPointer<QQuickItem> target;
        QString value; // Native NumberText/full numeric spelling; never a shell/DSL.
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
    bool active() const noexcept { return static_cast<bool>(request_); }
    bool usableTarget(QQuickItem& item) const; // Same actual window/clip check used immediately before input.
    bool manualDraftPresent() const; // App-private current-focus preflight, never a provider selector.
 signals:
    void activeChanged(bool active);
    void manualInput(); // Keep the manual target exposed before yielding its original event.
    void pointerShown();
    void pointerMoved(const QPointF& position);
    void pointerPressed();
    void pointerHidden();
 protected:
    bool eventFilter(QObject* watched, QEvent* event) override;
 private:
    enum class Step { Move, Press, Release, Select, Delete, Type, Commit };
    void advance() noexcept;
    bool current(std::uint64_t id) const;
    bool visibleCenter(QQuickItem& item, QPointF& center) const;
    bool mouse(QEvent::Type type, Qt::MouseButton button);
    bool selectAll();
    bool key(int code, Qt::KeyboardModifiers modifiers = Qt::NoModifier, const QString& text = {});
    void stop(bool delivered, const QString& diagnostic, bool restoreDraft) noexcept;
    void restoreDraft() noexcept;
    QPointer<QQuickWindow> window_;
    QTimer timer_;
    std::shared_ptr<Request> request_;
    std::uint64_t serial_ = 0;
    Step step_ = Step::Move;
    qsizetype character_ = 0;
    QString original_text_;
    const QString failed_ = QStringLiteral("The visible action could not be completed; inspect the current project");
    const QString interrupted_ = QStringLiteral("Visible action interrupted");
    QPointF center_;
    bool injecting_ = false, draft_ = false, commit_prepared_ = false, pressed_ = false;
};
}
