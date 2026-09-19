import ast
from collections.abc import Iterable

from openfield.models import Finding, Rule, SourceSpan


def finding_id(rule: Rule, relative_path: str, line: int) -> str:
    return f"{rule.id}:{relative_path}:{line}"


def _shadowed_in_enclosing_function(tree: ast.AST, call: ast.Call, name: str) -> bool:
    functions = (
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))
        and node.lineno <= call.lineno
        and (node.end_lineno or node.lineno) >= (call.end_lineno or call.lineno)
    )
    function = min(
        functions,
        key=lambda node: (node.end_lineno or node.lineno) - node.lineno,
        default=None,
    )
    if function is None:
        return False

    arguments = function.args
    parameters = {
        argument.arg
        for argument in (*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs)
    }
    if arguments.vararg:
        parameters.add(arguments.vararg.arg)
    if arguments.kwarg:
        parameters.add(arguments.kwarg.arg)
    return name in parameters or any(
        isinstance(node, ast.Name) and node.id == name and isinstance(node.ctx, ast.Store)
        for node in ast.walk(function)
    )


def analyze_source(
    source: str,
    relative_path: str,
    rules: Iterable[Rule],
) -> tuple[list[Finding], list[str]]:
    try:
        tree = ast.parse(source, filename=relative_path)
    except SyntaxError as exc:
        return [], [f"{relative_path}: syntax error at line {exc.lineno}"]

    module_aliases: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "httpx":
                    module_aliases[alias.asname or alias.name] = "httpx"

    findings: list[Finding] = []
    rule_by_key = {
        (qualified_name, rule.keyword): rule
        for rule in rules
        for qualified_name in rule.qualified_names
    }

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if not isinstance(node.func.value, ast.Name):
            continue
        module = node.func.value.id
        if module not in module_aliases or _shadowed_in_enclosing_function(tree, node, module):
            continue
        symbol = f"{module_aliases[module]}.{node.func.attr}"
        keywords = {keyword.arg for keyword in node.keywords if keyword.arg is not None}
        for keyword in keywords:
            rule = rule_by_key.get((symbol, keyword))
            if rule is None:
                continue
            findings.append(
                Finding(
                    id=finding_id(rule, relative_path, node.lineno),
                    rule_id=rule.id,
                    span=SourceSpan(
                        path=relative_path,
                        line=node.lineno,
                        end_line=node.end_lineno or node.lineno,
                    ),
                    symbol=symbol,
                    keyword=keyword,
                    impact=rule.impact,
                    evidence="reviewed-rule/direct-call-match",
                    source_url=rule.source_url,
                    suggestion=rule.suggestion,
                )
            )
    return sorted(findings, key=lambda item: (item.span.path, item.span.line, item.rule_id)), []
