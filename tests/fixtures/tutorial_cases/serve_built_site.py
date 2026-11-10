"""Run the real site-serve branch with a controlled document root and private port.

Only bind-port literals change. The actual HTTP handler and headers are untouched.
"""

import ast
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

source, output = map(Path, sys.argv[1:3])
port = int(sys.argv[3])
sys.path.insert(0, str(source.parent))


class PrivatePort(ast.NodeTransformer):
    def __init__(self, bind_port):
        self.bind_port = bind_port

    def visit_Constant(self, node):
        if node.value == 8873:
            return ast.copy_location(ast.Constant(self.bind_port), node)
        if node.value == '8873':
            return ast.copy_location(ast.Constant(str(self.bind_port)), node)
        return node


module = ast.fix_missing_locations(PrivatePort(port).visit(ast.parse(source.read_text())))
builder = ModuleType('actual_site_builder')
builder.__file__ = str(source)
sys.modules[builder.__name__] = builder
namespace = vars(builder)
exec(compile(module, str(source), 'exec'), namespace)  # noqa: S102 - trusted actual server definitions
main = next(
    node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == 'main'
)
branches = [
    node
    for node in ast.walk(main)
    if isinstance(node, ast.If) and ast.unparse(node.test) == 'args.serve'
]
if len(branches) != 1:
    raise RuntimeError('site-serve must expose one actual args.serve branch')
program = ast.fix_missing_locations(ast.Module(body=branches[0].body, type_ignores=[]))
namespace.update(args=SimpleNamespace(serve=True, port=port), output=output)
exec(compile(program, str(source), 'exec'), namespace)  # noqa: S102 - trusted actual server entry
