# 🤝 Contributing to Agent Fleet Orchestrator

Thank you for your interest in contributing to **Agent Fleet Orchestrator**!

## 🛠️ Development Setup
1. Clone the repository and install dependencies:
   ```bash
   git clone https://github.com/akmalkhaniub/agent-fleet-orchestrator.git
   cd agent-fleet-orchestrator
   python -m venv venv
   source venv/bin/activate  # Windows: .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Run the test suite:
   ```bash
   python -m pytest tests/ -v
   ```

## 📜 Pull Request Guidelines
- Ensure all code conforms to `RULES.md` and `AGENTS.md`.
- All new features must include unit tests in `tests/`.
- Ensure 100% of tests pass before submitting your PR.
