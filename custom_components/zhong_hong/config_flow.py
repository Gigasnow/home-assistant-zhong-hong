import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    DEFAULT_PORT,
    CONF_GATEWAY_ADDRESS,
    DEFAULT_GATEWAY_ADDRESS,
)

_LOGGER = logging.getLogger(__name__)


class ZhonghongConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ZhongHong HVAC."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            gw_addr = user_input.get(CONF_GATEWAY_ADDRESS, DEFAULT_GATEWAY_ADDRESS)

            # 设置唯一 ID 防止同一个网关重复添加
            await self.async_set_unique_id(f"{host}_{gw_addr}")
            self._abort_if_unique_id_configured()

            title = user_input.get(CONF_NAME) or f"ZhongHong ({host})"
            return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=self._get_schema(),
            errors=errors,
        )

    def _get_schema(self):
        """Return the schema for user input."""
        return vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
                vol.Optional(
                    CONF_GATEWAY_ADDRESS, default=DEFAULT_GATEWAY_ADDRESS
                ): int,
                vol.Optional(CONF_NAME, default=""): str,
            }
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ZhonghongOptionsFlow(config_entry)


class ZhonghongOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_PORT,
                        default=self.config_entry.data.get(CONF_PORT, DEFAULT_PORT),
                    ): cv.port,
                    vol.Optional(
                        CONF_GATEWAY_ADDRESS,
                        default=self.config_entry.data.get(
                            CONF_GATEWAY_ADDRESS, DEFAULT_GATEWAY_ADDRESS
                        ),
                    ): int,
                }
            ),
        )
