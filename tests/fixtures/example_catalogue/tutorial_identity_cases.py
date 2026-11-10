"""Authored programs that cannot supply a notebook load from the declared download."""

DOWNLOAD = "path = edi.download_data('right')\n"
LOAD = 'project = edi.Project.load(path)\n'

INVALID_DOWNLOADS = {
    'unused-download': "other = edi.download_data('right')\n" + LOAD,
    'load-before-download': LOAD + DOWNLOAD,
    'repeated-assignment': DOWNLOAD + "path = 'wrong'\n" + LOAD,
    'conditional-download': "if False:\n path = edi.download_data('right')\n" + LOAD,
    'augmented-assignment': DOWNLOAD + "path += '/wrong'\n" + LOAD,
    'annotated-assignment': DOWNLOAD + "path: str = 'wrong'\n" + LOAD,
    'deleted-name': DOWNLOAD + 'del path\n' + LOAD,
    'loop-target': DOWNLOAD + "for path in ['wrong']:\n pass\n" + LOAD,
    'assignment-expression': DOWNLOAD + "(path := 'wrong')\n" + LOAD,
    'destructured-assignment': DOWNLOAD + "path, other = ('wrong', 0)\n" + LOAD,
    'with-target': DOWNLOAD + "with open('wrong') as path:\n pass\n" + LOAD,
    'exception-target': DOWNLOAD + 'try:\n pass\nexcept ValueError as path:\n pass\n' + LOAD,
    'import-target': DOWNLOAD + 'import wrong as path\n' + LOAD,
    'definition-target': DOWNLOAD + 'def path():\n pass\n' + LOAD,
    'conditional-load': DOWNLOAD + 'if True:\n ' + LOAD,
    'deferred-load': DOWNLOAD + 'def later():\n ' + LOAD,
    'wrapped-load': DOWNLOAD + 'project = wrap(edi.Project.load(path))\n',
    'conditional-intervening-code': DOWNLOAD + 'if False:\n pass\n' + LOAD,
    'chained-download': "path = other = edi.download_data('right')\n" + LOAD,
    'nonliteral-destination': "path = edi.download_data('right', destination=unknown)\n" + LOAD,
    'duplicate-destination': (
        "path = edi.download_data('right', destination='data', destination='wrong')\n" + LOAD
    ),
}

VALID_DOWNLOADS = {
    'plain': DOWNLOAD + LOAD,
    'literal-destination': "path = edi.download_data('right', destination='data')\n" + LOAD,
    'expression-load': DOWNLOAD + 'edi.Project.load(path)\n',
}
