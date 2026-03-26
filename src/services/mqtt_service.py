import paho.mqtt.client as mqtt
import time
import threading
from typing import Dict, Generator
from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from ..config.settings import settings
from ..core.logging import setup_logging
from ..models import messages_pb2, schemas
from ..dal import crud, database
from ..dal.database import SessionLocal

logger = setup_logging()

# Dependency to get a DB session (kept for potential FastAPI route usage)
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_protocol_version(version_str: str):
    if version_str == "3.1":
        return mqtt.MQTTv31
    elif version_str == "3.1.1":
        return mqtt.MQTTv311
    elif version_str == "5.0" or version_str == "5":
        return mqtt.MQTTv5
    else:
        return mqtt.MQTTv311

class MessageProcessor(ABC):
    @abstractmethod
    def process(self, payload: messages_pb2.MsgPayload, data: bytes, service: "MQTTService") -> None:
        pass

class MachineStatusProcessor(MessageProcessor):
    def __init__(self, machine_data_store: Dict[int, schemas.MachineData]):
        self.machine_data_store = machine_data_store

    def process(self, payload: messages_pb2.MsgPayload, data: bytes, service: "MQTTService") -> None:
        status = messages_pb2.MsgMachineStatus()
        status.ParseFromString(data)

        machine_status = schemas.MachineStatus(
            x=status.rms.x,
            y=status.rms.y,
            z=status.rms.z,
            m=status.rms.m,
            st=status.st
        )

        machine_data = schemas.MachineData(
            sn=payload.sn,
            et=payload.et,
            ts=payload.ts,
            received_at=int(time.time() * 1000),
            status=machine_status
        )

        self.machine_data_store[payload.sn] = machine_data
        
        # Database insertion logic has been removed from here. 
        # It will be handled by a dedicated service or DAL function in the future.
        logger.info(
            f"Processed machine status for SN {payload.sn}: "
            f"x={machine_status.x:.3f}, y={machine_status.y:.3f}, "
            f"z={machine_status.z:.3f}, m={machine_status.m:.3f}, st={machine_status.st}"
        )

class RmsReportProcessor(MessageProcessor):
    def _triaxial_from_proto(self, proto: messages_pb2.MsgTriaxialValue) -> schemas.TriaxialValue:
        return schemas.TriaxialValue(
            x=float(proto.x),
            y=float(proto.y),
            z=float(proto.z),
            m=float(proto.m),
        )

    def process(self, payload: messages_pb2.MsgPayload, data: bytes, service: "MQTTService") -> None:
        report_proto = messages_pb2.MsgRmsReport()
        report_proto.ParseFromString(data)

        db_session = SessionLocal()
        try:
            # Create a Pydantic schema from the protobuf message for validation and structure
            report_schema = schemas.RmsReportCreate(
                sn=payload.sn,
                et=payload.et,
                ts=payload.ts,
                rms=self._triaxial_from_proto(report_proto.rms),
                peak=self._triaxial_from_proto(report_proto.peak),
                crest=self._triaxial_from_proto(report_proto.crest),
                impulse=self._triaxial_from_proto(report_proto.impulse),
                temperature=float(report_proto.temperature),
                iso=int(report_proto.iso),
            )

            # Save the data
            crud.create_rms_report(db=db_session, report=report_schema)

            logger.info(f"Saved RMS report for SN {payload.sn} to database, temperature={report_proto.temperature}")

        except Exception as e:
            logger.error(f"Failed to process or save RMS report for SN {payload.sn}: {e}")
        finally:
            db_session.close()

class UnknownMessageProcessor(MessageProcessor):
    def process(self, payload: messages_pb2.MsgPayload, data: bytes, service: "MQTTService") -> None:
        # We can decide if we want to log unknown events to the database in the future.
        # For now, just log to the console.
        logger.warning(f"Received unknown event type {payload.et} for SN {payload.sn}")

