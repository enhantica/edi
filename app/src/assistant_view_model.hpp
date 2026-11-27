// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <QObject>
#include <QAbstractListModel>
#include "assistant_values.hpp"
#include <QTimer>
#include <QQuickWindow>
#include <QPointF>
#include <QEventPoint>
#include <QUrl>
#include <QList>
#include <QVariantMap>
#include <QJsonObject>
#include <QJsonValue>
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

/// Messages waiting for a running fit or app action, oldest first. Roles `messageId` and `text`.
class AssistantQueueModel : public QAbstractListModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Waiting messages belong to the assistant")
    Q_PROPERTY(int count READ count NOTIFY countChanged)

   public:
    enum Role { MessageIdRole = Qt::UserRole + 1, TextRole };
    struct Entry {
        QString id, text;
    };
    using QAbstractListModel::QAbstractListModel;
    void setEntries(QList<Entry> entries) {
        const bool counted = entries.size() != entries_.size();
        beginResetModel();
        entries_ = std::move(entries);
        endResetModel();
        if (counted) emit countChanged();
    }
    int count() const { return static_cast<int>(entries_.size()); }
    int rowCount(const QModelIndex& parent = QModelIndex()) const override { return parent.isValid() ? 0 : count(); }
    QVariant data(const QModelIndex& index, int role) const override {
        if (!index.isValid() || index.row() >= entries_.size()) return {};
        const auto& entry = entries_.at(index.row());
        return role == MessageIdRole ? QVariant(entry.id) : role == TextRole ? QVariant(entry.text) : QVariant();
    }
    QHash<int, QByteArray> roleNames() const override { return {{MessageIdRole, "messageId"}, {TextRole, "text"}}; }

   signals:
    void countChanged();

   private:
    QList<Entry> entries_;
};

