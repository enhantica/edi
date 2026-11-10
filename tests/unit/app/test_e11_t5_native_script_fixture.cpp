// SPDX-License-Identifier: BSD-3-Clause
// Test-owned lexical environment for the actual migrated Qt procedures.
// It supplies the original fixtures' bindings; every ApplicationInfo operation
// still executes on the real same-engine product singleton.
#include <QCoreApplication>
#include <QFile>
#include <QJSValue>
#include <QJSValueIterator>
#include <QStringList>
#include "edi/report_html.hpp"
#include "edi/report_model.hpp"
#include <QJsonDocument>
#include <QMap>
#include <QMetaEnum>
#include <QQmlContext>
#include <QQmlEngine>
#include <QQmlExpression>
#include <QVariantMap>
#include <QtQml/qqml.h>
#include <memory>

class NativeScriptFixture final : public QObject {
    Q_OBJECT
    Q_PROPERTY(QJSValue Qt READ readQt WRITE writeQt)
    Q_PROPERTY(QJSValue qsTr READ readqsTr WRITE writeqsTr)
    Q_PROPERTY(QJSValue Math READ readMath WRITE writeMath)
    Q_PROPERTY(QJSValue JSON READ readJSON WRITE writeJSON)
    Q_PROPERTY(QJSValue Object READ readObject WRITE writeObject)
    Q_PROPERTY(QJSValue Array READ readArray WRITE writeArray)
    Q_PROPERTY(QJSValue Number READ readNumber WRITE writeNumber)
    Q_PROPERTY(QJSValue String READ readString WRITE writeString)
    Q_PROPERTY(QJSValue Boolean READ readBoolean WRITE writeBoolean)
    Q_PROPERTY(QJSValue Date READ readDate WRITE writeDate)
    Q_PROPERTY(QJSValue RegExp READ readRegExp WRITE writeRegExp)
    Q_PROPERTY(QJSValue Error READ readError WRITE writeError)
    Q_PROPERTY(QJSValue TypeError READ readTypeError WRITE writeTypeError)
    Q_PROPERTY(QJSValue Reflect READ readReflect WRITE writeReflect)
    Q_PROPERTY(QJSValue abandoned READ readabandoned WRITE writeabandoned)
    Q_PROPERTY(QJSValue acceptedOffer READ readacceptedOffer WRITE writeacceptedOffer)
    Q_PROPERTY(QJSValue action READ readaction WRITE writeaction)
    Q_PROPERTY(QJSValue activation READ readactivation WRITE writeactivation)
    Q_PROPERTY(QJSValue afterSave READ readafterSave WRITE writeafterSave)
    Q_PROPERTY(QJSValue afterSaveAbandoned READ readafterSaveAbandoned WRITE writeafterSaveAbandoned)
    Q_PROPERTY(QJSValue approvalOwner READ readapprovalOwner WRITE writeapprovalOwner)
    Q_PROPERTY(QJSValue assistantCommitReady READ readassistantCommitReady WRITE writeassistantCommitReady)
    Q_PROPERTY(QJSValue assistantCreate READ readassistantCreate WRITE writeassistantCreate)
    Q_PROPERTY(QJSValue assistantCreateGuard READ readassistantCreateGuard WRITE writeassistantCreateGuard)
    Q_PROPERTY(QJSValue assistantEditing READ readassistantEditing WRITE writeassistantEditing)
    Q_PROPERTY(QJSValue assistantFocusEpoch READ readassistantFocusEpoch WRITE writeassistantFocusEpoch)
    Q_PROPERTY(QJSValue assistantSaveIntent READ readassistantSaveIntent WRITE writeassistantSaveIntent)
    Q_PROPERTY(QJSValue colourScheme READ readcolourScheme WRITE writecolourScheme)
    Q_PROPERTY(QJSValue columnWidths READ readcolumnWidths WRITE writecolumnWidths)
    Q_PROPERTY(QJSValue commitInProgress READ readcommitInProgress WRITE writecommitInProgress)
    Q_PROPERTY(QJSValue connectionAttempt READ readconnectionAttempt WRITE writeconnectionAttempt)
    Q_PROPERTY(QJSValue consentSend READ readconsentSend WRITE writeconsentSend)
    Q_PROPERTY(QJSValue contentWidths READ readcontentWidths WRITE writecontentWidths)
    Q_PROPERTY(QJSValue contentY READ readcontentY WRITE writecontentY)
    Q_PROPERTY(QJSValue contextMenu READ readcontextMenu WRITE writecontextMenu)
    Q_PROPERTY(QJSValue copy READ readcopy WRITE writecopy)
    Q_PROPERTY(QJSValue copyError READ readcopyError WRITE writecopyError)
    Q_PROPERTY(QJSValue createIntent READ readcreateIntent WRITE writecreateIntent)
    Q_PROPERTY(QJSValue createOperation READ readcreateOperation WRITE writecreateOperation)
    Q_PROPERTY(QJSValue currentFolder READ readcurrentFolder WRITE writecurrentFolder)
    Q_PROPERTY(QJSValue cursorPosition READ readcursorPosition WRITE writecursorPosition)
    Q_PROPERTY(QJSValue draft READ readdraft WRITE writedraft)
    Q_PROPERTY(QJSValue elapsedSeconds READ readelapsedSeconds WRITE writeelapsedSeconds)
    Q_PROPERTY(QJSValue fillerWidth READ readfillerWidth WRITE writefillerWidth)
    Q_PROPERTY(QJSValue fittedWidths READ readfittedWidths WRITE writefittedWidths)
    Q_PROPERTY(QJSValue flashing READ readflashing WRITE writeflashing)
    Q_PROPERTY(QJSValue flexLayout READ readflexLayout WRITE writeflexLayout)
    Q_PROPERTY(QJSValue focus READ readfocus WRITE writefocus)
    Q_PROPERTY(QJSValue followsTail READ readfollowsTail WRITE writefollowsTail)
    Q_PROPERTY(QJSValue gesture READ readgesture WRITE writegesture)
    Q_PROPERTY(QJSValue hiddenRows READ readhiddenRows WRITE writehiddenRows)
    Q_PROPERTY(QJSValue hovered READ readhovered WRITE writehovered)
    Q_PROPERTY(QJSValue implicitHeight READ readimplicitHeight WRITE writeimplicitHeight)
    Q_PROPERTY(QJSValue intent READ readintent WRITE writeintent)
    Q_PROPERTY(QJSValue jumpedUserId READ readjumpedUserId WRITE writejumpedUserId)
    Q_PROPERTY(QJSValue lastUserId READ readlastUserId WRITE writelastUserId)
    Q_PROPERTY(QJSValue lastX READ readlastX WRITE writelastX)
    Q_PROPERTY(QJSValue lastY READ readlastY WRITE writelastY)
    Q_PROPERTY(QJSValue lineCount READ readlineCount WRITE writelineCount)
    Q_PROPERTY(QJSValue lower READ readlower WRITE writelower)
    Q_PROPERTY(QJSValue mainAxisHeight READ readmainAxisHeight WRITE writemainAxisHeight)
    Q_PROPERTY(QJSValue measureRun READ readmeasureRun WRITE writemeasureRun)
    Q_PROPERTY(QJSValue measuredWidths READ readmeasuredWidths WRITE writemeasuredWidths)
    Q_PROPERTY(QJSValue noticeState READ readnoticeState WRITE writenoticeState)
    Q_PROPERTY(QJSValue ownerLife READ readownerLife WRITE writeownerLife)
    Q_PROPERTY(QJSValue ownerToken READ readownerToken WRITE writeownerToken)
    Q_PROPERTY(QJSValue patternColourScheme READ readpatternColourScheme WRITE writepatternColourScheme)
    Q_PROPERTY(QJSValue picking READ readpicking WRITE writepicking)
    Q_PROPERTY(QJSValue presentedTo READ readpresentedTo WRITE writepresentedTo)
    Q_PROPERTY(QJSValue pressX READ readpressX WRITE writepressX)
    Q_PROPERTY(QJSValue pressY READ readpressY WRITE writepressY)
    Q_PROPERTY(QJSValue reached READ readreached WRITE writereached)
    Q_PROPERTY(QJSValue refitting READ readrefitting WRITE writerefitting)
    Q_PROPERTY(QJSValue refusal READ readrefusal WRITE writerefusal)
    Q_PROPERTY(QJSValue savedSelectionEnd READ readsavedSelectionEnd WRITE writesavedSelectionEnd)
    Q_PROPERTY(QJSValue savedSelectionStart READ readsavedSelectionStart WRITE writesavedSelectionStart)
    Q_PROPERTY(QJSValue scanStackedPalette READ readscanStackedPalette WRITE writescanStackedPalette)
    Q_PROPERTY(QJSValue selectedFile READ readselectedFile WRITE writeselectedFile)
    Q_PROPERTY(QJSValue selectedRow READ readselectedRow WRITE writeselectedRow)
    Q_PROPERTY(QJSValue selection READ readselection WRITE writeselection)
    Q_PROPERTY(QJSValue selectionRevision READ readselectionRevision WRITE writeselectionRevision)
    Q_PROPERTY(QJSValue settingZoom READ readsettingZoom WRITE writesettingZoom)
    Q_PROPERTY(QJSValue shownValue READ readshownValue WRITE writeshownValue)
    Q_PROPERTY(QJSValue spareHeight READ readspareHeight WRITE writespareHeight)
    Q_PROPERTY(QJSValue start READ readstart WRITE writestart)
    Q_PROPERTY(QJSValue submittedDrafts READ readsubmittedDrafts WRITE writesubmittedDrafts)
    Q_PROPERTY(QJSValue text READ readtext WRITE writetext)
    Q_PROPERTY(QJSValue typedRefusal READ readtypedRefusal WRITE writetypedRefusal)
    Q_PROPERTY(QJSValue unfitted READ readunfitted WRITE writeunfitted)
    Q_PROPERTY(QJSValue upper READ readupper WRITE writeupper)
    Q_PROPERTY(QJSValue variant READ readvariant WRITE writevariant)
    Q_PROPERTY(QJSValue variantSwitchDeadline READ readvariantSwitchDeadline WRITE writevariantSwitchDeadline)
    Q_PROPERTY(QJSValue webIntent READ readwebIntent WRITE writewebIntent)
    Q_PROPERTY(QJSValue webRequest READ readwebRequest WRITE writewebRequest)
    Q_PROPERTY(QJSValue wideEdges READ readwideEdges WRITE writewideEdges)
    Q_PROPERTY(QJSValue workReportBinding READ readworkReportBinding WRITE writeworkReportBinding)
    Q_PROPERTY(QJSValue workReportDraft READ readworkReportDraft WRITE writeworkReportDraft)
    Q_PROPERTY(QJSValue workingSince READ readworkingSince WRITE writeworkingSince)
    Q_PROPERTY(QJSValue x READ readx WRITE writex)
    Q_PROPERTY(QJSValue xLabelsHeight READ readxLabelsHeight WRITE writexLabelsHeight)
    Q_PROPERTY(QJSValue y READ ready WRITE writey)
    Q_PROPERTY(QJSValue zip READ readzip WRITE writezip)
    Q_PROPERTY(QJSValue zoom READ readzoom WRITE writezoom)
    Q_PROPERTY(QJSValue zoomX READ readzoomX WRITE writezoomX)
    Q_PROPERTY(QJSValue zoomY READ readzoomY WRITE writezoomY)
    QQmlEngine* engine_;
    QMap<QString,QJSValue> original_, getters_, setters_;
    std::unique_ptr<QQmlContext> context_;
    QJSValue original_object_, scope_getter_, scope_setter_;
    void assign(const QString& name, const QJSValue& value) {
        const auto found = setters_.constFind(name);
        if (found == setters_.cend()) { engine_->throwError(QJSValue::ReferenceError, name); return; }
        found.value().call({value});
    }
    QJSValue binding(const QString& name) const {
        const auto found = getters_.constFind(name);
        if (found != getters_.cend()) return found.value().call();
        if (original_.contains(name)) return original_.value(name);
        engine_->throwError(QJSValue::ReferenceError, name); return {};
    }
public:
    explicit NativeScriptFixture(QQmlEngine* engine) : engine_(engine) {
        for (const auto* name : {"Qt","qsTr","Math","JSON","Object","Array","Number","String","Boolean","Date","RegExp","Error","TypeError","Reflect"})
            original_.insert(QString::fromLatin1(name), engine_->globalObject().property(QString::fromLatin1(name)));
        original_object_ = engine_->globalObject().property(QStringLiteral("Object"));
        scope_getter_ = engine_->evaluate(QStringLiteral("(function(base,key){return function(){return base[key]}})"));
        scope_setter_ = engine_->evaluate(QStringLiteral("(function(base,key){return function(value){base[key]=value}})"));
    }
    QJSValue readQt() const { return binding(QStringLiteral("Qt")); }
    void writeQt(const QJSValue& value) { assign(QStringLiteral("Qt"), value); }
    QJSValue readqsTr() const { return binding(QStringLiteral("qsTr")); }
    void writeqsTr(const QJSValue& value) { assign(QStringLiteral("qsTr"), value); }
    QJSValue readMath() const { return binding(QStringLiteral("Math")); }
    void writeMath(const QJSValue& value) { assign(QStringLiteral("Math"), value); }
    QJSValue readJSON() const { return binding(QStringLiteral("JSON")); }
    void writeJSON(const QJSValue& value) { assign(QStringLiteral("JSON"), value); }
    QJSValue readObject() const { return binding(QStringLiteral("Object")); }
    void writeObject(const QJSValue& value) { assign(QStringLiteral("Object"), value); }
    QJSValue readArray() const { return binding(QStringLiteral("Array")); }
    void writeArray(const QJSValue& value) { assign(QStringLiteral("Array"), value); }
    QJSValue readNumber() const { return binding(QStringLiteral("Number")); }
    void writeNumber(const QJSValue& value) { assign(QStringLiteral("Number"), value); }
    QJSValue readString() const { return binding(QStringLiteral("String")); }
    void writeString(const QJSValue& value) { assign(QStringLiteral("String"), value); }
    QJSValue readBoolean() const { return binding(QStringLiteral("Boolean")); }
    void writeBoolean(const QJSValue& value) { assign(QStringLiteral("Boolean"), value); }
    QJSValue readDate() const { return binding(QStringLiteral("Date")); }
    void writeDate(const QJSValue& value) { assign(QStringLiteral("Date"), value); }
    QJSValue readRegExp() const { return binding(QStringLiteral("RegExp")); }
    void writeRegExp(const QJSValue& value) { assign(QStringLiteral("RegExp"), value); }
    QJSValue readError() const { return binding(QStringLiteral("Error")); }
    void writeError(const QJSValue& value) { assign(QStringLiteral("Error"), value); }
    QJSValue readTypeError() const { return binding(QStringLiteral("TypeError")); }
    void writeTypeError(const QJSValue& value) { assign(QStringLiteral("TypeError"), value); }
    QJSValue readReflect() const { return binding(QStringLiteral("Reflect")); }
    void writeReflect(const QJSValue& value) { assign(QStringLiteral("Reflect"), value); }
    QJSValue readabandoned() const { return binding(QStringLiteral("abandoned")); }
    void writeabandoned(const QJSValue& value) { assign(QStringLiteral("abandoned"), value); }
    QJSValue readacceptedOffer() const { return binding(QStringLiteral("acceptedOffer")); }
    void writeacceptedOffer(const QJSValue& value) { assign(QStringLiteral("acceptedOffer"), value); }
    QJSValue readaction() const { return binding(QStringLiteral("action")); }
    void writeaction(const QJSValue& value) { assign(QStringLiteral("action"), value); }
    QJSValue readactivation() const { return binding(QStringLiteral("activation")); }
    void writeactivation(const QJSValue& value) { assign(QStringLiteral("activation"), value); }
    QJSValue readafterSave() const { return binding(QStringLiteral("afterSave")); }
    void writeafterSave(const QJSValue& value) { assign(QStringLiteral("afterSave"), value); }
    QJSValue readafterSaveAbandoned() const { return binding(QStringLiteral("afterSaveAbandoned")); }
    void writeafterSaveAbandoned(const QJSValue& value) { assign(QStringLiteral("afterSaveAbandoned"), value); }
    QJSValue readapprovalOwner() const { return binding(QStringLiteral("approvalOwner")); }
    void writeapprovalOwner(const QJSValue& value) { assign(QStringLiteral("approvalOwner"), value); }
    QJSValue readassistantCommitReady() const { return binding(QStringLiteral("assistantCommitReady")); }
    void writeassistantCommitReady(const QJSValue& value) { assign(QStringLiteral("assistantCommitReady"), value); }
    QJSValue readassistantCreate() const { return binding(QStringLiteral("assistantCreate")); }
    void writeassistantCreate(const QJSValue& value) { assign(QStringLiteral("assistantCreate"), value); }
    QJSValue readassistantCreateGuard() const { return binding(QStringLiteral("assistantCreateGuard")); }
    void writeassistantCreateGuard(const QJSValue& value) { assign(QStringLiteral("assistantCreateGuard"), value); }
    QJSValue readassistantEditing() const { return binding(QStringLiteral("assistantEditing")); }
    void writeassistantEditing(const QJSValue& value) { assign(QStringLiteral("assistantEditing"), value); }
    QJSValue readassistantFocusEpoch() const { return binding(QStringLiteral("assistantFocusEpoch")); }
    void writeassistantFocusEpoch(const QJSValue& value) { assign(QStringLiteral("assistantFocusEpoch"), value); }
    QJSValue readassistantSaveIntent() const { return binding(QStringLiteral("assistantSaveIntent")); }
    void writeassistantSaveIntent(const QJSValue& value) { assign(QStringLiteral("assistantSaveIntent"), value); }
    QJSValue readcolourScheme() const { return binding(QStringLiteral("colourScheme")); }
    void writecolourScheme(const QJSValue& value) { assign(QStringLiteral("colourScheme"), value); }
    QJSValue readcolumnWidths() const { return binding(QStringLiteral("columnWidths")); }
    void writecolumnWidths(const QJSValue& value) { assign(QStringLiteral("columnWidths"), value); }
    QJSValue readcommitInProgress() const { return binding(QStringLiteral("commitInProgress")); }
    void writecommitInProgress(const QJSValue& value) { assign(QStringLiteral("commitInProgress"), value); }
    QJSValue readconnectionAttempt() const { return binding(QStringLiteral("connectionAttempt")); }
    void writeconnectionAttempt(const QJSValue& value) { assign(QStringLiteral("connectionAttempt"), value); }
    QJSValue readconsentSend() const { return binding(QStringLiteral("consentSend")); }
    void writeconsentSend(const QJSValue& value) { assign(QStringLiteral("consentSend"), value); }
    QJSValue readcontentWidths() const { return binding(QStringLiteral("contentWidths")); }
    void writecontentWidths(const QJSValue& value) { assign(QStringLiteral("contentWidths"), value); }
    QJSValue readcontentY() const { return binding(QStringLiteral("contentY")); }
    void writecontentY(const QJSValue& value) { assign(QStringLiteral("contentY"), value); }
    QJSValue readcontextMenu() const { return binding(QStringLiteral("contextMenu")); }
    void writecontextMenu(const QJSValue& value) { assign(QStringLiteral("contextMenu"), value); }
    QJSValue readcopy() const { return binding(QStringLiteral("copy")); }
    void writecopy(const QJSValue& value) { assign(QStringLiteral("copy"), value); }
    QJSValue readcopyError() const { return binding(QStringLiteral("copyError")); }
    void writecopyError(const QJSValue& value) { assign(QStringLiteral("copyError"), value); }
    QJSValue readcreateIntent() const { return binding(QStringLiteral("createIntent")); }
    void writecreateIntent(const QJSValue& value) { assign(QStringLiteral("createIntent"), value); }
    QJSValue readcreateOperation() const { return binding(QStringLiteral("createOperation")); }
    void writecreateOperation(const QJSValue& value) { assign(QStringLiteral("createOperation"), value); }
    QJSValue readcurrentFolder() const { return binding(QStringLiteral("currentFolder")); }
    void writecurrentFolder(const QJSValue& value) { assign(QStringLiteral("currentFolder"), value); }
    QJSValue readcursorPosition() const { return binding(QStringLiteral("cursorPosition")); }
    void writecursorPosition(const QJSValue& value) { assign(QStringLiteral("cursorPosition"), value); }
    QJSValue readdraft() const { return binding(QStringLiteral("draft")); }
    void writedraft(const QJSValue& value) { assign(QStringLiteral("draft"), value); }
    QJSValue readelapsedSeconds() const { return binding(QStringLiteral("elapsedSeconds")); }
    void writeelapsedSeconds(const QJSValue& value) { assign(QStringLiteral("elapsedSeconds"), value); }
    QJSValue readfillerWidth() const { return binding(QStringLiteral("fillerWidth")); }
    void writefillerWidth(const QJSValue& value) { assign(QStringLiteral("fillerWidth"), value); }
    QJSValue readfittedWidths() const { return binding(QStringLiteral("fittedWidths")); }
    void writefittedWidths(const QJSValue& value) { assign(QStringLiteral("fittedWidths"), value); }
    QJSValue readflashing() const { return binding(QStringLiteral("flashing")); }
    void writeflashing(const QJSValue& value) { assign(QStringLiteral("flashing"), value); }
    QJSValue readflexLayout() const { return binding(QStringLiteral("flexLayout")); }
    void writeflexLayout(const QJSValue& value) { assign(QStringLiteral("flexLayout"), value); }
    QJSValue readfocus() const { return binding(QStringLiteral("focus")); }
    void writefocus(const QJSValue& value) { assign(QStringLiteral("focus"), value); }
    QJSValue readfollowsTail() const { return binding(QStringLiteral("followsTail")); }
    void writefollowsTail(const QJSValue& value) { assign(QStringLiteral("followsTail"), value); }
    QJSValue readgesture() const { return binding(QStringLiteral("gesture")); }
    void writegesture(const QJSValue& value) { assign(QStringLiteral("gesture"), value); }
    QJSValue readhiddenRows() const { return binding(QStringLiteral("hiddenRows")); }
    void writehiddenRows(const QJSValue& value) { assign(QStringLiteral("hiddenRows"), value); }
    QJSValue readhovered() const { return binding(QStringLiteral("hovered")); }
    void writehovered(const QJSValue& value) { assign(QStringLiteral("hovered"), value); }
    QJSValue readimplicitHeight() const { return binding(QStringLiteral("implicitHeight")); }
    void writeimplicitHeight(const QJSValue& value) { assign(QStringLiteral("implicitHeight"), value); }
    QJSValue readintent() const { return binding(QStringLiteral("intent")); }
    void writeintent(const QJSValue& value) { assign(QStringLiteral("intent"), value); }
    QJSValue readjumpedUserId() const { return binding(QStringLiteral("jumpedUserId")); }
    void writejumpedUserId(const QJSValue& value) { assign(QStringLiteral("jumpedUserId"), value); }
    QJSValue readlastUserId() const { return binding(QStringLiteral("lastUserId")); }
    void writelastUserId(const QJSValue& value) { assign(QStringLiteral("lastUserId"), value); }
    QJSValue readlastX() const { return binding(QStringLiteral("lastX")); }
    void writelastX(const QJSValue& value) { assign(QStringLiteral("lastX"), value); }
    QJSValue readlastY() const { return binding(QStringLiteral("lastY")); }
    void writelastY(const QJSValue& value) { assign(QStringLiteral("lastY"), value); }
    QJSValue readlineCount() const { return binding(QStringLiteral("lineCount")); }
    void writelineCount(const QJSValue& value) { assign(QStringLiteral("lineCount"), value); }
    QJSValue readlower() const { return binding(QStringLiteral("lower")); }
    void writelower(const QJSValue& value) { assign(QStringLiteral("lower"), value); }
    QJSValue readmainAxisHeight() const { return binding(QStringLiteral("mainAxisHeight")); }
    void writemainAxisHeight(const QJSValue& value) { assign(QStringLiteral("mainAxisHeight"), value); }
    QJSValue readmeasureRun() const { return binding(QStringLiteral("measureRun")); }
    void writemeasureRun(const QJSValue& value) { assign(QStringLiteral("measureRun"), value); }
    QJSValue readmeasuredWidths() const { return binding(QStringLiteral("measuredWidths")); }
    void writemeasuredWidths(const QJSValue& value) { assign(QStringLiteral("measuredWidths"), value); }
    QJSValue readnoticeState() const { return binding(QStringLiteral("noticeState")); }
    void writenoticeState(const QJSValue& value) { assign(QStringLiteral("noticeState"), value); }
    QJSValue readownerLife() const { return binding(QStringLiteral("ownerLife")); }
    void writeownerLife(const QJSValue& value) { assign(QStringLiteral("ownerLife"), value); }
    QJSValue readownerToken() const { return binding(QStringLiteral("ownerToken")); }
    void writeownerToken(const QJSValue& value) { assign(QStringLiteral("ownerToken"), value); }
    QJSValue readpatternColourScheme() const { return binding(QStringLiteral("patternColourScheme")); }
    void writepatternColourScheme(const QJSValue& value) { assign(QStringLiteral("patternColourScheme"), value); }
    QJSValue readpicking() const { return binding(QStringLiteral("picking")); }
    void writepicking(const QJSValue& value) { assign(QStringLiteral("picking"), value); }
    QJSValue readpresentedTo() const { return binding(QStringLiteral("presentedTo")); }
    void writepresentedTo(const QJSValue& value) { assign(QStringLiteral("presentedTo"), value); }
    QJSValue readpressX() const { return binding(QStringLiteral("pressX")); }
    void writepressX(const QJSValue& value) { assign(QStringLiteral("pressX"), value); }
    QJSValue readpressY() const { return binding(QStringLiteral("pressY")); }
    void writepressY(const QJSValue& value) { assign(QStringLiteral("pressY"), value); }
    QJSValue readreached() const { return binding(QStringLiteral("reached")); }
    void writereached(const QJSValue& value) { assign(QStringLiteral("reached"), value); }
    QJSValue readrefitting() const { return binding(QStringLiteral("refitting")); }
    void writerefitting(const QJSValue& value) { assign(QStringLiteral("refitting"), value); }
    QJSValue readrefusal() const { return binding(QStringLiteral("refusal")); }
    void writerefusal(const QJSValue& value) { assign(QStringLiteral("refusal"), value); }
    QJSValue readsavedSelectionEnd() const { return binding(QStringLiteral("savedSelectionEnd")); }
    void writesavedSelectionEnd(const QJSValue& value) { assign(QStringLiteral("savedSelectionEnd"), value); }
    QJSValue readsavedSelectionStart() const { return binding(QStringLiteral("savedSelectionStart")); }
    void writesavedSelectionStart(const QJSValue& value) { assign(QStringLiteral("savedSelectionStart"), value); }
    QJSValue readscanStackedPalette() const { return binding(QStringLiteral("scanStackedPalette")); }
    void writescanStackedPalette(const QJSValue& value) { assign(QStringLiteral("scanStackedPalette"), value); }
    QJSValue readselectedFile() const { return binding(QStringLiteral("selectedFile")); }
    void writeselectedFile(const QJSValue& value) { assign(QStringLiteral("selectedFile"), value); }
    QJSValue readselectedRow() const { return binding(QStringLiteral("selectedRow")); }
    void writeselectedRow(const QJSValue& value) { assign(QStringLiteral("selectedRow"), value); }
    QJSValue readselection() const { return binding(QStringLiteral("selection")); }
    void writeselection(const QJSValue& value) { assign(QStringLiteral("selection"), value); }
    QJSValue readselectionRevision() const { return binding(QStringLiteral("selectionRevision")); }
    void writeselectionRevision(const QJSValue& value) { assign(QStringLiteral("selectionRevision"), value); }
    QJSValue readsettingZoom() const { return binding(QStringLiteral("settingZoom")); }
    void writesettingZoom(const QJSValue& value) { assign(QStringLiteral("settingZoom"), value); }
    QJSValue readshownValue() const { return binding(QStringLiteral("shownValue")); }
    void writeshownValue(const QJSValue& value) { assign(QStringLiteral("shownValue"), value); }
    QJSValue readspareHeight() const { return binding(QStringLiteral("spareHeight")); }
    void writespareHeight(const QJSValue& value) { assign(QStringLiteral("spareHeight"), value); }
    QJSValue readstart() const { return binding(QStringLiteral("start")); }
    void writestart(const QJSValue& value) { assign(QStringLiteral("start"), value); }
    QJSValue readsubmittedDrafts() const { return binding(QStringLiteral("submittedDrafts")); }
    void writesubmittedDrafts(const QJSValue& value) { assign(QStringLiteral("submittedDrafts"), value); }
    QJSValue readtext() const { return binding(QStringLiteral("text")); }
    void writetext(const QJSValue& value) { assign(QStringLiteral("text"), value); }
    QJSValue readtypedRefusal() const { return binding(QStringLiteral("typedRefusal")); }
    void writetypedRefusal(const QJSValue& value) { assign(QStringLiteral("typedRefusal"), value); }
    QJSValue readunfitted() const { return binding(QStringLiteral("unfitted")); }
    void writeunfitted(const QJSValue& value) { assign(QStringLiteral("unfitted"), value); }
    QJSValue readupper() const { return binding(QStringLiteral("upper")); }
    void writeupper(const QJSValue& value) { assign(QStringLiteral("upper"), value); }
    QJSValue readvariant() const { return binding(QStringLiteral("variant")); }
    void writevariant(const QJSValue& value) { assign(QStringLiteral("variant"), value); }
    QJSValue readvariantSwitchDeadline() const { return binding(QStringLiteral("variantSwitchDeadline")); }
    void writevariantSwitchDeadline(const QJSValue& value) { assign(QStringLiteral("variantSwitchDeadline"), value); }
    QJSValue readwebIntent() const { return binding(QStringLiteral("webIntent")); }
    void writewebIntent(const QJSValue& value) { assign(QStringLiteral("webIntent"), value); }
    QJSValue readwebRequest() const { return binding(QStringLiteral("webRequest")); }
    void writewebRequest(const QJSValue& value) { assign(QStringLiteral("webRequest"), value); }
    QJSValue readwideEdges() const { return binding(QStringLiteral("wideEdges")); }
    void writewideEdges(const QJSValue& value) { assign(QStringLiteral("wideEdges"), value); }
    QJSValue readworkReportBinding() const { return binding(QStringLiteral("workReportBinding")); }
    void writeworkReportBinding(const QJSValue& value) { assign(QStringLiteral("workReportBinding"), value); }
    QJSValue readworkReportDraft() const { return binding(QStringLiteral("workReportDraft")); }
    void writeworkReportDraft(const QJSValue& value) { assign(QStringLiteral("workReportDraft"), value); }
    QJSValue readworkingSince() const { return binding(QStringLiteral("workingSince")); }
    void writeworkingSince(const QJSValue& value) { assign(QStringLiteral("workingSince"), value); }
    QJSValue readx() const { return binding(QStringLiteral("x")); }
    void writex(const QJSValue& value) { assign(QStringLiteral("x"), value); }
    QJSValue readxLabelsHeight() const { return binding(QStringLiteral("xLabelsHeight")); }
    void writexLabelsHeight(const QJSValue& value) { assign(QStringLiteral("xLabelsHeight"), value); }
    QJSValue ready() const { return binding(QStringLiteral("y")); }
    void writey(const QJSValue& value) { assign(QStringLiteral("y"), value); }
    QJSValue readzip() const { return binding(QStringLiteral("zip")); }
    void writezip(const QJSValue& value) { assign(QStringLiteral("zip"), value); }
    QJSValue readzoom() const { return binding(QStringLiteral("zoom")); }
    void writezoom(const QJSValue& value) { assign(QStringLiteral("zoom"), value); }
    QJSValue readzoomX() const { return binding(QStringLiteral("zoomX")); }
    void writezoomX(const QJSValue& value) { assign(QStringLiteral("zoomX"), value); }
    QJSValue readzoomY() const { return binding(QStringLiteral("zoomY")); }
    void writezoomY(const QJSValue& value) { assign(QStringLiteral("zoomY"), value); }
    Q_INVOKABLE void exposeScope(const QJSValue& scope, const QStringList& lexicalNames) {
        if (!scope.isObject() || scope.strictlyEquals(engine_->globalObject()) ||
            (scope.isQObject() && scope.toQObject() == this)) return;
        QJSValueIterator iterator(scope);
        while (iterator.hasNext()) {
            iterator.next(); const auto name = iterator.name();
            if (name == QLatin1String("ApplicationInfo") || name.startsWith(QLatin1String("__native")) || lexicalNames.contains(name)) continue;
            expose(name, scope_getter_.call({scope, QJSValue(name)}), scope_setter_.call({scope, QJSValue(name)}));
        }
    }
    Q_INVOKABLE QString reportDocument(const QString& json) {
        try { return QString::fromStdString(edi::report_html(edi::report_from_json(json.toStdString()))); }
        catch (const std::exception& error) { engine_->throwError(QString::fromUtf8(error.what())); return {}; }
    }
    Q_INVOKABLE void expose(const QString& name, const QJSValue& getter, const QJSValue& setter) {
        if (metaObject()->indexOfProperty(name.toUtf8().constData()) >= 0) {
            getters_.insert(name, getter); setters_.insert(name, setter); return;
        }
        auto descriptor = engine_->newObject();
        descriptor.setProperty(QStringLiteral("configurable"), true);
        descriptor.setProperty(QStringLiteral("get"), getter);
        descriptor.setProperty(QStringLiteral("set"), setter);
        original_object_.property(QStringLiteral("defineProperty")).callWithInstance(original_object_,
            {engine_->globalObject(), QJSValue(name), descriptor});
    }
    Q_INVOKABLE QVariantMap execute(QObject* info) {
        QVariantMap result;
        QFile input(QString::fromUtf8(qgetenv("EDI_NATIVE_SCRIPT_INPUT")));
        if (!info || qjsEngine(info) != engine_ || !input.open(QIODevice::ReadOnly)) {
            result = {{"ok", false}, {"error", "The native witness requires its real same-engine singleton and an explicit input file"}};
        } else {
            auto native = engine_->newObject();
            const auto* meta = info->metaObject();
            for (int e = 0; e < meta->enumeratorCount(); ++e) {
                const auto keys = meta->enumerator(e);
                for (int k = 0; k < keys.keyCount(); ++k)
                    native.setProperty(QString::fromUtf8(keys.key(k)), keys.value(k));
            }
            // Install own enum values before the QObject prototype's read-only names.
            native.setPrototype(engine_->newQObject(info));
            auto global = engine_->globalObject();
            global.setProperty(QStringLiteral("ApplicationInfo"), native);
            global.setProperty(QStringLiteral("__nativeFixture"), engine_->newQObject(this));
            global.setProperty(QStringLiteral("__nativeOutput"), engine_->newArray());
            global.setProperty(QStringLiteral("__nativeInvocations"), 0);
            context_ = std::make_unique<QQmlContext>(engine_->rootContext());
            context_->setContextObject(this);
            // A real static QObject scope lets Qt resolve the same lexical
            // fixture values, including Qt/qsTr, before intrinsic fallbacks.
            const auto program = QStringLiteral("(function(){\n") + QString::fromUtf8(input.readAll()) + QStringLiteral("\n})()");
            QQmlExpression expression(context_.get(), this, program);
            expression.evaluate();
            const auto captured = global.property(QStringLiteral("__nativeOutput"));
            const int calls = global.property(QStringLiteral("__nativeInvocations")).toInt();
            const int outputs = captured.property(QStringLiteral("length")).toInt();
            const bool ok = !expression.hasError() && outputs > 0;
            result = {{"version", 2}, {"ok", ok}, {"error", expression.hasError() ? expression.error().toString() : QString()},
                      {"output", captured.property(QStringLiteral("join")).callWithInstance(captured, {QJSValue(QString())}).toString()},
                      {"outputCount", outputs}, {"nativeCalls", calls}};
            if (engine_->hasError()) engine_->catchError();
        }
        QFile output(QString::fromUtf8(qgetenv("EDI_NATIVE_SCRIPT_RESULT")));
        if (!output.open(QIODevice::WriteOnly)) return {{"ok", false}, {"error", "The native witness requires an explicit writable result file"}};
        output.write(QJsonDocument::fromVariant(result).toJson());
        return result;
    }
};
static void registerNativeScriptFixture() {
    qmlRegisterSingletonType<NativeScriptFixture>("EdiNativeScriptFixture", 1, 0, "NativeScriptFixture",
        [](QQmlEngine* engine, QJSEngine*) -> QObject* { return new NativeScriptFixture(engine); });
}
Q_COREAPP_STARTUP_FUNCTION(registerNativeScriptFixture)
#include "test_e11_t5_native_script_fixture.moc"
