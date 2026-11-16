// SPDX-License-Identifier: BSD-3-Clause
#include <QGuiApplication>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QPointer>
#include <QQmlApplicationEngine>
#include <QQuickItem>
#include <QQuickWindow>
#include <cstdio>
#include <functional>
#include <string>

QPointer<QQmlApplicationEngine> g_engine;
#include "web_control_geometry.inc"

int main(int argc, char** argv) {
    QGuiApplication application(argc, argv);
    QQmlApplicationEngine engine;
    g_engine = &engine;
    engine.loadData(R"QML(
import QtQuick
import QtQuick.Window
Window {
    visible: true; width: 800; height: 600
    Item {
        objectName: "transformedParent"
        x: 400; y: 100; width: 300; height: 200
        rotation: 90; scale: 1.5; transformOrigin: Item.TopLeft; clip: true
        TextInput {
            objectName: "editor"
            x: 20; y: 30; width: 200; height: 40; text: ""; font.pixelSize: 20
        }
    }
    TextInput {
        objectName: "otherEditor"
        x: 10; y: 20; width: 100; height: 30; text: "other"; font.pixelSize: 20
    }
}
)QML");
    QCoreApplication::processEvents();
    if (engine.rootObjects().size() != 1) return 2;
    auto* window = qobject_cast<QQuickWindow*>(engine.rootObjects().constFirst());
    if (window == nullptr) return 3;
    auto* editor = window->findChild<QQuickItem*>(QStringLiteral("editor"));
    auto* other = window->findChild<QQuickItem*>(QStringLiteral("otherEditor"));
    auto* transformed = window->findChild<QQuickItem*>(QStringLiteral("transformedParent"));
    if (editor == nullptr || other == nullptr || transformed == nullptr) return 4;
    QJsonArray observations;
    const auto observe = [&](const char* label, const char* name = "editor") {
        const bool before = editor->hasActiveFocus();
        const bool otherBefore = other->hasActiveFocus();
        const auto value = QJsonDocument::fromJson(edi_control_geometry(name));
        observations.append(QJsonObject{
            {"case", QString::fromUtf8(label)},
            {"value", value.object()},
            {"editorFocusBefore", before},
            {"editorFocusAfter", editor->hasActiveFocus()},
            {"otherFocusBefore", otherBefore},
            {"otherFocusAfter", other->hasActiveFocus()},
            {"inkWidth", editor->boundingRect().width()},
            {"declaredWidth", editor->width()},
            {"declaredHeight", editor->height()},
        });
    };
    observe("empty");
    editor->setProperty("text", QStringLiteral("Fe3+ specimen"));
    observe("populated");
    editor->setProperty("text", QString());
    observe("empty-again");
    transformed->setClip(false);
    observe("unclipped");
    transformed->setClip(true);
    transformed->setWidth(100);
    observe("partly-clipped");
    transformed->setWidth(300);
    transformed->setEnabled(false);
    observe("disabled-ancestor");
    transformed->setEnabled(true);
    transformed->setVisible(false);
    observe("hidden-ancestor");
    transformed->setVisible(true);
    other->forceActiveFocus(Qt::OtherFocusReason);
    QCoreApplication::processEvents();
    observe("focus-read");
    QQuickItem duplicate(window->contentItem());
    duplicate.setObjectName(QStringLiteral("editor"));
    duplicate.setWidth(70);
    duplicate.setHeight(30);
    observe("duplicate");
    duplicate.setVisible(false);
    observe("hidden-duplicate");
    observe("absent", "not-a-control");
    QQuickItem visualOnly(window->contentItem());
    visualOnly.setParent(nullptr);
    visualOnly.setObjectName(QStringLiteral("visualOnly"));
    visualOnly.setX(15);
    visualOnly.setY(25);
    visualOnly.setWidth(70);
    visualOnly.setHeight(30);
    observe("visual-only", "visualOnly");
    const auto bytes =
        QJsonDocument(QJsonObject{{"provider", QStringLiteral(EDI_GEOMETRY_PROVIDER_SHA)},
                                  {"observations", observations}})
            .toJson(QJsonDocument::Compact);
    std::fwrite(bytes.constData(), 1, bytes.size(), stdout);
    std::fputc('\n', stdout);
    return 0;
}
