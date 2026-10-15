// Trusted generated-resource composition for the actual private loader. No producer CPP inclusion.
#include "assistant_skills.hpp"
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
int main() {
    using namespace edi::assistant::detail;
    std::string line;
    while(std::getline(std::cin,line)) {
        try {
            if(line.size()>8*Limits::context_bytes) throw std::invalid_argument("trusted fixture exceeds host envelope");
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
