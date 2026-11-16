"""Only the committed inert ABSCOR2 deletion can adapt a historical CLI start."""


def absorption_start_bytes(name, contents):
    allowed = {'experiments/wish_2_9.edi', 'experiments/wish_4_7.edi', 'experiments/wish_5_6.edi'}
    if name not in allowed or b'_absorption.abscor2' in contents:
        return contents
    anchor = b'_absorption.abscor1 0.0(10)\n'
    if contents.count(anchor) != 1:
        return contents
    # 927a7a94 / ADR-0123: the removed zero field never entered the calculation.
    return contents.replace(anchor, anchor + b'_absorption.abscor2 0.0\n', 1)
