# RTBF - Claude Development Guide

This document contains information for Claude Code to assist with development of the RTBF (Right To Be Forgotten) project.

## Instructions for Claude

- Run `pre-commit run --all-files` to ensure code quality and tests pass after making changes.
- Activate and use Python virtual environment located at `<project-root>/.venv` before any development or running commands.

## Project Overview

RTBF is a Reddit comment management tool that automatically deletes or replaces comments after a configurable time period to help users maintain privacy and control over their digital footprint.

## Technology Stack

- **Language**: Python 3.12+
- **Package Manager**: Poetry
- **Main Dependencies**:
  - `praw` (Python Reddit API Wrapper)
- **Dev Dependencies**:
  - `black` (code formatting)
  - `flake8` (linting)
  - `mypy` (type checking)
  - `isort` (import sorting)
  - `bandit` (security linting)
  - `pytest` (testing)
  - `pre-commit` (git hooks)

## Development Commands

### Setup
```bash
# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Install pre-commit hooks
poetry run pre-commit install
```

### Code Quality
```bash
# Format code
poetry run black rtbf/

# Sort imports
poetry run isort rtbf/

# Lint code
poetry run flake8 rtbf/

# Type check
poetry run mypy rtbf/

# Security check
poetry run bandit -r rtbf/

# Run all pre-commit hooks
poetry run pre-commit run --all-files
```

### Testing
```bash
# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=rtbf
```

### Build and Run
```bash
# Build package
poetry build

# Run locally
poetry run rtbf

# Or run module directly
poetry run python -m rtbf
```

### Docker
```bash
# Build Docker image
docker build -t rtbf .

# Run Docker container
docker run -it --env-file .env rtbf
```

## Project Structure

```
rtbf/
├── rtbf/                   # Main package
│   ├── __init__.py         # Package initialization
│   └── __main__.py         # Main application entry point
├── .github/                # GitHub Actions workflows
│   └── workflows/
│       ├── code-quality.yml
│       └── docker-build.yml
├── .pre-commit-config.yaml # Pre-commit hooks configuration
├── pyproject.toml          # Poetry configuration and dependencies
├── poetry.lock             # Locked dependency versions
├── Dockerfile              # Docker build configuration
├── .dockerignore           # Docker build ignore patterns
├── .env                    # Environment variables (not in git)
├── README.md               # User-facing documentation
└── CLAUDE.md               # This file - development guide
```

## Environment Variables

The application requires these environment variables:

- `REDDIT_USERNAME` - Reddit username
- `REDDIT_PASSWORD` - Reddit password
- `REDDIT_CLIENT_ID` - Reddit app client ID
- `REDDIT_CLIENT_SECRET` - Reddit app client secret
- `REDDIT_USER_AGENT` - User agent string (optional)
- `EXPIRE_MINUTES` - Minutes before comments expire (default: 120)
- `STRATEGY` - Action to take: "delete", "update", or "emoji" (default: "delete")
- `REPLACEMENT_TEXT` - Text to replace comments with if using "update" strategy (ignored for "emoji" strategy)
- `WATERMARK` - Watermark text to identify already processed comments (default: "#rtbf")
- `APPEND_WATERMARK` - Whether to append watermark to replacement text (default: "true")
- `CHECK_INTERVAL_MINUTES` - Minutes between checks (default: 10)

## License

This project is licensed under GPL-3.0. See the LICENSE file for details.

## Code Quality Standards

- **Line Length**: 88 characters (Black default)
- **Type Hints**: Required for all functions and methods
- **Import Sorting**: isort with Black profile
- **Security**: Bandit security checks required
- **Testing**: Pytest for unit tests
- **Pre-commit**: All checks must pass before commit

## CI/CD

GitHub Actions workflows:
- **Code Quality**: Runs linting, formatting, and type checks on PRs and pushes
- **Docker Build**: Builds and pushes Docker images to GitHub Container Registry

## Common Tasks

When working on this project, you'll typically need to:

1. **Lint and format**: `poetry run pre-commit run --all-files`
2. **Type check**: `poetry run mypy rtbf/`
3. **Test changes**: `poetry run python -m rtbf` (with proper .env setup)
4. **Build Docker**: `docker build -t rtbf .`
5. **Run quality checks**: Use the commands in the "Code Quality" section above

## Notes for Claude

- Always run linting and type checking after code changes
- Use Poetry for all dependency management
- Follow the existing code style and patterns
- Ensure all environment variables are properly documented
- Test Docker builds when making changes to dependencies or build process
- The project uses GPL-3.0 license - ensure any code additions are compatible
