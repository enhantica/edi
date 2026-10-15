#include "fixture_services.hpp"
int main(int argc,char** argv) {
    QCoreApplication app(argc,argv);
    FixtureServices fixture;
    auto& dependencies=fixture.dependencies;
    auto& services=fixture.services;
    auto& sink=fixture.sink;
    auto connection=std::make_unique<native::ChatGptConnection>(sink,dependencies);
    std::string line;
    while(std::getline(std::cin,line)) {
        try {
            auto input=decode(QByteArray::fromStdString(line)).toObject();
            auto op=input["op"].toString(); Object result;
            if(op=="missing_dependency") {
                auto incomplete=dependencies;
                switch(input["index"].toInt()) {
                    case 0: incomplete.request={};break;
                    case 1: incomplete.open_browser={};break;
                    case 2: incomplete.read_record={};break;
                    case 3: incomplete.write_record={};break;
                    case 4: incomplete.erase_record={};break;
                    case 5: incomplete.list_registrations={};break;
                    case 6: incomplete.unix_seconds={};break;
                    case 7: incomplete.monotonic_ms={};break;
                }
                auto count=services.size();
                bool rejected=false;
                try { native::ChatGptConnection invalid(sink,std::move(incomplete)); }
                catch(const std::invalid_argument&) {rejected=true;}
                result={{"rejected",rejected},{"service_calls",static_cast<double>(services.size()-count)}};
            } else if(op=="sign_in") result=reply(connection->sign_in());
            else if(op=="connect_saved") result=reply(connection->connect_saved(input["id"].toString().toStdString()));
            else if(op=="send") result=reply(connection->send(encode(input["payload"]).toStdString()));
            else if(op=="cancel") connection->cancel(input["turn_id"].toString().toStdString());
            else if(op=="sign_out") connection->sign_out();
            else if(op=="destroy") connection.reset();
            else if(op=="recreate") connection=std::make_unique<native::ChatGptConnection>(sink,dependencies);
            else {
                result=fixture.dispatch(input);
                if(op=="advance") connection->poll();
            }
            if(op!="elapse_unpolled" && !input["defer_events"].toBool()) QCoreApplication::processEvents();
            auto output=fixture.snapshot();
            output["reply"]=result;
            output["state"]=connection ? decode(QByteArray::fromStdString(connection->state())) : QJsonValue();
            std::cout<<encode(output).toStdString()<<'\n'<<std::flush;
        } catch(const std::exception& error) {
            std::cout<<encode(Object{{"host_error",QString::fromUtf8(error.what())}}).toStdString()<<'\n'<<std::flush;
        }
    }
}
