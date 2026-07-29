from typing import List, Dict, Any
from src.scanner import SecurityIssue


class SecurityRemediator:
    """Generates automated patch recommendations for security scanner findings."""

    def generate_remediation_report(self, issues: List[SecurityIssue]) -> Dict[str, Any]:
        remediations = []
        for issue in issues:
            patch = self._suggest_patch(issue)
            remediations.append({
                "issue_id": issue.issue_id,
                "severity": issue.severity,
                "line_no": issue.line_no,
                "message": issue.message,
                "original_snippet": issue.snippet,
                "recommended_patch": patch,
            })
        return {
            "total_issues": len(issues),
            "high_severity_count": sum(1 for i in issues if i.severity == "HIGH"),
            "remediations": remediations,
        }

    def _suggest_patch(self, issue: SecurityIssue) -> str:
        if issue.issue_id == "DYNAMIC_EXEC":
            return "# REMEDIATION: Replace eval()/exec() with safe ast.literal_eval() or explicit mapping logic."
        elif issue.issue_id == "UNSAFE_SUBPROCESS":
            return "# REMEDIATION: Set shell=False and pass arguments as an explicit array list."
        elif issue.issue_id == "HARDCODED_SECRET":
            return "# REMEDIATION: Fetch secret from environment variable: os.environ.get('SECRET_KEY')"
        return "# REMEDIATION: Review security implications and add defensive validation checks."
