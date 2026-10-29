// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <QObject>
#include <QTimer>
#include <QQuickWindow>
#include <QPointF>
#include <QEventPoint>
#include <QUrl>
#include <QList>
#include <QVariantMap>
#include <QtQml/qqmlregistration.h>
#include <memory>
#include <functional>

#include "edi/assistant.hpp"
#include "row_table_model.hpp"
#include "assistant_work_report.hpp"
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
    Q_PROPERTY(edi_app::RowTableModel* skillSources READ skillSources CONSTANT)
    Q_PROPERTY(QString skillSourceRevision READ skillSourceRevision NOTIFY skillSourcesChanged)
    Q_PROPERTY(QString skillSourceError READ skillSourceError NOTIFY skillSourcesChanged)
    Q_PROPERTY(bool skillSourceImporting READ skillSourceImporting NOTIFY skillSourcesChanged)
    Q_PROPERTY(bool showActions READ showActions WRITE setShowActions NOTIFY showActionsChanged)
    Q_PROPERTY(bool showingActions READ showingActions NOTIFY showingActionsChanged)
    Q_PROPERTY(QQuickWindow* actionWindow READ actionWindow WRITE setActionWindow NOTIFY actionWindowChanged)
    Q_PROPERTY(QVariantMap workReportReceipt READ workReportReceipt NOTIFY workReportReceiptChanged)
    Q_PROPERTY(QString state READ state NOTIFY stateChanged)
    Q_PROPERTY(bool connected READ connected NOTIFY connectedChanged)
    Q_PROPERTY(QString connectionLabel READ connectionLabel NOTIFY connectionLabelChanged)
    Q_PROPERTY(edi_app::RowTableModel* models READ models CONSTANT)
    Q_PROPERTY(QString selectedModel READ selectedModel WRITE setSelectedModel NOTIFY selectedModelChanged)
    Q_PROPERTY(QString selectedEffort READ selectedEffort WRITE setSelectedEffort NOTIFY selectedEffortChanged)
    Q_PROPERTY(QStringList availableEfforts READ availableEfforts NOTIFY availableEffortsChanged)
    Q_PROPERTY(edi_app::RowTableModel* messages READ messages CONSTANT)
    Q_PROPERTY(edi_app::RowTableModel* sessions READ sessions CONSTANT)
    Q_PROPERTY(bool sessionsLoading READ sessionsLoading NOTIFY sessionsChanged)
    Q_PROPERTY(bool sessionsHaveMore READ sessionsHaveMore NOTIFY sessionsChanged)
    Q_PROPERTY(QString sessionsError READ sessionsError NOTIFY sessionsChanged)
    Q_PROPERTY(QString sessionSelection READ sessionSelection NOTIFY sessionsChanged)
    Q_PROPERTY(QString sessionDraft READ sessionDraft WRITE setSessionDraft)
    Q_PROPERTY(bool cachedHistoryClearing READ cachedHistoryClearing NOTIFY cachedHistoryChanged)
    Q_PROPERTY(QString cachedHistoryError READ cachedHistoryError NOTIFY cachedHistoryChanged)
    Q_PROPERTY(edi_app::RowTableModel* selectedFiles READ selectedFiles CONSTANT)
    Q_PROPERTY(edi_app::RowTableModel* skills READ skills CONSTANT)
    Q_PROPERTY(QString selectedSkill READ selectedSkill NOTIFY selectedSkillChanged)
    Q_PROPERTY(QVariantMap pendingPlan READ pendingPlan NOTIFY pendingPlanChanged)
    Q_PROPERTY(bool chatRevealRequested READ chatRevealRequested NOTIFY chatRevealRequestedChanged)
    Q_PROPERTY(QVariantMap pendingQuestion READ pendingQuestion NOTIFY pendingQuestionChanged)
    Q_PROPERTY(QString activeJobId READ activeJobId NOTIFY activeJobIdChanged)
    Q_PROPERTY(bool canCancel READ canCancel NOTIFY canCancelChanged)
    Q_PROPERTY(QString lastError READ lastError NOTIFY lastErrorChanged)
    Q_PROPERTY(QVariantMap usage READ usage NOTIFY usageChanged)
    Q_PROPERTY(QVariantMap account READ account NOTIFY accountChanged)
    Q_PROPERTY(QString contextPreview READ contextPreview NOTIFY contextPreviewChanged)
    Q_PROPERTY(QString contextConsentIdentity READ contextConsentIdentity NOTIFY contextPreviewChanged)
    Q_PROPERTY(bool draftAdmissionReady READ draftAdmissionReady NOTIFY draftAdmissionReadyChanged)
    Q_PROPERTY(bool contextConsentRequired READ contextConsentRequired NOTIFY contextPreviewChanged)
    Q_PROPERTY(bool contextApprovalBlocked READ contextApprovalBlocked NOTIFY contextPreviewChanged)

   public:
    explicit AssistantViewModel(QObject* parent = nullptr, AssistantWorkReportOptions options = {});
