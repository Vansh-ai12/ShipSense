import logging
from sqlmodel import Session

from services.events import EventEnvelope, EventType
from workers.base import run_consumer

logger = logging.getLogger(__name__)


def notify_client(env: EventEnvelope, session: Session) -> None:
    logger.info("NOTIFY client: %s for shipment %s", env.event_type, env.shipment_id)


HANDLERS = {
    EventType.AGENT_ASSIGNED: notify_client,
    EventType.NO_AGENT_AVAILABLE: notify_client,
    EventType.PARCEL_PICKED_UP: notify_client,
    EventType.DELIVERY_FAILED: notify_client,
    EventType.SHIPMENT_ON_HOLD: notify_client,
    EventType.DELIVERED: notify_client,
}


def main():
    run_consumer("notifier", "shipment-events", HANDLERS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()