from ...core.logging import setup_logging
from ...models import messages_pb2
from ..dispatcher import MessageProcessor

logger = setup_logging()


class UnknownMessageProcessor(MessageProcessor):
    def process(self, payload: messages_pb2.MsgPayload, data: bytes) -> None:
        logger.warning(f"Received unknown event type {payload.et} for SN {payload.sn}")