#ifndef __EMSCRIPTEN__
    AssistantViewModel(edi::assistant::native::NativeDependencies dependencies, QObject* parent = nullptr, AssistantWorkReportOptions options = {});
#endif
    ~AssistantViewModel() override;
    QVariantMap workReportReceipt() const;
    Q_INVOKABLE QVariantMap captureWorkReport();
    bool showActions() const;
    bool showingActions() const;
    QQuickWindow* actionWindow() const;
    void setShowActions(bool value);
    void setActionWindow(QQuickWindow* window);
    QString state() const;
    bool connected() const;
    QString connectionLabel() const;
    RowTableModel* models() const;
    QString selectedModel() const;
    QString selectedEffort() const;
    QStringList availableEfforts() const;
    RowTableModel* messages() const;
    RowTableModel* sessions() const;
    bool sessionsLoading() const;
    bool sessionsHaveMore() const;
    QString sessionsError() const;
    Q_INVOKABLE void refreshSessions(bool nextPage = false);
    Q_INVOKABLE void archiveSession(const QString& threadId);
    Q_INVOKABLE void selectSession(const QString& threadId);
    QString sessionSelection() const;
    Q_INVOKABLE bool sessionProjectRestorePending(const QString& intent = {}) const;
    Q_INVOKABLE bool beginSessionProjectRestore(const QString& intent);
    Q_INVOKABLE void cancelSessionSelection(const QString& intent = {});
    QString sessionDraft() const;
    void setSessionDraft(const QString&);
    Q_INVOKABLE void restoreLastSession();
    Q_INVOKABLE bool requestAssistantPane(QObject* originalToggle);
    Q_INVOKABLE void continueSessionRestore(const QString& threadId);
    bool cachedHistoryClearing() const;
    QString cachedHistoryError() const;
    Q_INVOKABLE void clearCachedHistory();
    RowTableModel* selectedFiles() const;
    RowTableModel* skills() const;
    QString selectedSkill() const;
    QVariantMap pendingPlan() const;
    bool chatRevealRequested() const;
    Q_INVOKABLE void dismissChatReveal();
    QVariantMap pendingQuestion() const;
    QString activeJobId() const;
    bool canCancel() const;
    QString lastError() const;
    QVariantMap usage() const;
    QVariantMap account() const;
    RowTableModel* skillSources() const;
    QString skillSourceError() const;
    QString skillSourceRevision() const;
    bool skillSourceImporting() const;
    Q_INVOKABLE bool addWebSkillSource(const QString& token,const QUrl& url);
    Q_INVOKABLE void cancelWebSkillSourceImport();
    Q_INVOKABLE QString beginSkillSourceSelection();
    Q_INVOKABLE bool addSkillSource(const QString& token, const QUrl& folder);
    Q_INVOKABLE void cancelSkillSourceSelection(const QString& token);
    Q_INVOKABLE bool setSkillSourceEnabled(const QString& id, bool enabled, const QString& revision = {});
    Q_INVOKABLE bool removeSkillSource(const QString& id, const QString& revision = {});
    Q_INVOKABLE void refreshSkillSources();
    Q_INVOKABLE void refreshUsage();
    QString contextPreview() const;
    QString contextConsentIdentity() const;
    bool draftAdmissionReady() const;
    bool contextConsentRequired() const;
    bool contextApprovalBlocked() const;
    void setSelectedModel(const QString& model);
    void setSelectedEffort(const QString& effort);
    /// Attach the live project through its existing worker and edit door; nullptr keeps a conversational session.
    void setProject(ProjectViewModel* project);
    Q_INVOKABLE void send(const QString& text);
    /// Submit on the owner thread; return its admitted row ID, or empty on refusal. Durable completed status alone acknowledges it.
    Q_INVOKABLE QString submitDraft(const QString& text);
    Q_INVOKABLE QVariantMap submitDraftAdmission(const QString& text);
    Q_INVOKABLE QString workReportDocument();
    /// Display-only intent label for a native action identifier; no action is executed.
    Q_INVOKABLE QString nativeActionLabel(const QString& action) const;
    Q_INVOKABLE QString nativeActionDescription(const QString& action, const QString& code) const;
    Q_INVOKABLE QVariantMap activityHumanDetails(const QString& rowId, const QString& kind, const QString& status) const;
    Q_INVOKABLE QString activityTechnicalDetails(const QString& rowId, const QString& kind, const QString& status) const;
    // Original normal-dialog observations only; this is not a model tool.
    Q_INVOKABLE bool observeCreateDialog(QObject* form, const QString& intent, const QString& outcome);
    Q_INVOKABLE bool openReport(const QString& rowId, const QString& link);
    Q_INVOKABLE void selectSkill(const QString& id);
    Q_INVOKABLE void approvePlan(const QString& id);
    Q_INVOKABLE void answerQuestion(const QString& id, const QString& answer);
    Q_INVOKABLE bool nativeProjectCreateCurrent(const QString& intent) const;
    Q_INVOKABLE void nativeProjectCreateReady(const QString& intent,bool ready);
    Q_INVOKABLE void nativeProjectCreateSaveChoice(const QString& intent,QObject* form,QObject* button);
    Q_INVOKABLE bool nativeProjectCreateSave(const QString& intent);
    // Actual grab owns this opaque proof until its sole tap, cancel or ungrab.
    // Final delivery only validates the original owner; it never cancels anew.
    Q_INVOKABLE QVariant beginManualControlInput(QQuickItem* control, const QEventPoint& point, QObject* actionOwner);
    Q_INVOKABLE bool completeManualControlInput(QQuickItem* control, const QEventPoint& point,
                                              QObject* actionOwner, const QVariant& proof);
    Q_INVOKABLE void cancel();
    Q_INVOKABLE bool resumeConnection();
    Q_INVOKABLE void signIn();
    Q_INVOKABLE QString acceptConnectionOffer(const QString& identity);
    Q_INVOKABLE void signOut();
    Q_INVOKABLE void clearHistory();
    Q_INVOKABLE QString beginFileSelection(bool requireSignedIn = false);
    Q_INVOKABLE bool addSelectedFiles(const QString& requestId, const QList<QUrl>& urls);
    Q_INVOKABLE void cancelFileSelection(const QString& requestId);
    Q_INVOKABLE bool removeSelectedFile(const QString& id);

   signals:
    void sessionsChanged();
    void sessionSelected(const QString& threadId);
    void cachedHistoryChanged();
    void sessionSelectionStarted(const QString& threadId);
    void sessionDraftRestored(const QString& threadId,const QString& text);
    void sessionProjectRequested(const QString& threadId,const QUrl& location,const QString& intent);
    void sessionConsentRequested(const QString& threadId);
    void workReportFinished(QVariantMap receipt);
    void workReportReceiptChanged();
    void accountChanged();
    void showActionsChanged();
    void showingActionsChanged();
    void actionControlsRequested(); // Original control reveal request, including repeated true requests.
    void actionWindowChanged();
    void actionPointerShown();
    void actionPointerMoved(const QPointF& position);
    void actionPointerPressed();
    void actionPointerHidden();
    void actionManualTakeover(); // Manual controls stay exposed for the original user event.
    void actionPageRequested(const QString& page, bool extra); // Normal-mode UI following; no scientific write.
    void fileSelectionRetired(const QString& requestId);
    /// Revokes deferred UI intent even when replacement context bytes are identical.
    void conversationRetired();
    void conversationClearRequested(const QString& intent);
    void conversationClearCommitted(const QString& intent);
    void stateChanged();
    void connectedChanged();
    void connectionLabelChanged();
    void selectedModelChanged();
    void selectedSkillChanged();
    void selectedEffortChanged();
    void availableEffortsChanged();
    void pendingPlanChanged();
    void chatRevealRequestedChanged();
    void pendingQuestionChanged();
    void activeJobIdChanged();
    void canCancelChanged();
    void lastErrorChanged();
    void skillSourcesChanged();
    void skillSourceSelectionRetired(const QString& token);
    void usageChanged();
    void contextPreviewChanged();
    void draftAdmissionReadyChanged();

   protected:
    bool eventFilter(QObject* watched, QEvent* event) override;
   private:
    friend class Session;
    QString submitDraftImpl(const QString&,bool* accountWaiting);
    void finishHistoryInitialization() noexcept;
    bool ordinarySaveNotification(ProjectViewModel*) const noexcept;
    struct ProjectResetInputs;
    std::shared_ptr<ProjectResetInputs> prepareProjectResetInputs();
    bool attachProject(ProjectViewModel* project, bool managedResult, bool ordinaryEmptyCreate = false, const std::shared_ptr<ProjectResetInputs>& resetInputs = {}); // Session-only exact attachment result.
    enum class AttachmentClear { NotRequested, Discarded, Failed };
    AttachmentClear drainAttachmentClear() noexcept;
    bool clearHistoryNow(bool* logicalDiscarded = nullptr);
    bool commitNativeProject(ProjectViewModel* project) noexcept;
    // Existing ordinary Create dialog only; its captured original intent cannot
    // become an unauthenticated fallback after Stop/replacement.
    bool prepareSessionProjectRestore(ProjectViewModel*,const QString& source,const std::function<bool()>& commit);
    bool retainsSessionProject(ProjectViewModel*) const;
    bool prepareOrdinaryProjectCreation(ProjectViewModel*, const QString& intent, const QString& location = {});
    void finishOrdinaryProjectCreationOutcome(const QString& intent, const QVariantMap& outcome) noexcept;
    void finishOrdinaryProjectCreation(ProjectViewModel*, const QString& intent, bool committed) noexcept;
    bool resultSettledReady() const;
    struct State;
    std::unique_ptr<State> state_;
};
}  // namespace edi_app
