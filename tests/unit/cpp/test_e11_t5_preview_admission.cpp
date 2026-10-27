#include <doctest/doctest.h>
#include <atomic>
#include <deque>
#include <mutex>
#include <vector>
#include <utility>
#include "e04_t9_support.hpp"
#include "edi/live_preview.hpp"

namespace {
edi::CalculationResult result_for(edi::WorkSnapshot& snapshot,const edi::work::CancelToken& token) {
    edi::CalculationResult result;result.stamps=snapshot.stamps;result.cancelled=token.cancelled();return result;
}
struct Events {
    std::mutex mutex;
    std::vector<edi::work::Event> values;
    void add(const edi::work::Event& e){std::lock_guard lock(mutex);values.push_back(e);}
    std::vector<std::uint64_t> ids(edi::work::EventKind kind){
        std::lock_guard lock(mutex);std::vector<std::uint64_t> out;
        for(const auto& e:values)if(e.kind==kind)out.push_back(e.id);return out;
    }
};
}
TEST_CASE("E11 preview queued FIFO settles actual generations and cancellation without replay") {
    edi::Project project;e04_t9::OwnerQueue queue;e04_t9::Barrier started;
    Events events;std::atomic<int> calculations=0;
    edi::work::Worker worker([&](auto delivery){queue.post(std::move(delivery));},
        {{},[&](const auto& e){events.add(e);}});
    std::vector<std::uint64_t> published,begin,end;
    edi::LivePreview preview(project,worker,{{},[&](const auto& r){published.push_back(r.generation);},
        [&](auto n){begin.push_back(n);},[&](auto n){end.push_back(n);}},
        {[&](auto& snapshot,const auto& token){
            const int n=++calculations;
#if !EDI_WORKER_OWNER_THREAD
            if(n==1)started.block();
#endif
            return result_for(snapshot,token);
        }});
    preview.recalculate();
#if !EDI_WORKER_OWNER_THREAD
    started.entered();
#endif
    preview.recalculate();
#if !EDI_WORKER_OWNER_THREAD
    started.release();
#endif
    for(int step=0;preview.busy() && step<16;++step)queue.one();
    queue.drain();
    CHECK_MESSAGE((!preview.busy() && preview.newest_request()==2),
        " E11 F2 queued preview settles with the actual newest generation");
    CHECK_MESSAGE((calculations==2 && published==std::vector<std::uint64_t>{2}),
        " E11 F2 cancelled first generation never publishes or replays");
    CHECK_MESSAGE((begin==std::vector<std::uint64_t>{1,2} && end==begin),
        " E11 F2 both actual calculations emit one ordered start and end");
    CHECK_MESSAGE(events.ids(edi::work::EventKind::Cancelled)==std::vector<std::uint64_t>{1},
        " E11 F2 coalescing cancels the real first ticket rather than ticket zero");
    CHECK_MESSAGE((events.ids(edi::work::EventKind::Started)==std::vector<std::uint64_t>{1,2}),
        " E11 F2 the worker starts exactly the two admitted jobs once");
    preview.recalculate();
    for(int step=0;preview.busy() && step<8;++step)queue.one();queue.drain();
    CHECK_MESSAGE((!preview.busy() && calculations==3 && published==std::vector<std::uint64_t>{2,3}),
        " E11 F2 later submission completes once without replaying stale queued work");
}
#if EDI_WORKER_OWNER_THREAD
TEST_CASE("E11 preview immediate FIFO Post publishes before submit returns without phantom busy") {
    edi::Project project;int posts=0,calculations=0;
    edi::work::Worker worker([&](auto delivery){
        if(++posts>48)throw std::runtime_error("bounded immediate Post recursion witness");
        delivery();
    });
    std::vector<std::uint64_t> published,begin,end;
    edi::LivePreview preview(project,worker,{{},[&](const auto& r){published.push_back(r.generation);},
        [&](auto n){begin.push_back(n);},[&](auto n){end.push_back(n);}},
        {[&](auto& snapshot,const auto& token){++calculations;return result_for(snapshot,token);}});
    CHECK_NOTHROW_MESSAGE(preview.recalculate(),
        " E11 F2 immediate supported owner Post cannot recurse while admitting preview");
    CHECK_MESSAGE((!preview.busy() && calculations==1 && published==std::vector<std::uint64_t>{1}),
        " E11 F2 first immediate calculation settles before recalculate returns");
    CHECK_NOTHROW_MESSAGE(preview.recalculate(),
        " E11 F2 later immediate submission remains usable after an early delivery");
    CHECK_MESSAGE((!preview.busy() && preview.newest_request()==2 && calculations==2 &&
        published==std::vector<std::uint64_t>{1,2} && begin==published && end==published),
        " E11 F2 immediate delivery preserves exact counts generations and settled busy state");
}
TEST_CASE("E11 preview scheduling Post failure leaves no unowned job for later submission") {
    for(bool retain_before_throw:{false,true}) {
        INFO(retain_before_throw);
        edi::Project project;std::deque<edi::work::Delivery> queue;
        bool reject=true;int calculations=0;
        edi::work::Worker worker([&](auto delivery){
            if(reject){reject=false;if(retain_before_throw)queue.push_back(std::move(delivery));
                throw std::runtime_error("test scheduling refusal");}
            queue.push_back(std::move(delivery));
        });
        std::vector<std::uint64_t> published,begin,end;
        edi::LivePreview preview(project,worker,{{},[&](const auto& r){published.push_back(r.generation);},
            [&](auto n){begin.push_back(n);},[&](auto n){end.push_back(n);}},
            {[&](auto& snapshot,const auto& token){++calculations;return result_for(snapshot,token);}});
        CHECK_THROWS_AS_MESSAGE(preview.recalculate(),std::runtime_error,
            " E11 F2 scheduling refusal reaches the owner synchronously");
        CHECK_MESSAGE((calculations==0 && published.empty()),
            " E11 F2 rejected scheduling has executed and published no calculation");
        CHECK_NOTHROW_MESSAGE(preview.recalculate(),
            " E11 F2 an actual new request can retry after Post admission refusal");
        if(retain_before_throw) {
            REQUIRE_MESSAGE(queue.size()==2,"E11 G4 refused and valid scheduling callbacks are independently queued");
            auto retired=std::move(queue.front());queue.pop_front();retired();
            CHECK_MESSAGE((calculations==0 && published.empty() && preview.busy() && queue.size()==1),
                "E11 G4 a rejected retained callback alone cannot consume the queued successor");
        }
        for(int step=0;!queue.empty() && step<24;++step){auto delivery=std::move(queue.front());queue.pop_front();delivery();}
        CHECK_MESSAGE((queue.empty() && !preview.busy() && preview.newest_request()==2 && calculations==1 &&
            published==std::vector<std::uint64_t>{2} && begin==published && end==published),
            " E11 F2 retained rejected callbacks cannot run old jobs or steal a later ticket");
    }
}
TEST_CASE("E11 preview Worker scheduling refusal and explicit cancellation retain FIFO ownership") {
    for(bool retain_before_throw:{false,true}) {
        INFO(retain_before_throw);
        std::deque<edi::work::Delivery> queue;bool reject=true;
        int orphan=0,valid=0,delivered=0;bool cancelled=false;
        Events events;
        edi::work::Worker worker([&](auto delivery){
            if(reject){reject=false;if(retain_before_throw)queue.push_back(std::move(delivery));
                throw std::runtime_error("test scheduling refusal");}
            queue.push_back(std::move(delivery));
        },{{},[&](const auto& e){events.add(e);}});
        CHECK_THROWS_AS_MESSAGE(worker.submit("rejected",[&](const auto&,const auto&){++orphan;return edi::work::Delivery{};}),
            std::runtime_error," E11 F2 public Worker refuses failed owner scheduling");
        const auto ticket=worker.submit("accepted",[&](const auto& token,const auto&){
            ++valid;cancelled=token.cancelled();return edi::work::Delivery([&]{++delivered;});});
        worker.cancel(ticket);
        if(retain_before_throw) {
            REQUIRE_MESSAGE(queue.size()==2,"E11 G4 public Worker retains separately observable callback identities");
            auto retired=std::move(queue.front());queue.pop_front();retired();
            CHECK_MESSAGE((orphan==0 && valid==0 && delivered==0 && queue.size()==1 &&
                events.ids(edi::work::EventKind::Started).empty()),
                "E11 G4 rejected callback does not start a valid later ticket before its own callback");
        }
        for(int step=0;!queue.empty() && step<16;++step){auto delivery=std::move(queue.front());queue.pop_front();delivery();}
        CHECK_MESSAGE((queue.empty() && orphan==0 && valid==1 && delivered==1 && cancelled),
            " E11 F2 failed scheduling never replays and the later real token still cancels cooperatively");
        CHECK_MESSAGE(events.ids(edi::work::EventKind::Started)==std::vector<std::uint64_t>{ticket},
            " E11 F2 only the successfully returned ticket owns a started job");
    }
}
TEST_CASE("E11 preview inline Post then throw retains actual admission and once settlement") {
    for(bool use_preview:{false,true}) {
        INFO(use_preview);
        bool throw_once=true;int jobs=0,deliveries=0;
        edi::work::Worker worker([&](auto delivery){
            const bool fail=std::exchange(throw_once,false);delivery();
            if(fail)throw std::runtime_error("actual inline scheduling delivered before throw");
        });
        if(use_preview) {
            edi::Project project;std::vector<std::uint64_t> published;
            edi::LivePreview preview(project,worker,{{},[&](const auto& r){published.push_back(r.generation);}},
                {[&](auto& snapshot,const auto& token){++jobs;return result_for(snapshot,token);}});
            CHECK_NOTHROW_MESSAGE(preview.recalculate(),"E11 G4 already entered inline work retains its real admission despite a later Post throw");
            CHECK_MESSAGE((jobs==1 && !preview.busy() && published==std::vector<std::uint64_t>{1}),
                "E11 G4 inline-then-throw completes the actual first generation without phantom busy");
            preview.recalculate();
            CHECK_MESSAGE((jobs==2 && !preview.busy() && published==std::vector<std::uint64_t>{1,2}),
                "E11 G4 a later preview request never replays already entered inline work");
        } else {
            edi::work::Ticket first=0;
            CHECK_NOTHROW_MESSAGE(first=worker.submit("actual",[&](const auto&,const auto&){++jobs;return edi::work::Delivery([&]{++deliveries;});}),
                "E11 G4 Worker returns the actual entered ticket after inline scheduling throws");
            CHECK_MESSAGE((first!=0 && jobs==1 && deliveries==1),"E11 G4 actual inline admission and final delivery are retained exactly once");
            const auto second=worker.submit("later",[&](const auto&,const auto&){++jobs;return edi::work::Delivery([&]{++deliveries;});});
            CHECK_MESSAGE((second>first && jobs==2 && deliveries==2),"E11 G4 later Worker admission preserves ordering without replay");
        }
    }
}
#endif
