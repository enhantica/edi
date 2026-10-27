#include <doctest/doctest.h>
#include <array>
#include <string>
#include "edi/edit.hpp"
#include "edi/io.hpp"

// Actual public column attachment, rather than an invented pointer flag. The
// extra test-owned table borrows the existing coefficient objects themselves.
template<> struct crysta::RowSchema<edi::Parameter> {
    static constexpr const char* name="_e11_parameter";
    static constexpr auto fields=std::tuple{&edi::Parameter::value,
        &edi::Parameter::uncertainty,&edi::Parameter::free,
        &edi::Parameter::start_value,&edi::Parameter::start_uncertainty};
    static constexpr std::array items{"value","uncertainty","free","start_value","start_uncertainty"};
};
template<> struct crysta::detail::ForeignTable<edi::Parameter> {
    using type=edi::ItemVec<edi::Parameter>;
};

// Reuse the existing unit carrier's allocation instrumentation. Count, rather
// than throw inside noexcept: an old allocating commit must fail an assertion,
// not terminate the carrier before the remaining channels can be inventoried.
namespace c13_t12_fault {
extern thread_local long remaining;
extern thread_local unsigned calls;
}
namespace {
constexpr std::array fixed{
    &edi::PeakBase::rise_alpha_0, &edi::PeakBase::rise_alpha_1,
    &edi::PeakBase::decay_beta_0, &edi::PeakBase::decay_beta_1,
    &edi::PeakBase::broad_gauss_sigma_0, &edi::PeakBase::broad_gauss_sigma_1,
    &edi::PeakBase::broad_gauss_sigma_2, &edi::PeakBase::broad_gauss_size,
    &edi::PeakBase::broad_gauss_strain, &edi::PeakBase::broad_lorentz_gamma_0,
    &edi::PeakBase::broad_lorentz_gamma_1, &edi::PeakBase::broad_lorentz_gamma_2,
    &edi::PeakBase::broad_lorentz_size, &edi::PeakBase::broad_lorentz_strain};
constexpr std::array optional{
    &edi::PeakBase::broad_gauss_u, &edi::PeakBase::broad_gauss_v,
    &edi::PeakBase::broad_gauss_w, &edi::PeakBase::broad_lorentz_x,
    &edi::PeakBase::broad_lorentz_y, &edi::PeakBase::mixing_eta_0,
    &edi::PeakBase::mixing_eta_1, &edi::PeakBase::asym_fcj_1,
    &edi::PeakBase::asym_fcj_2, &edi::PeakBase::asym_beba_a0,
    &edi::PeakBase::asym_beba_b0, &edi::PeakBase::asym_beba_a1,
    &edi::PeakBase::asym_beba_b1, &edi::PeakBase::asym_beba_limit};
constexpr std::array absorption{
    &edi::AbsorptionBase::abscor1, &edi::AbsorptionBase::abscor2,
    &edi::AbsorptionBase::mu_r};
void seed(edi::Parameter& p, double v) {
    p.value=v; p.uncertainty=v/7; p.free=true;
    p.start_value=v+3; p.start_uncertainty=v/11;
    if(p.spec==nullptr)p.spec=&edi::spec::peak_rise_alpha_0;
    p.dependence=edi::Dependence::Constrained;
    p.fit_blocker=edi::FitBlocker::Capability;
    p.fit_reason=std::string(2048, 'r')+std::to_string(v);
    p.fit_idle=true;
}
void same(const edi::Parameter& p,const edi::Parameter& expected) {
    CHECK_MESSAGE((p.value.get()==expected.value.get() &&
        p.uncertainty.get()==expected.uncertainty.get() && p.free.get()==expected.free.get() &&
        p.start_value.get()==expected.start_value.get() &&
        p.start_uncertainty.get()==expected.start_uncertainty.get() &&
        p.spec==expected.spec && p.dependence==expected.dependence &&
        p.fit_blocker==expected.fit_blocker && p.fit_reason==expected.fit_reason &&
        p.fit_idle==expected.fit_idle),
        " E11 F1 prepared restoration transfers every current scalar and fit metadata field");
}
template<class Prepared> void transfer(Prepared& prepared) {
    CHECK_MESSAGE(noexcept(prepared.commit()),
        " E11 F1 prepared transfer has an explicit nonthrowing commit boundary");
    c13_t12_fault::calls=0; c13_t12_fault::remaining=1000000;
    prepared.commit();
    const auto allocations=c13_t12_fault::calls;
    c13_t12_fault::remaining=-1;
    CHECK_MESSAGE(allocations==0,
        " E11 F1 prepared commit must not allocate after its first live write");
}
template<class Family,class Prepared,class Members>
void optional_lifetime(Family& live,Members members) {
    for(auto member:members) {
        auto& slot=live.*member;
        slot.emplace(); seed(*slot,17.25);
        slot->category.point_at(live.row);
        auto* held=&*slot;
        const auto retired_image=*held;
        Family absent=live; (absent.*member).reset();
        Prepared removal(live,std::move(absent)); transfer(removal);
        CHECK_MESSAGE((!slot && held->is_detached()),
            " E11 F1 removal retires the exact held coefficient cell");
        same(*held,retired_image);
        Family incoming=live; (incoming.*member).emplace();
        seed(*(incoming.*member),38.75);
        const auto wanted=*(incoming.*member);
        Prepared addition(live,std::move(incoming)); transfer(addition);
        REQUIRE_MESSAGE(slot.has_value()," E11 F1 absent-to-present restoration actually admits its slot");
        CHECK_MESSAGE((&*slot!=held && slot->is_attached() && held->is_detached()),
            " E11 F1 reintroduced slots use new live cells and never resurrect retired handles");
        same(*slot,wanted); same(*held,retired_image);
    }
}
}
TEST_CASE("E11 restore peak fixed and optional payloads transfer without allocation") {
    edi::Project project;
    auto bank=std::make_shared<edi::BraggPdExperiment>();bank->name="test";
    project.experiments.push_back(bank);
    auto& live=bank->peak;
    edi::PeakBase wanted;wanted.type=std::string(512,'p');wanted.cutoff_fwhm=37.25;
    double v=3.25;
    for(auto member:fixed)seed(wanted.*member,v++);
    for(auto member:optional){(wanted.*member).emplace();seed(*(wanted.*member),v++);
        (live.*member).emplace();(live.*member)->category.point_at(live.row);}
    std::vector<edi::Parameter*> identities;
    for(auto member:fixed)identities.push_back(&(live.*member));
    for(auto member:optional)identities.push_back(&*(live.*member));
    edi::ItemVec<edi::Parameter> columns;
    for(auto* parameter:identities)columns.push_back(std::shared_ptr<edi::Parameter>(bank,parameter));
    for(auto* parameter:identities)REQUIRE_MESSAGE(parameter->bound(),
        " E11 F1 retained parameters enter commit through real bound column cells");
    edi::detail::PreparedPeakRestore prepared(live,wanted);transfer(prepared);
    CHECK_MESSAGE((live.type==wanted.type && live.cutoff_fwhm==wanted.cutoff_fwhm),
        " E11 F1 profile selector and cutoff restore with all coefficient payloads");
    std::size_t index=0;
    for(auto member:fixed){same(live.*member,wanted.*member);
        CHECK_MESSAGE((&(live.*member)==identities[index++] && (live.*member).bound()),
            " E11 F1 fixed parameter retains its bound live cell identity");}
    for(auto member:optional){same(*(live.*member),*(wanted.*member));
        CHECK_MESSAGE((&*(live.*member)==identities[index++] && (live.*member)->is_attached() && (live.*member)->bound()),
            " E11 F1 engaged optional retains its live handle identity");}
    optional_lifetime<edi::PeakBase,edi::detail::PreparedPeakRestore>(live,optional);
}
TEST_CASE("E11 restore absorption transfers metadata even when scientific values compare equal") {
    edi::Project project;
    auto bank=std::make_shared<edi::BraggPdExperiment>();bank->name="test";
    project.experiments.push_back(bank);auto& live=bank->absorption;
    for(auto member:absorption){(live.*member).emplace();seed(*(live.*member),8.25);
        (live.*member)->category.point_at(live.row);}
    auto wanted=live;wanted.type=std::string(512,'a');
    for(auto member:absorption){(wanted.*member)->fit_reason=std::string(4096,'z');
        (wanted.*member)->fit_blocker=edi::FitBlocker::Data;
        (wanted.*member)->fit_idle=false;}
    std::vector<edi::Parameter*> identities;for(auto member:absorption)identities.push_back(&*(live.*member));
    edi::ItemVec<edi::Parameter> columns;
    for(auto* parameter:identities)columns.push_back(std::shared_ptr<edi::Parameter>(bank,parameter));
    for(auto* parameter:identities)REQUIRE_MESSAGE(parameter->bound(),
        " E11 F1 absorption coefficients enter commit through real bound column cells");
    edi::detail::PreparedAbsorptionRestore prepared(live,wanted);transfer(prepared);
    std::size_t index=0;for(auto member:absorption){same(*(live.*member),*(wanted.*member));
        CHECK_MESSAGE((&*(live.*member)==identities[index++] && (live.*member)->is_attached() && (live.*member)->bound()),
            " E11 F1 retained absorption coefficient keeps its attached handle");}
    CHECK_MESSAGE(live.type==wanted.type," E11 F1 absorption family selector restores exactly");
    optional_lifetime<edi::AbsorptionBase,edi::detail::PreparedAbsorptionRestore>(live,absorption);
}
TEST_CASE("E11 restore actual experiment control Undo retains exact saved scientific state") {
    auto project=edi::load_project("docs/user/cli/pd-neut-cwl_lab6-echidna_fcj-asymmetry/project");
    auto& bank=project.experiment();
    const auto saved=edi::project_edi_files(project);
    auto peak=edi::capture_experiment_controls(project,bank,true);
    bank.peak.cutoff_fwhm+=7.25;bank.peak.broad_gauss_u->value=0.1325;
    edi::Edit::restore_experiment_controls(project,std::move(peak))();
    CHECK_MESSAGE(edi::project_edi_files(project)==saved,
        " E11 F1 actual profile Undo restores exact pre-edit native saved state");
    edi::ExperimentControlsUndo absorption_before;
    absorption_before.experiment=&bank;absorption_before.absorption=bank.absorption;
    absorption_before.related=edi::capture_relations(project);absorption_before.fit_result=project.fit_result;
    bank.absorption.type="none";bank.absorption.mu_r.emplace(2.25);
    edi::Edit::restore_experiment_controls(project,std::move(absorption_before))();
    CHECK_MESSAGE(edi::project_edi_files(project)==saved,
        " E11 F1 actual absorption Undo restores exact pre-edit native saved state");
}
