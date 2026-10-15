// Tests-owned isolated component over actual production Qt store callbacks.
#include "../../../../core/src/assistant_json.hpp"
#include "fixture_services.hpp"
#include "connection_services.hpp"
#include <QCryptographicHash>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QStandardPaths>
#include <QTemporaryDir>

namespace {
QString status(native::StoreStatus value) {
    switch(value) {
        case native::StoreStatus::ok:return "ok";
        case native::StoreStatus::absent:return "absent";
        case native::StoreStatus::failed:return "failed";
    }
    throw std::invalid_argument("unknown actual store status");
}
native::RecordKey record_key(const QString& value) {
    if(value=="0:host")return {native::RecordKind::host,"host"};
    if(value.size()!=66 || value[1]!=':' || (value[0]!='1' && value[0]!='2'))
        throw std::invalid_argument("invalid isolated fixture key");
    for(const auto c:value.mid(2))
        if(!((c>='a' && c<='f') || (c>='0' && c<='9')))
            throw std::invalid_argument("invalid isolated fixture identity");
    return {value[0]=='1'?native::RecordKind::registration:native::RecordKind::credentials,
            value.mid(2).toStdString()};
}
QString relative_path(const native::RecordKey& value) {
    if(value.kind==native::RecordKind::host)return "host.json";
    return (value.kind==native::RecordKind::registration?"registrations/":"credentials/")+
           QString::fromStdString(value.id)+".json";
}
}
int main(int argc,char** argv) {
    QTemporaryDir isolated;
    if(!isolated.isValid())return 97;
    for(const auto* name:{"XDG_DATA_HOME","XDG_CONFIG_HOME","XDG_CACHE_HOME"})
        qputenv(name,isolated.path().toUtf8());
    QCoreApplication app(argc,argv);
    QCoreApplication::setOrganizationName("IndependentAssistantStore");
    QCoreApplication::setApplicationName("isolated-component-only");
    const auto root=QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation)+"/assistant/connections";
    if(!root.startsWith(isolated.path()+"/"))return 96;
    FixtureServices fixture;
    auto production=native::production_services();
    auto dependencies=fixture.dependencies;
    dependencies.read_record=[&](const native::RecordKey& record) {
        try {
            const auto result=production.dependencies.read_record(record);
            fixture.store_reads.push_back(Object{{"key",QString::fromStdString(key(record))},
                {"bytes",static_cast<double>(result.bytes.size())},{"status",status(result.status)}});
            return result;
        } catch(const edi::assistant::detail::Refusal& refused) {
            fixture.store_reads.push_back(Object{{"key",QString::fromStdString(key(record))},
                {"bytes",0},{"thrown_refusal",QString::fromStdString(refused.code)}});
            throw;
        }
    };
    dependencies.write_record=[&](const native::RecordKey& record,const QByteArray& bytes) {
        const auto result=production.dependencies.write_record(record,bytes);
        if(result==native::StoreStatus::ok) {
            fixture.records[key(record)]=bytes;fixture.writes.push_back(QString::fromStdString(key(record)));
        }
        return result;
    };
    dependencies.erase_record=[&](const native::RecordKey& record) {
        const auto result=production.dependencies.erase_record(record);
        if(result==native::StoreStatus::ok || result==native::StoreStatus::absent) {
            fixture.records.erase(key(record));fixture.erasures.push_back(QString::fromStdString(key(record)));
        }
        return result;
    };
    dependencies.list_registrations=production.dependencies.list_registrations;
    auto connection=std::make_unique<native::ChatGptConnection>(fixture.sink,dependencies);
    auto install=[&](const Object& row) {
        const auto record=record_key(row["key"].toString());
        const auto bytes=row["utf8"].toString().toUtf8();
        if(bytes.size()>2097152)throw std::invalid_argument("isolated input exceeds fixture bound");
        const auto name=root+"/"+relative_path(record);
        const auto folder=QFileInfo(name).absolutePath();
        if(!QDir().mkpath(folder))throw std::runtime_error("isolated fixture directory failed");
        for(const auto& dir:{root,root+"/registrations",root+"/credentials"})
            if(QDir().mkpath(dir))QFile::setPermissions(dir,QFile::ReadOwner|QFile::WriteOwner|QFile::ExeOwner);
        QFile file(name);
        if(!file.open(QIODevice::WriteOnly|QIODevice::Truncate) ||
           !file.setPermissions(QFile::ReadOwner|QFile::WriteOwner) || file.write(bytes)!=bytes.size())
            throw std::runtime_error("isolated fixture record install failed");
        file.close();fixture.records[key(record)]=bytes;
    };
    auto disk_snapshot=[&] {
        Array files;
        for(const auto& directory:{QString(),QString("registrations/"),QString("credentials/")}) {
            const auto entries=QDir(root+"/"+directory).entryInfoList({"*.json"},QDir::Files|QDir::NoSymLinks);
            for(const auto& entry:entries) {
                QFile file(entry.absoluteFilePath());
                if(!file.open(QIODevice::ReadOnly))throw std::runtime_error("isolated snapshot unavailable");
                const auto bytes=file.readAll();
                const auto forbidden=QFile::ReadGroup|QFile::WriteGroup|QFile::ExeGroup|QFile::ReadOther|QFile::WriteOther|QFile::ExeOther;
                files.push_back(Object{{"path",directory+entry.fileName()},{"bytes",static_cast<double>(bytes.size())},
                    {"sha256",QString::fromLatin1(QCryptographicHash::hash(bytes,QCryptographicHash::Sha256).toHex())},
                    {"owner_only",(entry.permissions()&forbidden)==0}});
            }
        }
        return files;
    };
    std::string line;
    while(std::getline(std::cin,line)) {
        try {
            const auto input=decode(QByteArray::fromStdString(line)).toObject();
            const auto op=input["op"].toString();Object result;
            if(op=="store_put")install(input);
            else if(op=="store_put_batch")for(const auto& row:input["records"].toArray())install(row.toObject());
            else if(op=="store_read") {
                try {
                    const auto read=dependencies.read_record(record_key(input["key"].toString()));
                    result={{"status",status(read.status)},{"bytes",static_cast<double>(read.bytes.size())}};
                } catch(const edi::assistant::detail::Refusal& refused) {
                    result={{"thrown_refusal",QString::fromStdString(refused.code)},{"bytes",0}};
                }
            } else if(op=="store_write" || op=="store_contending_write") {
                const auto record=record_key(input["key"].toString());
                const auto bytes=input["utf8"].toString().toUtf8();
                if(bytes.size()>2097152)throw std::invalid_argument("isolated write input exceeds fixture bound");
                try {
                    native::StoreStatus written;
                    if(op=="store_contending_write") {
                        auto contender=native::production_services();
                        written=contender.dependencies.write_record(record,bytes);
                    } else written=dependencies.write_record(record,bytes);
                    result={{"status",status(written)},{"written_bytes",written==native::StoreStatus::ok?static_cast<double>(bytes.size()):0}};
                } catch(const edi::assistant::detail::Refusal& refused) {
                    result={{"thrown_refusal",QString::fromStdString(refused.code)},{"written_bytes",0}};
                }
            } else if(op=="store_permissions") {
                const auto record=record_key(input["key"].toString());
                const auto allowed=QFile::ReadOwner|QFile::WriteOwner;
                const auto permissions=input["private"].toBool()?allowed:(allowed|QFile::ReadGroup);
                if(!QFile::setPermissions(root+"/"+relative_path(record),permissions))
                    throw std::runtime_error("isolated fixture permissions failed");
            } else if(op=="store_list") {
                try {
                    const auto list=dependencies.list_registrations();Array ids;
                    for(const auto& id:list.ids)ids.push_back(QString::fromStdString(id));
                    result={{"status",status(list.status)},{"ids",ids}};
                } catch(const edi::assistant::detail::Refusal& refused) {
                    result={{"thrown_refusal",QString::fromStdString(refused.code)},{"ids",Array{}}};
                }
            } else if(op=="sign_in")result=reply(connection->sign_in());
            else if(op=="connect_saved")result=reply(connection->connect_saved(input["id"].toString().toStdString()));
            else if(op=="recreate") {
                connection.reset();production.release_records();
                connection=std::make_unique<native::ChatGptConnection>(fixture.sink,dependencies);
            } else {
                result=fixture.dispatch(input);
                if(op=="advance")connection->poll();
            }
            if(op!="elapse_unpolled" && !input["defer_events"].toBool())QCoreApplication::processEvents();
            auto output=fixture.snapshot();output["reply"]=result;output["state"]=decode(QByteArray::fromStdString(connection->state()));
            output["isolated_root"]=root.startsWith(isolated.path()+"/");output["disk"]=disk_snapshot();
            std::cout<<encode(output).toStdString()<<'\n'<<std::flush;
        } catch(const std::exception& error) {
            std::cout<<encode(Object{{"host_error",QString::fromUtf8(error.what())}}).toStdString()<<'\n'<<std::flush;
        }
    }
}
