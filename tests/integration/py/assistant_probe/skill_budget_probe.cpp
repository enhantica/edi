// Trusted generated-resource composition for the actual private loader. No producer CPP inclusion.
#include "assistant_skills.hpp"
#include "edi/assistant.hpp"
#include <cmath>
#include <limits>
#include <iostream>
#include <string>
#include <vector>

namespace {
struct OwnedResource { std::string id, hash, content; };
std::string index_bytes;
std::vector<OwnedResource> owned;
std::vector<edi::assistant::detail::SkillResource> resources;
}
namespace edi::assistant::detail {
// Existing generated-data declarations, supplied by this component's original inputs.
// The archive's generated-data object is not extracted; actual loader code stays linked.
std::string_view skill_index_data() { return index_bytes; }
std::span<const SkillResource> skill_resource_data() { return resources; }
}

namespace {
using namespace edi::assistant::detail;
J observed_reply(const edi::assistant::Reply& reply) {
    return O{{"ok",reply.ok},{"code",reply.code},{"value",edi::json::parse(reply.value)}};
}
J model_observation(const J& input) {
    // Closed original fixture edits on the actual model; no calculation/fitted-value oracle.
    auto experiment=std::make_shared<edi::BraggPdExperiment>();
    experiment->name="dataset-A";
    experiment->experiment_type.beam_mode=edi::BeamModeEnum::CONSTANT_WAVELENGTH;
    experiment->data.emplace();
    experiment->data->two_theta=std::optional<std::vector<double>>{{12.25,19.75}};
    experiment->data->intensity_meas=std::vector<double>{17.5,23.25};
    experiment->data->intensity_meas_su=std::vector<double>{1.25,2.5};
    const auto fault=input.at("fault").string("fault");
    const auto count=static_cast<int>(input.at("exclusions").number("exclusions"));
    if(count<0 || count>20000)throw std::invalid_argument("closed fixture exclusion extent");
    for(int i=0;i<count;++i) {
        auto region=std::make_shared<edi::ExcludedRegion>(1.25,2.75);
        region->id="region-"+std::to_string(i);
        experiment->excluded_regions.push_back(region);
    }
    const double invalid=std::numeric_limits<double>::quiet_NaN();
    if(fault=="weight")experiment->dataset_weight=invalid;
    else if(fault=="origin")experiment->background_origin=invalid;
    else if(fault=="x-min")experiment->background_x_min=invalid;
    else if(fault=="x-max")experiment->background_x_max=invalid;
    else if(fault=="exclusion-first" || fault=="exclusion-second") {
        auto region=std::make_shared<edi::ExcludedRegion>(1.25,2.75);region->id="invalid-region";
        if(fault=="exclusion-first")region->first=invalid;else region->second=invalid;
        experiment->excluded_regions.push_back(region);
    } else if(fault=="axis-mode")experiment->experiment_type.beam_mode=edi::BeamModeEnum::TIME_OF_FLIGHT;
    else if(fault=="calc-sigma-length" || fault=="calc-sigma-nonfinite" || fault=="calc-observation-nonfinite") {
        experiment->calculation_only=true;
        if(fault=="calc-sigma-length")experiment->data->intensity_meas_su=std::vector<double>{1.25};
        if(fault=="calc-sigma-nonfinite")experiment->data->intensity_meas_su=std::vector<double>{1.25,invalid};
        if(fault=="calc-observation-nonfinite")experiment->data->intensity_meas=std::vector<double>{17.5,invalid};
    } else if(fault=="calculation-grid") {
        experiment->calculation_only=true;
        experiment->data->intensity_meas=std::vector<double>{};
        experiment->data->intensity_meas_su=std::vector<double>{};
    } else if(fault=="long-id")experiment->name=std::string(edi::assistant::Limits::id_bytes+1,'d');
    else if(fault!="none")throw std::invalid_argument("unknown closed model fixture");
    edi::Project project;project.metadata.name="Original metadata fixture";
    project.experiments.push_back(experiment);
    auto source=[&]()->J {return O{{"name",experiment->name.value()},
        {"weight_finite",std::isfinite(experiment->dataset_weight)},
        {"exclusions",static_cast<double>(experiment->excluded_regions.size())},
        {"calculation_only",experiment->calculation_only},
        {"intensity_count",static_cast<double>(experiment->data->intensity_meas.get().size())},
        {"sigma_count",static_cast<double>(experiment->data->intensity_meas_su.get().size())}};};
    const auto before=source();
    edi::work::Worker worker([](edi::work::Delivery){});
    edi::assistant::Controller controller(worker,{});
    J recovery;
    if(input.at("op").string("op")=="model_recovery") {
        const auto select=[&](const char* id) {return observed_reply(controller.user_command(
            edi::json::write(O{{"schema","edi.assistant/1"},{"type","select_skill"},{"id",id}})));};
        const auto small=select("fullprof-intake");
        const auto attached=observed_reply(controller.attach(&project,"metadata-project"));
        const auto small_context=edi::json::parse(controller.context());
        (void)controller.attach(nullptr,"");
        const auto large=select("project-assistance");
        (void)controller.attach(&project,"metadata-project");
        const auto large_context=edi::json::parse(controller.context());
        const auto catalog=observed_reply(controller.user_command(
            R"({"schema":"edi.assistant/1","type":"skill_catalog"})"));
        const auto recovered=select("fullprof-intake");
        recovery=O{{"small_selection",small},{"attached",attached},{"small_context",small_context},
            {"large_selection",large},{"large_context",large_context},{"catalog",catalog},
            {"recovered",recovered}};
    } else (void)controller.attach(&project,"metadata-project");
    const auto context=edi::json::parse(controller.context());
    return O{{"observation","model_returned"},{"context",context},{"before",before},{"after",source()},
        {"state",edi::json::parse(controller.state())},{"recovery",recovery}};
}
}

