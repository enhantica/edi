// SPDX-License-Identifier: BSD-3-Clause
#include "desktop_updates.hpp"

#include <QCoreApplication>
#include <cstdio>

namespace edi_app {
const char* app_version() noexcept { return "26.18"; }
const char* app_date() noexcept { return ""; }
}

int main(int argc, char** argv) {
    QCoreApplication application(argc, argv);
    if (argc != 2) return 2;
    edi_app::DesktopUpdates updates("26.18", QString::fromUtf8(argv[1]), {}, false);
    const bool managed = updates.managed();
    const bool launched = updates.startMaintenance();
    std::printf("%d %d\n", managed, launched);
}
