FROM python:3.11-slim

WORKDIR /app

# Install git for worktree operations
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Configure default git identity
RUN git config --global user.name "Fleet Orchestrator" && \
    git config --global user.email "orchestrator@local"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "cli.py", "dashboard", "--port", "8000", "--host", "0.0.0.0"]
