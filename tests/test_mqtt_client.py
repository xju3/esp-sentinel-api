from types import SimpleNamespace

from src.models import messages_pb2
from src.mqtt.client import MQTTClient
from src.processor.rms_report_processor import RmsReportProcessor


class StubDispatcher:
    def __init__(self) -> None:
        self.payloads = []

    def dispatch(self, payload) -> None:
        self.payloads.append(payload)


class StubRmsProcessor:
    def __init__(self) -> None:
        self.reports = []

    def save_direct_report(self, report: messages_pb2.MsgRmsReport) -> None:
        self.reports.append(report)


def test_on_message_parses_direct_rms_report():
    dispatcher = StubDispatcher()
    rms_processor = StubRmsProcessor()
    mqtt_client = MQTTClient(dispatcher=dispatcher, rms_processor=rms_processor)

    report = messages_pb2.MsgRmsReport(
        sn=2101,
        temperature=26.5,
        iso=6,
        rms_x=1.1,
        rms_y=1.2,
        rms_z=1.3,
        rms_m=1.4,
        peak_x=2.1,
        peak_y=2.2,
        peak_z=2.3,
        peak_m=2.4,
    )

    mqtt_client.on_message(None, None, SimpleNamespace(payload=report.SerializeToString()))

    assert len(rms_processor.reports) == 1
    assert rms_processor.reports[0].sn == 2101
    assert dispatcher.payloads == []


def test_on_message_falls_back_to_msgpayload_dispatch():
    dispatcher = StubDispatcher()
    rms_processor = StubRmsProcessor()
    mqtt_client = MQTTClient(dispatcher=dispatcher, rms_processor=rms_processor)

    payload = messages_pb2.MsgPayload(
        sn=2101,
        et=0,
        ts=1747305600123,
        data=b"legacy-machine-status",
    )

    mqtt_client.on_message(None, None, SimpleNamespace(payload=payload.SerializeToString()))

    assert len(dispatcher.payloads) == 1
    assert dispatcher.payloads[0].sn == 2101
    assert dispatcher.payloads[0].et == 0
    assert rms_processor.reports == []


def test_rms_report_processor_maps_flat_fields(monkeypatch):
    captured = {}

    class DummySession:
        def close(self) -> None:
            captured["closed"] = True

    def fake_create_rms_report(db, report) -> None:
        captured["db"] = db
        captured["report"] = report

    monkeypatch.setattr(
        "src.processor.rms_report_processor.crud.create_rms_report",
        fake_create_rms_report,
    )

    processor = RmsReportProcessor(session_factory=DummySession)
    report = messages_pb2.MsgRmsReport(
        sn=3101,
        temperature=31.2,
        iso=4,
        rms_x=3.1,
        rms_y=3.2,
        rms_z=3.3,
        rms_m=3.4,
        peak_x=4.1,
        peak_y=4.2,
        peak_z=4.3,
        peak_m=4.4,
    )

    processor.save_direct_report(report)

    saved = captured["report"]
    assert saved.sn == 3101
    assert saved.event_type == RmsReportProcessor.RMS_EVENT_TYPE
    assert saved.rms.x == 3.1
    assert saved.peak.m == 4.4
    assert saved.crest is None
    assert saved.impulse is None
    assert captured["closed"] is True
