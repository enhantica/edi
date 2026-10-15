// Tests-owned deterministic services shared by native and real-QML owners.
#pragma once
// Tests-owned services; no production endpoint, token verifier or state machine is replaced.
#include "chatgpt_connection.hpp"
#include <QCoreApplication>
#include <QElapsedTimer>
#include <QEventLoop>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QTcpSocket>
#include <QUrlQuery>
#include <iostream>
#include <memory>
#include <functional>
#include <cstdint>
#include <map>
#include <stdexcept>
#include <vector>

namespace native=edi::assistant::native;
using Object=QJsonObject;
using Array=QJsonArray;
QByteArray encode(const QJsonValue& value) {
    return value.isArray() ? QJsonDocument(value.toArray()).toJson(QJsonDocument::Compact)
                          : QJsonDocument(value.toObject()).toJson(QJsonDocument::Compact);
}
QJsonValue decode(const QByteArray& value) {
    auto document=QJsonDocument::fromJson(value);
    return document.isArray() ? QJsonValue(document.array()) : QJsonValue(document.object());
}
Object reply(const edi::assistant::Reply& value) {
    return { {"ok",value.ok},{"code",QString::fromStdString(value.code)},
             {"value",decode(QByteArray::fromStdString(value.value))} };
}
std::string key(const native::RecordKey& value) {
    return std::to_string(static_cast<int>(value.kind))+":"+value.id;
}
struct Pending {
    native::HttpRequest request;
    native::HttpCallbacks callbacks;
    bool cancelled=false;
};
struct Operation: native::HttpOperation {
    std::shared_ptr<Pending> pending;
    explicit Operation(std::shared_ptr<Pending> value):pending(std::move(value)){}
    ~Operation() override {cancel();}
    void cancel() noexcept override {pending->cancelled=true;}
};
struct FixtureServices {
    std::vector<std::shared_ptr<Pending>> operations;
    std::map<std::string,QByteArray> records;
    Array events,browsers,writes,erasures,services,store_reads;
    std::int64_t wall=1800000000;
    std::uint64_t elapsed=100;
    std::string fail;
    native::NativeDependencies dependencies;
    std::function<void(const std::string&)> sink;
    bool failure(const std::string& name) {
        services.push_back(QString::fromStdString(name));
        if(fail==name+"-throw") throw std::runtime_error("synthetic-sensitive-service-body");
        return fail==name;
    }
    FixtureServices() {
    dependencies.request=[this](native::HttpRequest request,native::HttpCallbacks callbacks)->std::unique_ptr<native::HttpOperation>{
        if(failure("request") || fail=="request-null") return nullptr;
        auto pending=std::make_shared<Pending>(Pending{std::move(request),std::move(callbacks),false});
        operations.push_back(pending);return std::make_unique<Operation>(pending);
    };
    dependencies.open_browser=[this](const QUrl& url){
        browsers.push_back(url.toString(QUrl::FullyEncoded));return !failure("browser");
    };
    dependencies.read_record=[this](const native::RecordKey& record)->native::RecordRead{
        if(failure("read")) return {native::StoreStatus::failed,{}};
        auto found=records.find(key(record));
        store_reads.push_back(Object{{"key",QString::fromStdString(key(record))},
            {"bytes",found==records.end()?0.:static_cast<double>(found->second.size())}});
        return found==records.end() ? native::RecordRead{native::StoreStatus::absent,{}}
                                   : native::RecordRead{native::StoreStatus::ok,found->second};
    };
    dependencies.write_record=[this](const native::RecordKey& record,const QByteArray& bytes){
        if(failure("write")) return native::StoreStatus::failed;
        records[key(record)]=bytes;writes.push_back(QString::fromStdString(key(record)));
        return native::StoreStatus::ok;
    };
    dependencies.erase_record=[this](const native::RecordKey& record){
        if(failure("erase")) return native::StoreStatus::failed;
        erasures.push_back(QString::fromStdString(key(record)));
        return records.erase(key(record)) ? native::StoreStatus::ok : native::StoreStatus::absent;
    };
    dependencies.list_registrations=[this]()->native::RegistrationList{
        if(failure("list")) return {native::StoreStatus::failed,{}};
        std::vector<std::string> ids;
        const auto prefix=std::to_string(static_cast<int>(native::RecordKind::registration))+":";
        for(const auto& [name,bytes]:records) if(name.starts_with(prefix)) ids.push_back(name.substr(prefix.size()));
        return {native::StoreStatus::ok,std::move(ids)};
    };
    dependencies.unix_seconds=[this]{failure("wall");return wall;};
    dependencies.monotonic_ms=[this]{failure("elapsed");return elapsed;};
    sink=[this](const std::string& text){events.push_back(decode(QByteArray::fromStdString(text)));};
    }
    Object dispatch(const Object& input) {
        auto op=input["op"].toString(); Object result;
            if(op=="store_put") {
                records[input["key"].toString().toStdString()]=input["utf8"].toString().toUtf8();
            } else if(op=="clear_store_receipts") {
                store_reads=Array{};writes=Array{};erasures=Array{};
            } else if(op=="fail") fail=input["value"].toString().toStdString();
            else if(op=="advance") {
                wall+=static_cast<std::int64_t>(input["seconds"].toDouble());
                elapsed+=static_cast<std::uint64_t>(input["milliseconds"].toDouble());
            } else if(op=="headers" || op=="data" || op=="finish") {
                auto pending=operations.at(input["index"].toInt());
                if(op=="headers") {
                    native::HttpHeaders headers;
                    for(const auto& entry:input["headers"].toArray()) {
                        auto values=entry.toArray();headers.emplace_back(values[0].toString().toUtf8(),values[1].toString().toUtf8());
                    }
                    pending->callbacks.headers(input["status"].toInt(),std::move(headers));
                } else if(op=="data") pending->callbacks.data(QByteArray::fromBase64(input["base64"].toString().toLatin1()));
                else pending->callbacks.finished(static_cast<native::HttpFailure>(input["failure"].toInt()));
            } else if(op=="callback") {
                auto authorized=QUrl(browsers.last().toString());
                auto url=QUrl(QUrlQuery(authorized).queryItemValue("redirect_uri",QUrl::FullyDecoded));
                QUrlQuery query;
                const auto fields=input["query"].toObject();
                for(auto it=fields.begin();it!=fields.end();++it) query.addQueryItem(it.key(),it.value().toString());
                QTcpSocket socket;
                socket.connectToHost(url.host(),url.port());
                QElapsedTimer timer;timer.start();
                while(socket.state()!=QAbstractSocket::ConnectedState && timer.elapsed()<100)
                    QCoreApplication::processEvents(QEventLoop::AllEvents,1);
                QByteArray request=input.contains("raw") ? input["raw"].toString().toUtf8() :
                    "GET "+url.path().toUtf8()+"?"+query.toString(QUrl::FullyEncoded).toUtf8()+
                    " HTTP/1.1\r\nHost: "+url.authority().toUtf8()+"\r\nConnection: close\r\n\r\n";
                socket.write(request);socket.flush();
                while(timer.elapsed()<100) QCoreApplication::processEvents(QEventLoop::AllEvents,1);
                result={{"response",QString::fromUtf8(socket.readAll())}};
            } else if(op!="inspect") throw std::invalid_argument("unknown independent native host command");
        return result;
    }
    Object snapshot() const {
            Array requests,stored;
            for(const auto& pending:operations) {
                Array headers;
                for(const auto& [name,value]:pending->request.headers) headers.push_back(Array{QString::fromUtf8(name),QString::fromUtf8(value)});
                requests.push_back(Object{{"url",pending->request.url.toString(QUrl::FullyEncoded)},
                    {"method",pending->request.method==native::HttpMethod::post ? "POST" : "GET"},
                    {"headers",headers},{"body",QString::fromUtf8(pending->request.body)},
                    {"body_limit",static_cast<double>(pending->request.body_limit_bytes)},
                    {"timeout_ms",static_cast<double>(pending->request.timeout_ms)},{"cancelled",pending->cancelled}});
            }
            for(const auto& [name,bytes]:records) stored.push_back(Object{{"key",QString::fromStdString(name)},{"bytes",QString::fromUtf8(bytes)}});
            Object output{{"events",events},{"browsers",browsers},{"requests",requests},
                          {"records",stored},{"writes",writes},{"erasures",erasures},{"services",services},
                          {"store_reads",store_reads}};
        return output;
    }
};
