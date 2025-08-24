import json
import logging
import os
import random
import time
from datetime import datetime, timedelta
from queue import Queue
from threading import Thread
from typing import Any, Callable, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import praw

REDDIT_USERNAME = os.getenv("REDDIT_USERNAME")
REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "comment_manager by u/user")

EXPIRE_MINUTES = int(os.getenv("EXPIRE_MINUTES", "120"))
DELETE_MINUTES = int(os.getenv("DELETE_MINUTES", "1440"))  # Default: 24 hours
STRATEGY = os.getenv("STRATEGY", "update")  # Default changed from 'delete' to 'update'
REPLACEMENT_TEXT = os.getenv("REPLACEMENT_TEXT", "[Comment deleted by user]")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
LLM_PROMPT = os.getenv(
    "LLM_PROMPT", "Rewrite this comment in a more friendly tone: {comment}"
)
LLM_API_URL = os.getenv("LLM_API_URL", "https://api.openai.com/v1/chat/completions")
LLM_API_KEY = os.getenv("LLM_API_KEY")
WATERMARK = os.getenv("WATERMARK", "#rtbf")
FLAG_IGNORE = os.getenv("FLAG_IGNORE", "/fn")
APPEND_WATERMARK = os.getenv("APPEND_WATERMARK", "true").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
COMMENT_LIMIT = int(os.getenv("COMMENT_LIMIT", "100"))
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "30"))

# Common emojis for the emoji strategy
COMMON_EMOJIS = [
    "😀",
    "😂",
    "😊",
    "😍",
    "🤔",
    "😎",
    "😢",
    "😡",
    "🙄",
    "😴",
    "👍",
    "👎",
    "👌",
    "✌️",
    "🤷",
    "🔥",
    "💯",
    "❤️",
    "🎉",
    "🤝",
    "🌟",
    "⚡",
    "💡",
    "🎯",
    "🚀",
    "💪",
    "🎈",
    "🎁",
    "☕",
    "🍕",
]

# Configure logging with environment variable
log_level = getattr(logging, LOG_LEVEL, logging.INFO)
logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class PrawQueue:
    def __init__(self) -> None:
        self.queue: Queue = Queue()
        self.worker = Thread(target=self._worker, daemon=True)
        self.worker.start()

    def _worker(self) -> None:
        while True:
            func, args, kwargs, result_callback = self.queue.get()
            try:
                result = func(*args, **kwargs)
                if result_callback:
                    result_callback(result)
            except Exception as e:
                logger.error(f"Error executing queued operation: {e}")
            finally:
                self.queue.task_done()
                time.sleep(1)

    def put(
        self,
        func: Callable[..., Any],
        *args: Any,
        result_callback: Optional[Callable[[Any], None]] = None,
        **kwargs: Any,
    ) -> None:
        self.queue.put((func, args, kwargs, result_callback))


def validate_config() -> None:
    required_vars = [
        "REDDIT_USERNAME",
        "REDDIT_PASSWORD",
        "REDDIT_CLIENT_ID",
        "REDDIT_CLIENT_SECRET",
    ]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    if STRATEGY not in ["update", "emoji", "llm"]:
        raise ValueError(
            f"Invalid STRATEGY '{STRATEGY}'. Must be 'update', 'emoji', or 'llm'"
        )

    # LLM_API_KEY is optional (e.g., Ollama doesn't require authentication)
    # No validation needed for LLM_API_KEY


validate_config()

reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    username=REDDIT_USERNAME,
    password=REDDIT_PASSWORD,
    user_agent=REDDIT_USER_AGENT,
)

# Enable validation to avoid deprecation warning
reddit.validate_on_submit = True

praw_queue = PrawQueue()


def get_random_emoji() -> str:
    """Get a random emoji from the common emojis list."""
    return random.choice(COMMON_EMOJIS)


def call_llm_api(comment_text: str) -> str:
    """Call the LLM API to generate a replacement for the comment."""
    try:
        # Format the prompt with the comment text
        prompt = LLM_PROMPT.format(comment=comment_text)

        # Prepare the API request
        payload = {
            "model": LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
            "temperature": 0.7,
        }

        headers = {
            "Content-Type": "application/json",
        }

        # Add Authorization header only if API key is provided
        if LLM_API_KEY:
            headers["Authorization"] = f"Bearer {LLM_API_KEY}"

        # Make the API request
        request = Request(
            LLM_API_URL, data=json.dumps(payload).encode("utf-8"), headers=headers
        )

        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))

        # Extract the generated text
        if "choices" in result and len(result["choices"]) > 0:
            generated_text: str = result["choices"][0]["message"]["content"].strip()
            logger.debug(f"LLM generated replacement: {generated_text[:100]}...")
            return generated_text
        else:
            logger.error(
                f"Unexpected API response format: {result}, falling back to emoji"
            )
            return get_random_emoji()

    except HTTPError as e:
        logger.error(
            f"LLM API HTTP error: {e.code} - {e.reason}, falling back to emoji"
        )
        return get_random_emoji()
    except URLError as e:
        logger.error(f"LLM API connection error: {e.reason}, falling back to emoji")
        return get_random_emoji()
    except json.JSONDecodeError as e:
        logger.error(f"LLM API JSON decode error: {e}, falling back to emoji")
        return get_random_emoji()
    except Exception as e:
        logger.error(f"LLM API unexpected error: {e}, falling back to emoji")
        return get_random_emoji()


