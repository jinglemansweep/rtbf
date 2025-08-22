# Build stage
FROM python:3.12-slim AS builder

WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry

# Copy project files
COPY pyproject.toml poetry.lock* README.md ./
COPY rtbf/ ./rtbf/

# Configure Poetry and build
RUN poetry config virtualenvs.create false && \
    poetry install --only=main && \
    poetry build

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
