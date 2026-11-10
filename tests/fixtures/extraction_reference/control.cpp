// SPDX-License-Identifier: BSD-3-Clause
// An independent writer proves that each requested I/O fault channel is reached.
#include <filesystem>
#include <fstream>
#include <cstdio>
#include <fcntl.h>
#include <string>
#include <unistd.h>
int main(int argc, char** argv) {
    if (argc != 3) return 7;
    const auto root = std::filesystem::path(argv[1]);
    std::filesystem::create_directories(root);
    const auto path = root / "project.edi";
    const std::string backend = argv[2];
    const std::string bytes = "independent file operation control\n";
    if (backend == "stdio") {
        FILE* file = std::fopen(path.c_str(), "wb");
        if (!file) return 1;
        bool okay = std::fwrite(bytes.data(), 1, bytes.size(), file) == bytes.size();
        if (okay) okay = std::fflush(file) == 0;
        const bool closed = std::fclose(file) == 0;
        return okay && closed ? 0 : 1;
    }
    if (backend == "posix") {
        const int file = ::open(path.c_str(), O_WRONLY | O_CREAT | O_EXCL, 0600);
        if (file < 0) return 1;
        bool okay = ::write(file, bytes.data(), bytes.size()) == static_cast<ssize_t>(bytes.size());
        if (okay) okay = ::fsync(file) == 0;
        const bool closed = ::close(file) == 0;
        return okay && closed ? 0 : 1;
    }
    if (backend != "cpp") return 7;
    std::ofstream file(root / "project.edi", std::ios::binary);
    file.write(bytes.data(), bytes.size());
    if (!file) return 1;
    file.flush();
    if (!file) return 1;
    file.close();
    return file ? 0 : 1;
}
