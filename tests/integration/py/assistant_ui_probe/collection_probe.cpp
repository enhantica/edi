// SPDX-License-Identifier: BSD-3-Clause
#include <QGuiApplication>
#include <QBuffer>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QTimer>
#include <QElapsedTimer>
#include <QThread>
#include "engine_setup.hpp"
#include "online_search.hpp"
#include "online_sources.hpp"
#include "project_view_model.hpp"
#include "session.hpp"

namespace {
struct Slot {
    using Member = QNetworkAccessManager* edi_app::OnlineSearch::*;
    friend Member transport(Slot);
};
template <Slot::Member member> struct Access {
    friend Slot::Member transport(Slot) { return member; }
};
template struct Access<&edi_app::OnlineSearch::network_>;

class Reply : public QNetworkReply {
    QByteArray content_;
    qint64 offset_ = 0;
public:
    Reply(const QNetworkRequest& request, QByteArray content, bool missing, QObject* parent)
        : QNetworkReply(parent), content_(std::move(content)) {
        setRequest(request);
        setUrl(request.url());
        open(QIODevice::ReadOnly | QIODevice::Unbuffered);
        if (missing) setError(QNetworkReply::HostNotFoundError, "offline primary unavailable");
        else setAttribute(QNetworkRequest::HttpStatusCodeAttribute, 200);
        QTimer::singleShot(0, this, [this, missing] {
            if (missing) emit errorOccurred(error());
            else emit readyRead();
            setFinished(true);
            emit finished();
        });
    }
    void abort() override {}
    qint64 bytesAvailable() const override { return content_.size() - offset_ + QNetworkReply::bytesAvailable(); }
    qint64 readData(char* target, qint64 limit) override {
        const auto count = std::min(limit, content_.size() - offset_);
        if (!count) return -1;
        memcpy(target, content_.constData() + offset_, count);
        offset_ += count;
        return count;
    }
};
class Transport : public QNetworkAccessManager {
    QString root_;
    bool dead_;
public:
    int requests = 0, fallback = 0;
    Transport(QString root, bool dead, QObject* parent) : QNetworkAccessManager(parent), root_(std::move(root)), dead_(dead) {}
protected:
    QNetworkReply* createRequest(Operation, const QNetworkRequest& request, QIODevice*) override {
        ++requests;
        const auto url = request.url();
        const bool primary = url.host() == "raw.githubusercontent.com";
        if (!primary) ++fallback;
        auto path = url.path();
        const auto marker = path.indexOf("/main/");
        if (marker >= 0) path = path.mid(marker + 6);
        else while (path.startsWith('/')) path.remove(0, 1);
        QFile file(root_ + '/' + path);
        const bool missing = (dead_ && primary) || !file.open(QIODevice::ReadOnly);
        return new Reply(request, missing ? QByteArray{} : file.readAll(), missing, this);
    }
};
}
int main(int argc, char** argv) {
    QGuiApplication app(argc, argv);
    if (argc != 4) return 2;
    edi_app::use_fresh_settings();
    qunsetenv("EDI_ONLINE_SOURCES");
    edi_app::Session session(nullptr);
    if (!session.createProject("fixture", {})) return 3;
    auto* search = session.onlineSearch();
    auto* network = new Transport(QString::fromLocal8Bit(argv[1]), QString::fromLocal8Bit(argv[3]) == "fallback", search);
    search->*transport(Slot{}) = network;
    const QString id = QString::fromLocal8Bit(argv[2]);
    search->setKind(id.startsWith("proj-") ? "project" : "data");
    search->setSourceId("easydiffraction");
    search->setField("id", id);
    search->search();
    QElapsedTimer clock;
    clock.start();
    while ((!search->searched() || search->busy()) && clock.elapsed() < 2000)
        QCoreApplication::processEvents(QEventLoop::AllEvents, 10);
    QJsonObject result;
    const auto* entry = search->results()->at(0);
    result["found"] = entry != nullptr;
    bool received = false;
    QString failed;
    QObject::connect(&session, &edi_app::Session::loadFailed, &app, [&](const QString& error) { failed = error; });
    QObject::connect(search, &edi_app::OnlineSearch::fileReady, &app,
        [&](const QString& kind, const QUrl& path, const edi_app::OnlineEntry& value, QObject*, QObject*, bool) {
            received = true;
            QFile file(path.toLocalFile());
            if (file.open(QIODevice::ReadOnly)) result["hex"] = QString::fromLatin1(file.readAll().toHex());
            result["id"] = value.id;
            if (kind == "project" && !session.openProject(path)) failed = session.lastError();
        });
    if (entry) {
        result["file"] = QString::fromStdString(entry->files[0].path);
        result["sha256"] = QString::fromStdString(entry->files[0].sha256);
        search->load(0, session.project(), nullptr);
        while ((search->busy() || (!received && search->message().isEmpty()) || session.openingExample()) && clock.elapsed() < 4000)
            QCoreApplication::processEvents(QEventLoop::AllEvents, 10);
    }
    result["received"] = received;
    result["error"] = !failed.isEmpty() ? failed : (received ? QString{} : search->message());
    if (session.project()) {
        QFile project(session.project()->path() + "/project.edi");
        if (project.open(QIODevice::ReadOnly)) result["project_hex"] = QString::fromLatin1(project.readAll().toHex());
    }
    result["fallback_requests"] = network->fallback;
    result["requests"] = network->requests;
    const auto output = QJsonDocument(result).toJson(QJsonDocument::Compact) + '\n';
    fwrite(output.constData(), 1, output.size(), stdout);
    return 0;
}
