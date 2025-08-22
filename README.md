# RTBF - Right To Be Forgotten

[![License](https://img.shields.io/badge/License-GPL_v3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![Code Quality](https://github.com/jinglemansweep/rtbf/actions/workflows/code-quality.yml/badge.svg)](https://github.com/jinglemansweep/rtbf/actions/workflows/code-quality.yml)
[![Docker Build and Push](https://github.com/jinglemansweep/rtbf/actions/workflows/docker-build.yml/badge.svg)](https://github.com/jinglemansweep/rtbf/actions/workflows/docker-build.yml)
[![Code style: black](https://img.shields.io/badge/Code%20style-black-000000.svg)](https://github.com/psf/black)
[![Typing: mypy](https://img.shields.io/badge/Typing-mypy-blue.svg)](https://mypy.readthedocs.io/)

A Python tool for automatically managing Reddit comments with configurable expiration policies. RTBF helps you maintain privacy and control over your digital footprint by automatically deleting or replacing your Reddit comments after a specified time period.

## ✨ Features

- **Automatic Comment Management**: Set comments to expire after a configurable time period
- **Flexible Strategies**: Choose to delete comments, replace with custom text, or replace with random emojis
- **Continuous Monitoring**: Runs continuously in the background, checking for expired comments
- **Rate Limited**: Built-in rate limiting to respect Reddit's API guidelines
- **Docker Support**: Easy deployment with Docker containers
- **Configurable**: Extensive configuration options via environment variables
- **Secure**: No storage of credentials - uses environment variables only

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- Reddit account with API access
- Reddit application credentials (see [Setup](#-setup))

### Installation

#### Using Poetry (Recommended)

```bash
# Clone the repository
git clone https://github.com/jinglemansweep/rtbf.git
cd rtbf

# Install dependencies with Poetry
poetry install

# Run the application
poetry run rtbf
```

#### Using Docker

```bash
# Pull the image
docker pull ghcr.io/jinglemansweep/rtbf:latest

# Run with environment file
docker run -it --env-file .env ghcr.io/jinglemansweep/rtbf:latest
```

#### Using pip

```bash
# Clone and install
git clone https://github.com/jinglemansweep/rtbf.git
cd rtbf
pip install .

# Run the application
rtbf
```

## ⚙️ Setup

### Strategy Options

RTBF supports three different strategies for handling expired comments:

- **delete**: Permanently removes the comment from Reddit
- **update**: Replaces the comment content with custom text
- **emoji**: Replaces the comment content with a random common emoji

### Watermark Feature

When using the "update" or "emoji" strategies, RTBF can append a watermark to replacement text to identify comments that have already been processed. This prevents the tool from repeatedly updating the same comments in future runs. Comments containing the watermark will be automatically skipped.

- **WATERMARK**: The text used to identify processed comments (default: `#rtbf`)
- **APPEND_WATERMARK**: Whether to automatically append the watermark (default: `true`)

### 1. Reddit API Setup

1. Go to [Reddit App Preferences](https://www.reddit.com/prefs/apps)
2. Click "Create App" or "Create Another App"
3. Fill in the details:
   - **Name**: Choose any name (e.g., "RTBF Comment Manager")
   - **App type**: Select "script"
   - **Description**: Optional
   - **About URL**: Optional
   - **Redirect URI**: `http://localhost:8080` (required but not used)
4. Note down your **Client ID** (under the app name) and **Client Secret**

### 2. Environment Configuration

Create a `.env` file in the project root:

```bash
# Required Reddit API credentials
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_reddit_password
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=RTBF/1.0 by u/your_username

# Optional configuration (with defaults)
EXPIRE_MINUTES=120                          # Comments older than 2 hours will be processed
STRATEGY=delete                             # "delete", "update", or "emoji"
REPLACEMENT_TEXT=[Comment deleted by user]  # Text to replace with if strategy=update
WATERMARK=#rtbf                             # Watermark to identify processed comments
APPEND_WATERMARK=true                       # Append watermark to replacement text
CHECK_INTERVAL_MINUTES=10                   # Check every 10 minutes
```

## 📋 Configuration Options

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `REDDIT_USERNAME` | Your Reddit username | - | ✅ |
| `REDDIT_PASSWORD` | Your Reddit password | - | ✅ |
| `REDDIT_CLIENT_ID` | Reddit app client ID | - | ✅ |
| `REDDIT_CLIENT_SECRET` | Reddit app client secret | - | ✅ |
| `REDDIT_USER_AGENT` | User agent string | `comment_manager by u/user` | ❌ |
| `EXPIRE_MINUTES` | Minutes before comments expire | `120` | ❌ |
| `STRATEGY` | Action: "delete", "update", or "emoji" | `delete` | ❌ |
| `REPLACEMENT_TEXT` | Replacement text for updates (ignored for emoji strategy) | `[Comment deleted by user]` | ❌ |
| `WATERMARK` | Watermark to identify processed comments | `#rtbf` | ❌ |
| `APPEND_WATERMARK` | Append watermark to replacement text | `true` | ❌ |
| `CHECK_INTERVAL_MINUTES` | Minutes between checks | `10` | ❌ |

## 🐳 Docker Usage

### Using Docker Compose

Create a `docker-compose.yml`:

```yaml
version: '3.8'
services:
  rtbf:
    image: ghcr.io/jinglemansweep/rtbf:latest
    env_file:
      - .env
    restart: unless-stopped
    container_name: rtbf
```

Run with:
```bash
docker-compose up -d
```

### Manual Docker Run

```bash
# Build locally
docker build -t rtbf .

# Run with environment file
docker run -d --name rtbf --env-file .env rtbf

# Or with individual environment variables
docker run -d --name rtbf \
  -e REDDIT_USERNAME=your_username \
  -e REDDIT_PASSWORD=your_password \
  -e REDDIT_CLIENT_ID=your_client_id \
  -e REDDIT_CLIENT_SECRET=your_secret \
  -e EXPIRE_MINUTES=120 \
  rtbf
```

## 🔧 Usage

### Running the Application

```bash
# With Poetry
poetry run rtbf

# With Python module
python -m rtbf

# With pip installation
rtbf
```

### Example Output

```
2024-01-15 10:30:00 - INFO - Starting comment manager...
2024-01-15 10:30:00 - INFO - Configuration: EXPIRE_MINUTES=120, STRATEGY=delete, CHECK_INTERVAL=10
2024-01-15 10:30:01 - INFO - Authenticated as: your_username
2024-01-15 10:30:01 - INFO - Checking for comments older than 120 minutes (cutoff: 2024-01-15 08:30:01)
2024-01-15 10:30:02 - INFO - Found expired comment from 2024-01-15 08:15:30: abc123
2024-01-15 10:30:03 - INFO - Deleted comment: abc123
2024-01-15 10:30:03 - INFO - Sleeping for 10 minutes...
```

## 🛡️ Security & Privacy

- **No Data Storage**: RTBF doesn't store any of your comments or credentials
- **Local Processing**: All processing happens locally or in your controlled environment
- **Environment Variables**: Credentials are managed via environment variables
- **Rate Limiting**: Built-in delays to respect Reddit's API limits
- **Open Source**: Full source code available for audit

## ⚠️ Important Notes

1. **Irreversible**: Deleted comments cannot be recovered
2. **API Limits**: Reddit has rate limits - the tool includes delays to respect them
3. **New Comments**: Only processes comments older than the configured time
4. **Active Monitoring**: The tool runs continuously and requires manual stopping

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting (`poetry run pre-commit run --all-files`)
5. Commit your changes (`git commit -m 'Add some amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Setup

```bash
# Clone and install development dependencies
git clone https://github.com/jinglemansweep/rtbf.git
cd rtbf
poetry install --with dev

# Install pre-commit hooks
poetry run pre-commit install

# Run code quality checks
poetry run black rtbf/
poetry run flake8 rtbf/
poetry run mypy rtbf/
```

## 📝 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## ⚖️ Legal Disclaimer

This tool is provided as-is for privacy management purposes. Users are responsible for:
- Complying with Reddit's Terms of Service
- Understanding the implications of automated comment deletion
- Ensuring they have the right to delete their own content

The authors are not responsible for any consequences of using this tool.
