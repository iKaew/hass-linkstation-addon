"""The linkstation component constants."""

from typing import Final

from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.components.sensor.const import SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfInformation

DOMAIN: Final = "linkstation"
PLATFORMS: Final = ["sensor"]

DEFAULT_NAME = "LinkStation"

LINKSTATION_RESTART_SERVICE: Final = "restart_linkstation"
LINKSTATION_REFRESH_SERVICE: Final = "refresh_linkstation"

LINKSTATION_DISK_STATUS_NORMAL = "normal"

LINKSTATION_STATUS_ATTR_NAME = "current_status"
ATTR_DISK_CAPACITY = "disk_capacity"
ATTR_DISK_USED = "disk_used"
ATTR_DISK_UNIT_NAME = "disk_unit_name"
ATTR_SERVER_NAME = "server_name"

CONF_MANUAL: Final = "manual"


DEFAULT_NAS_LANGUAGE: Final = "en"
DEFAULT_PROTOCOL: Final = "http"
DEFAULT_UPDATE_INTERVAL: Final = 15

SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key=LINKSTATION_STATUS_ATTR_NAME,
        name="status",
    ),
    SensorEntityDescription(
        key="disk_free",
        name="available",
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="disk_used_pct",
        name="used (%)",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)

SENSOR_KEYS: list[str] = [desc.key for desc in SENSOR_TYPES]