/// Native QML presentation of the shared controller. Owned by Session, including while no project is open.
class AssistantViewModel : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to Session")
    Q_PROPERTY(edi_app::RowTableModel* skillSources READ skillSources CONSTANT)
    Q_PROPERTY(QString skillSourceRevision READ skillSourceRevision NOTIFY skillSourceRevisionChanged)
    Q_PROPERTY(QString skillSourceError READ skillSourceError NOTIFY skillSourceErrorChanged)
    Q_PROPERTY(bool skillSourceImporting READ skillSourceImporting NOTIFY skillSourceImportingChanged)
    Q_PROPERTY(bool showActions READ showActions WRITE setShowActions NOTIFY showActionsChanged)
    Q_PROPERTY(bool showingActions READ showingActions NOTIFY showingActionsChanged)
    Q_PROPERTY(QQuickWindow* actionWindow READ actionWindow WRITE setActionWindow NOTIFY actionWindowChanged)
    Q_PROPERTY(QVariantMap workReportReceipt READ workReportReceipt NOTIFY workReportReceiptChanged)
    Q_PROPERTY(QString state READ state NOTIFY stateChanged)
    Q_PROPERTY(bool connected READ connected NOTIFY connectedChanged)
    Q_PROPERTY(bool conversationAvailable READ conversationAvailable NOTIFY conversationAvailableChanged)
    Q_PROPERTY(QString connectionLabel READ connectionLabel NOTIFY connectionLabelChanged)
    Q_PROPERTY(edi_app::RowTableModel* models READ models CONSTANT)
    Q_PROPERTY(QString selectedModel READ selectedModel WRITE setSelectedModel NOTIFY selectedModelChanged)
    Q_PROPERTY(QString selectedEffort READ selectedEffort WRITE setSelectedEffort NOTIFY selectedEffortChanged)
    Q_PROPERTY(QStringList availableEfforts READ availableEfforts NOTIFY availableEffortsChanged)
    Q_PROPERTY(edi_app::RowTableModel* messages READ messages CONSTANT)
    Q_PROPERTY(edi_app::RowTableModel* sessions READ sessions CONSTANT)
    Q_PROPERTY(bool sessionsLoading READ sessionsLoading NOTIFY sessionsLoadingChanged)
    Q_PROPERTY(bool sessionsHaveMore READ sessionsHaveMore NOTIFY sessionsHaveMoreChanged)
    Q_PROPERTY(QString sessionsError READ sessionsError NOTIFY sessionsErrorChanged)
    Q_PROPERTY(QString sessionSelection READ sessionSelection NOTIFY sessionSelectionChanged)
    Q_PROPERTY(QString sessionDraft READ sessionDraft WRITE setSessionDraft NOTIFY sessionDraftChanged)
    Q_PROPERTY(bool cachedHistoryClearing READ cachedHistoryClearing NOTIFY cachedHistoryClearingChanged)
    Q_PROPERTY(QString cachedHistoryError READ cachedHistoryError NOTIFY cachedHistoryErrorChanged)
    Q_PROPERTY(edi_app::RowTableModel* selectedFiles READ selectedFiles CONSTANT)
    Q_PROPERTY(edi_app::RowTableModel* skills READ skills CONSTANT)
    Q_PROPERTY(QString selectedSkill READ selectedSkill NOTIFY selectedSkillChanged)
    Q_PROPERTY(edi_app::AssistantPendingPlan pendingPlan READ pendingPlan NOTIFY pendingPlanChanged)
    Q_PROPERTY(bool chatRevealRequested READ chatRevealRequested NOTIFY chatRevealRequestedChanged)
    Q_PROPERTY(edi_app::AssistantPendingQuestion pendingQuestion READ pendingQuestion NOTIFY pendingQuestionChanged)
    Q_PROPERTY(QString activeJobId READ activeJobId NOTIFY activeJobIdChanged)
    Q_PROPERTY(bool canCancel READ canCancel NOTIFY canCancelChanged)
    Q_PROPERTY(QString lastError READ lastError NOTIFY lastErrorChanged)
    Q_PROPERTY(QVariantMap usage READ usage NOTIFY usageChanged)
    Q_PROPERTY(edi_app::AssistantAccount account READ account NOTIFY accountChanged)
    /// Every recorded account, grouped by provider in the Account dialog (ADR-0108 §8, §9).
    Q_PROPERTY(QList<edi_app::AssistantAccountEntry> accounts READ accounts NOTIFY accountsChanged)
    /// The providers edi offers, in order.
    Q_PROPERTY(QList<edi_app::AssistantProviderInfo> providers READ providers CONSTANT)
    /// Non-empty while the active Claude account runs under an organisation's managed settings or hooks that the user
    /// has not acknowledged yet; Send waits for acknowledgeManagedSettings() (ADR-0108 §4).
    Q_PROPERTY(QString managedSettingsNotice READ managedSettingsNotice NOTIFY managedSettingsNoticeChanged)
    /// The active account's provider (chatgpt, claude, copilot) and the company receiving the data.
    Q_PROPERTY(edi_app::AssistantProviderInfo activeProvider READ activeProvider NOTIFY activeProviderChanged)
    Q_PROPERTY(QString contextPreview READ contextPreview NOTIFY contextPreviewChanged)
    Q_PROPERTY(QString contextConsentIdentity READ contextConsentIdentity NOTIFY contextConsentIdentityChanged)
    Q_PROPERTY(bool draftAdmissionReady READ draftAdmissionReady NOTIFY draftAdmissionReadyChanged)
    Q_PROPERTY(bool contextConsentRequired READ contextConsentRequired NOTIFY contextConsentRequiredChanged)
    Q_PROPERTY(bool contextApprovalBlocked READ contextApprovalBlocked NOTIFY contextApprovalBlockedChanged)
    Q_PROPERTY(edi_app::AssistantQueueModel* queuedMessages READ queuedMessages CONSTANT)

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
    bool conversationAvailable() const;
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
    // The saved project Open a conversation selection asked for failed (not cancelled): the selection settles with
    // the Open's own cause; a startup reopen then leaves the ordinary Connect offer.
    Q_INVOKABLE void failSessionProjectOpen(const QString& intent, const QString& cause);
    QString sessionDraft() const;
    void setSessionDraft(const QString&);
    Q_INVOKABLE void restoreLastSession();
    Q_INVOKABLE bool requestAssistantPane(QObject* originalToggle);
    Q_INVOKABLE void continueSessionRestore(const QString& threadId);
    bool cachedHistoryClearing() const;
    QString cachedHistoryError() const;
    Q_INVOKABLE void clearCachedHistory();
    Q_INVOKABLE void showSteps(const QString& group, bool shown);
    RowTableModel* selectedFiles() const;
    RowTableModel* skills() const;
    QString selectedSkill() const;
    AssistantPendingPlan pendingPlan() const;
    bool chatRevealRequested() const;
    Q_INVOKABLE void dismissChatReveal();
    AssistantPendingQuestion pendingQuestion() const;
    QString activeJobId() const;
    bool canCancel() const;
    QString lastError() const;
    QVariantMap usage() const;
    AssistantAccount account() const;
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
    Q_INVOKABLE edi_app::AssistantDraftAdmission submitDraftAdmission(const QString& text);
    /// Messages waiting for a running fit or app action, oldest first.
    AssistantQueueModel* queuedMessages() const;
    /// Take a waiting message back to its own conversation's draft; false when it is unknown or already being sent.
    Q_INVOKABLE bool cancelQueuedMessage(const QString& id);
    /// Text of returned waiting messages for the conversation the composer shows; empty for any other.
    Q_INVOKABLE QString takeReturnedMessages();
    Q_INVOKABLE QString workReportDocument();
    /// Display-only intent label for a native action identifier; no action is executed.
    Q_INVOKABLE QString nativeActionLabel(const QString& action) const;
    Q_INVOKABLE QString nativeActionDescription(const QString& action, const QString& code) const;
    /// Established owner-thread safe human read; delegates canonical lookup/projection to prepareActivityRead.
    /// Returns the original map shape, including optional captured provenance, or empty on refusal/unavailability.
    Q_INVOKABLE QVariantMap activityHumanDetails(const QString& rowId, const QString& kind, const QString& status) const;
    /// Established explicit technical read; returns original indented canonical JSON or empty on refusal.
    Q_INVOKABLE QString activityTechnicalDetails(const QString& rowId, const QString& kind, const QString& status) const;
    /// Ephemeral full-human read of one original history value; never a stored snapshot or QML capability.
    struct PreparedActivityRead {
        QJsonObject payload;
        QJsonValue text;
        QString provenance, technical;
        QString rowId, kind, status;
        bool hasProvenance = false;
        std::function<bool()> current;
    };
    /// Owner-thread only. Applies the original first-id/kind/status and scope/version guards.
    /// Human mode projects only safe details; technical mode serializes only the original row.
    /// Technical JSON is explicit; unavailable reads have no current predicate.
    PreparedActivityRead prepareActivityRead(const QString& rowId, const QString& kind,
                                             const QString& status, bool includeTechnical) const;
    // Original normal-dialog observations only; this is not a model tool.
    Q_INVOKABLE bool observeCreateDialog(QObject* form, const QString& intent, const QString& outcome);
    Q_INVOKABLE bool openReport(const QString& rowId, const QString& link);
    Q_INVOKABLE void selectSkill(const QString& id);
    Q_INVOKABLE void approvePlan(const QString& id);
    Q_INVOKABLE void answerQuestion(const QString& id, const QString& answer);
    Q_INVOKABLE bool nativeProjectCreateCurrent(const QString& intent) const;
    Q_INVOKABLE void nativeProjectCreateReady(const QString& intent,bool ready);
    Q_INVOKABLE void nativeProjectCreateAsked(const QString& intent,QObject* form);
    Q_INVOKABLE void nativeProjectCreateDiscard(const QString& intent);
    Q_INVOKABLE bool nativeProjectCreateDiscards(const QString& intent) const;
    Q_INVOKABLE bool nativeProjectCreateSave(const QString& intent);
    // Actual grab owns this opaque proof until its sole tap, cancel or ungrab.
    // Final delivery only validates the original owner; it never cancels anew.
    Q_INVOKABLE edi_app::AssistantManualControlToken beginManualControlInput(QQuickItem* control, const QEventPoint& point, QObject* actionOwner);
    Q_INVOKABLE bool completeManualControlInput(QQuickItem* control, const QEventPoint& point,
                                              QObject* actionOwner, const edi_app::AssistantManualControlToken& proof);
    Q_INVOKABLE void cancel();
    // After a desktop Save: the saved conversation association follows the project folder.
    void projectSaved();
    Q_INVOKABLE bool resumeConnection();
    Q_INVOKABLE void signIn();
    Q_INVOKABLE QString acceptConnectionOffer(const QString& identity);
    Q_INVOKABLE void signOut();
    /// Make another recorded account the active one: the current runtime stops without signing out and a new,
    /// empty conversation starts with the other account. Refused while a turn or trial runs.
    Q_INVOKABLE void switchAccount(const QString& provider, const QString& id);
    /// Start an account of `provider` in a fresh config home; it is recorded once its sign-in succeeds.
    Q_INVOKABLE void addAccount(const QString& provider, const QString& host = {});
    QList<AssistantAccountEntry> accounts() const;
    QString managedSettingsNotice() const;
    AssistantProviderInfo activeProvider() const;
    /// The user read the managed-settings notice for the active account; remembered per account.
    Q_INVOKABLE void acknowledgeManagedSettings();
    QList<AssistantProviderInfo> providers() const;
    Q_INVOKABLE void clearHistory();
    Q_INVOKABLE QString beginFileSelection(bool requireSignedIn = false);
    Q_INVOKABLE bool addSelectedFiles(const QString& requestId, const QList<QUrl>& urls);
    Q_INVOKABLE void cancelFileSelection(const QString& requestId);
    Q_INVOKABLE bool removeSelectedFile(const QString& id);

   signals:
    void skillSourceRevisionChanged();
    void skillSourceErrorChanged();
    void skillSourceImportingChanged();
    void sessionsLoadingChanged();
    void sessionsHaveMoreChanged();
    void sessionsErrorChanged();
    void sessionSelectionChanged();
    void cachedHistoryClearingChanged();
    void cachedHistoryErrorChanged();
    void contextConsentIdentityChanged();
    void contextConsentRequiredChanged();
    void contextApprovalBlockedChanged();
    void sessionsChanged();
    void sessionSelected(const QString& threadId);
    void cachedHistoryChanged();
    void sessionSelectionStarted(const QString& threadId);
    void sessionDraftRestored(const QString& threadId,const QString& text);
    void sessionDraftChanged();
    void sessionProjectRequested(const QString& threadId,const QUrl& location,const QString& intent);
    void sessionConsentRequested(const QString& threadId);
    void workReportFinished(QVariantMap receipt);
    void workReportReceiptChanged();
    void accountChanged();
    void accountsChanged();
    void managedSettingsNoticeChanged();
    void activeProviderChanged();
    /// A saved conversation of another account was asked for; the panel offers Switch account and Cancel.
    void sessionAccountSwitchRequested(const QString& threadId, const QString& account, const QString& provider);
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
    void conversationAvailableChanged();
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
    void queuedMessagesChanged();
    void queuedMessageReturned(const QString& text);

   protected:
    bool eventFilter(QObject* watched, QEvent* event) override;
   private:
    friend class Session;
    mutable AssistantQueueModel* queued_model_ = nullptr;
    QString submitDraftImpl(const QString&,bool* accountWaiting);
    void finishHistoryInitialization() noexcept;
    bool ordinarySaveNotification(ProjectViewModel*) const noexcept;
    bool ordinaryProjectCreationPending() const;
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
    void finishOrdinaryProjectCreationOutcome(const QString& intent, const ProjectCreationResult& outcome) noexcept;
    void finishOrdinaryProjectCreation(ProjectViewModel*, const QString& intent, bool committed) noexcept;
    bool resultSettledReady() const;
    struct State;
    std::unique_ptr<State> state_;
    // Sign-out and account switching share one retirement; only sign-out asks the runtime to log out.
    void retireConnection(bool logout);
};
}  // namespace edi_app
