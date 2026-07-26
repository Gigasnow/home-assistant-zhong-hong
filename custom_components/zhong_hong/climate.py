"""Support for ZhongHong Climate entities with Multi-Gateway support."""

import logging

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.climate.const import (
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .client import AC_Feature
from .const import CONF_IP_ADDRESS, DOMAIN

_LOGGER = logging.getLogger(__name__)

SUPPORTED_HVAC_MODES = {
    HVACMode.OFF: 0,
    HVACMode.COOL: 1,
    HVACMode.DRY: 2,
    HVACMode.FAN_ONLY: 4,
    HVACMode.HEAT: 8,
}

SUPPORTED_FAN_MODES = {
    FAN_HIGH: 1,
    FAN_MEDIUM: 2,
    FAN_LOW: 4,
}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Zhonghong climate entity from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    gateway = config_entry.data.get(CONF_IP_ADDRESS, "")

    climates = []
    # 遍历 Coordinator 抓取到的所有空调设备
    for ac_name, config in coordinator.data.items():
        climates.append(
            ZhongHongClimateEntity(
                coordinator=coordinator,
                gateway=gateway,
                ac_name=ac_name,
                config=config,
                entry_id=config_entry.entry_id,  # 传入 entry_id 实现多网关隔离
            )
        )

    async_add_entities(climates, update_before_add=True)


class ZhongHongClimateEntity(CoordinatorEntity, ClimateEntity):
    """Representation of a ZhongHong Climate device."""

    _attr_hvac_modes = [
        HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
        HVACMode.OFF,
    ]
    _attr_fan_modes = [
        FAN_HIGH,
        FAN_MEDIUM,
        FAN_LOW,
    ]
    _attr_should_poll = False
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _enable_turn_on_off_backwards_compatibility = False

    _attr_max_temp: float = 30
    _attr_min_temp: float = 16
    _attr_precision: float = 1

    def __init__(self, coordinator, gateway, ac_name, config, entry_id):
        """初始化 Zhonghong 空调实体"""
        super().__init__(coordinator)
        self._gateway = gateway
        self._ac_name = ac_name
        self._entry_id = entry_id
        self._idx = config.get(AC_Feature.AC_IDX)
        self._attr_name = self._ac_name

        self._current_operation = None
        self._current_temperature = None
        self._target_temperature = None
        self._current_fan_mode = None
        self.is_initialized = False

        # 设备分组标识，包含 entry_id 防止多网关下设备重叠
        device_info = self.coordinator.client.device_info.copy()
        group_id = config.get(AC_Feature.GROUP, 0) + 1
        device_info["identifiers"] = {(DOMAIN, f"{self._entry_id}_{group_id}")}
        self._attr_device_info = device_info

    @property
    def unique_id(self):
        """Return the unique ID of the HVAC entity, preventing multi-gateway collision."""
        # 加入 entry_id，即使两台网关都有 1_0_1 空调，也会生成独立的 unique_id
        return f"zhong_hong_http_{self._entry_id}_{self._ac_name}"

    @property
    def has_entity_name(self) -> bool:
        """Indicate that entity has name defined."""
        return True

    @property
    def _ac_data(self):
        """Helper to safely get current AC data from coordinator."""
        if self.coordinator.data:
            return self.coordinator.data.get(self._ac_name, {})
        return {}

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current operation ie. heat, cool, idle."""
        if not self.is_on:
            return HVACMode.OFF

        mode_value = self._ac_data.get(AC_Feature.MODE)
        for key, value in SUPPORTED_HVAC_MODES.items():
            if value == mode_value:
                return key
        return None

    @property
    def current_temperature(self):
        """Return the current temperature."""
        temp = self._ac_data.get(AC_Feature.TEMP_INDOOR)
        return float(temp) if temp is not None else None

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        temp = self._ac_data.get(AC_Feature.TEMP_SET)
        return float(temp) if temp is not None else None

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return 1

    @property
    def is_on(self):
        """Return true if on."""
        state = self._ac_data.get(AC_Feature.STATE) == 1
        _LOGGER.debug("%s state: %s", self._ac_name, state)
        return state

    @property
    def fan_mode(self):
        """Return the fan setting."""
        fan_value = self._ac_data.get(AC_Feature.FAN)
        for key, value in SUPPORTED_FAN_MODES.items():
            if value == fan_value:
                return key
        return None

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is not None:
            _LOGGER.debug("async_set_temperature: %s", temperature)
            await self._send_control_command(
                {AC_Feature.STATE: 1, AC_Feature.TEMP_SET: int(temperature)}
            )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """设置新的HVAC模式并发送控制命令"""
        _LOGGER.debug("async_set_hvac_mode: %s", hvac_mode)
        if hvac_mode == HVACMode.OFF:
            if self.is_on:
                await self._send_control_command({AC_Feature.STATE: 0})
            return

        mode = SUPPORTED_HVAC_MODES.get(hvac_mode, 0)
        await self._send_control_command(
            {AC_Feature.STATE: 1, AC_Feature.MODE: mode}
        )

    async def async_set_fan_mode(self, fan_mode) -> None:
        """设置新的风速模式并发送控制命令"""
        _LOGGER.debug("async_set_fan_mode: %s", fan_mode)
        fan_speed = SUPPORTED_FAN_MODES.get(fan_mode, 0)
        await self._send_control_command(
            {AC_Feature.STATE: 1, AC_Feature.FAN: fan_speed}
        )

    async def _send_control_command(self, ac_json):
        """向网关发送控制命令"""
        await self.coordinator.client.async_set_ac(
            self._ac_name, self._idx, ac_json
        )
