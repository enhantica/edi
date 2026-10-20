// Tests-owned pure serialization adapter. No Session, provider or production QObject is queried.
#include <QCoreApplication>
#include <QJsonDocument>
#include <QJsonObject>
#include <QtQml/qqml.h>

#include "assistant_outgoing.hpp"
#include "assistant_native_tools.hpp"
#include "assistant_action_refusal.hpp"

class Outgoing679Projection final : public QObject {
    Q_OBJECT
public:
    using QObject::QObject;
    // Test-only direct use of the FIRST validator/argument boundary. No Session,
    // dispatcher, native work, provider or model mutation is constructed here.
    Q_INVOKABLE QJsonObject purpose(const QJsonObject& arguments,const QString& tool) const {
        try {
            if(tool.isEmpty())(void)edi_app::assistant_native_purpose(arguments);
            else edi_app::assistant_native_arguments(tool,arguments);
            return {{"kind","accepted"}};
        } catch(const edi_app::ActionRefusal& refusal) {
            return {{"kind","typed"},{"action_error",QString::fromLatin1(refusal.error)},
                {"action_field",QString::fromLatin1(refusal.field)}};
        } catch(const std::invalid_argument&) {return {{"kind","invalid"}};}
        catch(...) {return {{"kind","unexpected"}};}
    }
    Q_INVOKABLE QJsonObject encode(const QJsonObject& source) const {
        try {
        namespace outgoing=edi_app::outgoing;
        const auto admitted=outgoing::size(source,outgoing::Role::Result);
        const auto projected=outgoing::project(source,outgoing::Role::Result,admitted);
        const auto wire=QJsonDocument(projected).toJson(QJsonDocument::Compact);
        // Use the ACTUAL original maximum admission routine, not a copied code table/formula.
        auto maximum=source;
        outgoing::complete_result_maximum(maximum);
        const auto maximumAdmitted=outgoing::size(maximum,outgoing::Role::Result);
        const auto maximumProjected=outgoing::project(maximum,outgoing::Role::Result,maximumAdmitted);
        const auto maximumWire=QJsonDocument(maximumProjected).toJson(QJsonDocument::Compact);
        return {{"wire",QString::fromUtf8(wire)},{"admitted",static_cast<double>(admitted)},
            {"bytes",static_cast<double>(wire.size())},{"maximum_wire",QString::fromUtf8(maximumWire)},
            {"maximum_admitted",static_cast<double>(maximumAdmitted)},
            {"maximum_bytes",static_cast<double>(maximumWire.size())}};
        } catch(const std::invalid_argument&) {return {{"kind","invalid"}};}
        catch(const std::length_error&) {return {{"kind","capacity"}};}
        catch(...) {return {{"kind","unexpected"}};}
    }
};
static void registerOutgoing679Projection() {
    qmlRegisterSingletonType<Outgoing679Projection>("Outgoing679Reference",1,0,"Outgoing679",
        [](QQmlEngine*,QJSEngine*) -> QObject* {return new Outgoing679Projection;});
}
Q_COREAPP_STARTUP_FUNCTION(registerOutgoing679Projection)
#include "test_outgoing679_projection.moc"
