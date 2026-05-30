import ast
import base64
import json
import os
import re
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from statistics import mean
from typing import Any, Dict, List
from urllib.parse import quote, urlparse

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
from app.services.nim_service import generate_response

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
    "aws_access_key": {
        "pattern": r"\bAKIA[0-9A-Z]{16}\b",
        "severity": "critical",
        "message": "Possible AWS access key committed to source",
    },
    "private_key_material": {
        "pattern": r"-----BEGIN (RSA |EC |OPENSSH |DSA |)?PRIVATE KEY-----",
        "severity": "critical",
        "message": "Private key material committed to source",
    },
    "github_token": {
        "pattern": r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}\b",
        "severity": "critical",
        "message": "Possible GitHub token committed to source",
    },
    "jwt_token_literal": {
        "pattern": r"\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\b",
        "severity": "high",
        "message": "JWT-like token committed to source",
    },
    "hardcoded_connection_string": {
        "pattern": r"(Server|Data Source|Host)\s*=\s*[^;\n]+;[^\"\n]*(Password|Pwd|User Id|Uid)\s*=",
        "severity": "critical",
        "message": "Connection string with credential fields detected in source",
    },
    "cors_allow_any_origin": {
        "pattern": r"(AllowAnyOrigin\s*\(|Access-Control-Allow-Origin[\"']?\s*[:=]\s*[\"']?\*)",
        "severity": "high",
        "message": "Permissive CORS origin policy detected",
    },
    "csrf_disabled": {
        "pattern": r"(IgnoreAntiforgeryToken|ValidateAntiForgeryToken\s*=\s*false|csrf\s*[:=]\s*false)",
        "severity": "high",
        "message": "CSRF protection appears to be disabled",
    },
    "path_traversal_surface": {
        "pattern": r"(Path\.Combine|open\s*\(|File\.(Read|Write|Delete|Open)|send_file|send_from_directory)\s*\([^;\n]*(file|path|name|filename|request|params|query)",
        "severity": "medium",
        "message": "File path operation appears to use request-controlled input; verify path traversal protections",
    },
    "unsafe_deserialization": {
        "pattern": r"(BinaryFormatter|pickle\.loads|yaml\.load\s*\(|JsonConvert\.DeserializeObject<\s*object\s*>|ObjectInputStream)",
        "severity": "high",
        "message": "Unsafe or overly broad deserialization surface detected",
    },
    "ssrf_surface": {
        "pattern": r"(HttpClient|requests\.(get|post)|fetch|axios\.)\s*\([^;\n]*(url|uri|request|params|query)",
        "severity": "medium",
        "message": "Outbound request appears to use external input; verify SSRF protections",
    },
    "insecure_http_url": {
        "pattern": r'["\']http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)[^"\']+["\']',
        "severity": "medium",
        "message": "Plain HTTP URL detected; verify transport security",
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


@dataclass
class Dependency:
    manifest_path: str
    ecosystem: str
    name: str
    version: str | None
    source: str


SAST_SEVERITY_WEIGHTS = {"critical": 25.0, "high": 16.0, "medium": 7.0, "low": 2.5, "info": 0.5}


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
    return SAST_SEVERITY_WEIGHTS.get(severity, 1)


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


def _build_project_structure(tree_paths: list[str], files: List[Dict[str, str]]) -> Dict[str, Any]:
    normalized_paths = sorted({_normalized_path(path) for path in tree_paths if path} or {_normalized_path(file["path"]) for file in files})
    top_level_dirs: Counter[str] = Counter()
    root_files: list[str] = []
    manifest_names = {
        "package.json",
        "package-lock.json",
        "requirements.txt",
        "pyproject.toml",
        "poetry.lock",
        "pipfile.lock",
        "go.mod",
        "cargo.toml",
        "cargo.lock",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "composer.json",
        ".csproj",
        ".sln",
        "dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
    }
    entrypoint_names = {
        "main.py",
        "app.py",
        "manage.py",
        "index.js",
        "server.js",
        "main.ts",
        "program.cs",
        "startup.cs",
        "main.go",
        "lib.rs",
        "main.rs",
    }
    manifests: list[str] = []
    entrypoints: list[str] = []

    for path in normalized_paths:
        parts = path.split("/")
        base_name = parts[-1]
        if len(parts) == 1:
            root_files.append(path)
        else:
            top_level_dirs[parts[0]] += 1
        if base_name in manifest_names or any(path.endswith(name) for name in manifest_names if name.startswith(".")):
            manifests.append(path)
        if base_name in entrypoint_names:
            entrypoints.append(path)

    return {
        "total_paths_seen": len(normalized_paths),
        "top_level_directories": dict(top_level_dirs.most_common(30)),
        "root_files": root_files[:50],
        "manifest_files": manifests[:50],
        "entrypoint_candidates": entrypoints[:50],
        "sample_paths": normalized_paths[:80],
    }


def _repo_finding(rule_id: str, severity: str, message: str, path: str = "repository") -> Dict[str, Any]:
    return {
        "severity": severity,
        "message": message,
        "rule_id": rule_id,
        "line": 1,
        "file_path": path,
        "language": "Repository",
    }


def _collect_repository_findings(
    tree_paths: list[str],
    files: List[Dict[str, str]],
    project_structure: Dict[str, Any],
) -> List[Dict[str, Any]]:
    normalized_paths = [_normalized_path(path) for path in tree_paths]
    file_paths = {_normalized_path(file["path"]): file for file in files}
    findings: list[Dict[str, Any]] = []

    for path in normalized_paths:
        base_name = os.path.basename(path)
        if base_name in {"appsettings.development.json", "launchsettings.json"}:
            findings.append(
                _repo_finding(
                    "dev_runtime_settings_committed",
                    "medium",
                    "Development runtime settings are committed; verify local URLs, ports, profiles, and secrets are not exposed",
                    path,
                )
            )
        if "/wwwroot/" in path and base_name.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mov", ".avi")):
            findings.append(
                _repo_finding(
                    "user_uploaded_media_committed",
                    "low",
                    "User-uploaded or runtime media appears to be committed under wwwroot; verify the repo does not contain production/user data",
                    path,
                )
            )

    has_dependency_manifest = bool(project_structure.get("manifest_files"))
    has_lockfile = any(
        path.endswith(
            (
                "package-lock.json",
                "yarn.lock",
                "pnpm-lock.yaml",
                "poetry.lock",
                "pipfile.lock",
                "cargo.lock",
                "packages.lock.json",
                "composer.lock",
            )
        )
        for path in normalized_paths
    )
    if has_dependency_manifest and not has_lockfile:
        findings.append(
            _repo_finding(
                "missing_dependency_lockfile",
                "medium",
                "Dependency manifests were found, but no lockfile was detected; vulnerability matching and reproducible builds are less reliable",
            )
        )

    has_ci = any(path.startswith(".github/workflows/") or path.startswith(".gitlab-ci") or path == "azure-pipelines.yml" for path in normalized_paths)
    if not has_ci:
        findings.append(
            _repo_finding(
                "missing_ci_security_checks",
                "low",
                "No CI workflow was detected; add automated tests, dependency audit, and SAST checks before merge",
            )
        )

    gitignore = file_paths.get(".gitignore")
    if gitignore:
        content = gitignore["content"].lower()
        expected_patterns = ["appsettings.development.json", "secrets.json", "wwwroot/images", "wwwroot/posts"]
        missing = [pattern for pattern in expected_patterns if pattern not in content]
        if missing:
            findings.append(
                _repo_finding(
                    "gitignore_missing_sensitive_runtime_paths",
                    "medium",
                    f".gitignore does not cover sensitive/runtime path patterns: {', '.join(missing)}",
                    ".gitignore",
                )
            )

    return findings


def _dependency_finding(rule_id: str, severity: str, message: str, manifest_path: str) -> Dict[str, Any]:
    return {
        "severity": severity,
        "message": message,
        "rule_id": rule_id,
        "line": 1,
        "file_path": manifest_path,
        "language": "Dependency Manifest",
    }


def _normalize_dependency_name(raw_name: str) -> str:
    return raw_name.strip().strip("'\"").lower()


def _extract_exact_version(version_spec: str | None) -> str | None:
    if not version_spec:
        return None
    cleaned = version_spec.strip().strip("'\"")
    exact_match = re.match(r"^(?:==|=)?\s*([0-9][A-Za-z0-9.+!_-]*)$", cleaned)
    if exact_match:
        return exact_match.group(1)
    return None


def _parse_package_json_dependencies(path: str, content: str) -> tuple[list[Dependency], list[Dict[str, Any]]]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return [], [_dependency_finding("invalid_dependency_manifest", "high", "package.json is not valid JSON", path)]

    dependencies: list[Dependency] = []
    findings: list[Dict[str, Any]] = []
    for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        for name, version_spec in (data.get(section) or {}).items():
            version = _extract_exact_version(str(version_spec))
            dependencies.append(Dependency(path, "npm", _normalize_dependency_name(name), version, section))
            if version is None:
                findings.append(
                    _dependency_finding(
                        "dependency_version_range_not_exact",
                        "info",
                        f"{name} uses a non-exact version specifier in {section}; lockfile data is needed for precise vulnerability matching",
                        path,
                    )
                )
    return dependencies, findings


def _parse_package_lock_dependencies(path: str, content: str) -> tuple[list[Dependency], list[Dict[str, Any]]]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return [], [_dependency_finding("invalid_dependency_manifest", "high", "package-lock.json is not valid JSON", path)]

    dependencies: list[Dependency] = []
    packages = data.get("packages")
    if isinstance(packages, dict):
        for package_path, package_data in packages.items():
            if not package_path or not isinstance(package_data, dict):
                continue
            name = package_data.get("name")
            if not name and "node_modules/" in package_path:
                name = package_path.split("node_modules/")[-1]
            version = package_data.get("version")
            if name and version:
                dependencies.append(Dependency(path, "npm", _normalize_dependency_name(name), str(version), "package-lock"))
    else:
        for name, package_data in (data.get("dependencies") or {}).items():
            if isinstance(package_data, dict) and package_data.get("version"):
                dependencies.append(Dependency(path, "npm", _normalize_dependency_name(name), str(package_data["version"]), "package-lock"))
    return dependencies, []


def _parse_requirements_dependencies(path: str, content: str) -> tuple[list[Dependency], list[Dict[str, Any]]]:
    dependencies: list[Dependency] = []
    findings: list[Dict[str, Any]] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith(("-r ", "--")):
            continue
        match = re.match(r"([A-Za-z0-9_.-]+)\s*(==|~=|>=|<=|>|<)?\s*([^;#\s]+)?", stripped)
        if not match:
            continue
        name, operator, version_spec = match.groups()
        version = version_spec if operator == "==" else None
        dependencies.append(Dependency(path, "PyPI", _normalize_dependency_name(name), version, "requirements"))
        if version is None:
            findings.append(
                _dependency_finding(
                    "dependency_version_range_not_exact",
                    "info",
                    f"{name} is not pinned with ==; lockfile data is needed for precise vulnerability matching",
                    path,
                )
            )
    return dependencies, findings


def _parse_pyproject_dependencies(path: str, content: str) -> tuple[list[Dependency], list[Dict[str, Any]]]:
    dependencies: list[Dependency] = []
    findings: list[Dict[str, Any]] = []
    for match in re.finditer(r'["\']([A-Za-z0-9_.-]+)\s*(==|~=|>=|<=|>|<)?\s*([^"\']*)["\']', content):
        name, operator, version_spec = match.groups()
        if name.lower() in {"python"}:
            continue
        version = version_spec.strip() if operator == "==" else None
        dependencies.append(Dependency(path, "PyPI", _normalize_dependency_name(name), version, "pyproject"))
        if version is None:
            findings.append(
                _dependency_finding(
                    "dependency_version_range_not_exact",
                    "info",
                    f"{name} is not pinned with ==; lockfile data is needed for precise vulnerability matching",
                    path,
                )
            )
    return dependencies, findings


def _strip_xml_namespace(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _parse_dotnet_project_dependencies(path: str, content: str) -> tuple[list[Dependency], list[Dict[str, Any]]]:
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return [], [_dependency_finding("invalid_dependency_manifest", "high", ".NET project file is not valid XML", path)]

    dependencies: list[Dependency] = []
    findings: list[Dict[str, Any]] = []
    for node in root.iter():
        if _strip_xml_namespace(node.tag) != "PackageReference":
            continue
        name = node.attrib.get("Include") or node.attrib.get("Update")
        version = node.attrib.get("Version")
        for child in node:
            if _strip_xml_namespace(child.tag) == "Version" and child.text:
                version = child.text.strip()
                break
        if not name:
            continue
        exact_version = _extract_exact_version(version)
        dependencies.append(Dependency(path, "NuGet", _normalize_dependency_name(name), exact_version, "csproj"))
        if exact_version is None:
            findings.append(
                _dependency_finding(
                    "dependency_version_range_not_exact",
                    "info",
                    f"{name} does not use an exact NuGet version; lockfile data is needed for precise vulnerability matching",
                    path,
                )
            )
    return dependencies, findings


def _collect_dependencies(files: List[Dict[str, str]]) -> tuple[list[Dependency], list[Dict[str, Any]]]:
    dependencies: list[Dependency] = []
    findings: list[Dict[str, Any]] = []
    parsers = {
        "package.json": _parse_package_json_dependencies,
        "package-lock.json": _parse_package_lock_dependencies,
        "requirements.txt": _parse_requirements_dependencies,
        "pyproject.toml": _parse_pyproject_dependencies,
    }

    for file in files:
        base_name = os.path.basename(file["path"].lower())
        parser = _parse_dotnet_project_dependencies if base_name.endswith(".csproj") else parsers.get(base_name)
        if not parser:
            continue
        parsed_dependencies, parsed_findings = parser(file["path"], file["content"])
        dependencies.extend(parsed_dependencies)
        findings.extend(parsed_findings)

    deduped: dict[tuple[str, str, str | None, str], Dependency] = {}
    for dependency in dependencies:
        key = (dependency.ecosystem, dependency.name, dependency.version, dependency.manifest_path)
        deduped[key] = dependency
    return list(deduped.values()), findings


def _osv_severity(vulnerability: Dict[str, Any]) -> str:
    severity_values = [
        item.get("score") or item.get("type") or ""
        for item in vulnerability.get("severity", [])
        if isinstance(item, dict)
    ]
    database_severity = str(vulnerability.get("database_specific", {}).get("severity") or "")
    combined = " ".join(str(value).upper() for value in [database_severity, *severity_values])
    if "CRITICAL" in combined or re.search(r"\b9\.\d\b", combined):
        return "critical"
    if "HIGH" in combined or re.search(r"\b[78]\.\d\b", combined):
        return "high"
    if "MODERATE" in combined or "MEDIUM" in combined or re.search(r"\b[456]\.\d\b", combined):
        return "medium"
    return "medium"


def _query_osv_vulnerabilities(dependencies: list[Dependency]) -> Dict[str, Any]:
    if httpx is None:
        return {"vulnerabilities": [], "error": "httpx_not_installed", "queried_dependencies": 0}

    exact_dependencies = [dependency for dependency in dependencies if dependency.version][:100]
    if not exact_dependencies:
        return {"vulnerabilities": [], "error": None, "queried_dependencies": 0}

    queries = [
        {
            "package": {"name": dependency.name, "ecosystem": dependency.ecosystem},
            "version": dependency.version,
        }
        for dependency in exact_dependencies
    ]

    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.post("https://api.osv.dev/v1/querybatch", json={"queries": queries})
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        return {
            "vulnerabilities": [],
            "error": f"osv_query_failed:{exc.__class__.__name__}",
            "queried_dependencies": len(exact_dependencies),
        }

    vulnerabilities: list[Dict[str, Any]] = []
    for dependency, result in zip(exact_dependencies, data.get("results", [])):
        for vulnerability in result.get("vulns", [])[:10]:
            vulnerabilities.append(
                {
                    "id": vulnerability.get("id"),
                    "summary": vulnerability.get("summary") or vulnerability.get("details", "")[:180],
                    "severity": _osv_severity(vulnerability),
                    "package": dependency.name,
                    "version": dependency.version,
                    "ecosystem": dependency.ecosystem,
                    "manifest_path": dependency.manifest_path,
                    "aliases": vulnerability.get("aliases", [])[:5],
                    "references": [
                        reference.get("url")
                        for reference in vulnerability.get("references", [])[:3]
                        if reference.get("url")
                    ],
                }
            )

    return {
        "vulnerabilities": vulnerabilities[:80],
        "error": None,
        "queried_dependencies": len(exact_dependencies),
    }


def _scan_dependency_vulnerabilities(files: List[Dict[str, str]]) -> Dict[str, Any]:
    dependencies, manifest_findings = _collect_dependencies(files)
    osv_result = _query_osv_vulnerabilities(dependencies)
    vulnerability_findings = [
        _dependency_finding(
            "dependency_vulnerability",
            vulnerability["severity"],
            f"{vulnerability['package']} {vulnerability['version']} is affected by {vulnerability.get('id')}: {vulnerability.get('summary')}",
            vulnerability["manifest_path"],
        )
        for vulnerability in osv_result["vulnerabilities"]
    ]
    ecosystem_counter = Counter(dependency.ecosystem for dependency in dependencies)

    return {
        "dependencies_seen": len(dependencies),
        "ecosystems": dict(ecosystem_counter),
        "queried_dependencies": osv_result["queried_dependencies"],
        "osv_error": osv_result["error"],
        "vulnerabilities": osv_result["vulnerabilities"],
        "findings": [*vulnerability_findings, *manifest_findings],
    }


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


def _is_dependency_manifest(file_path: str) -> bool:
    base_name = os.path.basename(file_path.lower())
    return base_name in {
        "package.json",
        "package-lock.json",
        "requirements.txt",
        "pyproject.toml",
        "packages.lock.json",
    } or base_name.endswith((".csproj", ".fsproj", ".vbproj"))


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


def _find_dotnet_missing_authorization(file_path: str, content: str) -> List[Dict[str, Any]]:
    normalized = _normalized_path(file_path)
    if "/controllers/" not in normalized:
        return []

    if "weatherforecast" in normalized:
        return []

    class_has_authorize = bool(re.search(r"\[Authorize(?:\([^\]]*\))?\]", content))
    if class_has_authorize:
        return []

    findings: List[Dict[str, Any]] = []
    method_pattern = re.compile(
        r"(?P<attrs>(?:\s*\[[^\]]+\]\s*)+)\s*public\s+(?:async\s+)?[\w<>\[\],?\s]+\s+(?P<name>\w+)\s*\(",
        re.DOTALL,
    )
    public_auth_methods = {"login", "register", "refresh", "token", "forgotpassword", "resetpassword"}
    for match in method_pattern.finditer(content):
        attrs = match.group("attrs")
        method_name = match.group("name")
        if not re.search(r"\[(HttpPost|HttpPut|HttpPatch|HttpDelete)\b", attrs):
            continue
        if "Authorize" in attrs or method_name.lower() in public_auth_methods:
            continue
        line = content[: match.start()].count("\n") + 1
        findings.append(
            _finding(
                "dotnet_mutating_endpoint_without_authorize",
                "high",
                f"Mutating endpoint `{method_name}` has no detected [Authorize] attribute",
                line,
            )
        )
    return findings


def _find_dotnet_model_validation_gaps(content: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    method_pattern = re.compile(
        r"\[(HttpPost|HttpPut|HttpPatch)\b[^\]]*\]\s*public\s+(?:async\s+)?[\w<>\[\],?\s]+\s+\w+\s*\((?P<params>.*?)\)\s*\{(?P<body>.*?)\n\s*\}",
        re.DOTALL,
    )
    for match in method_pattern.finditer(content):
        params = match.group("params")
        body = match.group("body")
        line = content[: match.start()].count("\n") + 1
        receives_complex_body = any(token in params for token in ("Dto", "[FromBody]", "[FromForm]"))
        if receives_complex_body and "ModelState.IsValid" not in body:
            findings.append(
                _finding(
                    "dotnet_missing_modelstate_validation",
                    "medium",
                    "Mutating endpoint accepts DTO/form data without an obvious ModelState validation check",
                    line,
                )
            )
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
        findings.extend(_find_dotnet_missing_authorization(file_path, content))
        findings.extend(_find_dotnet_model_validation_gaps(content))
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
        8 if finding["severity"] == "critical" else 5 if finding["severity"] == "high" else 2.5 if finding["severity"] == "medium" else 1
        for finding in findings
        if finding.get("rule_id") in QUALITY_REVIEW_RULES
        or finding.get("rule_id") in SECURITY_REVIEW_RULES
        or finding.get("rule_id", "").startswith(("schema_", "missing_", "approved_", "dotnet_", "broad_", "duplicate_"))
    )
    score -= min(55, severity_penalty)
    return _score_to_percent(min(score, policy.implementation_cap))


def _compute_security_score(file_path: str, content: str, findings: List[Dict[str, Any]]) -> float:
    policy = _get_score_policy(file_path, content)
    score = policy.security_base
    for finding in findings:
        score -= _severity_weight(finding["severity"])
    if findings and not any(finding["severity"] in {"critical", "high"} for finding in findings):
        score = min(score, 78.0)
    if any(finding["severity"] == "high" for finding in findings):
        score = min(score, 60.0)
    if any(finding["severity"] == "critical" for finding in findings):
        score = min(score, 35.0)
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
        return {"files": [], "tree_paths": [], "default_branch": branch, "error": "httpx_not_installed"}

    owner, repo = _parse_github_repo(repository_url)
    if not owner or not repo:
        return {"files": [], "tree_paths": [], "default_branch": branch, "error": "invalid_github_repository"}

    headers = _github_headers(token)
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            repo_resp = client.get(f"https://api.github.com/repos/{owner}/{repo}", headers=headers)
            repo_resp.raise_for_status()
            repo_data = repo_resp.json()
            selected_branch = branch or repo_data.get("default_branch") or "main"

            branch_resp = client.get(
                f"https://api.github.com/repos/{owner}/{repo}/branches/{quote(selected_branch, safe='')}",
                headers=headers,
            )
            branch_resp.raise_for_status()
            branch_data = branch_resp.json()
            tree_sha = branch_data.get("commit", {}).get("commit", {}).get("tree", {}).get("sha")
            if not tree_sha:
                tree_sha = branch_data.get("commit", {}).get("sha") or selected_branch

            tree_resp = client.get(
                f"https://api.github.com/repos/{owner}/{repo}/git/trees/{tree_sha}?recursive=1",
                headers=headers,
            )
            tree_resp.raise_for_status()
            tree_data = tree_resp.json()
            tree = tree_data.get("tree", [])
            tree_paths = [node.get("path", "") for node in tree if node.get("path")]

            def fetch_priority(node: Dict[str, Any]) -> tuple[int, str]:
                path = _normalized_path(node.get("path", ""))
                if _is_dependency_manifest(path) or path.endswith((".sln", ".props", ".targets")):
                    return (0, path)
                if any(part in path for part in ("/controllers/", "/routes/", "/api/", "/security/", "/auth/", "/middleware/")):
                    return (1, path)
                if path.endswith((".cs", ".py", ".js", ".ts", ".tsx", ".java", ".go", ".rs", ".php", ".rb")):
                    return (2, path)
                return (3, path)

            files: List[Dict[str, str]] = []
            for node in sorted(tree, key=fetch_priority):
                if node.get("type") != "blob":
                    continue
                path = node.get("path", "")
                size = int(node.get("size") or 0)
                max_size = 2_000_000 if _is_dependency_manifest(path) else 300_000
                if not _is_text_file(path) or size > max_size:
                    continue
                raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{quote(selected_branch, safe='/')}/{quote(path, safe='/')}"
                raw_resp = client.get(raw_url, headers=headers)
                if raw_resp.status_code == 200:
                    content = raw_resp.text
                else:
                    blob_resp = client.get(
                        f"https://api.github.com/repos/{owner}/{repo}/git/blobs/{node.get('sha')}",
                        headers=headers,
                    )
                    if blob_resp.status_code != 200:
                        continue
                    blob_data = blob_resp.json()
                    if blob_data.get("encoding") != "base64":
                        continue
                    content = base64.b64decode(blob_data.get("content", "")).decode("utf-8", errors="replace")
                files.append({"path": path, "content": content})
                if len(files) >= max_files:
                    break

            return {
                "files": files,
                "tree_paths": tree_paths,
                "default_branch": selected_branch,
                "repository": {
                    "owner": owner,
                    "name": repo,
                    "full_name": repo_data.get("full_name"),
                    "description": repo_data.get("description"),
                    "private": repo_data.get("private"),
                    "default_branch": repo_data.get("default_branch"),
                    "html_url": repo_data.get("html_url"),
                    "stars": repo_data.get("stargazers_count"),
                    "forks": repo_data.get("forks_count"),
                    "open_issues": repo_data.get("open_issues_count"),
                },
                "tree_truncated": bool(tree_data.get("truncated")),
                "error": None,
            }
    except httpx.HTTPError as exc:
        return {"files": [], "tree_paths": [], "default_branch": branch, "error": f"github_fetch_failed:{exc.__class__.__name__}"}


async def _summarize_repository_review(review: Dict[str, Any]) -> Dict[str, Any]:
    compact_payload = {
        "repository": review["repository"],
        "project_structure": review.get("project_structure", {}),
        "languages": review["languages"],
        "dependency_vulnerabilities": review.get("dependency_vulnerabilities", {}).get("vulnerabilities", [])[:12],
        "risk_summary": review.get("risk_summary", {}),
        "findings": review["findings"][:20],
        "file_samples": review.get("file_samples", []),
    }
    prompt = (
        "You are a strict SAST and application-security reviewer. "
        "Review the following GitHub repository data, project structure, deterministic findings, dependency vulnerability data, and raw file snippets. "
        "Do not inflate the score or dismiss deterministic findings. "
        "Identify exploitable security issues, OWASP/CWE-style risks, unsafe defaults, missing authorization, dependency blind spots, and likely bugs. "
        "Return valid JSON with keys `summary`, `strengths`, `risks`, "
        "`recommended_next_steps`.\n\n"
        f"{json.dumps(compact_payload, indent=2)}"
    )
    system = "Be strict, evidence-based, practical, and concise. Return only JSON."
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


def _finding_counts(findings: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = Counter(finding["severity"] for finding in findings)
    return {severity: counts.get(severity, 0) for severity in ["critical", "high", "medium", "low", "info"]}


def _aggregate_sast_score(findings: List[Dict[str, Any]], *, base: float = 100.0, max_penalty: float = 95.0) -> float:
    penalty = sum(_severity_weight(finding["severity"]) for finding in findings)
    return _score_to_percent(base - min(max_penalty, penalty))


def _coverage_penalty(fetch_result: Dict[str, Any], file_reviews: List[Dict[str, Any]], dependency_vulnerabilities: Dict[str, Any]) -> float:
    penalty = 0.0
    if fetch_result.get("error"):
        penalty += 30.0
    if fetch_result.get("tree_truncated"):
        penalty += 15.0
    if not file_reviews:
        penalty += 50.0
    if dependency_vulnerabilities.get("dependencies_seen") and not dependency_vulnerabilities.get("queried_dependencies"):
        penalty += 10.0
    if not dependency_vulnerabilities.get("dependencies_seen"):
        penalty += 6.0
    return penalty


def _build_risk_summary(
    findings: List[Dict[str, Any]],
    file_reviews: List[Dict[str, Any]],
    dependency_vulnerabilities: Dict[str, Any],
) -> Dict[str, Any]:
    counts = _finding_counts(findings)
    top_rules = Counter(finding["rule_id"] for finding in findings).most_common(10)
    risky_files = Counter(finding.get("file_path", "repository") for finding in findings if finding.get("file_path")).most_common(10)
    return {
        "scan_profile": "strict_static_application_security_testing",
        "severity_counts": counts,
        "total_findings": len(findings),
        "high_or_critical_findings": counts["critical"] + counts["high"],
        "files_with_findings": len({finding.get("file_path") for finding in findings if finding.get("file_path")}),
        "analyzed_file_count": len(file_reviews),
        "top_rule_ids": [{"rule_id": rule_id, "count": count} for rule_id, count in top_rules],
        "riskiest_files": [{"file_path": path, "finding_count": count} for path, count in risky_files],
        "dependency_coverage": {
            "dependencies_seen": dependency_vulnerabilities.get("dependencies_seen", 0),
            "queried_dependencies": dependency_vulnerabilities.get("queried_dependencies", 0),
            "vulnerability_count": len(dependency_vulnerabilities.get("vulnerabilities", [])),
            "osv_error": dependency_vulnerabilities.get("osv_error"),
        },
    }


def _deterministic_repository_summary(review: Dict[str, Any]) -> Dict[str, Any]:
    risk_summary = review.get("risk_summary", {})
    severity_counts = risk_summary.get("severity_counts", {})
    top_rules = risk_summary.get("top_rule_ids", [])[:5]
    riskiest_files = risk_summary.get("riskiest_files", [])[:5]
    risks = [
        f"{severity_counts.get('critical', 0)} critical, {severity_counts.get('high', 0)} high, and {severity_counts.get('medium', 0)} medium findings were detected.",
    ]
    if top_rules:
        risks.append("Most frequent rule hits: " + ", ".join(f"{item['rule_id']} ({item['count']})" for item in top_rules))
    if riskiest_files:
        risks.append("Riskiest files: " + ", ".join(f"{item['file_path']} ({item['finding_count']})" for item in riskiest_files))
    return {
        "summary": (
            f"Strict deterministic SAST completed for {review['repository']['url']}. "
            f"Overall score is {review['scores']['overall_percent']}%, driven by {risk_summary.get('total_findings', 0)} findings."
        ),
        "strengths": [
            f"Repository metadata and {review['coverage']['analyzed_files']} text/source files were analyzed.",
            "Generated files were separated from the main score where possible.",
        ],
        "risks": risks,
        "recommended_next_steps": [
            "Fix high and critical findings before treating the repository as production-ready.",
            "Add authorization checks to mutating endpoints and avoid returning raw exception messages.",
            "Commit dependency lockfiles or exact versions so dependency vulnerability matching is reliable.",
            "Move development settings and runtime/user-uploaded assets out of source control.",
        ],
        "source_model": None,
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
    tree_paths = fetch_result.get("tree_paths", [])
    project_structure = _build_project_structure(tree_paths, files)
    repository_findings = _collect_repository_findings(tree_paths, files, project_structure)
    python_context = _build_python_review_context(files)
    gitignore_suggestions = _collect_gitignore_suggestions(files)
    dependency_vulnerabilities = _scan_dependency_vulnerabilities(files)

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
        ]
        + dependency_vulnerabilities["findings"]
        + repository_findings,
        key=lambda item: (_severity_weight(item["severity"]) * -1, item["file_path"], item.get("line") or 0),
    )

    language_counter = Counter(review["language"] for review in file_reviews if review["language"] != "Unknown")
    support_counter = Counter(review["support_level"] for review in file_reviews)
    syntax_score = _score_to_percent(mean([review["syntax_score"] for review in reviews_for_scores]) if reviews_for_scores else 0.0)
    file_implementation_score = _score_to_percent(mean([review["implementation_score"] for review in reviews_for_scores]) if reviews_for_scores else 0.0)
    file_security_score = _score_to_percent(mean([review["security_score"] for review in reviews_for_scores]) if reviews_for_scores else 0.0)
    coverage_penalty = _coverage_penalty(fetch_result, file_reviews, dependency_vulnerabilities)
    aggregate_security_score = _aggregate_sast_score(all_findings, base=100.0 - coverage_penalty, max_penalty=95.0)
    aggregate_implementation_score = _aggregate_sast_score(
        [finding for finding in all_findings if finding["severity"] in {"critical", "high", "medium"}],
        base=file_implementation_score,
        max_penalty=55.0,
    )
    security_score = min(file_security_score, aggregate_security_score)
    implementation_score = min(file_implementation_score, aggregate_implementation_score)
    maintainability_score = _score_to_percent((syntax_score * 0.45) + (implementation_score * 0.55))
    overall_score = _score_to_percent((syntax_score * 0.15) + (implementation_score * 0.25) + (security_score * 0.6))
    risk_summary = _build_risk_summary(all_findings, file_reviews, dependency_vulnerabilities)

    review = {
        "repository": {
            "url": repository_url,
            "branch": fetch_result.get("default_branch") or branch,
            "metadata": fetch_result.get("repository") or {},
        },
        "coverage": {
            "analyzed_files": len(file_reviews),
            "repository_paths_seen": len(tree_paths),
            "max_files": max_files,
            "fetch_error": fetch_result.get("error"),
            "tree_truncated": fetch_result.get("tree_truncated", False),
            "coverage_penalty": coverage_penalty,
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
        "score_explanation": {
            "mode": "strict_sast_weighted",
            "file_average_security_percent": file_security_score,
            "aggregate_security_percent": aggregate_security_score,
            "file_average_implementation_percent": file_implementation_score,
            "aggregate_implementation_percent": aggregate_implementation_score,
            "coverage_penalty": coverage_penalty,
            "overall_formula": "15% syntax + 25% implementation + 60% security",
            "severity_weights": SAST_SEVERITY_WEIGHTS,
        },
        "risk_summary": risk_summary,
        "languages": dict(language_counter.most_common()),
        "project_structure": project_structure,
        "dependency_vulnerabilities": dependency_vulnerabilities,
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
            "Scores are strict SAST-style risk indicators, not proof that code is secure or insecure.",
            "Security score is repository-risk weighted; many clean files do not hide high-impact findings.",
            "The scanner applies generic cross-language security rules to every supported text language, with deeper semantic checks for selected ecosystems.",
            "Dependency vulnerabilities are checked with OSV only when an exact package version is available from a lockfile or pinned manifest.",
            "Generated files are identified and excluded from repository-level score averages where possible.",
            "Binary assets and oversized files are intentionally skipped.",
        ],
    }
    risky_paths = [finding["file_path"] for finding in all_findings if finding.get("file_path")]
    sample_paths = []
    for path in risky_paths + [file["path"] for file in files]:
        if path not in sample_paths:
            sample_paths.append(path)
        if len(sample_paths) >= 5:
            break
    file_by_path = {file["path"]: file for file in files}
    review["file_samples"] = [
        {"path": path, "snippet": file_by_path[path]["content"][:1500]}
        for path in sample_paths
        if path in file_by_path
    ]
    review["ai_summary"] = await _summarize_repository_review(review)
    if review["ai_summary"].get("source_model") is None:
        review["ai_summary"] = _deterministic_repository_summary(review)
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
