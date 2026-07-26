import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .client import AC_Feature
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Zhonghong climate sensor entity from a config entry."""
    # 获取当前 config_entry 对应的 coordinator
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    sensors = []
    for ac_name, config in coordinator.data.items():
        sensors.append(
            ZhongHongSensor(
                coordinator=coordinator,
                ac_name=ac_name,
                config=config,
                entry_id=config_entry.entry_id,  # 传入 entry_id 保证唯一性
            )
        )

    async_add_entities(sensors, update_before_add=True)


class ZhongHongSensor(CoordinatorEntity, SensorEntity):
    """Representation of a ZhongHong AC Alarm Sensor."""

    def __init__(self, coordinator, ac_name, config, entry_id):
        super().__init__(coordinator)
        self._ac_name = ac_name
        self._entry_id = entry_id
        self._attr_name = "Alarm"  # 搭配 has_entity_name = True，界面上会自动显示为 "[空调名] Alarm"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

        # 关联 Device Info，并将 entry_id 融入 identifier，防止多网关合并设备
        device_info = self.coordinator.client.device_info.copy()
        group_id = config.get(AC_Feature.GROUP, 0) + 1
        device_info["identifiers"] = {(DOMAIN, f"{self._entry_id}_{group_id}")}
        self._attr_device_info = device_info

    @property
    def unique_id(self):
        """Return the unique ID of the sensor, preventing multi-gateway conflicts."""
        # 加入 entry_id 保证不同网关下的同名 AC1 也能有独立唯一的 ID
        return f"zhong_hong_{self._entry_id}_{self._ac_name}_alarm"

    @property
    def has_entity_name(self) -> bool:
        """Indicate that entity has name defined."""
        return True

    @property
    def icon(self) -> str:
        """Set icon."""
        return "mdi:alert-circle"

    @property
    def native_value(self):
        """Return the state of the sensor (HA 推荐使用 native_value 代替 state)."""
        ac_data = self.coordinator.data.get(self._ac_name)
        if ac_data:
            return ac_data.get(AC_Feature.ALARM)
        return None
