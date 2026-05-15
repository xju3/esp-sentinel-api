import time

from ..core.logging import setup_logging
from ..dal import crud
from ..dal.database import SessionLocal
from ..models import messages_pb2, schemas

logger = setup_logging()


class RmsReportProcessor:
    RMS_EVENT_TYPE = 1

    def __init__(self, session_factory=SessionLocal) -> None:
        self._session_factory = session_factory

    def _triaxial_value(self, x: float, y: float, z: float, m: float) -> schemas.TriaxialValue:
        return schemas.TriaxialValue(
            x=float(x),
            y=float(y),
            z=float(z),
            m=float(m),
        )

    def save_from_proto(self, payload: messages_pb2.MsgPayload, data: bytes) -> None:
        report_proto = messages_pb2.MsgRmsReport()
        report_proto.ParseFromString(data)
        self._save_report(
            report_proto=report_proto,
            sn=int(payload.sn or report_proto.sn),
            event_type=int(payload.et),
            source=f"MsgPayload data length={len(data)}",
        )

    def save_direct_report(self, report_proto: messages_pb2.MsgRmsReport) -> None:
        self._save_report(
            report_proto=report_proto,
            sn=int(report_proto.sn),
            event_type=self.RMS_EVENT_TYPE,
            source="direct MQTT payload",
        )

    def _save_report(
        self,
        report_proto: messages_pb2.MsgRmsReport,
        sn: int,
        event_type: int,
        source: str,
    ) -> None:
        if sn <= 0:
            raise ValueError("MsgRmsReport is missing a valid sn")

        logger.info(
            "Processing RMS report for SN %s, event_type %s from %s",
            sn,
            event_type,
            source,
        )

        logger.info(
            "Raw protobuf data - temperature: %s, iso: %s",
            report_proto.temperature,
            report_proto.iso,
        )
        logger.info(
            "RMS values - x: %s, y: %s, z: %s, m: %s",
            report_proto.rms_x,
            report_proto.rms_y,
            report_proto.rms_z,
            report_proto.rms_m,
        )

        db_session = self._session_factory()
        try:
            received_at = int(time.time() * 1000)
            report_schema = schemas.RmsReportCreate(
                sn=sn,
                event_type=event_type,
                timestamp=received_at,
                rms=self._triaxial_value(
                    report_proto.rms_x,
                    report_proto.rms_y,
                    report_proto.rms_z,
                    report_proto.rms_m,
                ),
                peak=self._triaxial_value(
                    report_proto.peak_x,
                    report_proto.peak_y,
                    report_proto.peak_z,
                    report_proto.peak_m,
                ),
                temperature=float(report_proto.temperature),
                iso=int(report_proto.iso),
            )

            crud.create_rms_report(db=db_session, report=report_schema)

            logger.info(
                "Saved RMS report for SN %s to database, temperature=%s",
                sn,
                report_proto.temperature,
            )

        except Exception as e:
            logger.error(f"Failed to process or save RMS report for SN {sn}: {e}")
        finally:
            db_session.close()


rms_report_processsor = RmsReportProcessor()
