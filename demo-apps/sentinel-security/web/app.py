import os
import sys
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.scanner import ASTSecurityScanner
from src.remediator import SecurityRemediator

app = FastAPI(
    title="AI Code Security & Review Sentinel",
    description="Interactive Code Vulnerability Scanner & Remediation Engine",
    version="1.0.0",
)


class ScanRequest(BaseModel):
    code: str


@app.post("/api/scan")
def scan_code(req: ScanRequest):
    scanner = ASTSecurityScanner(req.code)
    issues = scanner.scan()

    remediator = SecurityRemediator()
    report = remediator.generate_remediation_report(issues)

    return {
        "issues_count": len(issues),
        "issues": [i.to_dict() for i in issues],
        "report": report,
    }


@app.get("/", response_class=HTMLResponse)
def serve_scanner_ui():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>AI Code Security Sentinel Scanner</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { background-color: #0b0f19; color: #f8fafc; font-family: system-ui, sans-serif; padding: 2rem; }
            .card { background-color: #151c2c; border: 1px solid #232d42; border-radius: 12px; }
            textarea { background-color: #090d16 !important; color: #38bdf8 !important; font-family: monospace; }
            pre { background-color: #090d16; color: #34d399; padding: 1rem; border-radius: 8px; font-size: 0.85rem; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card p-4 shadow mb-4">
                <h2 class="text-info fw-bold mb-1">🛡️ AI Code Security & Review Sentinel</h2>
                <p class="text-muted small">Autonomously built by Agent Fleet Orchestrator</p>
                <form id="scanForm">
                    <div class="mb-3">
                        <label class="form-label text-slate-300">Paste Python Source Code</label>
                        <textarea id="codeSource" class="form-control border-secondary" rows="8" required>def process_user_input(user_command):
    API_KEY = "sk_live_secretkey999"
    result = eval(user_command)
    import subprocess
    subprocess.Popen("rm -rf /tmp", shell=True)
    return result</textarea>
                    </div>
                    <button type="submit" class="btn btn-primary fw-bold">Run Security Audit Scan</button>
                </form>
            </div>
            <div id="resultsCard" class="card p-4 shadow d-none">
                <h4 class="text-success mb-3">Audit Scan Report & Automated Patches</h4>
                <div id="scanReport"></div>
            </div>
        </div>
        <script>
            document.getElementById('scanForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const code = document.getElementById('codeSource').value;
                const res = await fetch('/api/scan', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code })
                });
                const data = await res.json();
                document.getElementById('resultsCard').classList.remove('d-none');
                document.getElementById('scanReport').innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
            });
        </script>
    </body>
    </html>
    """
