#include "assistant_data.hpp"
#include "assistant_outgoing.hpp"
#include <QJsonDocument>
#include <iostream>
#include <limits>

edi::PatternSource::Column values(const QJsonValue& input) {
    if (!input.isArray()) return {};
    std::vector<double> result;
    for (const auto& value : input.toArray())
        result.push_back(value.isDouble() ? value.toDouble() : std::numeric_limits<double>::quiet_NaN());
    return std::make_shared<const std::vector<double>>(std::move(result));
}
int main() {
    std::string line;
    while (std::getline(std::cin,line)) {
        QJsonParseError error;
        const auto document=QJsonDocument::fromJson(QByteArray::fromStdString(line),&error);
        if (error.error!=QJsonParseError::NoError || !document.isObject()) return 2;
        const auto input=document.object();
        edi::PatternSource pattern;
        pattern.x_item=input.value("axis_kind").toString("data.twotheta").toStdString();
        pattern.current=input.value("current").toBool(true);
        pattern.x=values(input.value("x"));pattern.meas=values(input.value("measured"));
        pattern.calc=values(input.value("calculated"));pattern.su=values(input.value("sigma"));
        pattern.bkg=values(input.value("background"));
        for (const auto& entry:input.value("excluded").toArray()) {
            const auto band=entry.toArray();
            if (band.size()!=2) return 3;
            pattern.excluded.push_back({band[0].toDouble(),band[1].toDouble()});
        }
        for (const auto& entry:input.value("phases").toArray()) {
            const auto object=entry.toObject();edi::PatternSource::Phase phase;
            phase.structure_id=object.value("phase_id").toString().toStdString();
            phase.position=values(object.value("positions"));pattern.phases.push_back(std::move(phase));
        }
        const auto result=edi_app::assistant_data::misfit(pattern,input.value("dataset_id").toString("bank"));
        QJsonObject observation = result;
        if (input.value("provider_wire").toBool()) {
            using namespace edi_app::outgoing;
            const QJsonObject outcome{{"misfit", QJsonArray{result}}};
            const auto bytes = size(outcome, Role::Result);
            const auto encoded = QJsonDocument(project(outcome, Role::Result, bytes))
                                     .toJson(QJsonDocument::Compact);
            if (static_cast<quint64>(encoded.size()) != bytes) return 4;
            observation = {{"native", result}, {"provider_text", QString::fromUtf8(encoded)}};
        }
        std::cout<<QJsonDocument(observation).toJson(QJsonDocument::Compact).toStdString()<<'\n'<<std::flush;
    }
}
