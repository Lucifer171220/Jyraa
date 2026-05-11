import ast
import json
import os
import re
from collections import Counter
from dataclasses import dataclass
from statistics import mean
from typing import Any, Dict, List
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models import BugReport, CodeReview
from app.services.code_review_rules import (
    DEFAULT_SCORE_POLICY,
    GENERATED_FILE_SCORE_POLICY,
    GENERATED_FILE_SUFFIXES,
    GENERATED_PATH_FRAGMENTS,
    GITIGNORE_SUGGESTION_RULES,
    IGNORED_PATH_FRAGMENTS,
    LANGUAGE_BY_EXTENSION,
    LANGUAGE_SCORE_POLICIES,
    TEXT_FILE_EXTENSIONS,
)
from app.services.ollama_service import generate_response

try:
    import httpx
except ImportError:  # pragma: no cover - optional dependency fallback
    httpx = None

SECURITY_PATTERNS = {
    "sql_injection": {
        "pattern": r'(execute|executemany|raw)\s*\(\s*["\'].*(%s|\{).*(["\'])',
        "severity": "critical",
        "message": "Possible SQL injection vulnerability detected",
    },
    "hardcoded_password": {
        "pattern": r'(password|passwd|pwd|secret|token|api_?key|auth)\s*[=:]\s*["\'][^"\']{8,}["\']',
        "severity": "high",
        "message": "Hardcoded password detected",
    },
    "xss_vulnerability": {
        "pattern": r'(innerHTML|outerHTML)\s*=',
        "severity": "high",
        "message": "Possible XSS vulnerability",
    },
}

STANDARD_PATTERNS = {
    "console_log": {
        "pattern": r'console\.(log|debug|info)\s*\(',
        "severity": "low",
        "message": "Console statement should be removed in production",
    },
    "eval_usage": {
        "pattern": r'\beval\s*\(',
        "severity": "high",
        "message": "Use of eval detected",
    },
}

SECURITY_REVIEW_RULES = {
    **SECURITY_PATTERNS,
    "command_injection": {
        "pattern": r"(subprocess\.(run|Popen)|exec|system|Runtime\.getRuntime\(\)\.exec)\s*\(",
        "severity": "high",
        "message": "Potential command execution surface detected",
    },
    "weak_crypto": {
        "pattern": r"\b(md5|sha1)\b",
        "severity": "medium",
        "message": "Weak cryptographic primitive detected",
    },
    "insecure_random": {
        "pattern": r"(Math\.random\(|random\.random\()",
        "severity": "medium",
        "message": "Non-cryptographic randomness used; verify this is safe",
    },
    "dangerously_set_html": {
        "pattern": r"(dangerouslySetInnerHTML|v-html)",
        "severity": "high",
        "message": "Unsafe HTML rendering surface detected",
    },
    "debug_mode": {
        "pattern": r"(debug\s*=\s*True|DEBUG\s*=\s*True|app\.run\(.*debug\s*=\s*True)",
        "severity": "medium",
        "message": "Debug mode enabled in source",
    },
}
QUALITY_REVIEW_RULES = {
    **STANDARD_PATTERNS,
    "todo_marker": {
        "pattern": r"\b(TODO|FIXME|HACK)\b",
        "severity": "info",
        "message": "Work-in-progress marker detected",
    },
    "merge_conflict_marker": {
        "pattern": r"^(<<<<<<<|=======|>>>>>>>).*$",
        "severity": "critical",
        "message": "Merge conflict marker found",
    },
}


@dataclass
class SchemaDefinition:
    name: str
    required_fields: set[str]
    optional_fields: set[str]


@dataclass
class PythonReviewContext:
    schema_definitions: dict[str, SchemaDefinition]
    file_contents: dict[str, str]


@dataclass
class GitignoreSuggestion:
    path: str
    message: str


def analyze_code_from_github(
    db: Session,
    pr_id: int,
    repository_url: str,
    github_pr_number: int,
    github_token: str | None = None,
):
    findings: List[Dict] = []
    files = _fetch_pr_files(repository_url, github_pr_number, github_token)
    for file in files:
        file_findings = _analyze_file(file["path"], file["content"])
        findings.extend([{**finding, "file_path": file["path"]} for finding in file_findings])
        for finding in file_findings:
            db.add(
                CodeReview(
                    pr_id=pr_id,
                    file_path=file["path"],
                    line_number=finding.get("line"),
                    severity=finding["severity"],
                    message=finding["message"],
                    rule_id=finding.get("rule_id"),
                )
            )
    db.commit()
    return _calculate_health_score(findings), findings


