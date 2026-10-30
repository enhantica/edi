#pragma once
#include <QByteArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJSValue>
#include <QMetaMethod>
#include <QObject>
#include <QQmlContext>
#include <QQmlEngine>
#include <QQmlExpression>
#include <QStringList>
#include <QVariantMap>
#include <stdexcept>

namespace e11_a2a_phase {
inline QVariant evaluate(QObject* row,const QString& source) {
    QQmlExpression expression(QQmlEngine::contextForObject(row),row,source);
    const auto value=expression.evaluate();
    if(expression.hasError())throw std::runtime_error(expression.error().toString().toStdString());
    return value;
}
inline QVariant unwrappedSnapshot(QObject* row) {
    auto value=row->property("humanDetailsSnapshot");
    if(value.metaType()==QMetaType::fromType<QJSValue>())value=value.value<QJSValue>().toVariant();
    return value;
}
inline bool absentSnapshot(QObject* row) {
    const auto value=evaluate(row,"humanDetailsSnapshot === null");
    if(value.metaType()!=QMetaType::fromType<bool>())
        throw std::runtime_error("The actual original snapshot-null observation is not boolean");
    return value.toBool();
}
inline QString observedCaption(QObject* row) {
    const auto headers=row->findChildren<QObject*>(QStringLiteral("assistant.activity.toggle"));
    if(headers.size()!=1)throw std::runtime_error("The typed web carrier needs its one actual original disclosure");
    if(row->property("kind").toString()!=QStringLiteral("activity"))
        throw std::runtime_error("A2a typed composition is scoped to its actual activity/web fixture");
    return headers.front()->property("text").toString();
}
}
#include "e11_t5_a2a_phase_adapter_impl.hpp"

namespace e11_a2a_phase {
inline void requireDeclaredPhase() {
    const auto actual=qgetenv("EDI_E11_T5_A2A_PHASE");
    if(!actual.isEmpty() && actual!=phaseName())throw std::runtime_error("The declared A2a phase disagrees with its selected source header");
    const auto source=qgetenv("EDI_E11_T5_A2A_SOURCE_SHA");
    if(!source.isEmpty() && source.size()!=40)throw std::runtime_error("The declared A2a source SHA must be complete");
    for(const auto byte:source)if(!((byte>='0'&&byte<='9')||(byte>='a'&&byte<='f')))
        throw std::runtime_error("The declared A2a phase source must be a lowercase full Git SHA");
}
inline void requirePhaseConsumer(QObject* row) {
    for(const auto* name:{"activityDescription","fullHumanDescription","humanActivityText","readHumanDetails"}) {
        bool present=false;
        for(int index=0;index<row->metaObject()->methodCount();++index)
            if(row->metaObject()->method(index).name()==name)present=true;
        if(present!=isOriginal())throw std::runtime_error("The declared phase disagrees with private-QML procedure retirement");
    }
}
inline QString descriptionExpression(bool full,const QString& source=QString()) {
    if(isOriginal())return "activityDescription("+QString(full?"true":"false")+(source.isEmpty()?QString():","+source)+")";
    return "a2aTestValues.description(a2aOriginalRow,"+QString(full?"true":"false")+","+(source.isEmpty()?QStringLiteral("payload"):source)+")";
}
inline QString bodyExpression(const QString& detail) {
    return isOriginal()?"fullHumanDescription("+detail+")":"a2aTestValues.body(a2aOriginalRow,"+detail+")";
}
inline QString copyExpression(const QString& detail) {
    return isOriginal()?"humanActivityText("+detail+")":"a2aTestValues.copy(a2aOriginalRow,"+detail+")";
}
inline QString webExpression(const QString& source) {
    return isOriginal()?"activityDescription(false,"+source+")":"ApplicationInfo.assistantWebSearchCaption("+source+")";
}
inline QStringList mechanismCalls() {
    if(isOriginal())return {"activityDescription(false,p)","activityDescription(true,p)",
        "fullHumanDescription({payload:p})","humanActivityText({payload:p})"};
    return {"ApplicationInfo.assistantWebSearchCaption(p)"};
}
inline QString noAdmittedSnapshotExpression() {
    return isOriginal()?QStringLiteral("readHumanDetails() === null"):
        QStringLiteral("a2aTestValues.snapshot(a2aOriginalRow).is_null === true");
}
}
