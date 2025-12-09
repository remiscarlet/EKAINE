import logging
import os
import signal
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)


class WatchdogTimer:
    """
    Detects hung/deadlocked async processes by monitoring task progress.
    If no progress for N seconds, sends SIGTERM to self.
    """

    def __init__(self, timeout_seconds: float = 300.0, check_interval: float = 10.0):
        self.timeout_seconds = timeout_seconds
        self.check_interval = check_interval
        self.last_progress = time.time()
        self.thread: Optional[threading.Thread] = None
        self.running = False

    def start(self) -> None:
        """Start the watchdog in a background thread."""
        self.running = True
        self.last_progress = time.time()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info(f"Watchdog timer started (timeout={self.timeout_seconds}s)")

    def stop(self) -> None:
        """Stop the watchdog."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
        logger.info("Watchdog timer stopped")

    def heartbeat(self) -> None:
        """Call this from your main event loop to signal progress."""
        logger.debug("Heartbeat Emitted")
        self.last_progress = time.time()

    def _run(self) -> None:
        """Background thread that monitors for timeouts."""
        while self.running:
            time.sleep(self.check_interval)
            elapsed = time.time() - self.last_progress

            if elapsed > self.timeout_seconds:
                logger.critical(
                    f"Watchdog timeout: no progress for {elapsed:.1f}s. " f"Process appears hung. Triggering restart..."
                )

                # Force exit so Docker restarts. Use os._exit to immediately terminate
                # the process (bypasses Python signal handlers and cleanup which may
                # be blocked by C-extensions). Fall back to SIGKILL if needed.
                try:
                    os._exit(1)
                except Exception:
                    os.kill(os.getpid(), signal.SIGKILL)
