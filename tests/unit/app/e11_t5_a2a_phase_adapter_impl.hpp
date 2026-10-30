#pragma once
namespace e11_a2a_phase {
inline bool isOriginal() {return true;}
inline QByteArray phaseName() {return QByteArrayLiteral("original");}
inline QVariantMap snapshot(QObject* row) {
    if(absentSnapshot(row))return {{"is_null",true}};
    const auto value=unwrappedSnapshot(row);
    if(value.metaType()!=QMetaType::fromType<QVariantMap>())
        throw std::runtime_error("Original phase requires the actual map snapshot representation");
    const auto map=value.toMap();
    for(const auto* key:{"row_id","kind","status"})
        if(map.value(key).metaType()!=QMetaType::fromType<QString>())
            throw std::runtime_error("Original snapshot has no exact stored string identity");
    return {{"is_null",false},{"snapshot",QVariantMap{{"row_id",map.value("row_id")},
        {"kind",map.value("kind")},{"status",map.value("status")}}}};
}
inline QString originalTyped(QObject* row,const QString& call,const QVariantMap& detail) {
    QQmlContext context(QQmlEngine::contextForObject(row));
    context.setContextProperty("e11A2aTypedDetail",detail);
    QQmlExpression expression(&context,row,call);
    const auto result=expression.evaluate();
    if(expression.hasError())throw std::runtime_error(expression.error().toString().toStdString());
    if(result.metaType()!=QMetaType::fromType<QString>())throw std::runtime_error("Original typed composition did not return a string");
    return result.toString();
}
inline QString description(QObject* row,bool full,const QVariantMap& payload) {
    return originalTyped(row,"activityDescription("+QString(full?"true":"false")+",e11A2aTypedDetail)",payload);
}
inline QString body(QObject* row,const QVariantMap& detail) {
    return originalTyped(row,QStringLiteral("fullHumanDescription(e11A2aTypedDetail)"),detail);
}
inline QString copy(QObject* row,const QVariantMap& detail) {
    return originalTyped(row,QStringLiteral("humanActivityText(e11A2aTypedDetail)"),detail);
}
}
