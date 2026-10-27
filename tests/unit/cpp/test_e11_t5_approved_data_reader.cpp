#include <doctest/doctest.h>
#include <algorithm>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>
#include "edi/io.hpp"
#include "json.hpp"

namespace {
struct ReaderScratch {
    std::filesystem::path root=std::filesystem::temp_directory_path()/
        ("edi-e11-approved-reader-"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    ReaderScratch(){std::filesystem::create_directories(root);}
    ~ReaderScratch(){std::error_code ignored;std::filesystem::remove_all(root,ignored);}
};
void write(const std::filesystem::path& path,const std::string& bytes) {
    std::ofstream out(path);out<<bytes;
    REQUIRE_MESSAGE(out.good()," E11 reader fixture must retain its exact independently supplied bytes");
}
void observations(const edi::PlainDataLoad& result,bool single,bool tof) {
    CHECK_MESSAGE((result.points==3 && result.more.empty()),
        " E11 approved reader retains every supplied observation in its original dataset");
    const auto& experiment=result.experiment;
    const std::vector<double> intensities{17.25,31.75,23.5},sigma{0.75,1.25,1.5};
    if(single) {
        REQUIRE_MESSAGE(experiment.reflections.has_value(),
            " E11 approved reflection reader keeps its actual native observation representation");
        const auto& data=*experiment.reflections;
        CHECK_MESSAGE((data.index_h.get()==std::vector<std::int32_t>{-1,2,0} &&
            data.index_k.get()==std::vector<std::int32_t>{2,0,1} &&
            data.index_l.get()==std::vector<std::int32_t>{3,-1,2}),
            " E11 approved reflection bytes preserve signed Miller indices and input row order");
        CHECK_MESSAGE((data.intensity_meas.get()==intensities && data.intensity_meas_su.get()==sigma),
            " E11 approved reflection bytes determine exact measured intensities and uncertainties");
        if(tof)CHECK_MESSAGE((data.wavelength.get()==std::vector<double>{1.125,1.375,1.625}),
            " E11 approved TOF reflection bytes retain each measured wavelength");
    } else {
        REQUIRE_MESSAGE(experiment.data.has_value(),
            " E11 approved powder reader keeps its actual native observation representation");
        CHECK_MESSAGE((experiment.data->axis()==std::vector<double>{21.5,22.75,25.125}),
            " E11 approved powder bytes determine the measured axis rather than the original path");
        CHECK_MESSAGE((experiment.data->intensity_meas.get()==intensities &&
            experiment.data->intensity_meas_su.get()==sigma),
            " E11 approved powder bytes determine exact intensities and uncertainties");
    }
}
}
TEST_CASE("E11 reader approved captured bytes and original source identity remain distinct") {
    for(const auto* corpus:{"pd-neut-cwl_lab6-echidna_fcj-asymmetry","pd-neut-tof_si-sepd_start-2",
        "sc-neut-cwl_tb2ti2o7-heidi_basic","sc-neut-tof_taurine-unknown_basic"}) {
        INFO(corpus);const std::string name=corpus;
        const bool single=name.starts_with("sc-"),tof=name.find("-tof_")!=std::string::npos;
        auto project=edi::load_project("docs/user/cli/"+name+"/project");
        const auto before=edi::project_edi_files(project);const auto template_name=project.experiment().name.value();
        ReaderScratch scratch;
        const auto source=scratch.root/(single?"publication_owner.hkl":"publication_owner.xye");
        const auto captured=scratch.root/"captured-input.part";
        const auto ordinary=scratch.root/(single?"ordinary_control.hkl":"ordinary_control.xye");
        const std::string bytes=!single?"21.5 17.25 .75\n22.75 31.75 1.25\n25.125 23.5 1.5\n":
            tof?"# TOF\n-1 2 3 17.25 .75 1.125\n2 0 -1 31.75 1.25 1.375\n0 1 2 23.5 1.5 1.625\n":
                "-1 2 3 17.25 .75\n2 0 -1 31.75 1.25\n0 1 2 23.5 1.5\n";
        write(source,"original path is identity only: not readable scientific data\n");
        write(captured,bytes);write(ordinary,bytes);
        for(bool rename:{false,true}) {
            INFO(rename);
            const auto loaded=edi::experiment_with_plain_data(project.experiment(),captured.string(),source.string(),rename);
            observations(loaded,single,tof);
            CHECK_MESSAGE((loaded.file_name==source.filename().string() && loaded.experiment.data_file==source.filename().string()),
                " E11 captured paths never replace the user's original native source identity");
            CHECK_MESSAGE(loaded.experiment.name.value()==(rename?"publication_owner":template_name),
                " E11 native rename policy uses the original basename and preserves explicit keep-name choice");
            const auto original=edi::experiment_with_plain_data(project.experiment(),ordinary.string(),rename);
            observations(original,single,tof);
            CHECK_MESSAGE((original.file_name==ordinary.filename().string() &&
                original.experiment.data_file==ordinary.filename().string() &&
                original.experiment.name.value()==(rename?"ordinary_control":template_name)),
                " E11 original three-argument ordinary reader remains a positive naming and data control");
        }
        CHECK_THROWS_AS_MESSAGE(edi::experiment_with_plain_data(project.experiment(),
            (scratch.root/"missing-capture.part").string(),ordinary.string(),false),edi::IoError,
            " E11 absent approved reader bytes cannot fall back to a readable original source");
        CHECK_MESSAGE(edi::project_edi_files(project)==before,
            " E11 approved and ordinary load preparations preserve the actual live template and saved state");
    }
}
TEST_CASE("E11 reader captured FullProf INT preserves independent CW and TOF input rows") {
    std::ifstream input("tests/fixtures/single_crystal/fullprof.json");
    const std::string body{std::istreambuf_iterator<char>(input),{}};
    const auto reference=edi::json::parse(body).at("cases");
    for(bool tof:{false,true}) {
        INFO(tof);
        const std::string example=tof?"sc-neut-tof_taurine_basic":"sc-neut-cwl_tbti_basic";
        const std::string project_name=tof?"sc-neut-tof_taurine-unknown_basic":"sc-neut-cwl_tb2ti2o7-heidi_basic";
        const auto& record=reference.at(example);
        const auto stem=record.at("stem").string("stem");
        std::ifstream fullprof("tests/fixtures/single_crystal/fullprof/"+example+"/"+stem+".int");
        const std::string bytes{std::istreambuf_iterator<char>(fullprof),{}};
        REQUIRE_MESSAGE(!bytes.empty(),"E11 FullProf reader reference retains actual independently published input bytes");
        auto project=edi::load_project("docs/user/cli/"+project_name+"/project");
        const auto before=edi::project_edi_files(project);ReaderScratch scratch;
        const auto source=scratch.root/"publication_owner.InT",captured=scratch.root/"measurement.int";
        const auto ordinary=scratch.root/"ordinary_control.INT";
        write(source,"unapproved original path bytes must never be opened\n");write(captured,bytes);write(ordinary,bytes);
        write(scratch.root/"measurement.xye",bytes);
        const auto loaded=edi::experiment_with_plain_data(project.experiment(),captured.string(),source.string(),true);
        const auto control=edi::experiment_with_plain_data(project.experiment(),ordinary.string(),true);
        REQUIRE_MESSAGE((loaded.experiment.reflections && control.experiment.reflections),
            "E11 FullProf data reaches actual native reflection storage in both reader entrances");
        const auto& data=*loaded.experiment.reflections;const auto& ordinary_data=*control.experiment.reflections;
        const auto& rows=record.at("input_rows").array("input_rows");
        REQUIRE_MESSAGE(data.size()==rows.size(),"E11 FullProf captured input retains the independent full observation count");
        for(std::size_t i=0;i<rows.size();++i) {
            const auto& row=rows[i].array("row");
            CHECK_MESSAGE((data.index_h[i]==row[0].number("h") && data.index_k[i]==row[1].number("k") &&
                data.index_l[i]==row[2].number("l") && data.intensity_meas[i]==row[3].number("intensity") &&
                data.intensity_meas_su[i]==row[4].number("sigma")),
                "E11 FullProf captured bytes preserve every independent signed-index observation and uncertainty");
            if(tof)CHECK_MESSAGE(data.wavelength[i]==row[5].number("wavelength"),
                "E11 TOF FullProf uses the wavelength column rather than its dataset code");
        }
        CHECK_MESSAGE((data.index_h.get()==ordinary_data.index_h.get() && data.index_k.get()==ordinary_data.index_k.get() &&
            data.index_l.get()==ordinary_data.index_l.get() && data.intensity_meas.get()==ordinary_data.intensity_meas.get() &&
            data.intensity_meas_su.get()==ordinary_data.intensity_meas_su.get() && data.wavelength.get()==ordinary_data.wavelength.get()),
            "E11 approved reader preserves FIRST ordinary FullProf row semantics on the exact same bytes");
        CHECK_MESSAGE(loaded.file_name==source.filename().string(),"E11 FullProf source identity retains its original case and filename");
        CHECK_THROWS_AS_MESSAGE(edi::experiment_with_plain_data(project.experiment(),ordinary.string(),
            (scratch.root/"wrong-selector.xye").string(),true),edi::IoError,
            "E11 approved byte entrance refuses an INT versus plain selector mismatch");
        CHECK_THROWS_AS_MESSAGE(edi::experiment_with_plain_data(project.experiment(),
            (scratch.root/"measurement.xye").string(),source.string(),true),edi::IoError,
            "E11 captured INT identity cannot silently use the plain-file selector");
        CHECK_MESSAGE(edi::project_edi_files(project)==before,"E11 FullProf preparation and mismatch refusals preserve the live template");
    }
}
TEST_CASE("E11 reader FullProf dataset partitions wavelength zero sigma and physical diagnostics survive capture") {
    for(bool tof:{false,true}) {
        INFO(tof);ReaderScratch scratch;
        auto project=edi::load_project(tof?"docs/user/cli/sc-neut-tof_taurine-unknown_basic/project":
            "docs/user/cli/sc-neut-cwl_tb2ti2o7-heidi_basic/project");
        const std::string bytes="FullProf independent input\n(3i4,2f12.4,i4,2f8.4)\n"+
            std::string(tof?"0 0 0\n":"1.375 0 0\n")+
            "2 1 3 9 .3 2 1.3 84\n1 2 3 -4 .7 7 1.5 88\n2 1 3 12 .4 2 1.7 92\n"
            "3 1 2 5 .2 4 1.9 94\n4 0 1 0 0 7 2.1 90\n";
        const auto captured=scratch.root/"measurement.int",source=scratch.root/"source.INT";
        write(captured,bytes);write(source,"original is not an approved byte source\n");
        const auto loaded=edi::experiment_with_plain_data(project.experiment(),captured.string(),source.string(),true);
        CHECK_MESSAGE((loaded.more.size()==2 && loaded.unweighted==1),
            "E11 FullProf retains distinct dataset codes and independently skips the zero-uncertainty row");
        std::vector<const edi::BraggPdExperiment*> banks{&loaded.experiment};
        for(const auto& bank:loaded.more)banks.push_back(&bank);
        std::vector<double> all;
        for(const auto* bank:banks) {
            REQUIRE_MESSAGE(bank->reflections.has_value(),"E11 every FullProf dataset retains its native measured reflections");
            const auto& data=*bank->reflections;
            for(std::size_t i=0;i<data.size();++i) {
                all.push_back(data.intensity_meas[i]);
                if(tof) {
                    const double expected=data.intensity_meas[i]==9?1.3:data.intensity_meas[i]==-4?1.5:
                        data.intensity_meas[i]==12?1.7:1.9;
                    CHECK_MESSAGE(data.wavelength[i]==expected,"E11 FullProf TOF wavelengths remain bound to their own input rows");
                }
            }
            if(!tof) {
                REQUIRE_MESSAGE(bank->instrument.setup_wavelength.has_value(),"E11 CW FullProf header supplies its fixed wavelength");
                CHECK_MESSAGE(bank->instrument.setup_wavelength->value.get()==1.375,
                    "E11 captured FullProf header wavelength overrides a different native template value");
            }
        }
        std::sort(all.begin(),all.end());
        CHECK_MESSAGE((all==std::vector<double>{-4,5,9,12}),"E11 FullProf partitions retain every weighted signed observation exactly once");
        write(captured,bytes+"2.5 1 3 9 1 2 1.25 94\n");
        bool refused=false;
        try{(void)edi::experiment_with_plain_data(project.experiment(),captured.string(),source.string(),false);}
        catch(const edi::IoError& error){refused=true;const std::string message=error.what();
            CHECK_MESSAGE((message.find("line")!=std::string::npos && message.find("9")!=std::string::npos),
                "E11 malformed FullProf row refuses with its original physical line diagnostic");}
        CHECK_MESSAGE(refused,"E11 malformed FullProf records cannot degrade into plain-reader skipped rows");
    }
}
