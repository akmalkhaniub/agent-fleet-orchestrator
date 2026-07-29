import ast
import re
from typing import List, Dict, Any


class SecurityIssue:
    def __init__(self, issue_id: str, severity: str, message: str, line_no: int, snippet: str = ""):
        self.issue_id = issue_id
        self.severity = severity  # HIGH, MEDIUM, LOW
        self.message = message
        self.line_no = line_no
        self.snippet = snippet

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "severity": self.severity,
            "message": self.message,
            "line_no": self.line_no,
            "snippet": self.snippet,
        }


class ASTSecurityScanner(ast.NodeVisitor):
    """Python AST Security Scanner identifying security risks & OWASP vulnerabilities."""

    def __init__(self, code: str):
        self.code = code
        self.lines = code.splitlines()
        self.issues: List[SecurityIssue] = []

    def scan(self) -> List[SecurityIssue]:
        try:
            tree = ast.parse(self.code)
            self.visit(tree)
        except SyntaxError as e:
            self.issues.append(SecurityIssue("SYNTAX_ERR", "HIGH", f"Syntax error: {e}", e.lineno or 1))

        # Regex scan for hardcoded secrets / API keys
        secret_patterns = [
            (r"(api[_-]?key|secret[_-]?key|password|bearer\s+[a-zA-Z0-9_\-\.]+)\s*=\s*['\"][^'\"]+['\"]", "HARDCODED_SECRET", "HIGH", "Potential hardcoded secret or API key detected."),
        ]
        for idx, line in enumerate(self.lines, start=1):
            for pattern, issue_id, severity, msg in secret_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    self.issues.append(SecurityIssue(issue_id, severity, msg, idx, line.strip()))

        return self.issues

    def visit_Call(self, node: ast.Call):
        # 1. Check forbidden eval() or exec()
        if isinstance(node.func, ast.Name):
            if node.func.id in ["eval", "exec"]:
                snippet = self.lines[node.lineno - 1].strip() if node.lineno <= len(self.lines) else ""
                self.issues.append(SecurityIssue(
                    "DYNAMIC_EXEC",
                    "HIGH",
                    f"Use of forbidden dynamic execution function '{node.func.id}()'.",
                    node.lineno,
                    snippet,
                ))

        # 2. Check unsafe subprocess with shell=True
        if isinstance(node.func, ast.Attribute) and node.func.attr in ["Popen", "run", "call"]:
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    snippet = self.lines[node.lineno - 1].strip() if node.lineno <= len(self.lines) else ""
                    self.issues.append(SecurityIssue(
                        "UNSAFE_SUBPROCESS",
                        "HIGH",
                        "Subprocess invocation with shell=True invites command injection vulnerabilities.",
                        node.lineno,
                        snippet,
                    ))

        self.generic_visit(node)
