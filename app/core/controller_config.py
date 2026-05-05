from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ControllerConfig:
    """Controller configuration for system-level features (WiFi, MQTT, etc.)."""
    
    # WiFi Configuration
    wifi_enabled: bool = False
    wifi_ssid: str = ""
    wifi_password: str = ""
    wifi_mode: str = "STA"  # STA (Station) or AP (Access Point)
    
    # Placeholder for future features
    mqtt_enabled: bool = False
    ethernet_enabled: bool = False
    modbus_enabled: bool = False
    
    def to_dict(self) -> dict:
        """Convert config to dictionary for JSON serialization."""
        return {
            "wifi_enabled": self.wifi_enabled,
            "wifi_ssid": self.wifi_ssid,
            "wifi_password": self.wifi_password,
            "wifi_mode": self.wifi_mode,
            "mqtt_enabled": self.mqtt_enabled,
            "ethernet_enabled": self.ethernet_enabled,
            "modbus_enabled": self.modbus_enabled,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ControllerConfig':
        """Create config from dictionary."""
        return cls(
            wifi_enabled=data.get("wifi_enabled", False),
            wifi_ssid=data.get("wifi_ssid", ""),
            wifi_password=data.get("wifi_password", ""),
            wifi_mode=data.get("wifi_mode", "STA"),
            mqtt_enabled=data.get("mqtt_enabled", False),
            ethernet_enabled=data.get("ethernet_enabled", False),
            modbus_enabled=data.get("modbus_enabled", False),
        )
    
    def get_adc2_pins(self) -> list[int]:
        """Return list of ADC2 pins that are unreliable when WiFi is enabled."""
        return [0, 2, 4, 12, 13, 14, 15, 25, 26, 27]
    
    def is_adc2_pin_unreliable(self, pin: int) -> bool:
        """Check if a pin is ADC2 and WiFi is enabled."""
        if not self.wifi_enabled:
            return False
        return pin in self.get_adc2_pins()
