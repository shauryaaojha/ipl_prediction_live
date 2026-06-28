"""Windows desktop notifications.

Sends toast notifications for scrape completion, errors, and status updates.
Falls back gracefully if notification libraries aren't available.
"""

from __future__ import annotations

from loguru import logger


def send_notification(title: str, message: str, duration: int = 5) -> None:
    """Send a Windows desktop notification.

    Tries win10toast first, then plyer, then logs the message.
    """
    # Try win10toast
    try:
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
        toaster.show_toast(
            title,
            message,
            duration=duration,
            threaded=True,
        )
        return
    except ImportError:
        pass
    except Exception as e:
        logger.debug("win10toast failed: {}", e)

    # Try plyer
    try:
        from plyer import notification as plyer_notif
        plyer_notif.notify(
            title=title,
            message=message,
            timeout=duration,
            app_name="IPL2026 Scraper",
        )
        return
    except ImportError:
        pass
    except Exception as e:
        logger.debug("plyer failed: {}", e)

    # Fallback: just log it
    logger.info("[NOTIFICATION] {}: {}", title, message)
