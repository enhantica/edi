// Tests-owned local-wire witness over the actual production Qt HTTP adapter.
#include "connection_services.hpp"
#include <QCoreApplication>
#include <QElapsedTimer>
#include <QEventLoop>
#include <QJsonDocument>
#include <QJsonObject>
#include <QTemporaryDir>
#include <QTcpServer>
#include <QTcpSocket>
#include <iostream>
#include <memory>

namespace native=edi::assistant::native;
int main(int argc,char** argv) {
    QTemporaryDir isolated;
    if(!isolated.isValid()) return 97;
    qputenv("XDG_DATA_HOME",isolated.path().toUtf8());
    QCoreApplication app(argc,argv);
    QCoreApplication::setOrganizationName("IndependentQtWire");
    QCoreApplication::setApplicationName("request-component-only");
    const bool truncated=argc>1 && QByteArray(argv[1])=="truncated";
    const int status=argc>1 && QByteArray(argv[1])=="http-error" ? 503 : 200;
    const QByteArray body="data: {\"type\":\"response.completed\",\"response\":{\"id\":\"independent-complete\",\"status\":\"completed\",\"output\":[]}}\n\n";
    QTcpServer server;
    if(!server.listen(QHostAddress::LocalHost,0)) return 96;
    bool sent=false;
    QObject::connect(&server,&QTcpServer::newConnection,&app,[&] {
        while(auto* socket=server.nextPendingConnection()) {
            QObject::connect(socket,&QTcpSocket::readyRead,socket,[&,socket] {
                if(sent)return;
                socket->readAll();sent=true;
                socket->write("HTTP/1.1 "+QByteArray::number(status)+" Independent\r\nContent-Type: text/event-stream\r\nContent-Length: "+QByteArray::number(body.size()+(truncated?64:0))+"\r\nConnection: close\r\n\r\n"+body);
                socket->disconnectFromHost();
            });
            QObject::connect(socket,&QTcpSocket::disconnected,socket,&QObject::deleteLater);
        }
    });
    auto production=native::production_services();
    int headers=0,completed=0,observed_status=0;
    bool successful=false;
    QByteArray observed;
    auto operation=production.dependencies.request({native::HttpMethod::get,
        QUrl("http://127.0.0.1:"+QString::number(server.serverPort())+"/local-independent-wire"),{}, {},65536,2000},
        {[&](int value,native::HttpHeaders){++headers;observed_status=value;},
         [&](QByteArray value){observed+=value;},
         [&](native::HttpFailure failure){++completed;successful=failure==native::HttpFailure::none;}});
    QElapsedTimer timer;timer.start();
    while(completed==0 && timer.elapsed()<2500) QCoreApplication::processEvents(QEventLoop::AllEvents,1);
    std::cout<<QJsonDocument(QJsonObject{{"sent",sent},{"headers",headers},{"status",observed_status},
        {"finished",completed},{"success",successful},{"body_exact",observed==body}}).toJson(QJsonDocument::Compact).toStdString()<<'\n';
    operation.reset();
    return completed==1?0:95;
}
