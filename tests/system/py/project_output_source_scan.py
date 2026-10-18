"Project output primitives belong to the shared output implementation."

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TOKEN = re.compile(
    r'R"([^ ()\\\t\r\n]{0,16})\([\s\S]*?\)\1"'
    r'|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''
    r'|//[^\n]*|/\*[\s\S]*?\*/|[A-Za-z_]\w*|::|[^\s]'
)

TYPES = {
    'ofstream',
    'wofstream',
    'basic_ofstream',
    'fstream',
    'wfstream',
    'basic_fstream',
    'QSaveFile',
    'QPdfWriter',
}
FLAGS = {
    'O_CREAT',
    'O_WRONLY',
    'O_RDWR',
    '_O_CREAT',
    '_O_WRONLY',
    '_O_RDWR',
    '_O_APPEND',
    'O_APPEND',
    'WriteOnly',
    'ReadWrite',
    'Append',
}
CALLS = {
    'fwrite',
    'fputs',
    'fputc',
    'fprintf',
    'fflush',
    'write',
    'pwrite',
    'writev',
    '_write',
    'unlink',
    'unlinkat',
    '_unlink',
    '_wunlink',
    'rename',
    'renameat',
    'renameat2',
    '_wrename',
    'remove',
    'remove_all',
    'copy_file',
    'copy_symlink',
    'create_directories',
    'create_directory',
    'resize_file',
    'truncate',
    'ftruncate',
    'link',
    'symlink',
    'mkdir',
    'rmdir',
    'creat',
    '_creat',
}
PY_METHODS = {
    'write_text',
    'write_bytes',
    'unlink',
    'rename',
    'replace',
    'mkdir',
    'touch',
    'rmdir',
    'write',
    'writelines',
    'truncate',
}
PY_FUNCTIONS = {
    'copy',
    'copy2',
    'copyfile',
    'copytree',
    'rmtree',
    'remove',
    'unlink',
    'rename',
    'replace',
    'mkdir',
    'makedirs',
    'rmdir',
    'removedirs',
    'write',
    'pwrite',
    'move',
    'copy_into',
    'move_into',
    'link',
    'symlink',
    'symlink_to',
    'hardlink_to',
}


def cpp_tokens(source):
    source = re.sub(r'(?m)^\s*#\s*include[^\n]*', '', source)
    return [
        match.group()
        for match in TOKEN.finditer(source)
        if not match.group().startswith(('//', '/*'))
    ]


def without_functions(atoms, names):
    result = list(atoms)
    for index, atom in enumerate(atoms):
        if atom not in names or index + 1 >= len(atoms) or atoms[index + 1] != '(':
            continue
        depth = 0
        end = index + 1
        for end in range(index + 1, len(atoms)):
            depth += atoms[end] == '('
            depth -= atoms[end] == ')'
            if depth == 0:
                break
        if end + 1 >= len(atoms) or atoms[end + 1] != '{':
            continue
        depth = 1
        finish = end + 2
        while finish < len(atoms) and depth:
            depth += atoms[finish] == '{'
            depth -= atoms[finish] == '}'
            finish += 1
        expected = cpp_tokens(
            'std::ofstream out(args.out);'
            if atom == 'write_results'
            else 'std::ofstream out(out_path);'
        )
        for start in range(end + 2, finish - len(expected) + 1):
            if atoms[start : start + len(expected)] == expected:
                result[start : start + len(expected)] = [''] * len(expected)
    return result


def diagnostic_call(atoms, index):
    depth = 0
    arguments = []
    for end in range(index + 2, len(atoms)):
        if atoms[end] == ')' and depth == 0:
            break
        depth += atoms[end] == '('
        depth -= atoms[end] == ')'
        arguments.append(atoms[end])
    return any(
        item in {'stderr', 'stdout', 'STDOUT_FILENO', 'STDERR_FILENO'} for item in arguments
    )


def unsafe_open(atoms, index):
    name = atoms[index]
    if name not in {'open', 'open64', 'fopen', 'fopen64', 'freopen', '_wopen', '_wfopen'}:
        return False
    if index + 1 >= len(atoms) or atoms[index + 1] != '(':
        return True
    if name not in {'fopen', 'fopen64', 'freopen', '_wfopen'}:
        return False
    end = index + 2
    depth = 0
    while end < len(atoms):
        if atoms[end] == ',' and depth == 0:
            break
        depth += atoms[end] == '('
        depth -= atoms[end] == ')'
        end += 1
    mode = atoms[end + 1] if end + 1 < len(atoms) else ''
    return not re.fullmatch(r'(?:L)?"r(?:b)?"', mode)


