import logging
import os
import time
from datetime import datetime, timedelta
from queue import Queue
from threading import Thread
from typing import Any, Callable, Optional

import praw

REDDIT_USERNAME = os.getenv("REDDIT_USERNAME")
REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "comment_manager by u/user")

EXPIRE_MINUTES = int(os.getenv("EXPIRE_MINUTES", "120"))
STRATEGY = os.getenv("STRATEGY", "delete")
REPLACEMENT_TEXT = os.getenv("REPLACEMENT_TEXT", "[Comment deleted by user]")
WATERMARK = os.getenv("WATERMARK", "#rtbf")
APPEND_WATERMARK = os.getenv("APPEND_WATERMARK", "true").lower() == "true"
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "10"))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
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

    if STRATEGY not in ["delete", "update"]:
        raise ValueError(f"Invalid STRATEGY '{STRATEGY}'. Must be 'delete' or 'update'")


validate_config()

reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    username=REDDIT_USERNAME,
    password=REDDIT_PASSWORD,
    user_agent=REDDIT_USER_AGENT,
)

praw_queue = PrawQueue()


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
        for comment in reddit.user.me().comments.new(limit=100):
            comment_time = datetime.fromtimestamp(comment.created_utc)

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
        f"WATERMARK={WATERMARK}, APPEND_WATERMARK={APPEND_WATERMARK}"
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
