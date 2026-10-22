// SPDX-License-Identifier: BSD-3-Clause
#include <QCoreApplication>
#include <QtQml/qqml.h>
#include "parameter_item.hpp"

class IntegerPrecisionProbe final : public QObject {
    Q_OBJECT
public:
    using QObject::QObject;
    Q_INVOKABLE bool setUncertainty(QObject* object, double uncertainty) const {
        auto* item = qobject_cast<edi_app::ParameterItem*>(object);
        if (!item || !item->parameter()) return false;
        auto* parameter = const_cast<edi::Parameter*>(item->parameter());
        parameter->uncertainty = uncertainty;
        return item->publish() == edi_app::ParameterItem::UncertaintyField;
    }
};
static void registerIntegerPrecisionProbe() {
    qmlRegisterSingletonType<IntegerPrecisionProbe>(
        "IntegerUncertaintyReference", 1, 0, "IntegerPrecision",
        [](QQmlEngine*, QJSEngine*) -> QObject* { return new IntegerPrecisionProbe; });
}
Q_COREAPP_STARTUP_FUNCTION(registerIntegerPrecisionProbe)
#include "test_integer_uncertainty.moc"
