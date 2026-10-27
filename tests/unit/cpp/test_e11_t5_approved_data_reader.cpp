#include <doctest/doctest.h>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>
#include "edi/io.hpp"

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
    for(const auto* corpus:{"pd-neut-cwl_lab6-echidna_fcj-asymmetry",
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
