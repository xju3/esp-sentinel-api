import paho.mqtt.client as mqtt
import time
import pymysql
from datetime import datetime, timedelta
from typing import Dict
from abc import ABC, abstractmethod
from ..config.settings import settings
from ..core.logging import setup_logging
from ..models import messages_pb2
from ..models.schemas import MachineData, MachineStatus

logger = setup_logging()

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
    def __init__(self, machine_data_store: Dict[int, MachineData]):
        self.machine_data_store = machine_data_store

    def process(self, payload: messages_pb2.MsgPayload, data: bytes, service: "MQTTService") -> None:
        status = messages_pb2.MsgMachineStatus()
        status.ParseFromString(data)

        machine_status = MachineStatus(
            x=status.rms.x,
            y=status.rms.y,
            rz=status.rms.z,
            rm=status.rms.m,
            st=status.st
        )

        machine_data = MachineData(
            sn=payload.sn,
            et=payload.et,
            ts=payload.ts,
            received_at=int(time.time() * 1000),
            status=machine_status
        )

        self.machine_data_store[payload.sn] = machine_data

        service.insert_machine_event(
            sn=payload.sn,
            et=payload.et,
            event_ts=payload.ts,
            status=machine_status,
            raw_payload=data
        )

        logger.info(
            f"Processed machine status for SN {payload.sn}: "
            f"rx={machine_status.x:.3f}, ry={machine_status.y:.3f}, "
            f"rz={machine_status.rz:.3f}, rm={machine_status.rm:.3f}, st={machine_status.st}"
        )

class RmsReportProcessor(MessageProcessor):
    def process(self, payload: messages_pb2.MsgPayload, data: bytes, service: "MQTTService") -> None:
        report = messages_pb2.MsgRmsReport()
        report.ParseFromString(data)

        service.insert_machine_event(
            sn=payload.sn,
            et=payload.et,
            event_ts=payload.ts,
            rms=report.rms,
            peak=report.peak,
            crest=report.crest,
            impulse=report.impulse,
            temperature=report.temperature,
            iso=report.iso,
            raw_payload=data
        )

        logger.info(f"Processed rms report for SN {payload.sn}, temperature={report.temperature}")

class UnknownMessageProcessor(MessageProcessor):
    def process(self, payload: messages_pb2.MsgPayload, data: bytes, service: "MQTTService") -> None:
        service.insert_machine_event(sn=payload.sn, et=payload.et, event_ts=payload.ts, raw_payload=data)
        logger.warning(f"Received unknown event type {payload.et} for SN {payload.sn}")

