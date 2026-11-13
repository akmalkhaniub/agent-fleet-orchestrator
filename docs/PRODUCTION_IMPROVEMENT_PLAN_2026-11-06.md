# Google Cloud Professional Agentic Architect: Production Improvement Plan
## Repository: agent-fleet-orchestrator
**Audit Date:** November 6, 2026  
**Target Standard:** Google Cloud Professional Agentic Architect (Domain 3: Multi-Agent & Domain 4: Production Observability)

---

### Current Assessment
A flagship multi-agent engine (388k lines, 2,559 files, FastMCP, LiteLLM) decomposing user intents into task DAGs executed concurrently across isolated git worktrees (`.worktrees/task-<id>`).

### Critical Gaps
1. **Missing Cloud Trace / OpenTelemetry Spans:** While logging is functional locally, multi-agent reasoning steps are not exported using OpenTelemetry Gen AI semantic conventions, preventing waterfall visualization in Google Cloud Trace.
2. **Reasoning Loop Vulnerability:** Lacks explicit circuit-breaker limits (`max_iterations`) on cyclic task dependencies, risking runaway API token billing.
3. **No Agent Registry Manifest:** Does not provide an automated export command to register the fleet into Google Cloud Agent Registry.
4. **Principal Access Boundary (PAB) Undefined:** Lacks declarative policy files restricting the orchestrator identity to specific GCP resource boundaries.

---

### Actionable Implementation Steps

#### 1. OpenTelemetry Gen AI Semantic Conventions
Export multi-agent spans to Google Cloud Trace:
```python
from opentelemetry import trace
from opentelemetry.exporter.gcp_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(CloudTraceSpanExporter()))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("agent-fleet-orchestrator")

with tracer.start_as_current_span("agent_task_execution") as span:
    span.set_attribute("gen_ai.system", "google_adk")
    span.set_attribute("gen_ai.request.model", "gemini-2.0-flash")
    span.set_attribute("agent.task_id", task_id)
```

#### 2. Implement Loop Circuit Breaker on Task DAGs
Enforce strict execution thresholds in the task coordinator:
```python
MAX_TURNS_PER_TASK = 5

if current_iteration > MAX_TURNS_PER_TASK:
    raise AgentLoopCircuitBreakerException(
        f"Task {task_id} exceeded maximum turns ({MAX_TURNS_PER_TASK}). Circuit breaker tripped."
    )
```

#### 3. Agent Registry Registration Script (`scripts/register_fleet.py`)
Add an automated registration script to register the fleet in Google Cloud Agent Registry:
```bash
gcloud agent-registry agents register fleet-orchestrator \
  --location=us-central1 \
  --display-name="Agent Fleet Orchestrator" \
  --manifest-url="https://fleet-run-xyz.a.run.app/.well-known/agent.json"
```

#### 4. Define Principal Access Boundary (PAB) YAML Policy
Author a PAB policy restricting the fleet identity strictly to designated project storage buckets and Cloud SQL instances.
