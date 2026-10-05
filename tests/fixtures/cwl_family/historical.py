"""Exact token translation for immutable pre-C11-T63 TCH byte witnesses."""

import re

TCH = b'cwl-' + b'pseudo-voigt'
FCJ = b'cwl-thompson-' + b'cox-hastings'


def original_tokens(contents):
    return re.sub(
        rb'(?m)(^_(?:peak\.type|fit_result\.profile_function)\s+["\']?)cwl-tch-pseudo-voigt(-fcj)?(?=["\']?\s|$)',
        lambda match: match[1] + (FCJ if match[2] else TCH),
        contents,
    )


def current_tokens(contents):
    for old, new in ((FCJ, b'cwl-tch-pseudo-voigt-fcj'), (TCH, b'cwl-tch-pseudo-voigt')):
        contents = re.sub(
            rb'(?m)(^_(?:peak\.type|fit_result\.profile_function)\s+["\']?)'
            + old
            + rb'(?=["\']?\s|$)',
            lambda match, new=new: match[1] + new,
            contents,
        )
    return contents