class MQTTService:
    def __init__(self):
        protocol = get_protocol_version(settings.mqtt_protocol_version)
        self.client = mqtt.Client(client_id=settings.mqtt_client_id, protocol=protocol)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.machine_data: Dict[int, MachineData] = {}

        self.processors: Dict[int, MessageProcessor] = {
            0: MachineStatusProcessor(self.machine_data),
            1: RmsReportProcessor(),
        }
        self.default_processor = UnknownMessageProcessor()

        self.db_conn = None
        self.init_db()

    def init_db(self):
        try:
            self.db_conn = pymysql.connect(
                host=settings.mysql_host,
                port=settings.mysql_port,
                user=settings.mysql_user,
                password=settings.mysql_password,
                database=settings.mysql_database,
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True
            )
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS machine_event (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        sn INT NOT NULL,
                        et TINYINT NOT NULL,
                        event_ts BIGINT NOT NULL,
                        received_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        st TINYINT NULL,
                        rms_rx FLOAT NULL,
                        rms_ry FLOAT NULL,
                        rms_rz FLOAT NULL,
                        rms_rm FLOAT NULL,
                        peak_x FLOAT NULL,
                        peak_y FLOAT NULL,
                        peak_z FLOAT NULL,
                        peak_m FLOAT NULL,
                        crest_x FLOAT NULL,
                        crest_y FLOAT NULL,
                        crest_z FLOAT NULL,
                        crest_m FLOAT NULL,
                        impulse_x FLOAT NULL,
                        impulse_y FLOAT NULL,
                        impulse_z FLOAT NULL,
                        impulse_m FLOAT NULL,
                        temperature FLOAT NULL,
                        iso INT NULL,
                        raw_payload LONGBLOB NULL,
                        INDEX idx_sn_et (sn, et),
                        INDEX idx_event_ts (event_ts)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """)
            logger.info("MySQL connection established and table machine_event ready")
        except Exception as e:
            logger.error(f"DB init failed: {e}")
            self.db_conn = None

    def insert_machine_event(self, *, sn: int, et: int, event_ts: int, raw_payload: bytes = None,
                             status: MachineStatus = None, rms=None, peak=None, crest=None, impulse=None,
                             temperature=None, iso=None):
        if self.db_conn is None:
            logger.warning("DB connection is not available, skip insert")
            return

        sql = """
            INSERT INTO machine_event (
                sn, et, event_ts, st,
                rms_rx, rms_ry, rms_rz, rms_rm,
                peak_x, peak_y, peak_z, peak_m,
                crest_x, crest_y, crest_z, crest_m,
                impulse_x, impulse_y, impulse_z, impulse_m,
                temperature, iso, raw_payload
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """

        params = [
            sn, et, event_ts,
            status.st if status is not None else None,
            status.x if status is not None else (rms.x if rms is not None else None),
            status.y if status is not None else (rms.y if rms is not None else None),
            status.rz if status is not None else (rms.z if rms is not None else None),
            status.rm if status is not None else (rms.m if rms is not None else None),
            peak.x if peak is not None else None,
            peak.y if peak is not None else None,
            peak.z if peak is not None else None,
            peak.m if peak is not None else None,
            crest.x if crest is not None else None,
            crest.y if crest is not None else None,
            crest.z if crest is not None else None,
            crest.m if crest is not None else None,
            impulse.x if impulse is not None else None,
            impulse.y if impulse is not None else None,
            impulse.z if impulse is not None else None,
            impulse.m if impulse is not None else None,
            temperature,
            iso,
            raw_payload
        ]

        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute(sql, params)
        except Exception as e:
            logger.error(f"Failed to insert machine_event: {e}")

    def query_machine_events(self, sn: int = None, day: str = None, start_at: str = None, end_at: str = None, limit: int = 20):
        if self.db_conn is None:
            return []

        where_clauses = []
        params = []

        if sn is not None:
            where_clauses.append("sn=%s")
            params.append(sn)

        if day is not None:
            try:
                day_dt = datetime.strptime(day, "%Y-%m-%d")
            except ValueError as e:
                raise ValueError("day must be in YYYY-MM-DD format")

            next_day = day_dt + timedelta(days=1)
            where_clauses.append("received_at >= %s AND received_at < %s")
            params.append(day_dt.strftime("%Y-%m-%d 00:00:00"))
            params.append(next_day.strftime("%Y-%m-%d 00:00:00"))

        if start_at is not None:
            try:
                start_dt = datetime.fromisoformat(start_at)
            except ValueError:
                raise ValueError("start_at must be ISO 8601 datetime format")
            where_clauses.append("received_at >= %s")
            params.append(start_dt.strftime("%Y-%m-%d %H:%M:%S"))

        if end_at is not None:
            try:
                end_dt = datetime.fromisoformat(end_at)
            except ValueError:
                raise ValueError("end_at must be ISO 8601 datetime format")
            where_clauses.append("received_at <= %s")
            params.append(end_dt.strftime("%Y-%m-%d %H:%M:%S"))

        if limit is None or limit <= 0:
            limit = 20

        sql = "SELECT * FROM machine_event"
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        sql += " ORDER BY received_at DESC LIMIT %s"
        params.append(limit)

        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()

            filtered_rows = []
            for row in rows:
                if isinstance(row.get("received_at"), datetime):
                    row["received_at"] = row["received_at"].isoformat(sep=" ")
                if isinstance(row.get("raw_payload"), (bytes, bytearray)):
                    # remove raw payload from response completely
                    row.pop("raw_payload", None)
                else:
                    row.pop("raw_payload", None)
                filtered_rows.append(row)
            return filtered_rows
        except Exception as e:
            logger.error(f"Failed to query machine_event: {e}")
            return []

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"Connected to MQTT broker at {settings.mqtt_host}:{settings.mqtt_port} with result code {rc}")
            self.client.subscribe(settings.mqtt_topic)
            logger.info(f"Subscribed to topic: {settings.mqtt_topic}")
        else:
            logger.error(f"Failed to connect to MQTT broker with result code {rc}")

    def on_disconnect(self, client, userdata, rc):
        logger.warning(f"Disconnected from MQTT broker with result code {rc}")

    def on_message(self, client, userdata, msg):
        try:
            payload = messages_pb2.MsgPayload()
            payload.ParseFromString(msg.payload)

            processor = self.processors.get(payload.et, self.default_processor)
            processor.process(payload, payload.data, self)

        except Exception as e:
            logger.error(f"Error parsing message: {e}")

    def connect(self):
        try:
            logger.info(f"Attempting to connect to MQTT broker at {settings.mqtt_host}:{settings.mqtt_port}")
            if settings.mqtt_username and settings.mqtt_password:
                self.client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
                logger.info("Using MQTT authentication")
            self.client.connect(settings.mqtt_host, settings.mqtt_port, 30)
            self.client.loop_start()
            logger.info("MQTT client loop started")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")

    def disconnect(self):
        logger.info("Disconnecting MQTT client")
        self.client.loop_stop()
        self.client.disconnect()
        if self.db_conn:
            self.db_conn.close()

    def get_machine_data(self, sn: int) -> MachineData:
        return self.machine_data.get(sn)

    def get_all_machines(self) -> list[int]:
        return list(self.machine_data.keys())

mqtt_service = MQTTService()