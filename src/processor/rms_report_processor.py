import time

from ..core.logging import setup_logging
from ..dal import crud
from ..dal.database import SessionLocal
from ..models import messages_pb2, schemas

logger = setup_logging()


class RmsReportProcessor:
    def __init__(self, session_factory=SessionLocal) -> None:
        self._session_factory = session_factory

    def _triaxial_from_proto(self, proto: messages_pb2.MsgTriaxialValue) -> schemas.TriaxialValue:
        return schemas.TriaxialValue(
            x=float(proto.x),
            y=float(proto.y),
            z=float(proto.z),
            m=float(proto.m),
        )

    def save_from_proto(self, payload: messages_pb2.MsgPayload, data: bytes) -> None:
        logger.info(
            f"Processing RMS report for SN {payload.sn}, event_type {payload.et}, data length: {len(data)} bytes"
        )

        report_proto = messages_pb2.MsgRmsReport()
        report_proto.ParseFromString(data)

        logger.info(
            f"Raw protobuf data - temperature: {report_proto.temperature}, iso: {report_proto.iso}"
        )
        logger.info(
            "RMS values - x: %s, y: %s, z: %s, m: %s",
            report_proto.rms.x,
            report_proto.rms.y,
            report_proto.rms.z,
            report_proto.rms.m,
        )

        db_session = self._session_factory()
        try:
            received_at = int(time.time() * 1000)
            report_schema = schemas.RmsReportCreate(
                sn=payload.sn,
                event_type=payload.et,
                timestamp=received_at,
                rms=self._triaxial_from_proto(report_proto.rms),
                peak=self._triaxial_from_proto(report_proto.peak),
                crest=self._triaxial_from_proto(report_proto.crest),
                impulse=self._triaxial_from_proto(report_proto.impulse),
                temperature=float(report_proto.temperature),
                iso=int(report_proto.iso),
            )

            crud.create_rms_report(db=db_session, report=report_schema)

            logger.info(
                f"Saved RMS report for SN {payload.sn} to database, temperature={report_proto.temperature}"
            )

        except Exception as e:
            logger.error(f"Failed to process or save RMS report for SN {payload.sn}: {e}")
        finally:
            db_session.close()


rms_report_processsor = RmsReportProcessor()
