"""Bounded Actions condition seam: supported atoms only, no invented reachability."""

import ast
import json
import math
import re
from pathlib import Path


def event_ref(event):
    return 'refs/pull/75/merge' if event == 'pull_request' else 'refs/heads/main'


def active(  # noqa: PLR0913 - each keyword is one workflow context input
    node,
    event,
    ref=None,
    outputs=None,
    states=None,
    *,
    core_only=False,
    repository='enhantica/edi',
    fork=False,
    repository_private=False,
    cancelled=False,
):
    ref = event_ref(event) if ref is None else ref
    value = node.get('if', 'success()')
    if isinstance(value, bool):
        value = 'true' if value else 'false'
    value = str(value).strip().removeprefix('${{').removesuffix('}}').strip()
    # Before: every status function assumed a successful, uncancelled run. After:
    # the caller supplies preceding job results and actual run cancellation. GitHub
    # applies success() implicitly unless the condition includes a status function.
    has_status = re.search(r'\b(?:success|failure|cancelled|always)\(\)', value)
    if not has_status:
        value = f'success() && ({value})'
    # Unknown atoms refuse instead of pretending the workflow executed them.
    values = {
        'github.event_name': event,
        'inputs.core_only': core_only,
        'github.repository': repository,
        'github.event.repository.private': repository_private,
        'github.event.pull_request.head.repo.fork': fork if event == 'pull_request' else '',
        'github.event.pull_request.head.repo.full_name': ('outside/edi' if fork else repository)
        if event == 'pull_request'
        else '',
        'github.ref': ref,
        'github.event.schedule': '17 3 * * *' if event == 'schedule' else '',
        'needs.edi-verification.outputs.paired': 'true' if event == 'pull_request' else 'false',
    }
    for (ident, key), item in (outputs or {}).items():
        values[
            'steps.' + ident + ('.' if key in {'outcome', 'conclusion'} else '.outputs.') + key
        ] = item
    for ident, item in (states or {}).items():
        values['needs.' + ident + '.result'] = item
    for name, item in values.items():
        value = re.sub(r'\b' + re.escape(name) + r'\b', repr(item), value)
    for name, item in [
        ('cancelled', cancelled),
        ('success', not cancelled and all(s == 'success' for s in (states or {}).values())),
        ('failure', any(s == 'failure' for s in (states or {}).values())),
        ('always', True),
    ]:
        value = value.replace(name + '()', str(item))
    value = value.replace('&&', ' and ').replace('||', ' or ')
    value = re.sub(r'!(?!=)', ' not ', value)
    value = re.sub(r'\btrue\b', 'True', value)
    value = re.sub(r'\bfalse\b', 'False', value)
    try:
        parsed = ast.parse(value.strip(), mode='eval')
    except SyntaxError as error:
        message = ' workflow condition is outside the bounded supported shape'
        raise AssertionError(message) from error
    assert all(
        isinstance(
            n,
            (
                ast.Expression,
                ast.BoolOp,
                ast.And,
                ast.Or,
                ast.UnaryOp,
                ast.Not,
                ast.Compare,
                ast.Eq,
                ast.NotEq,
                ast.Constant,
            ),
        )
        for n in ast.walk(parsed)
    ), ' workflow condition must be resolved from the actual event and preceding outputs'
    return bool(condition_value(parsed.body))


def condition_value(node):
    """GitHub's documented loose equality; unsupported AST atoms still refuse."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not condition_value(node.operand)
    if isinstance(node, ast.BoolOp):
        values = [condition_value(item) for item in node.values]
        return all(values) if isinstance(node.op, ast.And) else any(values)
    if isinstance(node, ast.Compare):
        left = condition_value(node.left)
        for operator, right_node in zip(node.ops, node.comparators, strict=True):
            right = condition_value(right_node)
            equal = actions_equal(left, right)
            if equal != isinstance(operator, ast.Eq):
                return False
            left = right
        return True
    raise AssertionError('workflow condition atom must belong to the bounded declared grammar')


def actions_equal(left, right):
    if isinstance(left, str) and isinstance(right, str):
        return left.casefold() == right.casefold()
    if type(left) is type(right):
        return left == right

    def number(value):
        if value is None or (isinstance(value, str) and not value):
            return 0
        if isinstance(value, (bool, int, float)):
            return float(value)
        try:
            parsed = json.loads(value)
        except (ValueError, TypeError):
            return math.nan
        return float(parsed) if type(parsed) in {int, float} else math.nan

    return number(left) == number(right)


def reached(node, event, ref=None, outputs=None, states=None, **context):
    assert active(node, event, ref, outputs, states, **context), (
        ' required workflow route must execute under its real job and step conditions'
    )
    assert not node.get('continue-on-error'), ' required workflow failure must propagate'


def workflow_cwd(job, step, repo, resolve):
    value = step.get(
        'working-directory', job.get('defaults', {}).get('run', {}).get('working-directory', '.')
    )
    value = resolve(value)
    assert '${{' not in value, ' working directory must resolve the actual workflow expression'
    path = Path(value)
    path = path if path.is_absolute() else repo / path
    assert path.resolve() == repo.resolve(), (
        ' bounded replay cannot silently repair a foreign workflow working directory'
    )
    return path


def workflow_env(job, step, base, resolve):
    env = {
        **base,
        **{k: resolve(v) for k, v in job.get('env', {}).items()},
        **{k: resolve(v) for k, v in step.get('env', {}).items()},
    }
    assert all('${{' not in str(v) for v in env.values()), (
        ' workflow environment must resolve each actual expression'
    )
    assert all(
        env.get(k) == v for k, v in base.items() if k.startswith('GITHUB_') and k != 'GITHUB_TOKEN'
    ), ' workflow environment cannot override independently observed GitHub event coordinates'
    return env
