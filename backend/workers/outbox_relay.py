import logging
import signal
import time
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, col, select

from db.engine import engine
from db.models import OutboxEvent
from services.kafka import publish_event

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 10
MAX_CONSECUTIVE_FAILS = 3
stop = False


def _term(*_):
    global stop
    stop = True


def now() -> datetime:
    return datetime.now(timezone.utc)


def relay_once(batch: int = 50) -> int:
    with Session(engine) as session:
        rows = session.exec(
            select(OutboxEvent)
            .where(col(OutboxEvent.published_at).is_(None),
                   OutboxEvent.next_attempt_at <= now())
            .order_by(OutboxEvent.created_at)
            .limit(batch)
            .with_for_update(skip_locked=True)
        ).all()

        failed_keys: set[str] = set()
        consecutive_fails = 0

        for row in rows:
            if row.key in failed_keys:          
                continue
            if consecutive_fails >= MAX_CONSECUTIVE_FAILS:  
                break
            try:
                publish_event(row.topic, key=row.key, value=row.payload, timeout=5)
                row.published_at = now()
                consecutive_fails = 0
            except Exception as exc:
                row.attempts += 1
                row.last_error = str(exc)[:500]
                row.next_attempt_at = now() + timedelta(seconds=min(2 ** row.attempts, 300))
                failed_keys.add(row.key)
                consecutive_fails += 1
                level = logging.ERROR if row.attempts >= MAX_ATTEMPTS else logging.WARNING  
                logger.log(level, "Publish failed for %s (attempt %s): %s",
                           row.id, row.attempts, exc)
            session.add(row)

        session.commit()
        return len(rows)


def loop():
    signal.signal(signal.SIGTERM, _term)                 # fix 5
    while not stop:
        try:
            if relay_once() == 0:
                time.sleep(1)
        except Exception:                                # fix 3
            logger.exception("relay_once crashed, retrying in 5s")
            time.sleep(5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    loop()