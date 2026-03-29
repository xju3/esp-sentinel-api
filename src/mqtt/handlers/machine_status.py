from ...models import messages_pb2
from ...processor.machine_status_processor import machine_status_processor
from ..dispatcher import MessageProcessor


class MachineStatusProcessor(MessageProcessor):
    def __init__(self, processor=machine_status_processor) -> None:
        self._processor = processor

    def process(self, payload: messages_pb2.MsgPayload, data: bytes) -> None:
        self._processor.update_from_proto(payload, data)