class MQTTService:
    def __init__(self):
        protocol = get_protocol_version(settings.mqtt_protocol_version)
        self.client = mqtt.Client(client_id=settings.mqtt_client_id, protocol=protocol)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.machine_data: Dict[int, schemas.MachineData] = {}

        self.processors: Dict[int, MessageProcessor] = {
            0: MachineStatusProcessor(self.machine_data),
            1: RmsReportProcessor(),
        }
        self.default_processor = UnknownMessageProcessor()

        # Reconnection settings
        self.is_connected = False
        self.reconnect_delay = 5  # seconds
        self.max_reconnect_delay = 300  # 5 minutes
        self.reconnect_thread = None
        self.should_reconnect = True
        self.reconnect_lock = threading.Lock()

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.is_connected = True
            self.reconnect_delay = 5  # Reset delay on successful connection
            logger.info(f"Connected to MQTT broker at {settings.mqtt_host}:{settings.mqtt_port} with result code {rc}")
            self.client.subscribe(settings.mqtt_topic)
            logger.info(f"Subscribed to topic: {settings.mqtt_topic}")
        else:
            self.is_connected = False
            logger.error(f"Failed to connect to MQTT broker with result code {rc}")

    def on_disconnect(self, client, userdata, rc):
        self.is_connected = False
        if rc != 0:
            logger.warning(f"Unexpected disconnection (code {rc}) from MQTT broker, will attempt to reconnect")
            self._schedule_reconnect()
        else:
            logger.info(f"Clean disconnection from MQTT broker with result code {rc}")

    def on_message(self, client, userdata, msg):
        try:
            payload = messages_pb2.MsgPayload()
            payload.ParseFromString(msg.payload)

            processor = self.processors.get(payload.et, self.default_processor)
            processor.process(payload, payload.data, self)

        except Exception as e:
            logger.error(f"Error parsing message: {e}")

    def connect(self):
        """Connect to MQTT broker with automatic reconnection on failure"""
        self.should_reconnect = True
        try:
            logger.info(f"Attempting to connect to MQTT broker at {settings.mqtt_host}:{settings.mqtt_port}")
            if settings.mqtt_username and settings.mqtt_password:
                self.client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
                logger.info("Using MQTT authentication")
            self.client.connect(settings.mqtt_host, settings.mqtt_port, 30)
            self.client.loop_start()
            logger.info("MQTT client loop started")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}, scheduling reconnection...")
            self._schedule_reconnect()

    def disconnect(self):
        """Disconnect from MQTT broker and stop reconnection attempts"""
        logger.info("Disconnecting MQTT client")
        self.should_reconnect = False
        self.client.loop_stop()
        self.client.disconnect()

    def get_machine_data(self, sn: int) -> schemas.MachineData:
        return self.machine_data.get(sn)

    def get_all_machines(self) -> list[int]:
        return list(self.machine_data.keys())

    def query_machine_events(
        self,
        sn: int | None = None,
        day: str | None = None,
        start_at: str | None = None,
        end_at: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        db_session = SessionLocal()
        try:
            return crud.get_rms_reports(
                db=db_session,
                sn=sn,
                day=day,
                start_at=start_at,
                end_at=end_at,
                limit=limit,
            )
        finally:
            db_session.close()

    def _schedule_reconnect(self):
        """Schedule a reconnect attempt in a background thread"""
        with self.reconnect_lock:
            if self.reconnect_thread is None or not self.reconnect_thread.is_alive():
                self.should_reconnect = True
                self.reconnect_thread = threading.Thread(
                    target=self._reconnect_loop, daemon=True, name="MQTTReconnectThread"
                )
                self.reconnect_thread.start()

    def _reconnect_loop(self):
        """Reconnect loop with exponential backoff"""
        while self.should_reconnect and not self.is_connected:
            try:
                logger.info(
                    f"Attempting to reconnect to MQTT broker in {self.reconnect_delay} seconds "
                    f"(next delay: {min(self.reconnect_delay * 2, self.max_reconnect_delay)}s)"
                )
                time.sleep(self.reconnect_delay)

                if not self.is_connected and self.should_reconnect:
                    logger.info(f"Reconnecting to MQTT broker at {settings.mqtt_host}:{settings.mqtt_port}")
                    self.client.reconnect()

                # Exponential backoff: increase delay for next attempt, cap at max
                self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)

            except Exception as e:
                logger.warning(f"Reconnection attempt failed: {e}, will retry in {self.reconnect_delay} seconds")

    def is_mqtt_connected(self) -> bool:
        """Check if MQTT client is connected"""
        return self.is_connected

mqtt_service = MQTTService()