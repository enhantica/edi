// Tests-only public stream/Sink consumer; uses the unchanged owner one-shot allocator.
#include "edi/assistant.hpp"
#include "assistant_json.hpp"
#include "interruption_fixture.hpp"
#include <cstdlib>
#include <exception>
#include <iostream>
#include <memory>
#include <new>
#include <optional>
#include <string_view>

void* operator new(std::size_t size) {
    independent_fault::allocation();
    if (void* memory=std::malloc(size ? size : 1)) return memory;
    throw std::bad_alloc();
}
void* operator new[](std::size_t size) { return ::operator new(size); }
void operator delete(void* memory) noexcept { std::free(memory); }
void operator delete[](void* memory) noexcept { std::free(memory); }
void operator delete(void* memory,std::size_t) noexcept { std::free(memory); }
void operator delete[](void* memory,std::size_t) noexcept { std::free(memory); }

using edi::json::Object;
using edi::json::Value;
using edi::assistant::Reply;
struct PlainFailure final : std::exception {
    const char* what() const noexcept override { return "Independent plain sink failure"; }
};
Value reply(const Reply& value) {
    return Object{{"ok",value.ok},{"code",value.code},{"value",value.value}};
}
int main() {
    std::string line;
    if(!std::getline(std::cin,line))return 96;
    try {
        const auto input=edi::json::parse(line);
        const auto point=input.at("point").string("point");
        const auto category=input.at("category").string("category");
        const auto mode=input.at("mode").string("mode");
        const auto prefix=input.at("prefix").string("prefix");
        const auto trigger=input.at("trigger").string("trigger");
        const auto followup=input.at("followup").string("followup");
        const auto as_length=input.at("as_length").boolean("as_length");
        const auto wanted=point=="terminal" ? std::string_view("\"type\":\"turn_finished\"")
                                           : std::string_view("\"type\":\"text_delta\"");
        // Actual existing Refusal declaration, not a copied/private exception implementation.
        const auto prepared=category=="refusal"
            ? std::make_exception_ptr(edi::assistant::detail::Refusal(
                "invalid_argument","Independent typed sink refusal"))
            : std::make_exception_ptr(PlainFailure{});
        std::optional<independent_fault::Arm> arm;
        std::uint64_t attempts=0,delivered=0,tools=0;
        bool selected=false,calibrating=false;
        const auto sink=[&](const std::string& event) {
            ++attempts;
            if(category!="natural" && category!="valid" && !selected &&
               std::string_view(event).find(wanted)!=std::string_view::npos) {
                selected=true;
                // Arm lives in preallocated outer storage across exception unwind.
                arm.emplace(calibrating || mode!="preparation" ? 0 : 1,as_length);
                std::rethrow_exception(prepared);
            }
            ++delivered;
            if(std::string_view(event).find("\"type\":\"tool_call\"")!=std::string_view::npos)++tools;
        };
        bool direct_caught=false;
        std::uint64_t direct_seen=0;
        bool direct_fired=false;
        if(category!="natural" && category!="valid") {
            const std::string event=point=="terminal" ? "{\"type\":\"turn_finished\"}"
                                                       : "{\"type\":\"text_delta\"}";
            calibrating=true;
            try {sink(event);} catch(const std::exception&) {direct_caught=true;}
            direct_seen=independent_fault::seen;direct_fired=independent_fault::fired;
            arm.reset(); // Disarm BEFORE observation encoding or real decoder construction.
            selected=false;calibrating=false;attempts=0;delivered=0;tools=0;
        }
        edi::assistant::OpenAiStream stream("independent-turn","independent-request",sink);
        const auto prefixed=stream.feed(prefix);
        Reply first;bool returned=false;int escaped=0;
        try {first=stream.feed(trigger);returned=true;}
        catch(const std::bad_alloc&) {escaped=1;}
        catch(const std::length_error&) {escaped=2;}
        catch(const std::exception&) {escaped=3;}
        const auto prep_seen=independent_fault::seen;
        const auto prep_fired=independent_fault::fired;
        arm.reset();
        const auto attempts_before_copy=attempts,delivered_before_copy=delivered,tools_before_copy=tools;
        bool copy_fired=false;int copy_escaped=0;
        if(mode=="cached-copy") {
            try {
                independent_fault::Arm copy(1,as_length);
                (void)stream.feed(followup);
            } catch(const std::bad_alloc&) {copy_escaped=1;}
              catch(const std::length_error&) {copy_escaped=2;}
              catch(const std::exception&) {copy_escaped=3;}
            copy_fired=independent_fault::fired;
        }
        const auto attempts_before=attempts,delivered_before=delivered,tools_before=tools;
        Reply finished_before,later,finished_after;
        bool observer_threw=false;
        try {
            finished_before=stream.finish();
            later=stream.feed(followup);
            finished_after=stream.finish();
        } catch(const std::exception&) {observer_threw=true;}
        const auto output=Object{
            {"prefix_ok",prefixed.ok},{"sink_selected",selected},
            {"direct_caught",direct_caught},{"direct_seen",static_cast<double>(direct_seen)},
            {"direct_fired",direct_fired},{"preparation_fired",prep_fired},
            {"preparation_seen",static_cast<double>(prep_seen)},
            {"first_returned",returned},{"first_escaped",escaped},{"first",reply(first)},
            {"copy_fired",copy_fired},{"copy_escaped",copy_escaped},
            {"attempts_before_copy",static_cast<double>(attempts_before_copy)},
            {"delivered_before_copy",static_cast<double>(delivered_before_copy)},
            {"tools_before_copy",static_cast<double>(tools_before_copy)},
            {"observer_threw",observer_threw},{"finish_before",reply(finished_before)},
            {"later",reply(later)},{"finish_after",reply(finished_after)},
            {"attempts_before",static_cast<double>(attempts_before)},
            {"attempts_after",static_cast<double>(attempts)},
            {"delivered_before",static_cast<double>(delivered_before)},
            {"delivered_after",static_cast<double>(delivered)},
            {"tools_before",static_cast<double>(tools_before)},
            {"tools_after",static_cast<double>(tools)}};
        std::cout<<edi::json::write(output)<<'\n';
    } catch(const std::exception& error) {
        independent_fault::enabled=false;
        std::cout<<edi::json::write(Object{{"host_error",error.what()}})<<'\n';
        return 95;
    }
}
