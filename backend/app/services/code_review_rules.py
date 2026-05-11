from __future__ import annotations

from dataclasses import dataclass


TEXT_FILE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".kts", ".go", ".rs", ".rb", ".php", ".cs", ".cpp",
    ".cc", ".cxx", ".c", ".h", ".hpp", ".swift", ".m", ".mm", ".scala", ".sh", ".bash", ".zsh", ".ps1",
    ".sql", ".html", ".css", ".scss", ".sass", ".less", ".vue", ".svelte", ".json", ".yaml", ".yml", ".toml",
    ".ini", ".env", ".xml", ".gradle", ".properties", ".md", ".csproj", ".sln", ".fs", ".fsproj",
}

IGNORED_PATH_FRAGMENTS = {
    "node_modules/", ".next/", "dist/", "build/", ".git/", ".venv/", "venv/", "__pycache__/", "coverage/",
    "bin/", "obj/", ".idea/", ".vs/",
}

GENERATED_PATH_FRAGMENTS = {
    "/migrations/", "\\migrations\\", "/generated/", "\\generated\\", "/obj/", "\\obj\\", "/bin/", "\\bin\\",
}

GENERATED_FILE_SUFFIXES = {
    ".designer.cs", ".g.cs", ".g.i.cs", ".generated.cs", ".generated.ts",
}

LANGUAGE_BY_EXTENSION = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".fs": "F#",
    ".cpp": "C/C++",
    ".cc": "C/C++",
    ".cxx": "C/C++",
    ".c": "C/C++",
    ".h": "C/C++",
    ".hpp": "C/C++",
    ".swift": "Swift",
    ".scala": "Scala",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".ps1": "PowerShell",
    ".sql": "SQL",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "CSS",
    ".sass": "CSS",
    ".less": "CSS",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".xml": "XML",
    ".csproj": ".NET Project",
    ".fsproj": ".NET Project",
    ".sln": ".NET Solution",
}


@dataclass(frozen=True)
class ScorePolicy:
    syntax_cap: float
    implementation_base: float
    implementation_cap: float
    security_base: float


LANGUAGE_SCORE_POLICIES = {
    "Python": ScorePolicy(96.0, 92.0, 95.0, 95.0),
    "JavaScript": ScorePolicy(97.0, 91.0, 94.0, 93.0),
    "TypeScript": ScorePolicy(97.0, 92.0, 95.0, 94.0),
    "C#": ScorePolicy(97.0, 91.0, 95.0, 94.0),
    "Java": ScorePolicy(97.0, 91.0, 94.0, 93.0),
    "Go": ScorePolicy(97.0, 92.0, 95.0, 94.0),
    "Rust": ScorePolicy(97.0, 92.0, 95.0, 94.0),
    "JSON": ScorePolicy(95.0, 88.0, 90.0, 91.0),
    "YAML": ScorePolicy(95.0, 88.0, 90.0, 91.0),
    ".NET Project": ScorePolicy(95.0, 88.0, 90.0, 92.0),
    ".NET Solution": ScorePolicy(95.0, 88.0, 90.0, 92.0),
}

DEFAULT_SCORE_POLICY = ScorePolicy(94.0, 87.0, 91.0, 90.0)
GENERATED_FILE_SCORE_POLICY = ScorePolicy(90.0, 78.0, 84.0, 88.0)

GITIGNORE_SUGGESTION_RULES = [
    {
        "pattern": "/bin/",
        "message": "Compiled build output is usually better ignored via `.gitignore`.",
    },
    {
        "pattern": "/obj/",
        "message": "Intermediate .NET build artifacts are usually better ignored via `.gitignore`.",
    },
    {
        "pattern": ".dll",
        "message": "Compiled .NET assembly files are usually build artifacts and should normally be ignored.",
    },
    {
        "pattern": ".exe",
        "message": "Built executable output is usually generated and should normally be ignored.",
    },
    {
        "pattern": ".pdb",
        "message": "Debug symbol files are usually generated locally and should normally be ignored.",
    },
    {
        "pattern": ".cache",
        "message": "Cache files are usually machine-generated and should normally be ignored.",
    },
    {
        "pattern": ".user",
        "message": "Visual Studio user-specific settings files are usually personal and should normally be ignored.",
    },
    {
        "pattern": ".suo",
        "message": "Visual Studio solution user option files are machine-specific and should normally be ignored.",
    },
    {
        "pattern": ".nupkg",
        "message": "NuGet package output is usually generated during packaging and should normally be ignored.",
    },
    {
        "pattern": "appsettings.development.json",
        "message": "Development-only appsettings files often contain local machine values or secrets and should be reviewed for `.gitignore`.",
    },
    {
        "pattern": "appsettings.local.json",
        "message": "Local appsettings overrides are usually machine-specific and should normally be ignored.",
    },
    {
        "pattern": "secrets.json",
        "message": "Secret configuration files should normally not be committed and should usually be ignored.",
    },
    {
        "pattern": "/node_modules/",
        "message": "Dependency directories should usually be ignored via `.gitignore`.",
    },
    {
        "pattern": "/dist/",
        "message": "Bundled frontend build output is usually better ignored via `.gitignore`.",
    },
    {
        "pattern": "/build/",
        "message": "Build output is usually better ignored via `.gitignore`.",
    },
    {
        "pattern": "/coverage/",
        "message": "Coverage reports are usually better ignored via `.gitignore`.",
    },
    {
        "pattern": ".env",
        "message": "Environment files often contain local secrets or machine-specific settings and should usually be ignored.",
    },
    {
        "pattern": ".local",
        "message": "Local-only configuration files are usually better ignored via `.gitignore`.",
    },
    {
        "pattern": ".sqlite",
        "message": "Local database files are usually better ignored via `.gitignore`.",
    },
    {
        "pattern": ".db",
        "message": "Local database files are usually better ignored via `.gitignore`.",
    },
]
