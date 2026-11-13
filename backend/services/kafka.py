from kafka import KafkaProducer

def publish_event(topic: str, key: str, value: dict):
    global _producer
    if _producer is None:
        _producer = KafkaProducer(
            bootstrap_servers=os.environ.get("localhost:9094"),
            key_serializer=lambda k: k.encode(),
            value_serializer=lambda v: json.dumps(v).encode(),
        )
    _producer.send(topic, key=key, value=value).get(timeout=5)
