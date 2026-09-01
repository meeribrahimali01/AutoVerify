# Sandbox container for executing user submitted automata converters
FROM python:3.12-slim

WORKDIR /sandbox

# Create unprivileged execution user
RUN useradd -m -u 1001 sandboxuser

USER sandboxuser

CMD ["python3"]
