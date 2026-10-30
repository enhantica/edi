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
