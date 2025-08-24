# RTBF - Claude Development Guide

This document contains information for Claude Code to assist with development of the RTBF (Right To Be Forgotten) project.

## Instructions for Claude

- Run `pre-commit run --all-files` to ensure code quality and tests pass after making changes.
- Activate and use Python virtual environment located at `<project-root>/.venv` before any development or running commands.

## Project Overview

RTBF is a Reddit comment management tool that uses a two-stage privacy system: first obfuscating comments (replacing content) after a short period, then permanently deleting them after a longer period. This provides immediate privacy protection while allowing for complete removal later.

## Two-Stage Privacy System

RTBF uses a sophisticated two-stage approach:

1. **Obfuscation Stage**: After `EXPIRE_MINUTES`, comments are replaced using the selected strategy (update/emoji/llm) while preserving the comment structure
2. **Destruction Stage**: After `DELETE_MINUTES`, comments are permanently deleted from Reddit

This design provides immediate privacy protection while allowing time to verify the system works correctly before permanent deletion.

**Priority Logic**:
- If `DELETE_MINUTES == EXPIRE_MINUTES`: Comments are deleted immediately (skipping obfuscation to save API requests)
- If comment is already obfuscated and deletion time reached: Delete immediately
- Otherwise: Obfuscate first, then delete when deletion time is reached

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
- `EXPIRE_MINUTES` - Minutes before comments are obfuscated (default: 120)
- `DELETE_MINUTES` - Minutes before comments are permanently deleted (default: 1440 = 24 hours)
- `STRATEGY` - Obfuscation method: "update", "emoji", or "llm" (default: "update")
- `REPLACEMENT_TEXT` - Text to replace comments with if using "update" strategy (ignored for "emoji" and "llm" strategies)
- `LLM_MODEL` - LLM model to use (default: "gpt-3.5-turbo")
- `LLM_PROMPT` - Prompt template for LLM with {comment} placeholder (default: "Rewrite this comment: {comment}")
- `LLM_API_URL` - OpenAI-compatible API URL (default: "https://api.openai.com/v1/chat/completions")
- `LLM_API_KEY` - API key for LLM service (optional, not needed for Ollama)
- `WATERMARK` - Watermark text to identify already processed comments (default: "#rtbf")
- `FLAG_IGNORE` - Ignore flag to protect comments from processing ("forget never") (default: "/fn")
- `APPEND_WATERMARK` - Whether to append watermark to replacement text (default: "true")
- `LOG_LEVEL` - Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: "INFO")
- `COMMENT_LIMIT` - Maximum number of comments to retrieve per check (default: "100")
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
