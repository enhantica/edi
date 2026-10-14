"""Follow PR fixture dependencies and classify actual app-build commands."""

import ast
import json
import re
import shlex
from pathlib import Path

LAUNCHERS = {
    'run',
    'call',
    'check_call',
    'check_output',
    'Popen',
    'system',
    'popen',
    'execv',
    'execve',
    'execl',
    'spawnv',
    'posix_spawn',
    'create_subprocess_exec',
    'create_subprocess_shell',
}
COMPILERS = {
    'cmake',
    'qt-cmake',
    'qmake',
    'ninja',
    'make',
    'app-build',
    'c++',
    'g++',
    'clang++',
    'cc',
    'gcc',
    'clang',
}


def pr_paths(root):
    root = Path(root)
    record = root / 'tests/test-groups.json'
    excluded = set()
    if record.is_file():
        groups = json.loads(record.read_text())['groups']
        excluded = set(groups.get('nightly-only', {}).get('paths', []))
    paths = [
        *root.glob('tests/unit/py/test_*.py'),
        *root.glob('tests/integration/py/test_*.py'),
        *root.glob('tests/system/py/test_*.py'),
    ]
    return [p for p in paths if str(p.relative_to(root)) not in excluded]


def strings(node, bindings, seen=frozenset()):
    if isinstance(node, ast.Name) and node.id in bindings and node.id not in seen:
        return strings(bindings[node.id], bindings, seen | {node.id})
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    return [
        value for child in ast.iter_child_nodes(node) for value in strings(child, bindings, seen)
    ]


def command_tokens(value):
    try:
        lexer = shlex.shlex(value, posix=True, punctuation_chars=';&|')
        lexer.whitespace_split = True
        return list(lexer)
    except ValueError:
        return value.split()


def app_command(words):
    tokens = [token for word in words for token in command_tokens(str(word))]
    if not tokens:
        return False
    for separator in (';', '&&', '||', '|'):
        if separator in tokens:
            chunks, chunk = [], []
            for token in tokens:
                if token in {';', '&&', '||', '|'}:
                    chunks.append(chunk)
                    chunk = []
                else:
                    chunk.append(token)
            return any(app_command(chunk) for chunk in [*chunks, chunk])
    executable = Path(tokens[0]).name
    if executable in {'bash', 'sh'} and '-c' in tokens:
        return app_command(tokens[tokens.index('-c') + 1 :])
    if executable == 'pixi' and tokens[1:2] == ['run']:
        return 'app-build' in tokens[2:]
    if executable not in COMPILERS or set(tokens) & {'--version', '--help', '-fsyntax-only', '-E'}:
        return False
    # Targets and build/configure operands describe the invocation. Module comments,
    # header includes and an adjacent app CMake file do not turn another probe into an app.
    joined = ' '.join(tokens)
    source = any('app/' in token and token.endswith(('.cpp', '.cc', '.cxx')) for token in tokens)
    explicit = any(
        term in joined
        for term in (
            'EDI_BUILD_APP=ON',
            '--target edi_app',
            '--build app',
            '--build build/app',
            'app-build',
            'edi_app_module',
        )
    )
    target = executable in {'ninja', 'make'} and any(
        Path(word).name == 'edi_app' for word in tokens[1:]
    )
    return source or explicit or target


def bindings(tree, nodes=None):
    return {
        target.id: node.value
        for node in (ast.walk(tree) if nodes is None else nodes)
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }


