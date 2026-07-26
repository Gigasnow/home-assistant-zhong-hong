"""Support for ZhongHong HVAC Controller with Multi-Gateway support."""
import logging
import voluptuous as vol

from homeassistant.components.climate import PLATFORM_SCHEMA, ClimateEntity
from homeassistant.components.climate.const import (
    HVACMode,
    ClimateEntityFeature,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    FAN_AUTO,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    UnitOfTemperature,
)
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ["zhong_hong_hvac==1.0.9"]

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 9999
DEFAULT_GATEWAY_ADDRESS = 1

CONF_GATEWAY_ADDRESS = "gateway_address"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(
            CONF_GATEWAY_ADDRESS, default=DEFAULT_GATEWAY_ADDRESS
        ): cv.positive_int,
        vol.Optional(CONF_NAME): cv.string,
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the ZhongHong climate platform."""
    # 修正类名为 ZhongHongGateway
    from zhong_hong_hvac.hub import ZhongHongGateway

    host = config.get(CONF_HOST)
    port = config.get(CONF_PORT)
    gw_addr = config.get(CONF_GATEWAY_ADDRESS)
    name_prefix = config.get(CONF_NAME)

    _LOGGER.info("Initializing ZhongHong gateway at %s:%s (addr: %s)", host, port, gw_addr)

    hub = ZhongHongGateway(host, port, gw_addr)
    devices = []

    try:
        ac_list = hub.discovery_ac()
    except Exception as err:
        _LOGGER.error("Failed to discover AC units from %s:%s: %s", host, port, err)
        return

    for addr_out, addr_in in ac_list:
        devices.append(
            ZhongHongClimate(hub, addr_out, addr_in, host, gw_addr, name_prefix)
        )

    add_entities(devices, True)


class ZhongHongClimate(ClimateEntity):
    """Representation of a ZhongHong climate entity."""

    def __init__(self, hub, addr_out, addr_in, host, gw_addr, name_prefix=None):
        """Initialize the climate device."""
        self._hub = hub
        self._addr_out = addr_out
        self._addr_in = addr_in
        self._host = host
        self._gw_addr = gw_addr
        self._name_prefix = name_prefix

        self._attr_unique_id = (
            f"zhong_hong_{self._host}_{self._gw_addr}_{self._addr_out}_{self._addr_in}"
        )

    @property
    def name(self):
        """Return the name of the climate device."""
        if self._name_prefix:
            return f"{self._name_prefix} AC {self._addr_out}-{self._addr_in}"
        return f"ZhongHong AC {self._host} {self._addr_out}-{self._addr_in}"

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return UnitOfTemperature.CELSIUS

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._hub.get_climate_info(self._addr_out, self._addr_in).current_temp

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._hub.get_climate_info(self._addr_out, self._addr_in).target_temp

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return 1

    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode."""
        return self._hub.get_climate_info(self._addr_out, self._addr_in).hvac_mode

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes."""
        return self._hub.hvac_modes

    @property
    def fan_mode(self):
        """Return the fan setting."""
        return self._hub.get_climate_info(self._addr_out, self._addr_in).fan_mode

    @property
    def fan_modes(self):
        """Return the list of available fan modes."""
        return [FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH]

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        self._hub.set_temperature(self._addr_out, self._addr_in, temperature)

    def set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        self._hub.set_hvac_mode(self._addr_out, self._addr_in, hvac_mode)

    def set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        self._hub.set_fan_mode(self._addr_out, self._addr_in, fan_mode)

    def update(self):
        """Retrieve latest state."""
        self._hub.query_status(self._addr_out, self._addr_in)
