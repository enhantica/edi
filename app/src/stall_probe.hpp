// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_STALL_PROBE_HPP
#define EDI_APP_STALL_PROBE_HPP

class QCoreApplication;

namespace edi_app {

// A development probe of the GUI thread, off unless EDI_STALL_PROBE is set: a 10 ms timer on the GUI thread writes
// a warning to the run log for every gap over 100 ms between its ticks ("stall-probe: gap N ms"), and on quit how
// many there were and the longest. Warnings, so the level chosen in the preferences keeps them. Measures how long the
// window could not answer, for the scale check of a long series.
void install_stall_probe(QCoreApplication& app);

}  // namespace edi_app

#endif  // EDI_APP_STALL_PROBE_HPP
