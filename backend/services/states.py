from db.models import DeliveryStatus
ALLOWED: dict[DeliveryStatus, set[DeliveryStatus]] = {
    DeliveryStatus.ORDER_RECEIVED:   {DeliveryStatus.BOOKED, DeliveryStatus.CANCELLED},
    DeliveryStatus.BOOKED:           {DeliveryStatus.PICKUP_PENDING, DeliveryStatus.CANCELLED},
    DeliveryStatus.PICKUP_PENDING:   {DeliveryStatus.AGENT_ASSIGNED, DeliveryStatus.CANCELLED},
    DeliveryStatus.AGENT_ASSIGNED:   {DeliveryStatus.PICKED_UP, DeliveryStatus.PICKUP_FAILED, DeliveryStatus.CANCELLED},
    DeliveryStatus.PICKUP_FAILED:    {DeliveryStatus.PICKUP_PENDING, DeliveryStatus.CANCELLED},  # retry/reassign
    DeliveryStatus.PICKED_UP:        {DeliveryStatus.IN_TRANSIT},
    DeliveryStatus.IN_TRANSIT:       {DeliveryStatus.OUT_FOR_DELIVERY},
    DeliveryStatus.OUT_FOR_DELIVERY: {DeliveryStatus.DELIVERED, DeliveryStatus.DELIVERY_FAILED},
    DeliveryStatus.DELIVERY_FAILED:  {DeliveryStatus.OUT_FOR_DELIVERY, DeliveryStatus.RETURNED},
    DeliveryStatus.DELIVERED:        set(),
    DeliveryStatus.RETURNED:         set(),
    DeliveryStatus.CANCELLED:        set(),
}