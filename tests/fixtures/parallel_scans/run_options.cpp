// Adapter to edi's public C++ run options; no project or model mutation.
#include "edi/threading.hpp"
extern "C" void set_workers(int count) { edi::set_scan_workers(count); }
extern "C" int get_workers() { return edi::scan_workers_setting(); }