def delete_comment_queued(comment: praw.models.Comment) -> None:
    def _delete() -> None:
        comment.delete()
        logger.info(f"Deleted comment: {comment.id}")

    praw_queue.put(_delete)


def update_comment_queued(comment: praw.models.Comment, new_text: str) -> None:
    def _update() -> None:
        comment.edit(new_text)
        logger.info(f"Updated comment: {comment.id}")

    praw_queue.put(_update)


def obfuscate_comment(comment: praw.models.Comment) -> None:
    """Apply the selected obfuscation strategy to a comment."""
    if STRATEGY == "update":
        # Prepare replacement text with watermark
        replacement_text = REPLACEMENT_TEXT
        if APPEND_WATERMARK:
            replacement_text = f"{REPLACEMENT_TEXT} ^({WATERMARK})"
        update_comment_queued(comment, replacement_text)
    elif STRATEGY == "emoji":
        # Replace with random emoji and watermark
        replacement_text = get_random_emoji()
        if APPEND_WATERMARK:
            replacement_text = f"{replacement_text} ^({WATERMARK})"
        update_comment_queued(comment, replacement_text)
    elif STRATEGY == "llm":
        # Replace with LLM-generated text and watermark
        replacement_text = call_llm_api(comment.body)
        if APPEND_WATERMARK:
            replacement_text = f"{replacement_text} ^({WATERMARK})"
        update_comment_queued(comment, replacement_text)


def process_expired_comments() -> None:
    """Process comments using two-stage system: obfuscation first, then deletion"""

    # Calculate cutoff times for obfuscation and deletion
    obfuscation_cutoff = datetime.now() - timedelta(minutes=EXPIRE_MINUTES)
    deletion_cutoff = datetime.now() - timedelta(minutes=DELETE_MINUTES)

    logger.info(
        f"Checking comments: obfuscation after {EXPIRE_MINUTES} minutes "
        f"({obfuscation_cutoff}), deletion after {DELETE_MINUTES} minutes "
        f"({deletion_cutoff})"
    )

    try:
        for comment in reddit.user.me().comments.new(limit=COMMENT_LIMIT):
            comment_time = datetime.fromtimestamp(comment.created_utc)

            # Skip comments that contain the ignore flag ("forget never")
            if FLAG_IGNORE in comment.body:
                logger.debug(
                    f"Skipping comment {comment.id}: contains ignore flag "
                    f"'{FLAG_IGNORE}'"
                )
                continue

            # Determine action based on age and current state
            is_obfuscation_ready = comment_time < obfuscation_cutoff
            is_deletion_ready = comment_time < deletion_cutoff
            already_obfuscated = WATERMARK in comment.body

            # Priority 1: Delete if deletion time reached
            if is_deletion_ready:
                # If deletion and obfuscation timeouts are the same, prioritize delete
                if DELETE_MINUTES == EXPIRE_MINUTES or already_obfuscated:
                    logger.info(f"Deleting comment from {comment_time}: {comment.id}")
                    delete_comment_queued(comment)
                    continue
                # Otherwise, obfuscate first if not already done
                elif not already_obfuscated:
                    logger.info(
                        f"Obfuscating comment (deletion pending) from {comment_time}: "
                        f"{comment.id}"
                    )
                    obfuscate_comment(comment)
                    continue

            # Priority 2: Obfuscate if obfuscation time reached and not already done
            elif is_obfuscation_ready and not already_obfuscated:
                logger.info(f"Obfuscating comment from {comment_time}: {comment.id}")
                obfuscate_comment(comment)
                continue

            else:
                logger.debug(
                    f"Comment from {comment_time} not ready for processing yet"
                )

    except Exception as e:
        logger.error(f"Error processing comments: {e}")


def main() -> None:
    """Main loop to continuously monitor and process expired comments"""
    logger.info("Starting comment manager...")
    logger.info(
        f"Configuration: EXPIRE_MINUTES={EXPIRE_MINUTES} (obfuscation), "
        f"DELETE_MINUTES={DELETE_MINUTES} (deletion), STRATEGY={STRATEGY}, "
        f"CHECK_INTERVAL={CHECK_INTERVAL_MINUTES}, WATERMARK={WATERMARK}, "
        f"FLAG_IGNORE={FLAG_IGNORE}, APPEND_WATERMARK={APPEND_WATERMARK}, "
        f"LOG_LEVEL={LOG_LEVEL}, COMMENT_LIMIT={COMMENT_LIMIT}"
    )

    if STRATEGY == "llm":
        api_key_status = "configured" if LLM_API_KEY else "not set (unauthenticated)"
        logger.info(
            f"LLM Configuration: MODEL={LLM_MODEL}, "
            f"API_URL={LLM_API_URL}, API_KEY={api_key_status}, "
            f"PROMPT={LLM_PROMPT[:50]}{'...' if len(LLM_PROMPT) > 50 else ''}"
        )

    try:
        user = reddit.user.me()
        logger.info(f"Authenticated as: {user}")
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        return

    while True:
        try:
            process_expired_comments()
            logger.info(f"Sleeping for {CHECK_INTERVAL_MINUTES} minutes...")
            time.sleep(CHECK_INTERVAL_MINUTES * 60)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()
