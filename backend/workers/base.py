# workers/base.py
import logging
import os
import signal
import time

from kafka import KafkaConsumer
from pydantic import ValidationError
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session

from db.engine import engine
from db.models import ProcessedEvent
from services.events import EventEnvelope
from services.kafka import publish_event

logger = logging.getLogger(__name__)

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9094")
MAX_TRIES = 3
stop = False


def _term(*_):
    global stop
    stop = True

# If event or process cant be fixed
def _dead_letter(topic: str, msg, group_id: str, error: str) -> None:
    publish_event(
        f"{topic}.dlq",
        key=msg.key.decode() if msg.key else "unknown",
        value={"original": msg.value.decode(errors="replace"),
               "failed_in": group_id, "error": error[:500]},
    )
    logger.error("Dead-lettered message in %s: %s", group_id, error[:200])


def _process(group_id: str, topic: str, handlers: dict, msg) -> None:
    # 1. validate the envelope
    try:
        env = EventEnvelope.model_validate_json(msg.value)
    except ValidationError as exc:
        _dead_letter(topic, msg, group_id, f"invalid envelope: {exc}")  # retrying can't fix it
        return

    # 2. is this event meant for us?
    handler = handlers.get(env.event_type)
    if handler is None:
        return

    # 3-4. dedupe + handler in one transaction, with retries
    last_error = ""
    for attempt in range(1, MAX_TRIES + 1):
        try:
            with Session(engine) as session:
                res = session.execute(
                    insert(ProcessedEvent)
                    .values(event_id=env.event_id, consumer=group_id)
                    .on_conflict_do_nothing()
                )
                if res.rowcount == 0:       # already processed by this consumer
                    return
                handler(env,session)       # <- the dispatcher/notifier logic
                session.commit()            # dedupe row and handler changes together
            return
        except Exception as exc:
            last_error = repr(exc)
            logger.warning("%s failed on %s (%s/%s): %s",
                           group_id, env.event_id, attempt, MAX_TRIES, exc)
            time.sleep(attempt)             # small backoff

    _dead_letter(topic, msg, group_id, last_error)


def run_consumer(group_id: str, topic: str, handlers: dict) -> None:
    signal.signal(signal.SIGTERM, _term)
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=BOOTSTRAP,
        group_id=group_id,              # each worker type has its own group
        enable_auto_commit=False,       # we commit manually after success
        auto_offset_reset="earliest",
    )
    logger.info("%s consuming %s", group_id, topic)
    try:
        while not stop:
            batch = consumer.poll(timeout_ms=1000, max_records=1)
            for records in batch.values():
                for msg in records:
                    _process(group_id, topic, handlers, msg)
                    consumer.commit()   # 5. only now does the offset move forward
    finally:
        consumer.close()