def launcher_names(tree):
    result = set(LAUNCHERS)
    nodes = tuple(ast.walk(tree))
    for node in nodes:
        if isinstance(node, ast.ImportFrom) and node.module in {'subprocess', 'os', 'asyncio'}:
            result.update(
                alias.asname or alias.name for alias in node.names if alias.name in LAUNCHERS
            )
        if isinstance(node, ast.Assign) and getattr(node.value, 'attr', '') in result:
            result.update(target.id for target in node.targets if isinstance(target, ast.Name))
    if not any(isinstance(node, ast.Call) and call_name(node) in result for node in nodes):
        return result
    # Derive the same transitive launcher set without repeatedly walking each body.
    calls_by_function = [
        (node.name, {call_name(call) for call in ast.walk(node) if isinstance(call, ast.Call)})
        for node in nodes
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    changed = True
    while changed:
        before = set(result)
        result.update(name for name, calls in calls_by_function if calls & result)
        changed = result != before
    return result


def call_name(node):
    return getattr(node.func, 'attr', getattr(node.func, 'id', ''))


def module_path(root, module, cache=None):
    key = (root, module)
    if cache is not None and key in cache:
        return cache[key]
    if not re.fullmatch(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*', module):
        return None
    path = root.joinpath(*module.split('.'))
    result = next(
        (p for p in (path.with_suffix('.py'), path / '__init__.py') if p.is_file()), None
    )
    if cache is not None:
        cache[key] = result
    return result


def imported_symbols(path, tree, root, cache):
    result = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            parent = path.parent
            for _ in range(max(0, node.level - 1)):
                parent = parent.parent
            base = parent if node.level else root
            target = module_path(base, node.module or '', cache)
            for alias in node.names:
                child = module_path(base, '.'.join(filter(None, (node.module, alias.name))), cache)
                if target or child:
                    result[alias.asname or alias.name] = (
                        child or target,
                        '*' if child else alias.name,
                    )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                target = module_path(root, alias.name, cache)
                if target:
                    result[alias.asname or alias.name.split('.')[0]] = (target, '*')
    return result


def selected_tree(tree, symbol):
    if symbol == '*':
        return tree
    if symbol == '@import':
        return ast.Module(
            body=[
                node
                for node in tree.body
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and not (isinstance(node, ast.If) and '__name__' in ast.unparse(node.test))
            ],
            type_ignores=[],
        )
    parts = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and node.name == symbol
    ]
    # Module initialization is visited once through @import; globals remain in bindings.
    return ast.Module(body=parts, type_ignores=[])


def process_dependencies(words, root, index):
    dependencies = []
    for word in words:
        if len(word) > 512 or '\n' in word or '\x00' in word:
            continue
        candidate = Path(word)
        if candidate.suffix in {'.py', '.sh', '.mjs', '.js'}:
            exact = candidate if candidate.is_absolute() else root / candidate
            candidates = [exact] if exact.is_file() else index.get(candidate.name, [])
            dependencies.extend((path, '*') for path in candidates)
        module = module_path(root, word, index['_modules'])
        if module:
            dependencies.append((module, '*'))
    return dependencies


def guarded_call(call, parents, imports, root):
    node = call
    trusted = root / 'tests/fixtures/fast_ci/processes.py'
    while node in parents:
        node = parents[node]
        if not isinstance(node, ast.With):
            continue
        for item in node.items:
            expression = item.context_expr
            if isinstance(expression, ast.Call):
                target = imports.get(call_name(expression))
                if target == (trusted, 'process_guard'):
                    return True
    return False


def cached_python(path, root, index):
    if path not in index['_python']:
        full = ast.parse(path.read_text())
        imports = imported_symbols(path, full, root, index['_modules'])
        trusted = (root / 'tests/fixtures/fast_ci/processes.py', 'process_guard')
        parents = (
            {child: parent for parent in ast.walk(full) for child in ast.iter_child_nodes(parent)}
            if trusted in imports.values()
            else {}
        )
        index.setdefault('_launchers', {})[path] = launcher_names(full)
        functions = {
            n.name
            for n in full.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        }
        globals_ = bindings(
            ast.Module(body=[n for n in full.body if isinstance(n, ast.Assign)], type_ignores=[])
        )
        index['_python'][path] = full, parents, imports, functions, globals_
    return index['_python'][path]


def python_routes(path, symbol, root, index):
    full, parents, imports, functions, globals_ = cached_python(path, root, index)
    tree = selected_tree(full, symbol)
    sites, dependencies = [], []
    if symbol not in {'*', '@import'}:
        dependencies.append((path, '@import'))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            dependencies.extend(
                (imports[alias.asname or alias.name.split('.')[0]][0], '@import')
                for alias in node.names
                if (alias.asname or alias.name.split('.')[0]) in imports
            )
    for scope in tree.body:
        nodes = tuple(ast.walk(scope))
        local = {**globals_, **bindings(scope, nodes)}
        for call in (n for n in nodes if isinstance(n, ast.Call)):
            name = call_name(call)
            alias = getattr(getattr(call.func, 'value', None), 'id', name)
            if name in functions:
                dependencies.append((path, name))
            if alias in imports:
                target, imported = imports[alias]
                dependencies.append((target, name if imported == '*' else imported))
            if name in index['_launchers'][path] and not guarded_call(
                call, parents, imports, root
            ):
                words = [
                    word
                    for arg in [*call.args, *(k.value for k in call.keywords)]
                    for word in strings(arg, local)
                ]
                if app_command(words):
                    sites.append(f'{path.relative_to(root)}:{call.lineno}')
                dependencies.extend(process_dependencies(words, root, index))
    return sites, dependencies


def script_routes(path, root, index):
    text = path.read_text()
    text = re.sub(r'(?m)^\s*#.*$|//[^\n]*|/\*.*?\*/', '', text, flags=re.DOTALL)
    dependencies = []
    sites = []
    if path.suffix == '.sh':
        for line in text.splitlines():
            if app_command([line]):
                sites.append(f'{path.relative_to(root)}:shell')
            dependencies.extend(process_dependencies(command_tokens(line), root, index))
    else:
        literals = re.findall(r"['\"]([^'\"]+)['\"]", text)
        dependencies.extend(process_dependencies(literals, root, index))
        aliases = re.findall(r'(?:spawn(?:Sync)?|exec(?:File)?(?:Sync)?)\s+as\s+(\w+)', text)
        launchers = r'spawn(?:Sync)?|exec(?:File)?(?:Sync)?' + ''.join(
            '|' + alias for alias in aliases
        )
        declared = {
            name: re.findall(r"['\"]([^'\"]+)['\"]", value)
            for name, value in re.findall(
                r'(?:const|let|var)\s+(\w+)\s*=\s*(\[[^;]+|[^;]+);', text
            )
        }
        for call in re.finditer('(?:' + launchers + r')\s*\((.*?)\)', text, re.DOTALL):
            words = re.findall(r"['\"]([^'\"]+)['\"]", call[1])
            for name in re.findall(r'\b\w+\b', call[1]):
                if name in declared:
                    words.extend(declared[name])
            if app_command(words):
                sites.append(f'{path.relative_to(root)}:process')
    return sites, dependencies


def app_build_sites(root, entrypoints=None):
    root = Path(root)
    candidates = [
        p
        for folder in ('tests', 'tools')
        for p in (root / folder).rglob('*')
        if p.is_file() and p.suffix in {'.py', '.sh', '.mjs', '.js'}
    ]
    index = {'_modules': {}, '_python': {}}
    for path in candidates:
        index.setdefault(path.name, []).append(path)
    entries = pr_paths(root) if entrypoints is None else list(entrypoints)
    if not entries and not (root / 'tests/test-groups.json').exists():
        entries = [p for p in candidates if p.is_relative_to(root / 'tests/fixtures')]
    pending = [(Path(path), '*') for path in entries]
    pending.extend(pytest_routes(entries, root, index))
    visited, sites = set(), []
    while pending:
        path, symbol = pending.pop()
        key = (path.resolve(), symbol)
        if key in visited or (path.resolve(), '*') in visited or not path.is_relative_to(root):
            continue
        visited.add(key)
        if path.suffix == '.py':
            found, routes = python_routes(path, symbol, root, index)
        else:
            found, routes = script_routes(path, root, index)
        sites.extend(found)
        pending.extend(routes)
    return sorted(set(sites))


def pytest_registration(path, root, index):
    cache = index.setdefault('_pytest', {})
    if path in cache:
        return cache[path]
    full, _, imported, _, _ = cached_python(path, root, index)
    fixtures, autouse, hooks = dict(imported), set(), set()
    for node in full.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            target = decorator.func if isinstance(decorator, ast.Call) else decorator
            if getattr(target, 'attr', getattr(target, 'id', '')) != 'fixture':
                continue
            fixtures[node.name] = (path, node.name)
            if isinstance(decorator, ast.Call) and any(
                k.arg == 'autouse' and isinstance(k.value, ast.Constant) and k.value.value is True
                for k in decorator.keywords
            ):
                autouse.add(node.name)
        if node.name.startswith('pytest_'):
            hooks.add((path, node.name))
    cache[path] = fixtures, autouse, hooks
    return cache[path]


def pytest_routes(entries, root, index):
    """Pytest calls ancestor hooks/autouse and the selected tests' requested fixtures."""
    pending = []
    for entry in entries:
        if entry.suffix != '.py':
            continue
        ancestors = [
            parent / 'conftest.py'
            for parent in entry.parents
            if parent.is_relative_to(root / 'tests')
        ]
        modules = [path for path in [*reversed(ancestors), entry] if path.is_file()]
        fixtures, requested = {}, set()
        for path in modules:
            definitions, automatic, hooks = pytest_registration(path, root, index)
            fixtures.update(definitions)
            requested.update(automatic)
            pending.extend(hooks)
            pending.append((path, '@import'))
        for node in ast.walk(cached_python(entry, root, index)[0]):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
                'test_'
            ):
                requested.update(arg.arg for arg in node.args.args)
            if isinstance(node, ast.Call) and call_name(node) == 'usefixtures':
                requested.update(value for arg in node.args for value in strings(arg, {}))
        visited = set()
        while requested - visited:
            name = (requested - visited).pop()
            visited.add(name)
            if name not in fixtures:
                continue
            path, symbol = fixtures[name]
            pending.append((path, symbol))
            for node in cached_python(path, root, index)[0].body:
                if (
                    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name == symbol
                ):
                    requested.update(arg.arg for arg in node.args.args)
    return pending
