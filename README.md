# Sentinel Server API

This is a server-side backend API project built with FastAPI. It listens to MQTT messages from the Sentinel topic and parses Protobuf-encoded data for machine status monitoring.

## Project Structure

```
src/
├── __init__.py
├── __main__.py
├── api/
│   ├── __init__.py
│   └── routes.py
├── config/
│   ├── __init__.py
│   └── settings.py
├── core/
│   ├── __init__.py
│   └── logging.py
├── main.py
├── models/
│   ├── __init__.py
│   ├── messages.proto
│   ├── messages_pb2.py
│   └── schemas.py
└── services/
    ├── __init__.py
    └── mqtt_service.py
tests/
├── __init__.py
pyproject.toml
README.md
```

## Installation

1. Install dependencies:
   ```bash
   pip install -e .
   ```

## Running the API

Run the server:
```bash
python -m src
```

Or directly:
```bash
uvicorn src.main:app --reload
```

The API will be available at http://127.0.0.1:8000

## API Documentation

- Interactive API docs: http://127.0.0.1:8000/docs
- Alternative docs: http://127.0.0.1:8000/redoc

## MQTT Integration

The server connects to MQTT broker at 139.9.50.7:1183 and subscribes to the "sentinel" topic. It parses incoming messages using the defined Protobuf schema:

- `MsgPayload`: Outer message with sn, et, ts, data
- `MsgMachineStatus`: Inner message for et=0, containing RMS values and status

### API Endpoints

- `GET /`: Root endpoint
- `GET /health`: Health check
- `GET /machines`: List all machine serial numbers
- `GET /machine/{sn}`: Get status for a specific machine

## Configuration

Settings can be configured via environment variables or `.env` file:

- `MQTT_HOST`: MQTT broker host (default: 139.9.50.7)
- `MQTT_PORT`: MQTT broker port (default: 1183)
- `MQTT_TOPIC`: MQTT topic to subscribe (default: sentinel)
- `MQTT_USERNAME`: MQTT username (optional)
- `MQTT_PASSWORD`: MQTT password (optional)
- `API_HOST`: API host (default: 0.0.0.0)
- `API_PORT`: API port (default: 8000)
- `LOG_LEVEL`: Logging level (default: INFO)

Copy `.env.example` to `.env` and configure as needed.

## Development

Install development dependencies:
```bash
pip install -e ".[dev]"
```

Run tests:
```bash
pytest
```
