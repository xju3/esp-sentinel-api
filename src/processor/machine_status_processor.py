import time
from typing import Dict

from ..core.logging import setup_logging
from ..dal import crud
from ..dal.database import SessionLocal
from ..models import messages_pb2, schemas

logger = setup_logging()


class MachineStatusProcessor:
    def __init__(self, session_factory=SessionLocal) -> None:
        self._machine_data: Dict[int, schemas.MachineData] = {}
        self._session_factory = session_factory

    def _triaxial_from_proto(self, proto: messages_pb2.MsgTriaxialValue) -> schemas.TriaxialValue:
        return schemas.TriaxialValue(
            x=float(proto.x),
            y=float(proto.y),
            z=float(proto.z),
            m=float(proto.m),
        )

    def update_from_proto(self, payload: messages_pb2.MsgPayload, data: bytes) -> None:
        status = messages_pb2.MsgMachineStatus()
        status.ParseFromString(data)

        rms_value = self._triaxial_from_proto(status.rms)
        machine_status = schemas.MachineStatus(
            rms=rms_value,
            st=status.st,
        )

        received_at = int(time.time() * 1000)
        machine_data = schemas.MachineData(
            sn=payload.sn,
            et=payload.et,
            received_at=received_at,
            status=machine_status,
        )

        self._machine_data[payload.sn] = machine_data

        db_session = self._session_factory()
        try:
            status_schema = schemas.MachineStatusCreate(
                sn=payload.sn,
                event_type=payload.et,
                rms=rms_value,
                st=int(status.st),
            )
            crud.create_machine_status(db=db_session, status=status_schema)
        except Exception as e:
            logger.error(f"Failed to save machine status for SN {payload.sn}: {e}")
        finally:
            db_session.close()

        logger.info(
            f"Processed machine status for SN {payload.sn}: "
            f"x={machine_status.rms.x:.3f}, y={machine_status.rms.y:.3f}, "
            f"z={machine_status.rms.z:.3f}, m={machine_status.rms.m:.3f}, st={machine_status.st}"
        )

    def get_machine_data(self, sn: int) -> schemas.MachineData | None:
        return self._machine_data.get(sn)

    def get_all_machines(self) -> list[int]:
        return list(self._machine_data.keys())


machine_status_processor = MachineStatusProcessor()
