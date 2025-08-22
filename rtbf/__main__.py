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
STRATEGY = os.getenv("STRATEGY", "delete")
REPLACEMENT_TEXT = os.getenv("REPLACEMENT_TEXT", "[Comment deleted by user]")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
LLM_PROMPT = os.getenv("LLM_PROMPT", "Rewrite this comment: {comment}")
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

    if STRATEGY not in ["delete", "update", "emoji", "llm"]:
        raise ValueError(
            f"Invalid STRATEGY '{STRATEGY}'. Must be 'delete', 'update', "
            f"'emoji', or 'llm'"
        )

    # Validate LLM configuration if LLM strategy is used
    if STRATEGY == "llm" and not LLM_API_KEY:
        raise ValueError("LLM_API_KEY is required when using 'llm' strategy")


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
            "Authorization": f"Bearer {LLM_API_KEY}",
        }

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
            logger.error(f"Unexpected API response format: {result}")
            return "[LLM response error]"

    except HTTPError as e:
        logger.error(f"LLM API HTTP error: {e.code} - {e.reason}")
        return "[LLM API error]"
    except URLError as e:
        logger.error(f"LLM API connection error: {e.reason}")
        return "[LLM connection error]"
    except json.JSONDecodeError as e:
        logger.error(f"LLM API JSON decode error: {e}")
        return "[LLM JSON error]"
    except Exception as e:
        logger.error(f"LLM API unexpected error: {e}")
        return "[LLM unexpected error]"


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


def process_expired_comments() -> None:
    """Process comments that have expired based on the configured time delay"""

    cutoff_time = datetime.now() - timedelta(minutes=EXPIRE_MINUTES)
    logger.info(
        f"Checking for comments older than {EXPIRE_MINUTES} minutes "
        f"(cutoff: {cutoff_time})"
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

            # Skip comments that already contain the watermark (already processed)
            if WATERMARK in comment.body:
                logger.debug(
                    f"Skipping comment {comment.id}: already contains watermark"
                )
                continue

            if comment_time < cutoff_time:
                logger.info(
                    f"Found expired comment from {comment_time}: " f"{comment.id}"
                )

                if STRATEGY == "delete":
                    delete_comment_queued(comment)
                elif STRATEGY == "update":
                    # Prepare replacement text with watermark
                    replacement_text = REPLACEMENT_TEXT
                    if APPEND_WATERMARK:
                        replacement_text = f"{REPLACEMENT_TEXT} {WATERMARK}"
                    update_comment_queued(comment, replacement_text)
                elif STRATEGY == "emoji":
                    # Replace with random emoji and watermark
                    replacement_text = get_random_emoji()
                    if APPEND_WATERMARK:
                        replacement_text = f"{replacement_text} {WATERMARK}"
                    update_comment_queued(comment, replacement_text)
                elif STRATEGY == "llm":
                    # Replace with LLM-generated text and watermark
                    replacement_text = call_llm_api(comment.body)
                    if APPEND_WATERMARK:
                        replacement_text = f"{replacement_text} {WATERMARK}"
                    update_comment_queued(comment, replacement_text)
            else:
                logger.debug(f"Comment from {comment_time} is not expired yet")

    except Exception as e:
        logger.error(f"Error processing comments: {e}")


def main() -> None:
    """Main loop to continuously monitor and process expired comments"""
    logger.info("Starting comment manager...")
    logger.info(
        f"Configuration: EXPIRE_MINUTES={EXPIRE_MINUTES}, "
        f"STRATEGY={STRATEGY}, CHECK_INTERVAL={CHECK_INTERVAL_MINUTES}, "
        f"WATERMARK={WATERMARK}, FLAG_IGNORE={FLAG_IGNORE}, "
        f"APPEND_WATERMARK={APPEND_WATERMARK}, LOG_LEVEL={LOG_LEVEL}, "
        f"COMMENT_LIMIT={COMMENT_LIMIT}"
    )

    if STRATEGY == "llm":
        logger.info(
            f"LLM Configuration: MODEL={LLM_MODEL}, "
            f"API_URL={LLM_API_URL}, "
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
