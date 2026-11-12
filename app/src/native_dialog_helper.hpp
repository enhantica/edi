// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_NATIVE_DIALOG_HELPER_HPP
#define EDI_NATIVE_DIALOG_HELPER_HPP
namespace edi_app {
/// Run only in a child process; the native platform may block while constructing its picker.
int native_dialog_helper_main(int argc, char** argv);
}
#endif
