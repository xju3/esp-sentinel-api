import os
import socket
import threading
import time

import paho.mqtt.client as mqtt

from ..config.settings import settings
from ..core.logging import setup_logging
from ..models import messages_pb2
from .dispatcher import MessageDispatcher
from .handlers.machine_status import MachineStatusProcessor
from .handlers.rms_report import RmsReportProcessor
from .handlers.unknown import UnknownMessageProcessor

logger = setup_logging()


def get_protocol_version(version_str: str):
    if version_str == "3.1":
        return mqtt.MQTTv31
    if version_str == "3.1.1":
        return mqtt.MQTTv311
    if version_str in {"5.0", "5"}:
        return mqtt.MQTTv5
    return mqtt.MQTTv311


class MQTTClient:
    def __init__(self, dispatcher: MessageDispatcher | None = None) -> None:
        self.is_connected = False
        self.reconnect_delay = 5
        self.max_reconnect_delay = 300
        self.reconnect_thread = None
        self.should_reconnect = True
        self.reconnect_lock = threading.Lock()

        protocol = get_protocol_version(settings.mqtt_protocol_version)
        self.client_id = self._build_client_id()
        self.client = mqtt.Client(client_id=self.client_id, protocol=protocol)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.client.reconnect_delay_set(min_delay=1, max_delay=self.max_reconnect_delay)

        self.dispatcher = dispatcher or MessageDispatcher(
            processors={
                0: MachineStatusProcessor(),
                1: RmsReportProcessor(),
            },
            default_processor=UnknownMessageProcessor(),
        )

    def _build_client_id(self) -> str:
        base_id = settings.mqtt_client_id or "sentinel-api-client"
        if not settings.mqtt_client_id_unique:
            return base_id
        suffix = f"{socket.gethostname()}-{os.getpid()}"
        return f"{base_id}-{suffix}"

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.is_connected = True
            self.reconnect_delay = 5
            logger.info(
                f"Connected to MQTT broker at {settings.mqtt_host}:{settings.mqtt_port} "
                f"with result code {rc} (client_id={self.client_id})"
            )
            self.client.subscribe(settings.mqtt_topic)
            logger.info(f"Subscribed to topic: {settings.mqtt_topic}")
        else:
            self.is_connected = False
            logger.error(f"Failed to connect to MQTT broker with result code {rc}")

    def on_disconnect(self, client, userdata, rc):
        self.is_connected = False
        if rc != 0:
            logger.warning(
                f"Unexpected disconnection (code {rc}) from MQTT broker, will attempt to reconnect"
            )
            self._schedule_reconnect()
        else:
            logger.info(f"Clean disconnection from MQTT broker with result code {rc}")

    def on_message(self, client, userdata, msg):
        try:
            payload = messages_pb2.MsgPayload()
            payload.ParseFromString(msg.payload)
            self.dispatcher.dispatch(payload)
        except Exception as e:
            logger.error(f"Error parsing message: {e}")

    def connect(self):
        self.should_reconnect = True
        try:
            logger.info(f"Attempting to connect to MQTT broker at {settings.mqtt_host}:{settings.mqtt_port}")
            logger.info(f"Using MQTT client id: {self.client_id}")
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
        logger.info("Disconnecting MQTT client")
        self.should_reconnect = False
        self.client.loop_stop()
        self.client.disconnect()

    def _schedule_reconnect(self):
        with self.reconnect_lock:
            if self.reconnect_thread is None or not self.reconnect_thread.is_alive():
                self.should_reconnect = True
                self.reconnect_thread = threading.Thread(
                    target=self._reconnect_loop, daemon=True, name="MQTTReconnectThread"
                )
                self.reconnect_thread.start()

    def _reconnect_loop(self):
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

                self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)

            except Exception as e:
                logger.warning(
                    f"Reconnection attempt failed: {e}, will retry in {self.reconnect_delay} seconds"
                )

    def is_mqtt_connected(self) -> bool:
        return self.is_connected


mqtt_client = MQTTClient()
