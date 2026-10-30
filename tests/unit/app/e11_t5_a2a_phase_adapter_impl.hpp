#pragma once
#include "assistant_message_presentation.hpp"
namespace e11_a2a_phase {
inline bool isOriginal() {return false;}
inline QByteArray phaseName() {return QByteArrayLiteral("native");}
inline QVariantMap snapshot(QObject* row) {
    if(absentSnapshot(row))return {{"is_null",true}};
    const auto value=unwrappedSnapshot(row);
    using Snapshot=edi_app::assistant_presentation::HumanActivitySnapshot;
    if(value.metaType()!=QMetaType::fromType<Snapshot>())
        throw std::runtime_error("Native phase requires its exact registered HumanActivitySnapshot metatype");
    const auto stored=value.value<Snapshot>();
    return {{"is_null",false},{"snapshot",QVariantMap{{"row_id",stored.rowId},
        {"kind",stored.kind},{"status",stored.status}}}};
}
inline edi_app::assistant_presentation::HumanActivityInput input(QObject* row,const QVariantMap& detail) {
    edi_app::assistant_presentation::HumanActivityInput value;
    value.kind=row->property("kind").toString();
    value.caption=observedCaption(row);
    value.payload=QJsonObject::fromVariantMap(detail.value("payload").toMap());
    value.text=detail.value("text").toString();
    value.provenance=detail.value("provenance").toString();
    value.commandActivity=false;value.decisionActivity=false;
    return value;
}
inline QString description(QObject* row,bool full,const QVariantMap& payload) {
    const auto value=input(row,{{"payload",payload}});
    const auto literal=edi_app::assistant_presentation::activityHumanDescription(value);
    if(full)return literal;
    // Transport every QString code unit literally into the EXISTING imported
    // row scope; a new C++ child context does not inherit component imports.
    QString source=QStringLiteral("ApplicationInfo.assistantSingleLineText(\"");
    for(const auto character:literal)
        source+=QStringLiteral("\\u")+QString::number(character.unicode(),16).rightJustified(4,QLatin1Char('0'));
    source+=QStringLiteral("\")");
    const auto result=evaluate(row,source);
    if(result.metaType()!=QMetaType::fromType<QString>())throw std::runtime_error("Native public normalization did not return a string");
    return result.toString();
}
inline QString body(QObject* row,const QVariantMap& detail) {
    const auto value=input(row,detail);
    return edi_app::assistant_presentation::fullHumanDescription(value,
        edi_app::assistant_presentation::humanDescriptionLines(value));
}
inline QString copy(QObject* row,const QVariantMap& detail) {
    return edi_app::assistant_presentation::humanCopyText(observedCaption(row),body(row,detail));
}
}
