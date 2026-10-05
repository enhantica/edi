#include <QtQml/qqml.h>

#include <QCoreApplication>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>

#include "edi/io.hpp"
#include "project_view_model.hpp"

class RelationUndoObserver final : public QObject {
    Q_OBJECT
   public:
    using QObject::QObject;
    Q_INVOKABLE QString state(QObject* object) const {
        const auto* vm = qobject_cast<edi_app::ProjectViewModel*>(object);
        if (vm == nullptr) return {};
        const auto& project = vm->project();
        QJsonArray aliases, constraints, parameters;
        for (const auto& alias : project.aliases) {
            aliases.append(
                QJsonArray{QString::fromStdString(alias->id.value()),
                           QString::fromStdString(alias->parameter_unique_name.value())});
        }
        for (const auto& constraint : project.constraints) {
            constraints.append(QJsonArray{QString::fromStdString(constraint->id.value()),
                                          QString::fromStdString(constraint->expression.value()),
                                          constraint->enabled.get()});
        }
        for (const auto* parameter : const_cast<edi::Project&>(project).parameters()) {
            parameters.append(QJsonArray{parameter->value.get(), parameter->free.get(),
                                         parameter->uncertainty.get().has_value()
                                             ? QJsonValue(*parameter->uncertainty.get())
                                             : QJsonValue(),
                                         static_cast<int>(parameter->dependence)});
        }
        return QString::fromUtf8(QJsonDocument(QJsonObject{{"aliases", aliases},
                                                           {"constraints", constraints},
                                                           {"parameters", parameters}})
                                     .toJson(QJsonDocument::Compact));
    }
    Q_INVOKABLE bool seedPriorUncertainty(QObject* object) const {
        auto* vm = qobject_cast<edi_app::ProjectViewModel*>(object);
        if (vm == nullptr) return false;
        auto& project = const_cast<edi::Project&>(vm->project());
        project.structure().atom_sites[0]->adp_iso.uncertainty = .023;
        project.structure().atom_sites[0]->adp_iso.free = true;
        project.structure().atom_sites[1]->adp_iso.uncertainty = .017;
        return true;
    }
};
static void registerRelationUndoObserver() {
    qmlRegisterSingletonType<RelationUndoObserver>(
        "RelationUndoReference", 1, 0, "RelationUndoObserver",
        [](QQmlEngine*, QJSEngine*) -> QObject* { return new RelationUndoObserver; });
}
Q_COREAPP_STARTUP_FUNCTION(registerRelationUndoObserver)
#include "test_constraint_undo_observer.moc"
