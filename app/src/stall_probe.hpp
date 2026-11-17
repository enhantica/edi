// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_STALL_PROBE_HPP
#define EDI_APP_STALL_PROBE_HPP

class QCoreApplication;

namespace edi_app {

// A development probe of the GUI thread, off unless EDI_STALL_PROBE is set: a 10 ms timer on the GUI thread writes
// a warning to the run log for every gap over 100 ms between its ticks ("stall-probe: gap N ms"), and on quit how
// many there were and the longest. Warnings, so the level chosen in the preferences keeps them. Measures how long the
// window could not answer, for the scale check of a long series.
// With EDI_STALL_PROBE_STACKS=<file> (Linux) a watchdog thread also samples the GUI thread's stack every 50 ms of a
// stall into that file, as module and offset pairs to resolve with addr2line. The unwinder is not safe in a signal
// handler that interrupts an allocation, so a sampled run can corrupt the heap and abort at exit: use it to find
// where a stall is, and take the stall numbers from a run without it.
void install_stall_probe(QCoreApplication& app);

}  // namespace edi_app

#endif  // EDI_APP_STALL_PROBE_HPP
