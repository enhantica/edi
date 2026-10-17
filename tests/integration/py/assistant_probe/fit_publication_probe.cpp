#include "edi/fit_job.hpp"
#include "edi/io.hpp"
#include "edi/parameter_walk.hpp"
#include "edi/presentation.hpp"
#include <cmath>
#include "json.hpp"
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdlib>
#include <deque>
#include <iostream>
#include <memory>
#include <mutex>
#include <new>
#include <thread>

namespace {
thread_local bool armed=false, fired=false, finished=false;
thread_local const edi::Parameter* watched=nullptr;
thread_local double original=0;
void allocation() {
    if(armed && !finished && watched && watched->value.get()!=original) {
        armed=false;fired=true;throw std::bad_alloc();
    }
}
}
void* operator new(std::size_t n) {allocation();if(void* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void* operator new[](std::size_t n) {return ::operator new(n);}
void operator delete(void* p) noexcept {std::free(p);}
void operator delete[](void* p) noexcept {std::free(p);}
void operator delete(void* p,std::size_t) noexcept {std::free(p);}
void operator delete[](void* p,std::size_t) noexcept {std::free(p);}
using edi::json::Value;
using edi::json::Object;
using edi::json::Array;
Value saved(edi::Project& project) {
    Object files;
    for(const auto& [name,text]:edi::project_edi_files(project))files.emplace_back(name,text);
    Array rows;
    for(const auto& row:edi::parameter_entries(project)) {
        const auto& p=*row.parameter;
        rows.push_back(Object{{"path",row.path},{"value",p.value.get()},
            {"free",p.free.get()},{"uncertainty",p.uncertainty.get()?Value(*p.uncertainty.get()):Value(nullptr)},
            {"start_value",p.start_value.get()?Value(*p.start_value.get()):Value(nullptr)},
            {"start_uncertainty",p.start_uncertainty.get()?Value(*p.start_uncertainty.get()):Value(nullptr)},
            {"address",std::to_string(reinterpret_cast<std::uintptr_t>(row.parameter))}});
    }
    return Object{{"files",files},{"rows",rows}};
}
int main(int argc,char** argv) {
    if(argc!=3)return 96;
    auto project=edi::load_project(argv[1]);
    for(const auto& row:edi::parameter_entries(project))
        row.parameter->free=row.path.ends_with(".scale") || row.path.ends_with(".cell.length_a");
    project.fit_result.message="independently planted original record";
    const auto before=saved(project);
    for (const auto& row : edi::parameter_entries(project))
        if (row.path.ends_with(".cell.length_a")) { watched=row.parameter; break; }
    if (!watched) return 95;
    original=watched->value.get();
    std::mutex mutex;std::condition_variable ready;std::deque<edi::work::Delivery> pending;
    edi::work::Worker worker([&](edi::work::Delivery next){
        {std::lock_guard lock(mutex);pending.push_back(std::move(next));}ready.notify_one();
    });
    int completions=0;edi::FitStatus status=edi::FitStatus::ERROR;
    edi::FitJob::Hooks hooks;
    hooks.finished=[&](const edi::FitReport& report){finished=true;++completions;status=report.status;};
    edi::FitJob job(project,worker,std::move(hooks));
    const bool started=job.start();
    armed=std::string(argv[2])=="armed";
    bool escaped=false;
    const auto end=std::chrono::steady_clock::now()+std::chrono::seconds(8);
    while(!finished && !escaped && std::chrono::steady_clock::now()<end) {
        edi::work::Delivery next;
        {std::unique_lock lock(mutex);ready.wait_for(lock,std::chrono::milliseconds(2),[&]{return !pending.empty();});
         if(pending.empty())continue;next=std::move(pending.front());pending.pop_front();}
        try {next();} catch(const std::bad_alloc&) {escaped=true;}
    }
    armed=false;
    const auto after=saved(project);
    const bool moved=watched->value.get()!=original;
    bool complete=finished && status==edi::FitStatus::DONE && project.fit_result.held() &&
        std::isfinite(project.fit_result.objective_value) &&
        project.fit_result.message!="independently planted original record";
    for(std::size_t i=0;i<project.experiments.size();++i)
        complete=complete && edi::capture_pattern(project,i).current;
    std::cout<<edi::json::write(Object{{"started",started},{"fault_fired",fired},
        {"escaped",escaped},{"finished_count",completions},{"running",job.running()},
        {"native_done",status==edi::FitStatus::DONE},{"moved",moved},{"complete_publication",complete},{"before",before},{"after",after}})<<'\n';
}
