import logging
import time
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from db.engine import engine
from db.models import OutboxEvent
from services.kafka import publish_event

logger = logging.getLogger(__name__)


def now() -> datetime:
    return datetime.now(timezone.utc)


def relay_once(batch: int = 50) -> int:
    with Session(engine) as session:
        rows = session.exec(
            select(OutboxEvent)
            .where(OutboxEvent.published_at.is_(None), OutboxEvent.next_attempt_at <= now())
            .order_by(OutboxEvent.created_at)
            .limit(batch)
            .with_for_update(skip_locked=True)     # two relays never take the same row
        ).all()

        for row in rows:
            try:
                publish_event(row.topic, key=row.key, value=row.payload)
                row.published_at = now()
            except Exception as exc:
                row.attempts += 1
                row.last_error = str(exc)[:500]
                row.next_attempt_at = now() + timedelta(seconds=min(2 ** row.attempts, 300))
                logger.warning("Publish failed for %s (attempt %s): %s", row.id, row.attempts, exc)
            session.add(row)

        session.commit()
        return len(rows)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    while True:
        if relay_once() == 0:
            time.sleep(1)