def create_bugs_from_findings(db: Session, pr_id: int, findings: List[Dict], issue_id: int) -> List[BugReport]:
    bugs: List[BugReport] = []
    for finding in findings:
        if finding["severity"] not in {"critical", "high"}:
            continue
        bug = BugReport(
            pr_id=pr_id,
            issue_id=issue_id,
            severity=finding["severity"],
            description=finding["message"],
            code_location=f'{finding.get("file_path", "")}:{finding.get("line", "")}'.rstrip(":"),
            suggestion=f"Investigate rule {finding.get('rule_id', 'unknown')} and patch the affected code path.",
        )
        db.add(bug)
        bugs.append(bug)
    db.commit()
    return bugs


def _analyze_file(file_path: str, content: str) -> List[Dict]:
    findings: List[Dict] = []
    all_rules = {**SECURITY_REVIEW_RULES, **QUALITY_REVIEW_RULES}
    for rule_id, rule in all_rules.items():
        for match in re.finditer(rule["pattern"], content, re.IGNORECASE):
            line = content[: match.start()].count("\n") + 1
            findings.append(
                {
                    "severity": rule["severity"],
                    "message": rule["message"],
                    "rule_id": rule_id,
                    "line": line,
                }
            )
    return findings


def _calculate_health_score(findings: List[Dict]) -> float:
    score = 100.0
    weights = {"critical": 15, "high": 10, "medium": 5, "low": 2, "info": 0.5}
    for finding in findings:
        score -= weights.get(finding["severity"], 1)
    return max(0.0, min(100.0, score))


def _severity_weight(severity: str) -> float:
    return {"critical": 15, "high": 10, "medium": 5, "low": 2, "info": 0.5}.get(severity, 1)


def _score_to_percent(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)


def _detect_language(file_path: str) -> str:
    _, extension = os.path.splitext(file_path.lower())
    return LANGUAGE_BY_EXTENSION.get(extension, "Unknown")


def _normalized_path(file_path: str) -> str:
    return file_path.replace("\\", "/").lower()


def _is_generated_file(file_path: str, content: str = "") -> bool:
    normalized = _normalized_path(file_path)
    base_name = os.path.basename(normalized)
    if any(fragment in normalized for fragment in GENERATED_PATH_FRAGMENTS):
        return True
    if any(base_name.endswith(suffix) for suffix in GENERATED_FILE_SUFFIXES):
        return True
    generated_markers = ("<auto-generated", "@generated", "generated code", "do not modify this code")
    return any(marker in content.lower() for marker in generated_markers)


def _get_score_policy(file_path: str, content: str = ""):
    if _is_generated_file(file_path, content):
        return GENERATED_FILE_SCORE_POLICY
    return LANGUAGE_SCORE_POLICIES.get(_detect_language(file_path), DEFAULT_SCORE_POLICY)


def _collect_gitignore_suggestions(files: List[Dict[str, str]]) -> List[Dict[str, str]]:
    suggestions: list[GitignoreSuggestion] = []
    seen_paths: set[str] = set()

    for file in files:
        normalized = _normalized_path(file["path"])
        if normalized in seen_paths:
            continue
        for rule in GITIGNORE_SUGGESTION_RULES:
            if rule["pattern"] in normalized:
                suggestions.append(GitignoreSuggestion(path=file["path"], message=rule["message"]))
                seen_paths.add(normalized)
                break

    return [{"path": item.path, "message": item.message} for item in suggestions[:25]]


def _field_has_default(node: ast.AST) -> bool:
    if isinstance(node, ast.AnnAssign):
        return node.value is not None
    if isinstance(node, ast.Assign):
        return True
    return False


