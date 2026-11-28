// SPDX-License-Identifier: BSD-3-Clause
#include <doctest/doctest.h>

#include <algorithm>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <string>
#include <system_error>
#include <vector>

#include "crysta/analysis.hpp"
#include "crysta/model.hpp"
#include "edi/io.hpp"

namespace {
namespace fs = std::filesystem;

std::string utf8(const fs::path& path) {
    const auto bytes = path.u8string();
    return {bytes.begin(), bytes.end()};
}

class PathFixture {
public:
    PathFixture()
        : root(fs::temp_directory_path() /
               ("edi-unicode-" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()))) {
        REQUIRE_MESSAGE(fs::create_directory(root), "The path test owns an empty directory");
    }

    ~PathFixture() {
        std::error_code error;
        fs::remove_all(root, error);
    }

    fs::path data_in(const fs::path& folder) const {
        const auto directory = root / folder;
        REQUIRE_MESSAGE(fs::create_directory(directory), "The OS creates the intended data folder");
        const auto path = directory / "measured.xye";
        std::ofstream data(path);
        data << "12.5 36 6\n13.75 49 7\n16 81 9\n";
        data.close();
        REQUIRE_MESSAGE(data.good(), "The OS writes the three source rows");
        return path;
    }

    void check_directory(const fs::path& expected) const {
        std::vector<fs::path> names;
        for (const auto& entry : fs::directory_iterator(root)) {
            if (entry.is_directory()) {
                names.push_back(entry.path().filename());
            }
        }
        const std::vector<fs::path> wanted{expected};
        REQUIRE_MESSAGE(names == wanted, "The OS lists exactly the intended Unicode folder");
    }

    const fs::path root;
};

const fs::path source = fs::path(__FILE__).parent_path().parent_path().parent_path() /
                        "fixtures/independent_experiments/project";
const std::vector<fs::path> folders{fs::path(u8"Universit\u00e9"), fs::path(u8"\u0141\u00f3d\u017a")};
}  // namespace

TEST_CASE("edi saves and reopens a project in a Unicode folder") {
    const auto project = edi::load_project(utf8(source));
    for (const auto& folder : folders) {
        const auto name = utf8(folder);
        SUBCASE(name.c_str()) {
            const PathFixture fixture;
            const auto target = utf8(fixture.root / folder);
            edi::save_project(project, target);
            fixture.check_directory(folder);
            const auto reopened = edi::load_project(target);
            CHECK_MESSAGE(reopened.metadata.name == "Independent crystals", "edi reopens the saved project metadata");
            edi::save_project(reopened, target);
            fixture.check_directory(folder);
            CHECK_MESSAGE(edi::load_project(target).experiments.size() == 3, "edi reopens all three source experiments after saving again");
        }
    }
}

TEST_CASE("crysta saves and reopens a project in a Unicode folder") {
    const auto project = crysta::load_project(utf8(source));
    for (const auto& folder : folders) {
        const auto name = utf8(folder);
        SUBCASE(name.c_str()) {
            const PathFixture fixture;
            const auto target = utf8(fixture.root / folder);
            crysta::save_project(project, target);
            fixture.check_directory(folder);
            const auto reopened = crysta::load_project(target);
            auto names = reopened.experiments.keys();
            std::ranges::sort(names);
            const std::vector<std::string> expected{"amber", "copper", "violet"};
            CHECK_MESSAGE(names == expected, "crysta reopens all three datablocks named in the source files");
            crysta::save_project(reopened, target);
            fixture.check_directory(folder);
            CHECK_MESSAGE(crysta::load_project(target).experiments.size() == 3, "crysta reopens all three source experiments after saving again");
        }
    }
}

TEST_CASE("edi reads measured data from a Unicode folder") {
    for (const auto& folder : folders) {
        const auto name = utf8(folder);
        SUBCASE(name.c_str()) {
            const PathFixture fixture;
            const auto path = fixture.data_in(folder);
            fixture.check_directory(folder);
            const auto rows = edi::read_plain_data(utf8(path));
            const std::vector<double> expected{36, 49, 81};
            CHECK_MESSAGE(rows.y == expected, "edi reads each of the three intensities from the OS-created file");
        }
    }
}

TEST_CASE("crysta reads measured data from a Unicode folder") {
    for (const auto& folder : folders) {
        const auto name = utf8(folder);
        SUBCASE(name.c_str()) {
            const PathFixture fixture;
            const auto path = fixture.data_in(folder);
            fixture.check_directory(folder);
            const auto rows = crysta::read_plain_data(utf8(path));
            const std::vector<double> expected{36, 49, 81};
            CHECK_MESSAGE(rows.y == expected, "crysta reads each of the three intensities from the OS-created file");
        }
    }
}