def cpp_violations(source, excluded=(), *, sites=False):
    atoms = without_functions(cpp_tokens(source), excluded)
    aliases = dict(re.findall(r'namespace\s+(\w+)\s*=\s*([\w:]+)\s*;', source))
    safe_aliases = {name for name, target in aliases.items() if target == 'crysta::output'}
    filesystem_aliases = {'fs', 'filesystem', 'QFile'} | {
        name for name, target in aliases.items() if target == 'std::filesystem'
    }
    violations = []
    for index, atom in enumerate(atoms):
        if atom in TYPES or atom in FLAGS:
            violations.append((index, atom))
        if atom in {'out', 'app', 'trunc'} and index and atoms[index - 1] == '::':
            violations.append((index, atom))
        call = index + 1 < len(atoms) and atoms[index + 1] == '('
        prefix = ''.join(atoms[max(0, index - 5) : index])
        reference = (
            call
            or prefix.endswith('::')
            or (index > 0 and atoms[index - 1] == '=' and atom not in {'link', 'symlink'})
        )
        if (
            atom in CALLS
            and reference
            and not (
                prefix.endswith('crysta::output::')
                or any(prefix.endswith(alias + '::') for alias in safe_aliases)
            )
        ):
            if (
                call
                and atom in {'fprintf', 'fputs', 'fputc', 'fflush', 'fwrite', 'write'}
                and diagnostic_call(atoms, index)
            ):
                continue
            violations.append((index, atom))
        if atom == 'copy' and any(prefix.endswith(alias + '::') for alias in filesystem_aliases):
            violations.append((index, atom))
        if unsafe_open(atoms, index):
            violations.append((index, atom))
    return violations if sites else [atom for _, atom in violations]


def python_write_open(node, name, aliases, owner):
    if name not in {'open', 'fdopen'}:
        return False
    method = isinstance(node.func, ast.Attribute) and owner not in {'os', 'io'}
    alias = isinstance(node.func, ast.Name) and node.func.id in aliases
    mode = list(node.args[0 if method or alias else 1 :])
    mode += [kw.value for kw in node.keywords if kw.arg == 'mode']
    return any(
        isinstance(item, ast.Constant)
        and isinstance(item.value, str)
        and any(flag in item.value for flag in 'wax+')
        for item in mode
    )


def python_aliases(tree):
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            aliases.update({item.asname or item.name: item.name for item in node.names})
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Attribute):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    aliases[target.id] = node.value.attr
    return aliases


def python_violations(source):
    tree = ast.parse(source)
    aliases = python_aliases(tree)
    result = []
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.Attribute, ast.Name))
            and (node.attr if isinstance(node, ast.Attribute) else node.id) in FLAGS
        ):
            result.append((node.lineno, 'writable-open-flag'))
        if not isinstance(node, ast.Call):
            continue
        callee = node.func
        name = (
            callee.attr
            if isinstance(callee, ast.Attribute)
            else callee.id
            if isinstance(callee, ast.Name)
            else ''
        )
        name = aliases.get(name, name)
        owner = (
            callee.value.id
            if isinstance(callee, ast.Attribute) and isinstance(callee.value, ast.Name)
            else ''
        )
        if name in PY_METHODS | PY_FUNCTIONS:
            # str.replace is a text operation; Path.replace takes only one path operand.
            if name == 'replace' and len(node.args) >= 2:
                continue
            if isinstance(callee, ast.Attribute) and ast.unparse(callee.value) in {
                'sys.stderr',
                'sys.stdout',
            }:
                continue
            result.append((node.lineno, name))
        if python_write_open(node, name, aliases, owner):
            result.append((node.lineno, name))
    return result


def scan(root=ROOT):
    contract = json.loads((ROOT / 'tests/fixtures/project_output/contract.json').read_text())
    operations = json.loads(
        (ROOT / 'tests/fixtures/project_output/non_project_operations.json').read_text()
    )
    files = set(contract['project_output'])
    for folder in contract['roots']:
        files.update(
            str(path.relative_to(root))
            for path in (root / folder).rglob('*')
            if path.suffix in {'.cpp', '.hpp', '.h', '.py'}
        )
    result = []
    for name in sorted(files - set(contract['helpers'])):
        path = root / name
        if not path.is_file():
            result.append((name, 'missing project output source'))
            continue
        excluded = (
            {'write_results', 'write_joint_results'} if name == 'src/cli/main.cpp' else set()
        )
        source = path.read_text()
        permitted = [item for item in operations if item['source'] == name]
        if path.suffix == '.py':
            violations = python_violations(source)
        else:
            atoms = without_functions(cpp_tokens(source), excluded)
            allowed = set()
            for item in permitted:
                context = cpp_tokens(item['context'])
                matches = [
                    index + item['offset']
                    for index in range(len(atoms) - len(context) + 1)
                    if atoms[index : index + len(context)] == context
                ]
                allowed.update(matches[: item['limit']])
            violations = [
                atom
                for index, atom in cpp_violations(source, excluded, sites=True)
                if index not in allowed
            ]
        result.extend((name, problem) for problem in violations)
    return result
