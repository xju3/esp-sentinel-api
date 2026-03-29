from ...models import messages_pb2
from ...processor.rms_report_processor import rms_report_processsor
from ..dispatcher import MessageProcessor


class RmsReportProcessor(MessageProcessor):
    def __init__(self, processor=rms_report_processsor) -> None:
        self._processor = processor

    def process(self, payload: messages_pb2.MsgPayload, data: bytes) -> None:
        self._processor.save_from_proto(payload, data)
