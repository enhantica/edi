// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_APP_INFO_HPP
#define EDI_APP_APP_INFO_HPP

#include <QColor>
#include <QDir>
#include <QFileInfo>
#include <QJSValue>
#include <QVariantMap>
#include <QObject>
#include <QPoint>
#include <QString>
#include <QStringList>
#include <QUrl>
#include <QtQml/qqmlregistration.h>

#include "edi/palette.hpp"

// What the app says about itself — its name, version and links. The only source of the identity the user
// sees; the base's own fallback (gui-components ProjectConfig.js) is never shown.
class ApplicationInfo : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_SINGLETON
    Q_PROPERTY(QString name READ name CONSTANT)
    Q_PROPERTY(QString namePrefixForLogo READ namePrefixForLogo CONSTANT)
    Q_PROPERTY(QString nameSuffixForLogo READ nameSuffixForLogo CONSTANT)
    Q_PROPERTY(QString version READ version CONSTANT)
    Q_PROPERTY(QString releaseDate READ releaseDate CONSTANT)
    Q_PROPERTY(QString homepageUrl READ homepageUrl CONSTANT)
    Q_PROPERTY(QString docsUrl READ docsUrl CONSTANT)
    Q_PROPERTY(QString issuesUrl READ issuesUrl CONSTANT)
    Q_PROPERTY(QString contactUrl READ contactUrl CONSTANT)
    Q_PROPERTY(QString licenseUrl READ licenseUrl CONSTANT)
    Q_PROPERTY(QString appLicenseUrl READ appLicenseUrl CONSTANT)
    Q_PROPERTY(QString copyingUrl READ copyingUrl CONSTANT)
    Q_PROPERTY(QString noticesUrl READ noticesUrl CONSTANT)
    // edi's own licences, as the About window names them: their SPDX identifiers and their bundled texts, index for
    // index.
    Q_PROPERTY(QStringList appLicenceIds READ appLicenceIds CONSTANT)
    Q_PROPERTY(QStringList appLicenceUrls READ appLicenceUrls CONSTANT)
    Q_PROPERTY(QStringList componentNames READ componentNames CONSTANT)
    Q_PROPERTY(QStringList componentVersions READ componentVersions CONSTANT)
    Q_PROPERTY(QStringList componentLicences READ componentLicences CONSTANT)
    Q_PROPERTY(QStringList componentUses READ componentUses CONSTANT)
    Q_PROPERTY(QString description READ description CONSTANT)
    Q_PROPERTY(QString copyrightHolder READ copyrightHolder CONSTANT)
    Q_PROPERTY(QString developerYearsFrom READ developerYearsFrom CONSTANT)
    Q_PROPERTY(QString developerYearsTo READ developerYearsTo CONSTANT)
    // The element symbols of the core's element table, H to Og: what an atom-type picker lists.
    Q_PROPERTY(QStringList elementSymbols READ elementSymbols CONSTANT)
    // The Develop preference's engine thread counts: whether this build can run fills on several threads
    // (the single-thread web build cannot), and the largest count it offers.
    Q_PROPERTY(bool engineThreadsSelectable READ engineThreadsSelectable CONSTANT)
    Q_PROPERTY(int engineThreadsMaximum READ engineThreadsMaximum CONSTANT)
    Q_PROPERTY(bool assistantAvailable READ assistantAvailable CONSTANT)
    Q_PROPERTY(QString assistantUnavailableReason READ assistantUnavailableReason CONSTANT)

   public:
    enum EditorKind { ParameterFieldEditor, ParameterCellEditor, TextCellEditor };
    Q_ENUM(EditorKind)
    enum NumberOperation {
        NumberScientific,
        NumberScientificExponent,
        NumberExponentOf,
        NumberFull,
        NumberPlainFull,
        NumberParameter,
        NumberRuled,
        NumberRounded,
        NumberError,
        NumberSharedExponent,
        NumberPlain,
        NumberAxisFormat,
        NumberAxisTick,
        NumberDecimal,
        NumberCompact,
        NumberSuDigits,
        NumberRuledDigits,
        NumberNarrowParameter,
        NumberFitted,
        NumberOwnUncertainty,
        NumberExponent
    };
    Q_ENUM(NumberOperation)
    enum FitOutcomeOperation { FitIcon, FitRing, FitWord, FitMeaning, FitColor, FitTextColor };
    Q_ENUM(FitOutcomeOperation)

    explicit ApplicationInfo(QObject* parent = nullptr);

    QString name() const { return QStringLiteral("EasyDiffraction"); }
    QString namePrefixForLogo() const { return QStringLiteral("easy"); }
    QString nameSuffixForLogo() const { return QStringLiteral("diffraction"); }
    // The demo mode's images are a regression pin compared across commits, so they show a fixed
    // identity instead of the build's version and date.
    static void useDemoIdentity();
    static bool demoIdentity();
    QString version() const;
    QString releaseDate() const;
    QString homepageUrl() const { return QStringLiteral("https://easydiffraction.org"); }
    QString docsUrl() const { return QStringLiteral("https://docs.easydiffraction.org/app/"); }
    QString issuesUrl() const { return QStringLiteral("https://github.com/enhantica/edi/issues"); }
    QString contactUrl() const { return QStringLiteral("https://easydiffraction.org/#contact"); }
    // The licence texts are bundled in the app's resources, so the About window shows them without a network:
    // the source code's (BSD 3-Clause), the distributed app's (GPL-3.0: it links Qt Graphs and Qt Quick 3D;
    // ADR-0015 §6), and the notices of every component the app links or bundles.
    QString licenseUrl() const { return QStringLiteral("qrc:/LICENSE"); }
    QString appLicenseUrl() const { return QStringLiteral("qrc:/app/DISTRIBUTION-LICENSE.md"); }
    QString copyingUrl() const { return QStringLiteral("qrc:/COPYING"); }
    QString noticesUrl() const { return QStringLiteral("qrc:/THIRD-PARTY-NOTICES"); }
    QStringList appLicenceIds() const { return {QStringLiteral("BSD-3-Clause"), QStringLiteral("GPL-3.0-only")}; }
    QStringList appLicenceUrls() const { return {licenseUrl(), copyingUrl()}; }
    // The components this build carries, from DEPENDENCIES.md's column for its surface (the desktop or the web app), in
    // that file's order: their names, versions (empty when none is given), licences and uses, index for index.
    QStringList componentNames() const { return componentColumn(0); }
    QStringList componentVersions() const { return componentColumn(3); }
    QStringList componentLicences() const { return componentColumn(1); }
    QStringList componentUses() const { return componentColumn(2); }
    // The licence text the notices give for the component at `index` in the lists above, without its indent;
    // empty for an index out of range.
    Q_INVOKABLE QString componentLicenceText(int index) const;
    // The text of a bundled licence resource (one of the URLs above); empty for any other URL.
    Q_INVOKABLE QString licenceText(const QString& url) const;
    // The diagnostics view's text (the owner, 2026-10-06): the platform and browser, the build flavour and why it
    // was chosen (web), threads, the Qt version and graphics backend, edi's and crysta's versions with the crysta
    // SDK commit, and the feature switches; one "name: value" line each, to read and to copy.
    Q_INVOKABLE QString diagnostics() const;
    /// Original Panel projection/selection on the current QML thread; no cache or canonical lookup.
    /// Borrows actual Panel/engine values; original JS errors remain pending except the projection's explicit catch.
    Q_INVOKABLE QJSValue assistantUsageData(QObject* panel) const;
    Q_INVOKABLE QJSValue assistantUsageWindow(QObject* panel) const;
    Q_INVOKABLE QJSValue assistantAllowanceWindow(QObject* panel, const QJSValue& minutes) const;
    Q_INVOKABLE QJSValue assistantUsageAllowances(QObject* panel) const;
    /// Original account display relations and shared native word formatter bridge.
    /// Borrows current QML-thread values; no new normalization, identity or disclosure policy.
    Q_INVOKABLE QJSValue assistantAccountPlan(QObject* panel) const;
    Q_INVOKABLE QJSValue assistantAccountInitial(QObject* panel) const;
    Q_INVOKABLE QJSValue assistantAccountPlanLabel(QObject* panel) const;
    /// Three-argument word formatter bridge; index and array are ignored as in the original callback.
    Q_INVOKABLE QJSValue assistantAccountPlanWord(const QJSValue& word, const QJSValue& index,
                                                const QJSValue& array) const;
    /// Original Panel translation/String/Date/Math presentation relations; errors stay pending.
    Q_INVOKABLE QJSValue assistantUsageCaption(QObject* panel) const;
    Q_INVOKABLE QJSValue assistantAllowanceColor(const QJSValue& remaining, const QJSValue& colors) const;
    Q_INVOKABLE QJSValue assistantUsageResetLabel(const QJSValue& value, const QJSValue& now) const;
    /// Original Date.now source and existing dialog clock publication; no timer/service is added.
    Q_INVOKABLE QJSValue assistantUsageNow() const;
    Q_INVOKABLE void refreshAssistantUsageClock(QObject* dialog) const;
    /// Apply the original connected-change close condition at its original current-owner read point.
    Q_INVOKABLE void assistantAccountConnectionChanged(QObject* panel, QObject* dialog) const;
    // Puts `text` on the clipboard (the web build's needs the click that asks for it).
    Q_INVOKABLE void copyText(const QString& text) const;
    Q_INVOKABLE QString fileSizeKilobytes(qint64 bytes) const;
    // Declaration-only members of existing global ApplicationInfo (QML singleton ApplicationInfo).
    /// Capture the original session draft intent in its existing view field.
    /// Borrows actual QML-thread controls; no retained pointers; JS exceptions remain pending.
    Q_INVOKABLE void composerSessionSelectionStarted(QObject* composer, QObject* editor, const QString& threadId) const;
    /// Apply the original restore/IME/successor checks, then publish actual text through sessionDraft.
    /// Borrows actual QML-thread controls; no extra account/window policy; JS exceptions remain pending.
    Q_INVOKABLE void composerSessionDraftRestored(QObject* composer, QObject* editor,
                                                 const QString& threadId, const QString& text) const;
    /// Capture the original Clear text/revision/intent without consuming editor text.
    /// Borrows actual QML-thread controls; data stays in the original view field; errors remain pending.
    Q_INVOKABLE void composerConversationClearRequested(QObject* composer, QObject* editor, const QString& intent) const;
    /// Consume only the matching Clear record and clear the unchanged, idle original editor.
    /// Borrows actual QML-thread controls; no native/history operation is initiated; errors remain pending.
    Q_INVOKABLE void composerConversationClearCommitted(QObject* composer, QObject* editor, const QString& intent) const;
    /// Apply original revision/pending/report retirement resets, in order, on the QML thread.
    /// Borrows the actual composer; no additional record or editor reset; errors remain pending.
    Q_INVOKABLE void composerConversationRetired(QObject* composer) const;
    /// Preserve original text/preedit/IME revision increments; text events also publish sessionDraft.
    /// Borrows actual QML-thread controls; preserves native int conversion; errors remain pending.
    Q_INVOKABLE void composerDraftEdited(QObject* composer, QObject* editor, bool publishText) const;
    /// Refresh the selected-file pending display, advancing the revision only for file change events.
    /// Borrows the actual Composer; selection and admission remain in AssistantViewModel.
    Q_INVOKABLE void composerRefreshFilePresentation(QObject* composer, bool advanceRevision) const;
    /// Acknowledge the current message table in the original Composer function scope.
    Q_INVOKABLE void composerAcknowledgeVisiblePrompt() const;
    /// Original window focus procedures; view state and Qt's delayed queue retain ownership.
    Q_INVOKABLE bool assistantContainsItem(const QJSValue& ancestor, const QJSValue& item) const;
    Q_INVOKABLE QJSValue assistantWorkflowPage() const;
    Q_INVOKABLE void rehostAssistant() const;
    Q_INVOKABLE void focusAssistantOpener() const;
    Q_INVOKABLE void retireAssistantFocus() const;
    Q_INVOKABLE void restoreAssistantFocus() const;
    Q_INVOKABLE bool assistantHomeFocusCovered() const;
    Q_INVOKABLE void enforceAssistantHomeFocus() const;
    /// Original consent and admission procedures, called in their retained QML function scope.
    Q_INVOKABLE QJSValue composerCaptureConsentDraft() const;
    Q_INVOKABLE bool composerOwnsConsentDraft(const QJSValue& draft) const;
    Q_INVOKABLE QJSValue composerSubmitApprovedDraft(const QJSValue& draft) const;
    Q_INVOKABLE bool composerExplainBlockedSubmission() const;
    Q_INVOKABLE QJSValue composerSubmit(const QJSValue& approved) const;
    Q_INVOKABLE void panelRetireConsentSend() const;
    Q_INVOKABLE bool panelOwnsConsentSend(const QJSValue& intent) const;
    Q_INVOKABLE void panelResumeConsentSend() const;
    Q_INVOKABLE void panelConsentContextChanged() const;
    Q_INVOKABLE void panelContextApproved(const QJSValue& offer) const;
    Q_INVOKABLE void panelScheduleConsentSend() const;
    Q_INVOKABLE void panelSubmissionRequested(const QJSValue& draft) const;
    Q_INVOKABLE void panelContextApprovalRequested(const QJSValue& text) const;
    Q_INVOKABLE QJSValue connectionBeginOffer() const;
    Q_INVOKABLE void connectionPresentOffer(const QJSValue& offer) const;
    Q_INVOKABLE void connectionResumeAcceptedOffer() const;
    Q_INVOKABLE void connectionScheduleAcceptedOffer() const;
    Q_INVOKABLE void connectionShowFailure() const;
    Q_INVOKABLE void connectionRefreshContext() const;
    Q_INVOKABLE QJSValue connectionDisclosedContext() const;
    Q_INVOKABLE void connectionAccepted() const;
    Q_INVOKABLE void connectionUpdateAcceptButton() const;
    Q_INVOKABLE void connectionResetOffer(bool refresh, bool retired) const;
    /// Common desktop/browser project transactions; Session retains canonical project ownership.
    Q_INVOKABLE void afterProjectChanges(const QJSValue& action, const QJSValue& abandoned) const;
    Q_INVOKABLE void openWorkflowPage(const QJSValue& page) const;
    Q_INVOKABLE void resetWorkflow() const;
    Q_INVOKABLE void saveCurrentProject() const;
    Q_INVOKABLE void saveCurrentProjectAs(const QJSValue& intent) const;
    Q_INVOKABLE QJSValue finishProjectSaveAs(const QJSValue& target, const QJSValue& zip, const QJSValue& copy) const;
    Q_INVOKABLE void cancelProjectSaveAs() const;
    Q_INVOKABLE void projectWindowClosing(const QJSValue& close) const;
    Q_INVOKABLE void projectChangesQuestion(const QJSValue& action, const QJSValue& abandoned) const;
    Q_INVOKABLE void unsavedProjectOpened() const;
    Q_INVOKABLE void abandonUnsavedProjectAction() const;
    Q_INVOKABLE void acceptUnsavedProject() const;
    Q_INVOKABLE void projectWebSaveFinished(const QJSValue& saved) const;
    Q_INVOKABLE void discardUnsavedProject() const;
    Q_INVOKABLE void prepareProjectSaveChoice() const;
    Q_INVOKABLE void acceptProjectSaveChoice() const;
    Q_INVOKABLE void openProjectSavePicker(const QJSValue& target) const;
    Q_INVOKABLE void acceptProjectSavePicker(bool zip) const;
    Q_INVOKABLE void dropProject(const QJSValue& drop) const;
    Q_INVOKABLE bool prepareProjectCreation(const QJSValue& intent) const;
    Q_INVOKABLE bool projectCreationSaveCurrent(const QJSValue& intent, const QJSValue& control) const;
    Q_INVOKABLE bool chooseProjectCreationSave(const QJSValue& intent, const QJSValue& control) const;
    Q_INVOKABLE void finishProjectCreationGuard(const QJSValue& intent) const;
    Q_INVOKABLE QJSValue createProjectFromIntent(const QJSValue& values, const QJSValue& intent) const;
    Q_INVOKABLE bool showProjectReport(const QJSValue& project) const;
    Q_INVOKABLE void restoreSessionProject(const QJSValue& thread, const QJSValue& location, const QJSValue& intent) const;
    Q_INVOKABLE void resetProjectAfterChanges() const;
    /// Existing editor and scientific-form procedures; model writes retain their original backend/Undo owner.
    Q_INVOKABLE void editorRefreshCleanText() const;
    Q_INVOKABLE void editorRememberDraft(EditorKind kind) const;
    Q_INVOKABLE void editorBeginAssistantEdit(EditorKind kind) const;
    Q_INVOKABLE void editorAllowAssistantCommit(EditorKind kind) const;
    Q_INVOKABLE void parameterEditorReset() const;
    Q_INVOKABLE void editorCancelAssistantEdit(EditorKind kind) const;
    Q_INVOKABLE void editorEscape(EditorKind kind, const QJSValue& event) const;
    Q_INVOKABLE void editorCommit(EditorKind kind) const;
    Q_INVOKABLE void parameterEditorFocusChanged(EditorKind kind) const;
    Q_INVOKABLE void editorRetireOwner() const;
    Q_INVOKABLE void editorDestroyed() const;
    Q_INVOKABLE void parameterEditorItemChanged(EditorKind kind) const;
    Q_INVOKABLE void editorValueChanged(EditorKind kind) const;
    Q_INVOKABLE void parameterEditorFitToggled(const QJSValue& checked) const;
    Q_INVOKABLE void editorTextChanged() const;
    Q_INVOKABLE void editorCompositionChanged(EditorKind kind) const;
    Q_INVOKABLE void parameterEditorCompleted() const;
    Q_INVOKABLE QJSValue typedInputRefusal(const QString& text, const QString& accepts) const;
    Q_INVOKABLE QJSValue parameterFreeRows(bool fittable) const;
    Q_INVOKABLE QJSValue parameterFreeCount() const;
    Q_INVOKABLE void applyParametersFree(const QJSValue& free) const;
    Q_INVOKABLE void parameterMenuMembershipChanged() const;
    Q_INVOKABLE void ensureParameterSelection() const;
    Q_INVOKABLE void parameterSelectionChanged(bool projectChanged) const;
    Q_INVOKABLE void updateParameterSliderLimits() const;
    Q_INVOKABLE void parameterSliderPressed(bool destroying) const;
    Q_INVOKABLE QJSValue parameterBound(const QJSValue& value) const;
    Q_INVOKABLE QJSValue formShownValue(const QJSValue& uid, const QJSValue& value, bool omitNaN) const;
    Q_INVOKABLE QJSValue measuredRangeIncrement(const QJSValue& summary) const;
    Q_INVOKABLE QJSValue instrumentWavelengthBand(const QJSValue& low, const QJSValue& high) const;
    Q_INVOKABLE void chooseExperimentType(const QJSValue& axis, const QJSValue& token) const;
    Q_INVOKABLE void chooseBackgroundType(const QJSValue& token) const;
    Q_INVOKABLE void applyGeneratedCategory(int row, const QString& name, const QString& value) const;
    Q_INVOKABLE QJSValue parameterSegments(const QJSValue& entry, bool category) const;
    Q_INVOKABLE QJSValue parameterDatablockColor(const QJSValue& kind, const QJSValue& name) const;
    Q_INVOKABLE QJSValue derivedBackgroundValue(const QJSValue& value) const;
    Q_INVOKABLE void parameterCellRefit() const;
    Q_INVOKABLE QJSValue parameterCellScaledPixelSize() const;
    /// Remaining form, picker, preference and shared view procedures on the current QML engine.
    Q_INVOKABLE void loadFormFiles(bool experiments) const;
    Q_INVOKABLE bool chooseStructureFile() const;
    Q_INVOKABLE QJSValue takeStructureWebIntent(const QJSValue& request) const;
    Q_INVOKABLE void chooseExperimentData(const QJSValue& experiment) const;
    Q_INVOKABLE void formFilesOpened(const QJSValue& request, const QJSValue& files, bool experiments) const;
    Q_INVOKABLE void formFilesCancelled(const QJSValue& request, bool experiments) const;
    Q_INVOKABLE void acceptExperimentDataFile() const;
    Q_INVOKABLE void formPickerDestroyed() const;
    Q_INVOKABLE bool sameExperimentGesture(const QJSValue& point) const;
    Q_INVOKABLE void discardExperimentGesture(const QJSValue& point) const;
    Q_INVOKABLE void experimentGrabChanged(const QJSValue& transition, const QJSValue& point) const;
    Q_INVOKABLE void experimentGestureCancelled(const QJSValue& point) const;
    Q_INVOKABLE void experimentGestureTapped(const QJSValue& point) const;
    Q_INVOKABLE void activateFormBlock(const QJSValue& row, bool structure) const;
    Q_INVOKABLE void rejectExperimentDataFile() const;
    Q_INVOKABLE void commitValueField(const QJSValue& restoreBinding) const;
    Q_INVOKABLE void activateSelector(const QJSValue& index, const QJSValue& restoreBinding) const;
    Q_INVOKABLE void resetPreferences() const;
    Q_INVOKABLE void applyPreferences() const;
    Q_INVOKABLE void preferencesColourChanged() const;
    Q_INVOKABLE void preferencesStackedPaletteChanged() const;
    Q_INVOKABLE void preferencesLegacyPaletteChanged() const;
    Q_INVOKABLE void persistPreference(int kind) const;
    Q_INVOKABLE QJSValue preferenceItemsUnder(const QJSValue& item, const QJSValue& wanted) const;
    Q_INVOKABLE QJSValue preferenceBoxNeed(const QJSValue& box) const;
    Q_INVOKABLE QJSValue preferenceButtonNeed(const QJSValue& button) const;
    Q_INVOKABLE QJSValue preferenceRowItems() const;
    Q_INVOKABLE QJSValue preferenceRowWidth(bool controls) const;
    Q_INVOKABLE QJSValue preferenceContentHeight() const;
    Q_INVOKABLE void alignFieldTitle(const QJSValue& field, const QJSValue& installMargin, const QJSValue& installWidth) const;
    Q_INVOKABLE void showWorkflowSidebarTab(const QJSValue& extra) const;
    Q_INVOKABLE void showWorkflowMainTab(const QJSValue& index) const;
    Q_INVOKABLE void placeWorkflowSidebar() const;
    Q_INVOKABLE void workflowCompleted(const QJSValue& installShadow, const QJSValue& installContinueMargin) const;
    Q_INVOKABLE void workflowCurrentChanged() const;
    Q_INVOKABLE void workflowDirtyChanged() const;
    Q_INVOKABLE void workflowStayRequested() const;
    /// Existing text-tab transactions and remaining Composer input procedures.
    Q_INVOKABLE void textTabShowBlock() const;
    Q_INVOKABLE QJSValue textTabApplyTo(const QJSValue& source, const QString& text) const;
    Q_INVOKABLE void textTabApplyEdit() const;
    Q_INVOKABLE void textTabAskLeave(const QJSValue& apply, const QJSValue& leave, const QJSValue& drop, const QJSValue& stay) const;
    Q_INVOKABLE void textTabSourceChanged() const;
    Q_INVOKABLE void textTabChanged(int cause) const;
    Q_INVOKABLE void textTabShowChoice(const QJSValue& index, const QJSValue& restoreBinding) const;
    Q_INVOKABLE void textTabAnswer(const QString& name, const QJSValue& argument) const;
    Q_INVOKABLE void textDiscardCompleted() const;
    Q_INVOKABLE void textDiscardApplied() const;
    Q_INVOKABLE void textDiscardDiscarded() const;
    Q_INVOKABLE void composerRememberSelection() const;
    Q_INVOKABLE void composerFocusEditor() const;
    Q_INVOKABLE void composerFinishWorkReport(const QJSValue& receipt) const;
    Q_INVOKABLE void composerSubmitWorkReport() const;
    Q_INVOKABLE void composerChooseFiles() const;
    Q_INVOKABLE void composerAcceptFiles() const;
    Q_INVOKABLE void composerCancelFiles() const;
    Q_INVOKABLE void composerFileSelectionRetired(const QJSValue& request) const;
    Q_INVOKABLE void composerOwnerChanged() const;
    Q_INVOKABLE void composerChoicesEnabledChanged() const;
    Q_INVOKABLE bool composerLocalWorkReport() const;
    Q_INVOKABLE bool composerHasDraft() const;
    /// Existing assistant choice, notice, conversation and message presentation procedures.
    Q_INVOKABLE QJSValue assistantEffortRank(const QJSValue& value) const;
    Q_INVOKABLE QJSValue assistantEffortLabel(const QJSValue& value) const;
    Q_INVOKABLE QJSValue assistantEffortChoices() const;
    Q_INVOKABLE QJSValue assistantSelectedModelRow() const;
    Q_INVOKABLE QJSValue assistantSelectedEffortLabel() const;
    Q_INVOKABLE QJSValue assistantSelectedEffortRow() const;
    Q_INVOKABLE void assistantCloseChoices() const;
    Q_INVOKABLE void assistantOpenChoices() const;
    Q_INVOKABLE QJSValue assistantChoiceCurrent(const QJSValue& original) const;
    Q_INVOKABLE void assistantChoiceFocusRow(const QJSValue& table, const QJSValue& index, const QJSValue& original) const;
    Q_INVOKABLE bool assistantModelAvailable(const QJSValue& model, const QJSValue& index) const;
    Q_INVOKABLE void assistantChoiceReconcile(const QJSValue& group, const QJSValue& original) const;
    Q_INVOKABLE void assistantChoiceFocusModel(const QJSValue& start, const QJSValue& step, const QJSValue& original) const;
    Q_INVOKABLE void assistantChoiceFocusEffort(const QJSValue& index, const QJSValue& original) const;
    Q_INVOKABLE void assistantChooseModel(const QJSValue& id) const;
    Q_INVOKABLE void assistantChooseEffort(const QJSValue& token) const;
    Q_INVOKABLE void assistantChoicesOpened() const;
    Q_INVOKABLE void assistantChoicesClosed() const;
    Q_INVOKABLE QJSValue assistantChoiceLabelWidth() const;
    Q_INVOKABLE void assistantChoiceActivateKey(const QJSValue& value, const QJSValue& event, bool model) const;
    Q_INVOKABLE void assistantChoiceModelNavigate(const QJSValue& index, int step, const QJSValue& event) const;
    Q_INVOKABLE void assistantChoiceEffortNavigate(const QJSValue& row, bool forward, bool wrap, const QJSValue& event) const;
    Q_INVOKABLE void panelCaptureNotice() const;
    Q_INVOKABLE bool panelNoticeAnchorPresent() const;
    Q_INVOKABLE void panelNoticeOwnerChanged(int cause) const;
    Q_INVOKABLE void panelCompleted() const;
    Q_INVOKABLE void panelSessionConsentRequested() const;
    Q_INVOKABLE QJSValue panelOpenReportLink(const QJSValue& sourceRowId, const QJSValue& link) const;
    Q_INVOKABLE void panelShownChanged() const;
    Q_INVOKABLE void panelFocusComposer() const;
    Q_INVOKABLE void panelSubmissionBlocked() const;
    Q_INVOKABLE void panelFilesEntered(const QJSValue& drag) const;
    Q_INVOKABLE void panelFilesDropped(const QJSValue& drop) const;
    Q_INVOKABLE void panelConnectionRejected() const;
    Q_INVOKABLE QJSValue conversationUserTarget(const QJSValue& direction) const;
    Q_INVOKABLE void conversationJumpToUser(const QJSValue& direction) const;
    Q_INVOKABLE void conversationObserveAdmission() const;
    Q_INVOKABLE void conversationRevealNotice() const;
    Q_INVOKABLE void conversationPositionAtTail() const;
    Q_INVOKABLE void conversationFollowOutput() const;
    Q_INVOKABLE void conversationUpdated(bool modelData) const;
    Q_INVOKABLE void conversationContentYChanged() const;
    Q_INVOKABLE void conversationMovementChanged(bool started) const;
    Q_INVOKABLE void conversationScrollChanged(bool position) const;
    Q_INVOKABLE QJSValue assistantMessageTableTone(const QJSValue& lift) const;
    Q_INVOKABLE QJSValue assistantSentFileLabel(const QJSValue& file) const;
    Q_INVOKABLE QJSValue assistantWidestSentFile() const;
    Q_INVOKABLE void panelConnectionActivated() const;
    Q_INVOKABLE void conversationDetailsChanging() const;
    Q_INVOKABLE QJSValue connectionNaturalButtonsWidth() const;
    Q_INVOKABLE void connectionPresentationChanged(int cause) const;
    Q_INVOKABLE void composerReturnPressed(const QJSValue& event) const;
    Q_INVOKABLE void assistantChoicesKey(const QJSValue& event, bool released) const;
    Q_INVOKABLE void assistantMessageCopyKey(const QJSValue& event) const;
    /// Shared table procedures; the original view maps, row ownership and model notifications remain authoritative.
    Q_INVOKABLE QJSValue tableColumnRowOwner(const QJSValue& row) const;
    Q_INVOKABLE void tableApplyWidths(const QJSValue& row) const;
    Q_INVOKABLE void tablePadForFiller(const QJSValue& cell, const QJSValue& column) const;
    Q_INVOKABLE QJSValue tableCellKind(const QJSValue& cell) const;
    Q_INVOKABLE void tableAlignCell(const QJSValue& cell, const QJSValue& kind) const;
    Q_INVOKABLE void tableScheduleFitColumns() const;
    Q_INVOKABLE QJSValue tableColumnWidths() const;
    Q_INVOKABLE void tableFitColumns() const;
    Q_INVOKABLE void tableRefit() const;
    Q_INVOKABLE void tableColumnsChanged(bool widthsChanged) const;
    Q_INVOKABLE void tableDestroyed() const;
    Q_INVOKABLE QJSValue tableTextWidth(int row, const QString& role) const;
    Q_INVOKABLE QJSValue tableAdvance(const QString& text) const;
    Q_INVOKABLE QJSValue tableTextColumnWidth(const QString& role, const QString& title, bool natural) const;
    Q_INVOKABLE void tableForgetWidths() const;
    Q_INVOKABLE void tableRemeasure() const;
    Q_INVOKABLE void tableDataChanged(const QJSValue& topLeft, const QJSValue& bottomRight) const;
    Q_INVOKABLE void tableOwnerCallback(int kind) const;
    Q_INVOKABLE bool tableRevealRow(int index) const;
    Q_INVOKABLE bool tableRevealItem(const QJSValue& item) const;
    Q_INVOKABLE void tableKeyPressed(const QJSValue& event) const;
    /// Shared control procedures retain the original QML state, layout and native model owners.
    Q_INVOKABLE QJSValue toolbarUnits() const;
    Q_INVOKABLE QJSValue toolbarMeasure() const;
    Q_INVOKABLE QJSValue toolbarIsComboBox(const QJSValue& unit) const;
    Q_INVOKABLE QJSValue toolbarGroupOf(const QJSValue& unit) const;
    Q_INVOKABLE QJSValue toolbarBoxGap(const QJSValue& before, const QJSValue& unit) const;
    Q_INVOKABLE QJSValue toolbarRowWidth(const QJSValue& row, const QJSValue& gap, bool boxes) const;
    Q_INVOKABLE void toolbarLayout() const;
    Q_INVOKABLE QJSValue iconElidedIndex() const;
    Q_INVOKABLE QJSValue iconNaturalWidth(const QJSValue& segment, const QJSValue& piece) const;
    Q_INVOKABLE QJSValue iconFixedWidth(const QJSValue& segment) const;
    Q_INVOKABLE QJSValue iconOtherWidth() const;
    Q_INVOKABLE QJSValue sidebarIsOpen(const QJSValue& key, const QJSValue& group) const;
    Q_INVOKABLE void sidebarSetOpen(const QJSValue& key, const QJSValue& open, const QJSValue& group) const;
    Q_INVOKABLE QJSValue sidebarEdge(const QJSValue& group, bool last) const;
    Q_INVOKABLE QJSValue sidebarOrderedChildren(const QJSValue& parent) const;
    Q_INVOKABLE QJSValue sidebarShownGroups(const QJSValue& group) const;
    Q_INVOKABLE QJSValue statusKeysFit() const;
    Q_INVOKABLE QJSValue statusRoomFor() const;
    Q_INVOKABLE QJSValue statusMeasuredWidth(bool compact) const;
    Q_INVOKABLE QJSValue statusWidthWith(const QJSValue& itemWidth, bool buttons) const;
    Q_INVOKABLE QJSValue statusFitValues() const;
    Q_INVOKABLE QJSValue statusProgressText() const;
    Q_INVOKABLE QJSValue colourMapTitles() const;
    /// Preference actions use the existing view records and assistant selection authority.
    Q_INVOKABLE void preferencesClosed() const;
    Q_INVOKABLE void preferenceAssistantChanged() const;
    Q_INVOKABLE void preferenceCopyDiagnostics(const QJSValue& button, const QJSValue& report) const;
    Q_INVOKABLE void preferenceSourceRevision() const;
    Q_INVOKABLE void preferenceSourceGesture(bool remove, bool pressed) const;
    Q_INVOKABLE void preferenceBeginSourceSelection(bool web) const;
    Q_INVOKABLE void preferenceCompleteSourceSelection(bool web, bool accepted) const;
    Q_INVOKABLE void preferenceRetireSourceSelection(const QJSValue& token, bool web) const;
    Q_INVOKABLE QJSValue preferenceColourTitles() const;
    Q_INVOKABLE QJSValue preferenceStackedChoices() const;
    Q_INVOKABLE QJSValue preferenceEngineThreads() const;
    Q_INVOKABLE void preferenceActivated(const QJSValue& index, int setting) const;
    /// NumberText presentation; project uncertainty formatting remains ProjectViewModel/core-owned.
    Q_INVOKABLE QJSValue numberPresentation(NumberOperation operation, const QJSValue& value, const QJSValue& second,
                                          const QJSValue& third, const QJSValue& fourth) const;
    /// Report preview/export procedures retain ReportViewModel as data and publication authority.
    Q_INVOKABLE void saveReportPreview() const;
    Q_INVOKABLE QJSValue savedReportRow(const QJSValue& format) const;
    Q_INVOKABLE void reportExportFailure(const QJSValue& message) const;
    Q_INVOKABLE void reportExportChanged(int event) const;
    Q_INVOKABLE QJSValue reportChartsIncluded() const;
    Q_INVOKABLE QJSValue reportSection(const QJSValue& name, bool numbered) const;
    Q_INVOKABLE QJSValue reportKeyValues(const QJSValue& rows) const;
    Q_INVOKABLE void reportGrabFigures(const QJSValue& done) const;
    Q_INVOKABLE void reportCaptureStart(const QJSValue& jobs, const QJSValue& done) const;
    Q_INVOKABLE void reportCaptureAll() const;
    Q_INVOKABLE void reportCaptureFrame() const;
    Q_INVOKABLE QJSValue reportTableDotWidth() const;
    Q_INVOKABLE QJSValue reportTableSplit(const QJSValue& text) const;
    Q_INVOKABLE QJSValue reportTableLayout() const;
    Q_INVOKABLE QJSValue reportTableWidth() const;
    Q_INVOKABLE void reportTableRowsChanged() const;
    Q_INVOKABLE QJSValue reportCorrelationLabelWidth() const;
    Q_INVOKABLE QJSValue reportCorrelationColor(const QJSValue& value) const;
    /// Shared scene, legend, block and correlation presentation; existing native controllers own the data.
    Q_INVOKABLE QJSValue legendToggleAt(const QJSValue& item, const QJSValue& x, const QJSValue& y) const;
    Q_INVOKABLE QJSValue legendRichLabel(const QJSValue& pieces) const;
    Q_INVOKABLE QJSValue legendMarkPiece(const QJSValue& mark, const QJSValue& width, const QJSValue& color) const;
    Q_INVOKABLE QJSValue legendSegments() const;
    Q_INVOKABLE QJSValue factorPresentation(const QJSValue& value, bool rich) const;
    Q_INVOKABLE QJSValue fitOutcomePresentation(FitOutcomeOperation operation, const QJSValue& key, const QJSValue& neutral) const;
    Q_INVOKABLE void stepBlock(const QJSValue& offset) const;
    Q_INVOKABLE QJSValue blockSegments(const QJSValue& index, const QJSValue& name, const QJSValue& nameColor, const QJSValue& outcome, const QJSValue& isTemplate) const;
    Q_INVOKABLE void activateBlock(const QJSValue& index, const QJSValue& restoreBinding) const;
    Q_INVOKABLE QJSValue correlationNumbers() const;
    Q_INVOKABLE QJSValue correlationEdgeText(const QJSValue& index) const;
    Q_INVOKABLE QJSValue correlationValueAt(const QJSValue& index) const;
    Q_INVOKABLE void correlationCommit(const QJSValue& text, bool count) const;
    Q_INVOKABLE void correlationNumberDone(const QJSValue& restoreBinding) const;
    Q_INVOKABLE void correlationToggle(bool full) const;
    Q_INVOKABLE QJSValue correlationWidestLabel() const;
    Q_INVOKABLE QJSValue structureHoverText(const QJSValue& result) const;
    Q_INVOKABLE void structurePointer(const QJSValue& event, int kind) const;
    Q_INVOKABLE void structureHoverShow(const QJSValue& x, const QJSValue& y) const;
    Q_INVOKABLE void structureColourChoice(const QJSValue& index) const;
    /// Pattern chart UI procedures; the existing controller owns source, series, transforms and ranges.
    Q_INVOKABLE QJSValue patternTickValues(const QJSValue& axis) const;
    Q_INVOKABLE QJSValue patternYValues(const QJSValue& axis, const QJSValue& scale) const;
    Q_INVOKABLE QJSValue patternGridTicks(const QJSValue& axis) const;
    Q_INVOKABLE QJSValue patternYLabelText(const QJSValue& text, const QJSValue& axis, const QJSValue& scale, const QJSValue& format) const;
    Q_INVOKABLE QJSValue patternYLabelsRoom() const;
    Q_INVOKABLE void patternAlignPanes() const;
    Q_INVOKABLE QJSValue patternClosedTexts(bool measured) const;
    Q_INVOKABLE void patternChoice(const QJSValue& index, int kind) const;
    Q_INVOKABLE QJSValue patternSameRanges(const QJSValue& a, const QJSValue& b) const;
    Q_INVOKABLE void patternViewChanged(int event) const;
    Q_INVOKABLE void patternStructureReady() const;
    Q_INVOKABLE void patternBraggSeries(const QJSValue& index, const QJSValue& series, bool added) const;
    Q_INVOKABLE QJSValue patternBraggLabelsRoom() const;
    Q_INVOKABLE void patternPointer(const QJSValue& mouse, int kind) const;
    Q_INVOKABLE void patternHoverRead(const QJSValue& pane, const QJSValue& area, const QJSValue& mouse) const;
    Q_INVOKABLE void patternHoverShow(const QJSValue& text, const QJSValue& atX, const QJSValue& atY) const;
    Q_INVOKABLE void chartToolbarAction(int action) const;
    Q_INVOKABLE void renewPatternChart() const;
    /// Evolution presentation and the common tick/coordinate rules; existing models own results and selection.
    Q_INVOKABLE QJSValue chartNiceStep(const QJSValue& span, const QJSValue& count) const;
    Q_INVOKABLE QJSValue chartGridShares(const QJSValue& axis) const;
    Q_INVOKABLE QJSValue chartCoordinate(const QJSValue& position, bool vertical) const;
    Q_INVOKABLE QJSValue evolutionMeasuredStyle() const;
    Q_INVOKABLE QJSValue evolutionReportRange() const;
    Q_INVOKABLE QJSValue evolutionXEntries(bool closed) const;
    Q_INVOKABLE QJSValue evolutionMoved(const QJSValue& mouse) const;
    Q_INVOKABLE void evolutionPointer(const QJSValue& mouse, int event) const;
    Q_INVOKABLE void evolutionResetZoom() const;
    Q_INVOKABLE void evolutionDrawReportPoints() const;
    Q_INVOKABLE void evolutionReportChanged() const;
    /// Single-crystal chart procedures retain the reflection models and measured layers as authorities.
    Q_INVOKABLE QJSValue singleModels() const;
    Q_INVOKABLE QJSValue singleHiddenModels() const;
    Q_INVOKABLE QJSValue singleRangeModels() const;
    Q_INVOKABLE QJSValue singleCalculated() const;
    Q_INVOKABLE QJSValue singleReportRange() const;
    Q_INVOKABLE QJSValue singleFullRange(bool high) const;
    Q_INVOKABLE void singleUpdateLegend() const;
    Q_INVOKABLE void singleToggleRow(const QJSValue& key) const;
    Q_INVOKABLE QJSValue singlePart(const QJSValue& x, const QJSValue& y, const QJSValue& su, const QJSValue& used, const QJSValue& want) const;
    Q_INVOKABLE void singleDrawModel(const QJSValue& model, const QJSValue& usedLayer, const QJSValue& leftOutLayer) const;
    Q_INVOKABLE void singleRedraw() const;
    Q_INVOKABLE void singleDrawDiagonal() const;
    Q_INVOKABLE void singleStateChanged(int event) const;
    Q_INVOKABLE void singleModelChanged(bool stacked) const;
    Q_INVOKABLE void singleQuantityChoice(const QJSValue& index) const;
    Q_INVOKABLE QJSValue singleNearest(const QJSValue& px, const QJSValue& py) const;
    Q_INVOKABLE void singleHoverRead(const QJSValue& px, const QJSValue& py) const;
    Q_INVOKABLE void singlePointer(const QJSValue& mouse, int event) const;
    /// Scan view state/lifecycle and input procedures; ScanViewModel and ScanLayer own data and presentation.
    Q_INVOKABLE QJSValue scanStackedPalette() const;
    Q_INVOKABLE QJSValue chartCapitalised(const QJSValue& text) const;
    Q_INVOKABLE void scanSetZoom(const QJSValue& x, const QJSValue& y) const;
    Q_INVOKABLE void scanResetZoom() const;
    Q_INVOKABLE void scanPublishZoom() const;
    Q_INVOKABLE void scanViewLifecycle(int event) const;
    Q_INVOKABLE void scanReportShown() const;
    Q_INVOKABLE void scanPointer(const QJSValue& mouse, int event) const;
    Q_INVOKABLE QJSValue scanIntensityCounts(const QJSValue& value) const;
    Q_INVOKABLE QJSValue scanIntensityText(const QJSValue& value) const;
    Q_INVOKABLE void scanLegendToggle(const QJSValue& key) const;
    Q_INVOKABLE QJSValue scanRowEntries() const;
    Q_INVOKABLE QJSValue scanClosedTexts(int kind) const;
    Q_INVOKABLE void scanChoice(const QJSValue& index, int kind) const;
    Q_INVOKABLE void scanToggle(int kind) const;
    /// Common control presentation and the existing working-indicator timer procedures.
    Q_INVOKABLE void queueToolbarBinding(const QJSValue& install) const;
    Q_INVOKABLE QJSValue toolbarWidestEntry() const;
    Q_INVOKABLE QJSValue tabTitleSegments() const;
    Q_INVOKABLE QJSValue digitCellWidth() const;
    Q_INVOKABLE QJSValue digitTextRuns() const;
    Q_INVOKABLE QJSValue digitRunIsDigit(const QJSValue& text) const;
    Q_INVOKABLE QJSValue palettePositions() const;
    Q_INVOKABLE QJSValue nameBlockIcon(const QJSValue& kind) const;
    Q_INVOKABLE QJSValue nameParameterIcon(const QJSValue& name) const;
    Q_INVOKABLE QJSValue nameSegments(const QJSValue& item) const;
    Q_INVOKABLE QJSValue blockNamesShown() const;
    Q_INVOKABLE QJSValue blockNamesLine(const QJSValue& row) const;
    Q_INVOKABLE void blockNamesChanged() const;
    Q_INVOKABLE QJSValue workingInitialVariant() const;
    Q_INVOKABLE QJSValue workingText() const;
    Q_INVOKABLE void workingStateChanged(int event) const;
    Q_INVOKABLE void workingScheduleVariant() const;
    Q_INVOKABLE void workingChangeVariant() const;
    Q_INVOKABLE void workingElapsed() const;
    Q_INVOKABLE void workingCadence(bool peak) const;
    Q_INVOKABLE void workingAnimation(bool started) const;
    /// Recent-project persistence/navigation and row activation/setup retain their existing owners and records.
    Q_INVOKABLE QJSValue recentWebRows() const;
    Q_INVOKABLE QJSValue recentWebKey(const QJSValue& path) const;
    Q_INVOKABLE void recentOpen(const QJSValue& path) const;
    Q_INVOKABLE QJSValue recentPaths() const;
    Q_INVOKABLE void recentRefresh() const;
    Q_INVOKABLE void recentRemember(const QJSValue& path) const;
    Q_INVOKABLE void recentForget(const QJSValue& index) const;
    Q_INVOKABLE void recentCompleted() const;
    Q_INVOKABLE void tableRowEditing() const;
    Q_INVOKABLE void tableRowActivated() const;
    Q_INVOKABLE void tableRowCompleted(const QJSValue& installOpacity) const;
    /// Searchable popup filtering, geometry and existing opening/request lifecycle.
    Q_INVOKABLE void searchPositionPopup(const QJSValue& opening) const;
    Q_INVOKABLE QJSValue searchMeasuredWidth(bool optionsOnly) const;
    Q_INVOKABLE QJSValue searchAnyMatch() const;
    Q_INVOKABLE QJSValue searchFolded(const QJSValue& text) const;
    Q_INVOKABLE void searchPlacePopup(const QJSValue& opening) const;
    Q_INVOKABLE QJSValue searchMatches(const QJSValue& text) const;
    Q_INVOKABLE QJSValue searchPickedIndex() const;
    Q_INVOKABLE void searchAccepted() const;
    Q_INVOKABLE void searchCompleted(const QJSValue& alignBinding, const QJSValue& modelBinding, const QJSValue& focusBinding) const;
    Q_INVOKABLE void searchSchedule(const QJSValue& original) const;
    Q_INVOKABLE void searchTriggered() const;
    Q_INVOKABLE void searchAboutToShow() const;
    Q_INVOKABLE void searchAboutToHide() const;
    Q_INVOKABLE void searchOpened() const;
    /// Validate original history attachment metadata on the owning QML engine/thread.
    /// Returns a fresh array of original member references, or empty for invalid metadata.
    /// Preserves original array-like/property/call semantics; thrown JS values remain pending.
    Q_INVOKABLE QJSValue assistantHistoryInputFiles(const QString& kind, const QJSValue& payload) const;
    // Declaration-only members of existing global ApplicationInfo (QML singleton ApplicationInfo).
    /// Open the original session popup, then refresh through the actual current panel assistant.
    /// Borrows QML-thread controls; no new store/eligibility; property/call errors remain pending.
    Q_INVOKABLE void openSessionBrowser(QObject* panel, QObject* dialog) const;
    /// Preserve original opened/more/loading/scroll prefetch order and the existing next-page request.
    /// Borrows actual QML-thread popup/table controls; no debounce/timer/policy; errors remain pending.
    Q_INVOKABLE void prefetchSessionBrowser(QObject* panel, QObject* dialog, QObject* table) const;
    /// Activate the actual session row before resolving its current owner/ID for selectSession.
    /// Borrows actual QML-thread controls; original selection guards remain native; errors remain pending.
    Q_INVOKABLE void activateSessionBrowserRow(QObject* panel, QObject* row) const;
    /// Sum original visible button implicit widths and original count/spacing gaps for the live binding.
    /// Borrows actual QML-thread controls; no retained geometry; errors remain pending.
    Q_INVOKABLE qreal sessionBrowserButtonsWidth(QObject* panel, QObject* buttons) const;
    /// Stateless compact message presentation; no canonical/detail lookup or clipboard write.
    Q_INVOKABLE QVariantMap assistantActivityPresentation(const QString& kind, const QString& status,
                                                        const QJSValue& payload, QObject* assistant) const;
    /// Original display-only literal normalization and web captions; no lookup or clipboard write.
    Q_INVOKABLE QString assistantSingleLineText(const QJSValue& value) const;
    Q_INVOKABLE QString assistantWebSearchCaption(const QJSValue& payload) const;
    /// Lazy native caption only at its actual compact/full-body consumer branch.
    Q_INVOKABLE QString assistantNativeActivityCaption(const QJSValue& payload, QObject* assistant) const;
    /// Format the original lazy projected value; no canonical read or new invalidation policy.
    /// Owner/engine thread only; only the exact native snapshot type is accepted.
    Q_INVOKABLE QString assistantActivityDescription(const QJSValue& snapshot, const QString& kind,
        const QJSValue& compact, const QJSValue& payload, QObject* assistant) const;
    /// Preserve the original payload/text/status invalidation and refresh ordering.
    Q_INVOKABLE void assistantMessageChanged(const QJSValue& component, const QString& cause) const;
    /// Expand reads once; collapse clears the existing lazy value.
    Q_INVOKABLE void assistantMessageDisclosureChanged(const QJSValue& component, bool checked) const;
    /// Copy one current original activity; technical JSON is read only on explicit preference.
    /// Uses the existing clipboard writer once; retired owners receive no success feedback.
    Q_INVOKABLE void assistantCopyActivity(const QJSValue& component, bool includeTechnical, bool offered = true) const;
    /// Copy only literal completed user text, including when its assistant owner is null.
    Q_INVOKABLE void assistantCopyUserText(const QJSValue& component, bool offered = true) const;
    /// Clear the original row's copy feedback, optionally stopping its original visual timer.
    Q_INVOKABLE void assistantMessageClearFeedback(const QJSValue& component, bool stopTimer = true) const;
    /// Close disclosure, clear feedback and deselect original row editors on identity/pool/reuse changes.
    Q_INVOKABLE void assistantMessageReset(const QJSValue& component) const;
    /// Route the toolbar action through the existing UI owner; browsers only show availability.
    Q_INVOKABLE void assistantToolbarActivated(const QJSValue& window, const QJSValue& toggle,
        const QJSValue& panel, const QJSValue& session, const QJSValue& preferences,
        const QJSValue& desktopOnlyDialog) const;
    /// Desktop availability captured before QML observation; not provider connection or permission.
    /// Read on the owning QObject thread. Browser builds remain unavailable.
    bool assistantAvailable() const;
    /// Localized desktop-only explanation, or empty when available. No network access.
    QString assistantUnavailableReason() const;
    bool engineThreadsSelectable() const;
    // Twice the cores the platform reports, at least 16 and at most 64: a browser may report fewer cores
    // than the machine has (Brave reports 4 of an M2's 12), so a larger count can still be tried.
    int engineThreadsMaximum() const;
    // Sets the engine's thread count for every fill: 0 for Auto, else that many threads.
    Q_INVOKABLE void setEngineThreads(int count) const;
    // Writes the settings file to the browser's storage at once (engine_setup.hpp store_settings_now).
    Q_INVOKABLE void storeSettings() const;
    // Where a link inside the bundled licence text at `from` leads, resolved against that text's own location
    // (the app notice's "../COPYING" is qrc:/COPYING): the URL when it is one of the bundled licence texts above,
    // empty for anything else, so a link opens only what licenceText reads.
    Q_INVOKABLE QString licenceLinkTarget(const QString& from, const QString& link) const;

   private:
    // One column of the notices' "Components" list: 0 the name, 1 the licence, 2 the use, 3 the version.
    static QStringList componentColumn(int column);
    const bool assistant_available_;

   public:
    QString description() const;
    // The holder of the copyright in edi's source (LICENSE), named in the About dialog.
    QString copyrightHolder() const { return QStringLiteral("EasyScience contributors"); }
    // The About dialog's copyright years, as easydiffractionbeta's (Gui/Globals/Configs.qml): from the
    // EasyDiffraction project's first year to the current release's.
    QString developerYearsFrom() const { return QStringLiteral("2019"); }
    QString developerYearsTo() const { return QStringLiteral("2026"); }
    // ADR-0017 §8, ADR-0022 §4: an element's colour from a type symbol — the core table's colour of
    // edi::element_of(typeSymbol) in `scheme` ("jmol" or "vesta", the structure view's) — or `fallback` for an
    // element the table does not have. The app holds no element colour of its own.
    QStringList elementSymbols() const;
    // The colour at `position` in the palette `scheme` (a token of edi::colour_scheme_from_name, data/palettes; another
    // reads as edi::colour_scheme_or_default does), `count` one past the last position in use, in the theme:
    // edi::figure_colour. The calculated curve's colour in the palette and theme: edi::role_colour.
    Q_INVOKABLE QColor figureColour(const QString& scheme, int position, int count, bool dark) const;
    Q_INVOKABLE QColor calculationColour(const QString& scheme, bool dark) const;
    // How many colours a palette lists (edi::kPaletteColourCount), and whether it keeps its first two for experiments.
    Q_PROPERTY(int paletteColourCount READ paletteColourCount CONSTANT)
    int paletteColourCount() const { return static_cast<int>(edi::kPaletteColourCount); }
    Q_INVOKABLE bool reservesExperimentColours(const QString& scheme) const;
    // A local file's path as the app shows it, and the URL of the folder it is in (the Preferences' settings file).
    Q_INVOKABLE QString localPath(const QUrl& file) const { return QDir::toNativeSeparators(file.toLocalFile()); }
    Q_INVOKABLE QUrl folderOf(const QUrl& file) const {
        return QUrl::fromLocalFile(QFileInfo(file.toLocalFile()).absolutePath());
    }
    // The palettes' tokens and their titles, in the order Preferences lists them (edi::colour_scheme_names), and the
    // token a stored preference stands for (edi::colour_scheme_or_default).
    Q_PROPERTY(QStringList colourSchemes READ colourSchemes CONSTANT)
    Q_PROPERTY(QStringList colourSchemeTitles READ colourSchemeTitles CONSTANT)
    QStringList colourSchemes() const;
    QStringList colourSchemeTitles() const;
    Q_INVOKABLE QString colourSchemeOrDefault(const QString& scheme) const;
    // The scan views' colour maps (edi::scan_colour_map_names, edi ADR-0041), and the one a stored name stands for:
    // itself when listed, else Blue-Red.
    Q_PROPERTY(QStringList scanColourMaps READ scanColourMaps CONSTANT)
    QStringList scanColourMaps() const;
    Q_INVOKABLE QString scanColourMapOrDefault(const QString& name) const;
    // A colour choice's title: a palette's or a map's (edi::scan_colour_map_title).
    Q_INVOKABLE QString scanColourTitle(const QString& choice) const;
    // The Map's directions (edi::scan_map_direction_names) and their titles, the one a stored name stands for (Auto for
    // another), and whether `map` is drawn inverted in `direction` on `background` in the theme
    // (edi::scan_map_inverted).
    Q_PROPERTY(QStringList scanMapDirections READ scanMapDirections CONSTANT)
    Q_PROPERTY(QStringList scanMapDirectionTitles READ scanMapDirectionTitles CONSTANT)
    QStringList scanMapDirections() const;
    QStringList scanMapDirectionTitles() const;
    Q_INVOKABLE QString scanMapDirectionOrDefault(const QString& name) const;
    Q_INVOKABLE bool scanMapInverted(const QString& map, const QString& direction, const QColor& background,
                                     bool dark) const;
    // The Stacked spacing steps (edi::stacked_spacing_names) and their titles, and a step's s (Wide's for another
    // name).
    Q_PROPERTY(QStringList stackedSpacings READ stackedSpacings CONSTANT)
    Q_PROPERTY(QStringList stackedSpacingTitles READ stackedSpacingTitles CONSTANT)
    QStringList stackedSpacings() const;
    QStringList stackedSpacingTitles() const;
    Q_INVOKABLE double stackedSpacingShare(const QString& name) const;
    // `stops` colours sampled evenly along a map in the theme, from its low end to its high end, inverted when
    // `inverted`: a colour bar's gradient.
    Q_INVOKABLE QList<QColor> scanColourStops(const QString& map, bool dark, bool inverted, int stops = 16) const;
    // Where a window of `width` x `height` kept at `x`, `y` opens: there when that point is on a connected screen, else
    // centred on the primary screen's available area (a screen unplugged since).
    Q_INVOKABLE QPoint onScreenPosition(int x, int y, int width, int height) const;
    /// Store the original Main Window settings after restoration and outside maximized/fullscreen.
    Q_INVOKABLE void storeWindowGeometry(QObject* window, QObject* settings) const;
    /// Restore the existing settings through the screen-placement owner and actual Main store hook.
    Q_INVOKABLE void restoreWindowGeometry(QObject* window, QObject* settings) const;
    Q_INVOKABLE QColor elementColor(const QString& typeSymbol, const QColor& fallback,
                                    const QString& scheme = QStringLiteral("jmol")) const;
    // `colour` as drawn flat on any of `backgrounds`: its lightness moved to 2:1 contrast on each, its hue kept (edi
    // ADR-0047).
    Q_INVOKABLE QColor readableColour(const QColor& colour, const QList<QColor>& backgrounds) const;
};

#endif  // EDI_APP_APP_INFO_HPP
