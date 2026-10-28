// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#ifndef __EMSCRIPTEN__
#include <QObject>
#include <QString>
#include <QTemporaryDir>
#include <QUrl>
#include <functional>
#include <memory>

// Public GitHub snapshots enter the FIRST local skill-source validator; this
// helper only acquires immutable regular bytes and never executes repository code.
class AssistantSkillWebImport final : public std::enable_shared_from_this<AssistantSkillWebImport> {
public:
    using Completion=std::function<void(std::unique_ptr<QTemporaryDir>,QString,QString)>;
    static std::shared_ptr<AssistantSkillWebImport> start(QObject*,const QUrl&,Completion);
    ~AssistantSkillWebImport();
    void cancel() noexcept;
private:
    struct State;
    explicit AssistantSkillWebImport(std::unique_ptr<State>);
    std::unique_ptr<State> state_;
};
#endif