int main() {
    using namespace edi::assistant::detail;
    std::string line;
    while(std::getline(std::cin,line)) {
        try {
            if(line.size()>8*edi::assistant::Limits::context_bytes) throw std::invalid_argument("trusted fixture exceeds host envelope");
            const auto input=edi::json::parse(line);
            index_bytes=input.at("index_json").string("index_json");
            resources.clear(); owned.clear();
            const auto& originals=input.at("resources").array("resources");
            owned.reserve(originals.size());resources.reserve(originals.size());
            for(const auto& resource:originals)
                owned.push_back({resource.at("id").string("id"),resource.at("sha256").string("sha256"),
                                 resource.at("content").string("content")});
            for(const auto& resource:owned) resources.push_back({resource.id,resource.hash,resource.content});
            const auto operation=input.at("op").string("op");
            J result;
            if(operation=="model_context" || operation=="model_recovery") {
                std::cout<<edi::json::write(model_observation(input))<<'\n'<<std::flush;continue;
            }
            if(operation=="context") result=skill_context(input.at("selected").string("selected"),input.at("tools"));
            else if(operation=="catalog") result=skill_catalog(input.at("selected").string("selected"),
                input.at("has_selected_files").boolean("has_selected_files"),input.at("tools"));
            else throw std::invalid_argument("unknown trusted helper operation");
            const auto encoded=edi::json::write(result);
            std::cout<<edi::json::write(O{{"observation","returned"},{"result",std::move(result)},
                {"encoded_bytes",static_cast<double>(encoded.size())}})<<'\n'<<std::flush;
        } catch(const Refusal& error) {
            std::cout<<edi::json::write(O{{"observation","threw_refusal"},{"code",error.code}})<<'\n'<<std::flush;
        } catch(const std::exception& error) {
            std::cout<<edi::json::write(O{{"observation","threw_std_exception"},{"message",error.what()}})<<'\n'<<std::flush;
        }
    }
}
