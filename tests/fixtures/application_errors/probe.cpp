// SPDX-License-Identifier: BSD-3-Clause
#include <QEvent>
#include <QGuiApplication>
#include <QJsonDocument>
#include <QJsonObject>
#include <QString>
#include <cstdio>
#include <exception>
#include <stdexcept>

namespace {
QString observed;
int reports = 0;
}
namespace edi_app {
struct RunLog {
    static void reportCaught(const QString& message) {
        observed = message;
        ++reports;
    }
};
}
#include "application_provider.inc"

class Receiver : public QObject {
public:
    bool unknown = false;
    int subsequent = 0;
    bool event(QEvent* event) override {
        if (event->type() == QEvent::User) {
            if (unknown) throw 1739;
            throw std::runtime_error("injected event error at item 17");
        }
        if (event->type() == QEvent::Type(QEvent::User + 1)) {
            ++subsequent;
            return true;
        }
        return QObject::event(event);
    }
};

int main(int argc, char** argv) {
    GuardedApplication app(argc, argv);
    Receiver receiver;
    receiver.unknown = argc > 1 && QString::fromLocal8Bit(argv[1]) == "unknown";
    QEvent bad(QEvent::User);
    const bool accepted = QCoreApplication::sendEvent(&receiver, &bad);
    QEvent next(QEvent::Type(QEvent::User + 1));
    const bool continued = QCoreApplication::sendEvent(&receiver, &next);
    const QJsonObject result{{"accepted", accepted}, {"continued", continued},
                             {"subsequent", receiver.subsequent}, {"reports", reports},
                             {"message", observed}};
    const auto bytes = QJsonDocument(result).toJson(QJsonDocument::Compact);
    std::fwrite(bytes.constData(), 1, bytes.size(), stdout);
}
