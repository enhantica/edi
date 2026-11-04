#include <doctest/doctest.h>
#include <limits>
#include "edi/calculation.hpp"
#include "edi/io.hpp"
#include "../../fixtures/c34_t28_allocation_failure.hpp"
// Independently frozen from dev e782 before the bounded implementation existed.
// Comparing two new overloads alone would conceal shared byte-codec regressions.
#include "../../fixtures/assistant_dev_integration/prechange_stamp_codec.inc"

namespace {
edi::WorkStamps prechange(const edi::Project& live) {
    edi::WorkStamps stamps;
    for(const auto& bank:live.experiments)
        stamps.experiment_inputs.push_back(edi::e11_prechange_codec::calculation_inputs(live.structures,*bank));
    for(const auto& structure:live.structures)
        stamps.structure_inputs.push_back(edi::e11_prechange_codec::geometry_inputs(*structure));
    stamps.relations=edi::e11_prechange_codec::relation_inputs(live.aliases,live.constraints);
    stamps.experiments=live.experiments.record();stamps.structures=live.structures.record();
    stamps.experiments_generation=live.experiments.generation();
    stamps.structures_generation=live.structures.generation();
    // The editor record is opaque. Retain the existing unbounded owner API's
    // identity, and independently exercise its note_edit invalidation below.
    const auto original=edi::work_stamps(live);
    stamps.edits=original.edits;stamps.edits_at=original.edits_at;
    stamps.aliases=live.aliases.record();stamps.constraints=live.constraints.record();
    return stamps;
}
void same(const edi::WorkStamps& actual,const edi::WorkStamps& old) {
    INFO("component equality experiment=",actual.experiment_inputs==old.experiment_inputs,
        " geometry=",actual.structure_inputs==old.structure_inputs,
        " relations=",actual.relations==old.relations,
        " relation bytes actual=",actual.relations.size()," old=",old.relations.size());
    CHECK_MESSAGE((actual.experiment_inputs==old.experiment_inputs &&
        actual.structure_inputs==old.structure_inputs && actual.relations==old.relations),
        " E11 F3 bounded capture retains exact committed pre-change scientific codec bytes");
    CHECK_MESSAGE((actual.experiments==old.experiments && actual.structures==old.structures &&
        actual.experiments_generation==old.experiments_generation &&
        actual.structures_generation==old.structures_generation && actual.edits==old.edits &&
        actual.edits_at==old.edits_at && actual.aliases==old.aliases && actual.constraints==old.constraints),
        " E11 F3 bounded capture retains actual current native membership and write identities");
}
void check_capture(edi::Project& project) {
    const auto expected=prechange(project);
    const auto saved=edi::project_edi_files(project);
    const auto actual=edi::work_stamps(project,std::size_t{16}*1024*1024);
    same(actual,expected);same(edi::work_stamps(project),expected);
    std::size_t payload=expected.relations.size();
    for(const auto& bytes:expected.experiment_inputs)payload+=bytes.size();
    for(const auto& bytes:expected.structure_inputs)payload+=bytes.size();
    REQUIRE_MESSAGE(payload>0," E11 F3 frozen codec contains a real retained source payload");
    CHECK_THROWS_AS_MESSAGE(edi::work_stamps(project,0),std::length_error,
        " E11 F3 zero finite capacity refuses before source buffer retention");
    CHECK_THROWS_AS_MESSAGE(edi::work_stamps(project,payload-1),std::length_error,
        " E11 F3 a budget below independently encoded retained bytes cannot be admitted");
    same(prechange(project),expected);
    CHECK_MESSAGE(edi::project_edi_files(project)==saved,
        " E11 F3 successful capture and all finite refusals preserve native scientific saved state");
    CHECK_MESSAGE(edi::unchanged_since(project,actual),
        " E11 F3 finite capture is an actual usable publication identity");
}
}
TEST_CASE("E11 bounded stamps link and preserve pre-change codec across powder and measured single crystal") {
    for(const auto* path:{
        "docs/user/cli/pd-neut-cwl_lab6-echidna_fcj-asymmetry/project",
        "docs/user/cli/pd-neut-tof_si-sepd_start-2/project",
        "docs/user/cli/sc-neut-cwl_tb2ti2o7-heidi_basic/project",
        "docs/user/cli/sc-neut-tof_taurine-unknown_basic/project"}) {
        INFO(path);auto project=edi::load_project(path);check_capture(project);
        const auto before=edi::work_stamps(project,std::size_t{16}*1024*1024);
        auto& value=project.structure().cell.length_a.value;
        value=value.get();
        CHECK_MESSAGE(!edi::unchanged_since(project,before),
            " E11 F3 equal value native writes still supersede a finite publication stamp");
        check_capture(project);
        const auto editor_before=edi::work_stamps(project,std::size_t{16}*1024*1024);
        project.note_edit();
        const auto editor_after=edi::work_stamps(project,std::size_t{16}*1024*1024);
        CHECK_MESSAGE((editor_before.edits && editor_before.edits==editor_after.edits &&
            editor_before.edits_at!=editor_after.edits_at && !edi::unchanged_since(project,editor_before)),
            " E11 F3 real owner edits preserve their record and renew its publication generation");
    }
}
TEST_CASE("E11 bounded stamps retain original alias relation source and collection identities") {
    auto project=edi::load_project("docs/user/cli/pd-neut-tof_si-sepd_start-2/project");
    const auto name=project.structure().name.value();
    REQUIRE_MESSAGE((project.structure().cell.length_a.dependence==edi::Dependence::Independent &&
        project.structure().cell.length_b.dependence!=edi::Dependence::Independent),
        "E11 frozen alias fixture retains the independent and symmetry-dependent cubic source controls");
    // .edi datablock/category/item grammar is the pre-integration contract;
    // expected membership never comes from today's named_parameters producer.
    edi::ParameterAlias source;source.id="stamp_source";source.parameter_unique_name=name+".cell.length_a";
    edi::ParameterAlias target;target.id="stamp_target";target.parameter_unique_name=name+".cell.length_b";
    project.aliases.push_back(source);project.aliases.push_back(target);
    edi::ParameterConstraint constraint;constraint.id="stamp_relation";
    constraint.expression="stamp_target = 2.75 * stamp_source";constraint.enabled=false;
    project.constraints.push_back(constraint);
    check_capture(project);
    const auto before=edi::work_stamps(project,std::size_t{16}*1024*1024);
    auto& value=project.structure().cell.length_a.value;value=value.get();
    CHECK_MESSAGE(!edi::unchanged_since(project,before),
        " E11 F3 aliased source equal writes renew original relation input identities");
    check_capture(project);
    project.constraints.front()->expression="stamp_target = 3.25 * stamp_source";
    check_capture(project);
}
TEST_CASE("E11 bounded stamps refuse before input-sized row payload and relation scratch growth") {
    // Observe actual ordinary new/new[] request sizes in the established carrier.
    // Only the known input-sized roles are bounded here; exception bookkeeping,
    // allocator overhead, aligned allocations and process RSS are not an oracle.
    for(int role=0;role<3;++role) {
        INFO(role);
        edi::Project project;project.structures.clear();project.experiments.clear();
        std::size_t capacity=64*1024,threshold=512*1024;
        if(role==0) {
            for(int i=0;i<1024;++i){edi::Structure row;row.name="row_"+std::to_string(i);project.structures.push_back(row);}
            capacity=0;threshold=project.structures.size()*sizeof(std::string);
        } else {
            edi::Structure row;row.name="source";project.structures.push_back(row);
            if(role==1) {
                edi::AtomSite site;site.id="atom";site.wyckoff_letter=std::string(1024*1024,'w');
                project.structure().atom_sites.push_back(site);
            } else {
                project.structure().name=std::string(1024*1024,'n');
                // No experiments read the name, and geometry excludes it. First
                // prove the earlier roles fit before adding the alias lookup.
                CHECK_NOTHROW_MESSAGE(edi::work_stamps(project,capacity),
                    "E11 G2 relation control admits the independent earlier geometry and container roles");
                edi::ParameterAlias alias;alias.id="source";
                alias.parameter_unique_name=project.structure().name.value()+".cell.length_a";
                project.aliases.push_back(alias);
            }
        }
        c34_t28_fault::largest_allocation=0;c34_t28_fault::observing=true;
        bool refused=false;
        try{(void)edi::work_stamps(project,capacity);}
        catch(const std::length_error&){refused=true;}
        catch(...){c34_t28_fault::observing=false;throw;}
        c34_t28_fault::observing=false;
        const auto refused_largest=c34_t28_fault::largest_allocation;
        CHECK_MESSAGE(refused,"E11 G2 the independently insufficient capacity actually refuses");
        CHECK_MESSAGE(refused_largest<threshold,
            "E11 G2 refusal precedes known input-sized retained rows source payload or relation naming scratch");
        c34_t28_fault::largest_allocation=0;c34_t28_fault::observing=true;
        try{(void)edi::work_stamps(project);}
        catch(...){c34_t28_fault::observing=false;throw;}
        c34_t28_fault::observing=false;
        CHECK_MESSAGE(c34_t28_fault::largest_allocation>=threshold,
            "E11 G2 positive unbounded control proves instrumentation reaches the same actual input-sized allocation role");
    }
}
