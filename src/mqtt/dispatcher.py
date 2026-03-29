from abc import ABC, abstractmethod
from typing import Dict

from ..models import messages_pb2


class MessageProcessor(ABC):
    @abstractmethod
    def process(self, payload: messages_pb2.MsgPayload, data: bytes) -> None:
        raise NotImplementedError


class MessageDispatcher:
    def __init__(self, processors: Dict[int, MessageProcessor], default_processor: MessageProcessor) -> None:
        self._processors = processors
        self._default_processor = default_processor

    def dispatch(self, payload: messages_pb2.MsgPayload) -> None:
        processor = self._processors.get(payload.et, self._default_processor)
        processor.process(payload, payload.data)
