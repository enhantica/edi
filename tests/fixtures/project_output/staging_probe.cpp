#include <cstdio>
#include <cstring>

#include "crysta/model.hpp"
#ifdef EDI_OBSERVER
#include "edi/io.hpp"
#endif
int main(int argc, char** argv) {
    if (argc != 4) return 3;
    try {
#ifdef EDI_OBSERVER
        auto& project = *new edi::Project(edi::load_project(argv[2]));
        std::puts("entered");
        std::fflush(stdout);
        if (std::strcmp(argv[1], "save-as") == 0)
            edi::save_project_as(project, argv[3]);
        else
            edi::save_project(project, argv[3]);
#else
        auto& project = *new crysta::Project(crysta::load_project(argv[2]));
        std::puts("entered");
        std::fflush(stdout);
        crysta::save_project(project, argv[3]);
#endif
        std::puts("published");
    } catch (const std::exception& error) {
        std::puts("refused");
        std::puts(error.what());
    }
}
