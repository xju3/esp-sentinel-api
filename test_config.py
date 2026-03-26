#!/usr/bin/env python3
"""
Configuration validation script.
Tests that all required environment variables are loaded correctly.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config.settings import settings

def test_configuration():
    """Test that configuration is loaded correctly."""
    print("Testing configuration loading...")

    # Test MQTT settings
    print(f"MQTT Host: {settings.mqtt_host}")
    print(f"MQTT Port: {settings.mqtt_port}")
    print(f"MQTT Topic: {settings.mqtt_topic}")
    print(f"MQTT Username: {settings.mqtt_username}")
    print(f"MQTT Password: {'*' * len(settings.mqtt_password) if settings.mqtt_password else None}")

    # Test API settings
    print(f"API Host: {settings.api_host}")
    print(f"API Port: {settings.api_port}")

    # Test logging
    print(f"Log Level: {settings.log_level}")

    # Test MySQL settings
    print(f"MySQL Host: {settings.mysql_host}")
    print(f"MySQL Port: {settings.mysql_port}")
    print(f"MySQL User: {settings.mysql_user}")
    print(f"MySQL Database: {settings.mysql_database}")
    print(f"MySQL Password: {'*' * len(settings.mysql_password) if settings.mysql_password else None}")

    # Test computed field
    print(f"Database URL: {settings.SQLALCHEMY_DATABASE_URL.replace(settings.mysql_password, '*' * len(settings.mysql_password))}")

    print("✅ Configuration loaded successfully!")

if __name__ == "__main__":
    test_configuration()