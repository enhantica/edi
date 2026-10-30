// SPDX-License-Identifier: BSD-3-Clause
// Native-only public admission checks. No native snapshot is manufactured here.
#include <QCoreApplication>
#include <QJSValue>
#include <QMetaObject>
#include <QQmlEngine>
#include <QVariantMap>
#include <QtQml/qqml.h>
#include "e11_t5_a2a_phase_adapter.hpp"

class NativeSnapshotBoundaryProof final : public QObject {
    Q_OBJECT
    QQmlEngine* engine_;
public:
    explicit NativeSnapshotBoundaryProof(QQmlEngine* engine) : engine_(engine) {}
    Q_INVOKABLE bool explicitNativePhase() const {
        e11_a2a_phase::requireDeclaredPhase();
        return !e11_a2a_phase::isOriginal()
            && qgetenv("EDI_E11_T5_A2A_PHASE") == QByteArrayLiteral("native")
            && qgetenv("EDI_E11_T5_A2A_SOURCE_SHA").size() == 40;
    }
    Q_INVOKABLE QVariantMap pendingErrorIdentity(QObject* applicationInfo, QObject* assistant) {
        // Resolve every ordinary input BEFORE installing the same-engine error.
        const bool sameEngine = applicationInfo && qjsEngine(applicationInfo) == engine_;
        if (!sameEngine || !assistant || engine_->hasError())
            return {{"ok", false}, {"error", "missing real singleton/owner, different singleton engine, or pre-existing error"}};
        const auto carrier = engine_->newObject();
        const auto compact = engine_->newObject();
        const auto payload = engine_->newObject();
        const auto sentinel = engine_->newErrorObject(QJSValue::GenericError,
                                                     "boundary-pending-sentinel");
        QString actual;
        engine_->throwError(sentinel);
        const bool installed = engine_->hasError();
        const bool invoked = QMetaObject::invokeMethod(applicationInfo,
            "assistantActivityDescription", Qt::DirectConnection,
            Q_RETURN_ARG(QString, actual), Q_ARG(QJSValue, carrier),
            Q_ARG(QString, QStringLiteral("activity")), Q_ARG(QJSValue, compact),
            Q_ARG(QJSValue, payload), Q_ARG(QObject*, assistant));
        const bool preserved = engine_->hasError();
        // Test observer cleanup only, AFTER the public invocation and observation.
        const auto caught = engine_->catchError();
        const bool identity = caught.strictlyEquals(sentinel);
        // The original entry readiness guard returns an EMPTY QString before fallback.
        const bool exact = actual.isEmpty();
        return {{"ok", installed && invoked && preserved && identity && exact},
                {"same_engine", sameEngine}, {"installed", installed},
                {"invoked", invoked}, {"preserved", preserved},
                {"identity", identity}, {"actual", actual}};
    }
};

static void registerNativeSnapshotBoundaryProof() {
    qmlRegisterSingletonType<NativeSnapshotBoundaryProof>(
        "NativeSnapshotBoundaryAcceptance", 1, 0, "NativeSnapshotBoundaryProof",
        [](QQmlEngine* engine, QJSEngine*) -> QObject* {
            return new NativeSnapshotBoundaryProof(engine);
        });
}
Q_COREAPP_STARTUP_FUNCTION(registerNativeSnapshotBoundaryProof)
#include "test_e11_t5_native_snapshot_boundary.moc"
