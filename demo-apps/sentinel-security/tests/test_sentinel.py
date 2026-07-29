import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.scanner import ASTSecurityScanner
from src.remediator import SecurityRemediator


def test_scanner_detects_eval():
    vulnerable_code = "def bad():\n    x = '1 + 1'\n    return eval(x)\n"
    scanner = ASTSecurityScanner(vulnerable_code)
    issues = scanner.scan()

    assert len(issues) >= 1
    eval_issue = next(i for i in issues if i.issue_id == "DYNAMIC_EXEC")
    assert eval_issue.severity == "HIGH"
    assert eval_issue.line_no == 3


def test_scanner_detects_hardcoded_secrets():
    vulnerable_code = "API_KEY = 'sk_live_1234567890secretkey'\n"
    scanner = ASTSecurityScanner(vulnerable_code)
    issues = scanner.scan()

    assert len(issues) >= 1
    secret_issue = next(i for i in issues if i.issue_id == "HARDCODED_SECRET")
    assert secret_issue.severity == "HIGH"


def test_remediator_patch_generation():
    vulnerable_code = "eval('2 + 2')\n"
    scanner = ASTSecurityScanner(vulnerable_code)
    issues = scanner.scan()

    remediator = SecurityRemediator()
    report = remediator.generate_remediation_report(issues)

    assert report["total_issues"] == 1
    assert report["high_severity_count"] == 1
    assert "ast.literal_eval" in report["remediations"][0]["recommended_patch"]