def _extract_name(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_pydantic_model(class_node: ast.ClassDef) -> bool:
    for base in class_node.bases:
        if _extract_name(base) == "BaseModel":
            return True
    return False


def _build_python_review_context(files: List[Dict[str, str]]) -> PythonReviewContext:
    schema_definitions: dict[str, SchemaDefinition] = {}
    file_contents = {file["path"]: file["content"] for file in files}

    for file in files:
        if not file["path"].lower().endswith(".py"):
            continue
        try:
            tree = ast.parse(file["content"])
        except SyntaxError:
            continue

        for node in tree.body:
            if not isinstance(node, ast.ClassDef) or not _is_pydantic_model(node):
                continue

            required_fields: set[str] = set()
            optional_fields: set[str] = set()
            for statement in node.body:
                if isinstance(statement, (ast.AnnAssign, ast.Assign)):
                    target = statement.target if isinstance(statement, ast.AnnAssign) else statement.targets[0]
                    field_name = _extract_name(target)
                    if not field_name:
                        continue
                    if _field_has_default(statement):
                        optional_fields.add(field_name)
                    else:
                        required_fields.add(field_name)

            schema_definitions[node.name] = SchemaDefinition(
                name=node.name,
                required_fields=required_fields,
                optional_fields=optional_fields,
            )

    return PythonReviewContext(schema_definitions=schema_definitions, file_contents=file_contents)


def _is_text_file(file_path: str) -> bool:
    lower = file_path.lower()
    if any(fragment in lower for fragment in IGNORED_PATH_FRAGMENTS):
        return False
    _, extension = os.path.splitext(lower)
    return extension in TEXT_FILE_EXTENSIONS


def _brace_balance_penalty(content: str, opening: str, closing: str) -> float:
    opens = content.count(opening)
    closes = content.count(closing)
    return abs(opens - closes) * 1.6


def _line_number(node: ast.AST, fallback: int = 1) -> int:
    return getattr(node, "lineno", fallback) or fallback


def _finding(rule_id: str, severity: str, message: str, line: int) -> Dict[str, Any]:
    return {
        "severity": severity,
        "message": message,
        "rule_id": rule_id,
        "line": line,
    }


def _collect_function_param_names(function_node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    names = {arg.arg for arg in function_node.args.args}
    names.update(arg.arg for arg in function_node.args.kwonlyargs)
    if function_node.args.vararg:
        names.add(function_node.args.vararg.arg)
    if function_node.args.kwarg:
        names.add(function_node.args.kwarg.arg)
    return names


def _find_schema_constructor_findings(
    tree: ast.AST,
    schema_definitions: dict[str, SchemaDefinition],
) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []

    class SchemaConstructorVisitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:
            model_name = None
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == "schemas":
                model_name = node.func.attr
            elif isinstance(node.func, ast.Name):
                model_name = node.func.id

            schema = schema_definitions.get(model_name or "")
            if not schema:
                self.generic_visit(node)
                return

            provided_keywords = {kw.arg for kw in node.keywords if kw.arg}
            unknown_fields = sorted(field for field in provided_keywords if field not in schema.required_fields and field not in schema.optional_fields)
            missing_required = sorted(field for field in schema.required_fields if field not in provided_keywords)

            if unknown_fields:
                findings.append(
                    _finding(
                        "schema_constructor_unknown_fields",
                        "high",
                        f"{model_name} is constructed with unknown field(s): {', '.join(unknown_fields)}",
                        _line_number(node),
                    )
                )
            if missing_required:
                findings.append(
                    _finding(
                        "schema_constructor_missing_required_fields",
                        "high",
                        f"{model_name} is missing required field(s): {', '.join(missing_required)}",
                        _line_number(node),
                    )
                )

            self.generic_visit(node)

    SchemaConstructorVisitor().visit(tree)
    return findings


def _route_lacks_ownership_check(function_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    param_names = _collect_function_param_names(function_node)
    if "current_user" not in param_names:
        return False

    source = ast.unparse(function_node)
    mutating_markers = ("db.commit()", ".status =", ".user_id =", ".assignee_user_id =", ".delete(", ".update(")
    if not any(marker in source for marker in mutating_markers):
        return False

    object_lookup_present = ".first()" in source or ".one_or_none()" in source or ".get(" in source
    if not object_lookup_present:
        return False

    ownership_markers = (
        "current_user.user_id",
        "current_user.username",
        "is_admin",
        "role",
        "permission",
        ".owner_id",
        ".user_id !=",
        ".user_id ==",
    )
    if any(marker in source for marker in ownership_markers):
        return False

    return True


def _find_authz_findings(tree: ast.AST) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _route_lacks_ownership_check(node):
            findings.append(
                _finding(
                    "missing_resource_ownership_check",
                    "high",
                    "Route mutates a looked-up resource with current_user present but no ownership or permission check was detected",
                    _line_number(node),
                )
            )
    return findings


def _find_action_lifecycle_findings(tree: ast.AST) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != "execute_actions":
            continue

        source = ast.unparse(node)
        if "AgentActionStatus.APPROVED.value" in source and 'action.result = {"status": "done"}' in source:
            success_status_updates = (
                "action.status = AgentActionStatus.DONE.value",
                'action.status = "done"',
                "action.status = AgentActionStatus.EXECUTED.value",
                'action.status = "executed"',
                "action.status = AgentActionStatus.COMPLETED.value",
                'action.status = "completed"',
            )
            if not any(marker in source for marker in success_status_updates):
                findings.append(
                    _finding(
                        "approved_action_not_finalized",
                        "medium",
                        "Approved actions are executed, but no terminal success status is set, so they may be replayed later",
                        _line_number(node),
                    )
                )
    return findings


def _python_semantic_findings(
    file_path: str,
    content: str,
    context: PythonReviewContext | None,
) -> List[Dict[str, Any]]:
    if not file_path.lower().endswith(".py"):
        return []

    try:
        tree = ast.parse(content)
    except SyntaxError as exc:
        return [
            _finding(
                "python_syntax_error",
                "critical",
                f"Python syntax error: {exc.msg}",
                getattr(exc, "lineno", 1) or 1,
            )
        ]

    findings: List[Dict[str, Any]] = []
    if context:
        findings.extend(_find_schema_constructor_findings(tree, context.schema_definitions))
    findings.extend(_find_authz_findings(tree))
    findings.extend(_find_action_lifecycle_findings(tree))
    return findings


def _find_duplicate_extension_filename(file_path: str) -> List[Dict[str, Any]]:
    base_name = os.path.basename(file_path.lower())
    parts = base_name.split(".")
    if len(parts) >= 3 and parts[-1] == parts[-2]:
        return [
            _finding(
                "duplicate_file_extension",
                "low",
                "Filename appears to contain a duplicated extension, which is often accidental",
                1,
            )
        ]
    return []


def _find_generic_exception_handling(file_path: str, content: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    generic_patterns = [
        (
            r"catch\s*\(\s*Exception\b[^\)]*\)\s*\{",
            "broad_exception_catch",
            "medium",
            "Broad exception catch detected; prefer handling narrower exception types where possible",
        ),
        (
            r"except\s+Exception\b[^\n:]*:",
            "broad_exception_catch",
            "medium",
            "Broad exception catch detected; prefer handling narrower exception types where possible",
        ),
    ]
    if _detect_language(file_path) not in {"C#", "Java", "Python", "JavaScript", "TypeScript", "PHP"}:
        return findings

    for pattern, rule_id, severity, message in generic_patterns:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            line = content[: match.start()].count("\n") + 1
            findings.append(_finding(rule_id, severity, message, line))
    return findings


def _extract_dotnet_route_params(route_template: str) -> set[str]:
    return set(re.findall(r"\{(\w+)(?::[^}]+)?\}", route_template))


def _extract_csharp_method_params(signature: str) -> list[str]:
    params_block_match = re.search(r"\((.*)\)", signature, re.DOTALL)
    if not params_block_match:
        return []
    raw_params = params_block_match.group(1).strip()
    if not raw_params:
        return []

    params: list[str] = []
    for chunk in raw_params.split(","):
        cleaned = re.sub(r"\[[^\]]+\]", "", chunk).strip()
        parts = [part for part in cleaned.split() if part]
        if not parts:
            continue
        name = parts[-1].strip()
        name = name.split("=")[0].strip()
        if name:
            params.append(name)
    return params


def _find_dotnet_route_mismatches(content: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    method_pattern = re.compile(
        r"(?P<attrs>(?:\s*\[[^\]]+\]\s*)+)\s*public\s+(?:async\s+)?[\w<>\[\],?\s]+\s+(?P<name>\w+)\s*\((?P<params>.*?)\)",
        re.DOTALL,
    )

    for match in method_pattern.finditer(content):
        attrs = match.group("attrs")
        params = _extract_csharp_method_params(match.group(0))
        line = content[: match.start()].count("\n") + 1
        route_params: set[str] = set()
        for attr_match in re.finditer(r'\[(Http\w+|Route)\("([^"]+)"\)\]', attrs):
            route_params.update(_extract_dotnet_route_params(attr_match.group(2)))

        if route_params:
            missing = sorted(name for name in route_params if name not in params)
            if missing:
                findings.append(
                    _finding(
                        "dotnet_route_parameter_mismatch",
                        "high",
                        f"Route template parameter(s) {', '.join(missing)} do not appear in the method signature",
                        line,
                    )
                )
    return findings


def _find_dotnet_error_leakage(content: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    pattern = r"return\s+BadRequest\s*\(\s*ex\.Message\s*\)"
    for match in re.finditer(pattern, content):
        line = content[: match.start()].count("\n") + 1
        findings.append(
            _finding(
                "dotnet_exception_message_leak",
                "medium",
                "Controller returns raw exception messages to clients, which can leak internal details",
                line,
            )
        )
    return findings


def _find_dotnet_response_dto_mismatches(content: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    method_pattern = re.compile(
        r"public\s+(?:async\s+)?Task<(?P<return>ActionResult<(?P<generic>\w+)>)>\s+(?P<name>\w+)\s*\((?P<params>.*?)\)\s*\{(?P<body>.*?)\n\s*\}",
        re.DOTALL,
    )
    return_pattern = re.compile(r"return\s+Ok\s*\(\s*(?P<value>\w+)\s*\)")
    decl_pattern = re.compile(r"var\s+(?P<name>\w+)\s*=\s*await\s+[^;]+;")

    for method in method_pattern.finditer(content):
        generic = method.group("generic")
        body = method.group("body")
        line = content[: method.start()].count("\n") + 1
        returned_names = [m.group("value") for m in return_pattern.finditer(body)]
        declared_vars = {m.group("name") for m in decl_pattern.finditer(body)}

        if not returned_names:
            continue
        for value_name in returned_names:
            if value_name in declared_vars and generic and generic not in value_name.lower():
                findings.append(
                    _finding(
                        "dotnet_response_type_mismatch",
                        "medium",
                        f"ActionResult<{generic}> returns `{value_name}`; verify the response DTO matches the declared action result type",
                        line,
                    )
                )
                break
    return findings


def _find_dotnet_semantic_findings(file_path: str, content: str) -> List[Dict[str, Any]]:
    normalized = _normalized_path(file_path)
    if _detect_language(file_path) != "C#":
        return []

    findings: List[Dict[str, Any]] = []
    if "/controllers/" in normalized:
        findings.extend(_find_dotnet_route_mismatches(content))
        findings.extend(_find_dotnet_error_leakage(content))
        findings.extend(_find_dotnet_response_dto_mismatches(content))
    return findings


def _find_javascript_console_noise(file_path: str, content: str) -> List[Dict[str, Any]]:
    if _detect_language(file_path) not in {"JavaScript", "TypeScript"}:
        return []

    findings: List[Dict[str, Any]] = []
    for match in re.finditer(r"console\.(log|debug|info)\s*\(", content):
        line = content[: match.start()].count("\n") + 1
        findings.append(
            _finding(
                "frontend_console_debugging_left_in_source",
                "low",
                "Console debugging call left in source; verify it should ship to production",
                line,
            )
        )
    return findings


def _find_react_html_injection(content: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for match in re.finditer(r"dangerouslySetInnerHTML\s*=\s*\{\s*\{", content):
        line = content[: match.start()].count("\n") + 1
        findings.append(
            _finding(
                "react_dangerous_html",
                "high",
                "React dangerous HTML injection detected; verify content is sanitized",
                line,
            )
        )
    return findings


def _find_react_missing_list_keys(content: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    map_pattern = re.compile(r"\.map\s*\(\s*\(?\s*[\w\s,]*\)?\s*=>\s*\(\s*<(?P<tag>\w+)(?P<body>[^>]*)>", re.DOTALL)
    for match in map_pattern.finditer(content):
        body = match.group("body")
        if "key=" in body:
            continue
        line = content[: match.start()].count("\n") + 1
        findings.append(
            _finding(
                "react_missing_list_key",
                "medium",
                "List rendered from `.map()` appears to be missing a `key` prop on the first JSX element",
                line,
            )
        )
    return findings


def _find_javascript_fetch_without_error_handling(content: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    fetch_pattern = re.compile(r"fetch\s*\(", re.MULTILINE)
    for match in fetch_pattern.finditer(content):
        line = content[: match.start()].count("\n") + 1
        surrounding = content[match.start(): match.start() + 400]
        if ".catch(" not in surrounding and "try {" not in surrounding and "catch (" not in surrounding:
            findings.append(
                _finding(
                    "javascript_fetch_without_error_handling",
                    "medium",
                    "Fetch call appears to lack nearby error handling",
                    line,
                )
            )
    return findings


def _find_javascript_effect_dependency_smells(content: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    effect_pattern = re.compile(r"useEffect\s*\(\s*\(\s*=>.*?\)\s*,\s*\[\s*\]\s*\)", re.DOTALL)
    for match in effect_pattern.finditer(content):
        snippet = match.group(0)
        if not any(token in snippet for token in ("fetch(", "props.", "state", "set", "useRef", "dispatch", ".")):
            continue
        line = content[: match.start()].count("\n") + 1
        findings.append(
            _finding(
                "react_effect_empty_dependencies_smell",
                "low",
                "useEffect with empty dependency array contains logic that may depend on changing values; verify dependencies",
                line,
            )
        )
    return findings


def _find_frontend_env_exposure(content: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for match in re.finditer(r"(process\.env\.[A-Z0-9_]+|import\.meta\.env\.[A-Z0-9_]+)", content):
        token = match.group(1)
        if any(prefix in token for prefix in ("REACT_APP_", "NEXT_PUBLIC_", "VITE_")):
            continue
        line = content[: match.start()].count("\n") + 1
        findings.append(
            _finding(
                "frontend_env_access_smell",
                "medium",
                "Frontend source accesses an env var without an obvious public-safe prefix; verify secrets are not exposed client-side",
                line,
            )
        )
    return findings


def _find_javascript_react_semantic_findings(file_path: str, content: str) -> List[Dict[str, Any]]:
    if _detect_language(file_path) not in {"JavaScript", "TypeScript"}:
        return []

    findings: List[Dict[str, Any]] = []
    findings.extend(_find_javascript_console_noise(file_path, content))
    findings.extend(_find_javascript_fetch_without_error_handling(content))
    findings.extend(_find_frontend_env_exposure(content))

    lower_path = file_path.lower()
    is_react_like = lower_path.endswith((".jsx", ".tsx")) or "usestate(" in content or "useeffect(" in content.lower() or "react" in content.lower()
    if is_react_like:
        findings.extend(_find_react_html_injection(content))
        findings.extend(_find_react_missing_list_keys(content))
        findings.extend(_find_javascript_effect_dependency_smells(content))
    return findings


def _semantic_findings(
    file_path: str,
    content: str,
    context: PythonReviewContext | None,
) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    findings.extend(_find_duplicate_extension_filename(file_path))
    findings.extend(_find_generic_exception_handling(file_path, content))
    findings.extend(_find_dotnet_semantic_findings(file_path, content))
    findings.extend(_find_javascript_react_semantic_findings(file_path, content))
    findings.extend(_python_semantic_findings(file_path, content, context))
    return findings


def _review_support_level(file_path: str, content: str = "") -> str:
    language = _detect_language(file_path)
    if _is_generated_file(file_path, content):
        return "generated"
    is_react_like = language in {"JavaScript", "TypeScript"} and (
        file_path.lower().endswith((".jsx", ".tsx"))
        or "usestate(" in content.lower()
        or "useeffect(" in content.lower()
        or "react" in content.lower()
    )
    if language in {"Python", "C#"} or is_react_like:
        return "specialized"
    if language in {"JavaScript", "TypeScript", "Java", "Go", "Rust", "PHP", "JSON", "YAML", ".NET Project", ".NET Solution"}:
        return "generic"
    return "limited"


def _apply_support_score_adjustment(
    support_level: str,
    syntax_score: float,
    implementation_score: float,
    security_score: float,
    findings: List[Dict[str, Any]],
) -> tuple[float, float, float]:
    if support_level == "specialized":
        return syntax_score, implementation_score, security_score
    if support_level == "generated":
        return min(syntax_score, 90.0), min(implementation_score, 82.0), min(security_score, 88.0)
    if support_level == "generic":
        floor_penalty = 2.5 if findings else 5.0
        return (
            min(syntax_score, 95.0),
            min(implementation_score - floor_penalty, 88.0),
            min(security_score - floor_penalty, 89.0),
        )
    floor_penalty = 5.0 if findings else 9.0
    return (
        min(syntax_score, 92.0),
        min(implementation_score - floor_penalty, 82.0),
        min(security_score - floor_penalty, 84.0),
    )


def _compute_syntax_score(file_path: str, content: str, findings: List[Dict[str, Any]]) -> float:
    policy = _get_score_policy(file_path, content)
    score = 100.0
    lines = content.splitlines()
    lower_path = file_path.lower()
    _, extension = os.path.splitext(lower_path)

    if any(finding.get("rule_id") == "merge_conflict_marker" for finding in findings):
        score -= 35

    if "\t" in content and extension in {".py", ".yml", ".yaml"}:
        score -= 3

    if extension in {".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".go", ".rs", ".c", ".cc", ".cpp", ".cxx", ".cs", ".php"}:
        score -= _brace_balance_penalty(content, "{", "}")
        score -= _brace_balance_penalty(content, "(", ")") * 0.5
        score -= _brace_balance_penalty(content, "[", "]") * 0.35
    elif extension in {".py"}:
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("def ", "class ", "if ", "elif ", "else", "for ", "while ", "try", "except", "with ")) and not stripped.endswith(":"):
                score -= 4
        if re.search(r"^\s*(return|yield|break|continue)\b", content, re.MULTILINE) and not re.search(r":\s*$", content, re.MULTILINE):
            score -= 1
    elif extension in {".json"}:
        try:
            json.loads(content)
        except json.JSONDecodeError:
            score -= 25
    elif extension in {".yml", ".yaml"}:
        if "\t" in content:
            score -= 10

    long_lines = sum(1 for line in lines if len(line) > 160)
    score -= min(10, long_lines * 0.35)
    score = min(score, policy.syntax_cap)

    return _score_to_percent(score)


def _compute_implementation_score(file_path: str, content: str, findings: List[Dict[str, Any]]) -> float:
    policy = _get_score_policy(file_path, content)
    score = policy.implementation_base
    lines = [line for line in content.splitlines() if line.strip()]
    if not lines:
        return min(80.0, policy.implementation_cap)

    average_line_length = mean(len(line) for line in lines)
    if average_line_length > 90:
        score -= min(10, (average_line_length - 90) * 0.18)

    function_like_blocks = len(re.findall(r"\b(function|def|class|interface|struct|enum|async function|public |private |protected )\b", content))
    if function_like_blocks == 0 and len(lines) > 120:
        score -= 8

    duplicate_log_statements = len(re.findall(r"(console\.(log|debug|info)|print\s*\()", content))
    score -= min(8, duplicate_log_statements * 0.5)

    severity_penalty = sum(
        3 if finding["severity"] == "high" else 1.5 if finding["severity"] == "medium" else 0.6
        for finding in findings
        if finding.get("rule_id") in QUALITY_REVIEW_RULES
        or finding.get("rule_id") in SECURITY_REVIEW_RULES
        or finding.get("rule_id", "").startswith(("schema_", "missing_", "approved_", "dotnet_", "broad_", "duplicate_"))
    )
    score -= min(25, severity_penalty)
    return _score_to_percent(min(score, policy.implementation_cap))


def _compute_security_score(file_path: str, content: str, findings: List[Dict[str, Any]]) -> float:
    policy = _get_score_policy(file_path, content)
    score = policy.security_base
    for finding in findings:
        score -= _severity_weight(finding["severity"])
    return _score_to_percent(score)


def _file_review(file_path: str, content: str, context: PythonReviewContext | None = None) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    for rule_id, rule in {**SECURITY_REVIEW_RULES, **QUALITY_REVIEW_RULES}.items():
        flags = re.IGNORECASE | re.MULTILINE
        for match in re.finditer(rule["pattern"], content, flags):
            line = content[: match.start()].count("\n") + 1
            findings.append(
                {
                    "severity": rule["severity"],
                    "message": rule["message"],
                    "rule_id": rule_id,
                    "line": line,
                }
            )

    findings.extend(_semantic_findings(file_path, content, context))
    findings.sort(key=lambda item: (_severity_weight(item["severity"]) * -1, item.get("line") or 0, item["rule_id"]))

    support_level = _review_support_level(file_path, content)
    syntax_score = _compute_syntax_score(file_path, content, findings)
    implementation_score = _compute_implementation_score(file_path, content, findings)
    security_score = _compute_security_score(file_path, content, findings)
    syntax_score, implementation_score, security_score = _apply_support_score_adjustment(
        support_level,
        syntax_score,
        implementation_score,
        security_score,
        findings,
    )
    syntax_score = _score_to_percent(syntax_score)
    implementation_score = _score_to_percent(implementation_score)
    security_score = _score_to_percent(security_score)

    return {
        "file_path": file_path,
        "language": _detect_language(file_path),
        "support_level": support_level,
        "generated": _is_generated_file(file_path, content),
        "syntax_score": syntax_score,
        "implementation_score": implementation_score,
        "security_score": security_score,
        "finding_count": len(findings),
        "findings": findings,
    }


def _github_headers(token: str | None = None) -> Dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    github_token = token or os.getenv("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"
    return headers


def _parse_github_repo(repository_url: str) -> tuple[str, str] | tuple[None, None]:
    parsed = urlparse(repository_url)
    path_parts = [part for part in parsed.path.split("/") if part]
    if "github.com" not in parsed.netloc or len(path_parts) < 2:
        return None, None
    return path_parts[0], path_parts[1].removesuffix(".git")


def _fetch_repository_files(repository_url: str, branch: str | None = None, token: str | None = None, max_files: int = 120) -> Dict[str, Any]:
    if httpx is None:
        return {"files": [], "default_branch": branch, "error": "httpx_not_installed"}

    owner, repo = _parse_github_repo(repository_url)
    if not owner or not repo:
        return {"files": [], "default_branch": branch, "error": "invalid_github_repository"}

    headers = _github_headers(token)
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            repo_resp = client.get(f"https://api.github.com/repos/{owner}/{repo}", headers=headers)
            repo_resp.raise_for_status()
            repo_data = repo_resp.json()
            selected_branch = branch or repo_data.get("default_branch") or "main"

            tree_resp = client.get(
                f"https://api.github.com/repos/{owner}/{repo}/git/trees/{selected_branch}?recursive=1",
                headers=headers,
            )
            tree_resp.raise_for_status()
            tree_data = tree_resp.json()
            tree = tree_data.get("tree", [])

            files: List[Dict[str, str]] = []
            for node in tree:
                if node.get("type") != "blob":
                    continue
                path = node.get("path", "")
                size = int(node.get("size") or 0)
                if not _is_text_file(path) or size > 300_000:
                    continue
                raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{selected_branch}/{path}"
                raw_resp = client.get(raw_url, headers=headers)
                if raw_resp.status_code != 200:
                    continue
                files.append({"path": path, "content": raw_resp.text})
                if len(files) >= max_files:
                    break

            return {"files": files, "default_branch": selected_branch, "error": None}
    except httpx.HTTPError as exc:
        return {"files": [], "default_branch": branch, "error": f"github_fetch_failed:{exc.__class__.__name__}"}


async def _summarize_repository_review(review: Dict[str, Any]) -> Dict[str, Any]:
    compact_payload = {
        "repository": review["repository"],
        "languages": review["languages"],
        "findings": review["findings"][:8],
        "file_samples": review.get("file_samples", []),  # raw snippets (see Fix 4)
    }
    prompt = (
        "You are a senior security and code review assistant. "
        "Review the following repository data and raw file snippets. "
        "Identify real security issues, bad practices, and bugs. "
        "Return valid JSON with keys `summary`, `strengths`, `risks`, "
        "`recommended_next_steps`.\n\n"
        f"{json.dumps(compact_payload, indent=2)}"
    )
    system = "Be precise, practical, and avoid hype."
    answer, source_model = await generate_response(prompt=prompt, system=system)
    try:
        parsed = json.loads(answer)
        return {
            "summary": str(parsed.get("summary") or "").strip(),
            "strengths": parsed.get("strengths") or [],
            "risks": parsed.get("risks") or [],
            "recommended_next_steps": parsed.get("recommended_next_steps") or [],
            "source_model": source_model,
        }
    except (json.JSONDecodeError, TypeError):
        return {
            "summary": answer.strip(),
            "strengths": [],
            "risks": [],
            "recommended_next_steps": [],
            "source_model": source_model,
        }


async def review_repository_from_github(
    repository_url: str,
    *,
    branch: str | None = None,
    github_token: str | None = None,
    max_files: int = 120,
) -> Dict[str, Any]:
    fetch_result = _fetch_repository_files(repository_url, branch=branch, token=github_token, max_files=max_files)
    files = fetch_result["files"]
    python_context = _build_python_review_context(files)
    gitignore_suggestions = _collect_gitignore_suggestions(files)

    file_reviews = [_file_review(file["path"], file["content"], python_context) for file in files]
    scored_reviews = [review for review in file_reviews if not review["generated"]]
    reviews_for_scores = scored_reviews or file_reviews
    all_findings = sorted(
        [
            {
                **finding,
                "file_path": review["file_path"],
                "language": review["language"],
            }
            for review in file_reviews
            for finding in review["findings"]
        ],
        key=lambda item: (_severity_weight(item["severity"]) * -1, item["file_path"], item.get("line") or 0),
    )

    language_counter = Counter(review["language"] for review in file_reviews if review["language"] != "Unknown")
    support_counter = Counter(review["support_level"] for review in file_reviews)
    syntax_score = _score_to_percent(mean([review["syntax_score"] for review in reviews_for_scores]) if reviews_for_scores else 0.0)
    implementation_score = _score_to_percent(mean([review["implementation_score"] for review in reviews_for_scores]) if reviews_for_scores else 0.0)
    security_score = _score_to_percent(mean([review["security_score"] for review in reviews_for_scores]) if reviews_for_scores else 0.0)
    maintainability_score = _score_to_percent((syntax_score * 0.45) + (implementation_score * 0.55))
    overall_score = _score_to_percent((syntax_score * 0.25) + (implementation_score * 0.35) + (security_score * 0.4))

    review = {
        "repository": {
            "url": repository_url,
            "branch": fetch_result.get("default_branch") or branch,
        },
        "coverage": {
            "analyzed_files": len(file_reviews),
            "max_files": max_files,
            "fetch_error": fetch_result.get("error"),
            "generated_files_skipped_from_scores": len([review for review in file_reviews if review["generated"]]),
            "support_breakdown": dict(support_counter),
        },
        "scores": {
            "syntax_correctness_percent": syntax_score,
            "implementation_quality_percent": implementation_score,
            "security_percent": security_score,
            "maintainability_percent": maintainability_score,
            "overall_percent": overall_score,
        },
        "languages": dict(language_counter.most_common()),
        "findings": all_findings[:50],
        "gitignore_suggestions": gitignore_suggestions,
        "file_reviews": [
            {
                "file_path": review_item["file_path"],
                "language": review_item["language"],
                "syntax_correctness_percent": review_item["syntax_score"],
                "implementation_quality_percent": review_item["implementation_score"],
                "security_percent": review_item["security_score"],
                "support_level": review_item["support_level"],
                "generated": review_item["generated"],
                "finding_count": review_item["finding_count"],
            }
            for review_item in sorted(file_reviews, key=lambda item: item["security_score"])
        ],
        "notes": [
            "Scores are heuristic percentages, not a compiler-grade proof of correctness.",
            "The review is language-aware: some ecosystems receive specialized semantic checks, while others receive generic structural review.",
            "Generated files are identified and excluded from repository-level score averages where possible.",
            "Binary assets and oversized files are intentionally skipped.",
        ],
    }
    review["file_samples"] = [
        {"path": f["path"], "snippet": f["content"][:1500]}
        for f in files[:5]  # send first 5 files as samples
    ]
    review["ai_summary"] = await _summarize_repository_review(review)
    return review


def _fetch_pr_files(repository_url: str, pull_number: int, token: str | None = None) -> List[Dict]:
    if httpx is None:
        return []
    github_token = token or os.getenv("GITHUB_TOKEN")
    parsed = urlparse(repository_url)
    path_parts = [part for part in parsed.path.split("/") if part]
    if "github.com" not in parsed.netloc or len(path_parts) < 2:
        return []
    owner, repo = path_parts[0], path_parts[1].removesuffix(".git")

    headers = {"Accept": "application/vnd.github+json"}
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    try:
        with httpx.Client(timeout=20.0) as client:
            files_resp = client.get(
                f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/files",
                headers=headers,
            )
            files_resp.raise_for_status()
            files = files_resp.json()

            fetched_files: List[Dict] = []
            for file in files:
                patch = file.get("patch")
                if patch:
                    fetched_files.append({"path": file["filename"], "content": patch})
            return fetched_files
    except httpx.HTTPError:
        return []
