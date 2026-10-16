// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <QObject>
#include <QTimer>
#include <QUrl>
#include <QVariantMap>
#include <QtQml/qqmlregistration.h>
#include <memory>

#include "edi/assistant.hpp"
#include "row_table_model.hpp"
#ifndef __EMSCRIPTEN__
#include "chatgpt_connection.hpp"
#endif

namespace edi_app {
class ProjectViewModel;
class Session;

/// Native QML presentation of the shared controller. Owned by Session, including while no project is open.
class AssistantViewModel : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to Session")
    Q_PROPERTY(QString state READ state NOTIFY stateChanged)
    Q_PROPERTY(bool connected READ connected NOTIFY connectedChanged)
    Q_PROPERTY(QString connectionLabel READ connectionLabel NOTIFY connectionLabelChanged)
    Q_PROPERTY(edi_app::RowTableModel* models READ models CONSTANT)
    Q_PROPERTY(QString selectedModel READ selectedModel WRITE setSelectedModel NOTIFY selectedModelChanged)
    Q_PROPERTY(QString selectedEffort READ selectedEffort WRITE setSelectedEffort NOTIFY selectedEffortChanged)
    Q_PROPERTY(QStringList availableEfforts READ availableEfforts NOTIFY availableEffortsChanged)
    Q_PROPERTY(edi_app::RowTableModel* messages READ messages CONSTANT)
    Q_PROPERTY(edi_app::RowTableModel* selectedFiles READ selectedFiles CONSTANT)
    Q_PROPERTY(edi_app::RowTableModel* skills READ skills CONSTANT)
    Q_PROPERTY(QString selectedSkill READ selectedSkill NOTIFY selectedSkillChanged)
    Q_PROPERTY(QVariantMap pendingPlan READ pendingPlan NOTIFY pendingPlanChanged)
    Q_PROPERTY(QVariantMap pendingQuestion READ pendingQuestion NOTIFY pendingQuestionChanged)
    Q_PROPERTY(QString activeJobId READ activeJobId NOTIFY activeJobIdChanged)
    Q_PROPERTY(bool canCancel READ canCancel NOTIFY canCancelChanged)
    Q_PROPERTY(QString lastError READ lastError NOTIFY lastErrorChanged)
    Q_PROPERTY(QVariantMap usage READ usage NOTIFY usageChanged)
    Q_PROPERTY(QString contextPreview READ contextPreview NOTIFY contextPreviewChanged)
    Q_PROPERTY(bool contextConsentRequired READ contextConsentRequired NOTIFY contextPreviewChanged)

   public:
    explicit AssistantViewModel(QObject* parent = nullptr);
#ifndef __EMSCRIPTEN__
    AssistantViewModel(edi::assistant::native::NativeDependencies dependencies, QObject* parent = nullptr);
#endif
    ~AssistantViewModel() override;
    QString state() const;
    bool connected() const;
    QString connectionLabel() const;
    RowTableModel* models() const;
    QString selectedModel() const;
    QString selectedEffort() const;
    QStringList availableEfforts() const;
    RowTableModel* messages() const;
    RowTableModel* selectedFiles() const;
    RowTableModel* skills() const;
    QString selectedSkill() const;
    QVariantMap pendingPlan() const;
    QVariantMap pendingQuestion() const;
    QString activeJobId() const;
    bool canCancel() const;
    QString lastError() const;
    QVariantMap usage() const;
    Q_INVOKABLE void refreshUsage();
    QString contextPreview() const;
    bool contextConsentRequired() const;
    void setSelectedModel(const QString& model);
    void setSelectedEffort(const QString& effort);
    /// Attach the live project through its existing worker and edit door; nullptr keeps a conversational session.
    void setProject(ProjectViewModel* project);
    Q_INVOKABLE void send(const QString& text);
    Q_INVOKABLE bool openReport(const QString& rowId, const QString& link);
    Q_INVOKABLE void selectSkill(const QString& id);
    Q_INVOKABLE void approvePlan(const QString& id);
    Q_INVOKABLE void answerQuestion(const QString& id, const QString& answer);
    Q_INVOKABLE void cancel();
    Q_INVOKABLE void signIn();
    Q_INVOKABLE void signOut();
    Q_INVOKABLE void clearHistory();
    Q_INVOKABLE QString beginFileSelection();
    Q_INVOKABLE bool addSelectedFiles(const QString& requestId, const QList<QUrl>& urls);
    Q_INVOKABLE void cancelFileSelection(const QString& requestId);
    Q_INVOKABLE bool removeSelectedFile(const QString& id);

   signals:
    void fileSelectionRetired(const QString& requestId);
    /// Revokes deferred UI intent even when replacement context bytes are identical.
    void conversationRetired();
    void stateChanged();
    void connectedChanged();
    void connectionLabelChanged();
    void selectedModelChanged();
    void selectedSkillChanged();
    void selectedEffortChanged();
    void availableEffortsChanged();
    void pendingPlanChanged();
    void pendingQuestionChanged();
    void activeJobIdChanged();
    void canCancelChanged();
    void lastErrorChanged();
    void usageChanged();
    void contextPreviewChanged();

   private:
    friend class Session;
    bool attachProject(ProjectViewModel* project, bool managedResult); // Session-only exact attachment result.
    enum class AttachmentClear { NotRequested, Discarded, Failed };
    AttachmentClear drainAttachmentClear() noexcept;
    bool clearHistoryNow(bool* committed = nullptr);
    bool resultSettledReady() const;
    struct State;
    std::unique_ptr<State> state_;
};
}  // namespace edi_app
