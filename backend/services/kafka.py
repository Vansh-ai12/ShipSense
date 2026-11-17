import json
import os

from kafka import KafkaProducer

_producer: KafkaProducer | None = None


def _get_producer() -> KafkaProducer:
    global _producer
    if _producer is None:
        _producer = KafkaProducer(
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP", "localhost:9094"),
        acks="all",
        retries=3,
        max_in_flight_requests_per_connection=1,   # fix 1
        key_serializer=lambda k: k.encode("utf-8"),
        value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),  # fix 2
    )
    return _producer


def publish_event(topic: str, key: str, value: dict, timeout: int = 10) -> None:
    # .get() waits for the broker's acknowledgement and raises if the send failed
    _get_producer().send(topic, key=key, value=value).get(timeout=timeout)