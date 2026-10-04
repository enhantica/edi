"""Visible whole-declaration witnesses for  review F6.

Literal shapes come from review-2's reachable first-match witnesses. This
builder generates input only; it never imports either implementation.
"""

ROW_TAGS = {
    'polynomial': ('order', 'coef'),
    'chebyshev': ('order', 'coef'),
    'line-segment': ('position', 'intensity'),
}
DAMAGES = (
    'extra-complete',
    'extra-first-only',
    'extra-second-only',
    'foreign-complete',
    'foreign-first-only',
    'foreign-second-only',
    'duplicate-first-column',
    'duplicate-second-column',
    'repeat-type',
    'repeat-unknown-type',
    'repeat-origin',
    'repeat-x_min',
    'repeat-x_max',
    'loop-type',
    'loop-origin',
    'loop-x_min',
    'loop-x_max',
)


def damage_declaration(text, kind, damage):
    first, second = ROW_TAGS[kind]
    foreign = ('position', 'intensity') if kind != 'line-segment' else ('order', 'coef')

    def loop(tags, values):
        return '\nloop_\n' + ''.join(f'_background.{tag}\n' for tag in tags) + values + '\n'

    if damage.startswith(('extra-', 'foreign-')):
        tags = (first, second) if damage.startswith('extra-') else foreign
        if damage.endswith('complete'):
            return text + loop(tags, '0 20')
        index = 0 if damage.endswith('first-only') else 1
        return text + loop((tags[index],), '0' if index == 0 else '20')
    if damage.startswith('duplicate-'):
        tag = first if damage == 'duplicate-first-column' else second
        marker = f'loop_\n_background.{first}\n_background.{second}\n'
        start = text.index(marker)
        end = text.index('\nloop_', start + len(marker))
        # order,coef,coef -> 0,10,20 changes the constant; order,coef,order
        # -> 0,10,1 changes the power. The point analogue changes x or y.
        value = '1' if tag == first else '20'
        body = '0 10 ' + value + '\n'
        if kind == 'line-segment':
            body += '100 35 ' + ('90' if tag == first else '45') + '\n'
        return text[:start] + marker + f'_background.{tag}\n' + body + text[end:]
    if damage in {'repeat-type', 'repeat-unknown-type'}:
        token = kind if damage == 'repeat-type' else 'unsupported-background'
        return text + f'\n_background.type {token}\n'
    tag = damage.split('-', 1)[1]
    value = {'origin': '0', 'x_min': '0', 'x_max': '100', 'type': kind}[tag]
    if damage.startswith('loop-'):
        return text + loop((tag,), value)
    # Foreign scalars are ambiguous too; duplicate an independently chosen
    # nonzero foreign field so presence cannot be silently discarded.
    if f'_background.{tag} ' not in text:
        text += f'\n_background.{tag} 50\n'
    return text + f'\n_background.{tag} {value}\n'
