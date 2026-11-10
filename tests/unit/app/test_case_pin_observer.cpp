// Test-only observation of the real app worker, with no independent fitting implementation.
#include <QtQml/qqml.h>

#include <QCoreApplication>
#include <QFile>
#include <QJSEngine>
#include <QJsonDocument>
#include <QJsonObject>
#include <QPointer>
#include <QQmlEngine>

#include "edi/report.hpp"
#include "fit_view_model.hpp"
#include "project_view_model.hpp"
#include "report_view_model.hpp"

class CasePinProof final : public QObject {
    Q_OBJECT
    Q_PROPERTY(bool completed READ completed NOTIFY changed)
   public:
    using QObject::QObject;
    bool completed() const { return completed_; }
    Q_INVOKABLE QString identity() const { return qEnvironmentVariable("EDI_CASE_PIN_ID"); }
    Q_INVOKABLE QString operation() const {
        return qEnvironmentVariable("EDI_CASE_PIN_OPERATION");
    }
    Q_INVOKABLE bool ready(QObject* object) const {
        auto* view = qobject_cast<edi_app::ProjectViewModel*>(object);
        if (!view || view->project().experiments.empty()) return false;
        for (const auto& experiment : view->project().experiments) {
            if (experiment->experiment_type.sample_form == edi::SampleFormEnum::SINGLE_CRYSTAL) {
                if (!experiment->reflections || experiment->reflections->intensity_calc.empty())
                    return false;
            } else if (!experiment->data || experiment->data->intensity_calc.empty()) {
                return false;
            }
        }
        return true;
    }
    Q_INVOKABLE bool start(QObject* object) {
        auto* view = qobject_cast<edi_app::ProjectViewModel*>(object);
        if (!view || completed_) return false;
        initial_ = view->report()->model().value("parameters");
        if (operation() == "calc") {
            std::size_t count = 0;
            double checksum = 0;
            for (const auto& experiment : view->project().experiments) {
                const auto& values =
                    experiment->experiment_type.sample_form == edi::SampleFormEnum::SINGLE_CRYSTAL
                        ? experiment->reflections->intensity_calc
                        : experiment->data->intensity_calc;
                count += values.size();
                for (double value : values) checksum += value;
            }
            machine_ = QString::fromStdString(
                edi::calc_report(count, checksum, 0, edi::VerbosityEnum::FULL));
            completed_ = true;
            emit changed();
            return true;
        }
        QPointer<edi_app::ProjectViewModel> owner(view);
        view->fit()->startNative([this, owner](const edi::FitReport& report, bool) {
            if (owner && report.adopted() && report.status != edi::FitStatus::CANCELLED &&
                report.result) {
                machine_ = QString::fromStdString(edi::machine_report(
                    owner->project(), *report.result, edi::VerbosityEnum::FULL));
            }
            completed_ = true;
            emit changed();
        });
        return true;
    }
    Q_INVOKABLE bool writeReceipt() const {
        if (!completed_ || machine_.isEmpty()) return false;
        const QJsonObject document{
            {"case", identity()},      {"operation", operation()},
            {"completed", completed_}, {"initial_parameters", QJsonValue::fromVariant(initial_)},
            {"machine", machine_},
        };
        QFile file(qEnvironmentVariable("EDI_CASE_PIN_RECEIPT"));
        if (!file.open(QIODevice::WriteOnly | QIODevice::Truncate)) return false;
        const auto bytes = QJsonDocument(document).toJson();
        return file.write(bytes) == bytes.size() && file.flush();
    }
   signals:
    void changed();

   private:
    bool completed_ = false;
    QVariant initial_;
    QString machine_;
};

static void register_case_pin_proof() {
    qmlRegisterSingletonType<CasePinProof>(
        "CasePinAcceptance", 1, 0, "CasePinProof",
        [](QQmlEngine*, QJSEngine*) -> QObject* { return new CasePinProof; });
}
Q_COREAPP_STARTUP_FUNCTION(register_case_pin_proof)
#include "test_case_pin_observer.moc"
