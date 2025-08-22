# Build stage
FROM python:3.12-slim AS builder

WORKDIR /app

# Copy project files
COPY pyproject.toml ./
COPY rtbf/ ./rtbf/

# Install Python dependencies and build wheel
RUN pip install --upgrade pip setuptools && \
    pip install --no-cache-dir build && \
    python -m build --wheel

# Runtime stage
FROM python:3.12-slim

# Create non-root user
RUN groupadd -r rtbf && useradd -r -g rtbf rtbf

WORKDIR /app

# Copy wheel from builder stage and install
COPY --from=builder /app/dist/*.whl ./
RUN pip install --no-cache-dir *.whl && rm *.whl

# Switch to non-root user
USER rtbf

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import rtbf; print('OK')" || exit 1

# Default command
CMD ["python", "-m", "rtbf"]