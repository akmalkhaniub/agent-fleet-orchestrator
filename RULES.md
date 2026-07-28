# Defensive Coding & Architectural Rules

All coding agents in the fleet must adhere to these project conventions:

1. **Defensive Coding**:
   - Always validate inputs and handle potential null/empty data gracefully.
   - Do NOT swallow exceptions silently in try-except blocks.

2. **No Dynamic Execution**:
   - Forbidden: Use of `eval()` or `exec()` is strictly banned across all files.

3. **Documentation**:
   - Every public module, class, and function must include explanatory docstrings.

4. **Testing**:
   - Every feature implementation task MUST be accompanied by unit tests covering nominal and edge cases.
   - Minimum target test coverage: **80%**.

5. **Inter-Agent Coordination**:
   - Log task state transitions and questions in `/coordination` using structured JSON messages.
