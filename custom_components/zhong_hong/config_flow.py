"""Config flow for ZhongHong HVAC integration."""

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_PORT
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_GATEWAY_ADDRESS,
    CONF_IP_ADDRESS,
    CONF_PASSWORD,
    CONF_REFRESH_INTERVAL,
    CONF_USERNAME,
    DEFAULT_GATEWAY_ADDRESS,
    DEFAULT_PASSWORD,
    DEFAULT_PORT,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_USERNAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class ZhonghongConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ZhongHong HVAC."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # 统一使用 CONF_IP_ADDRESS ("ip_address") 作为键名
            ip_address = user_input[CONF_IP_ADDRESS]
            gw_addr = user_input.get(CONF_GATEWAY_ADDRESS, DEFAULT_GATEWAY_ADDRESS)

            # 设置唯一 ID 防止同一个网关重复添加
            await self.async_set_unique_id(f"{ip_address}_{gw_addr}")
            self._abort_if_unique_id_configured()

            title = user_input.get(CONF_NAME) or f"中弘网关 ({ip_address})"
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
                vol.Required(CONF_IP_ADDRESS): str,  # 表单字段对齐为 ip_address
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
                vol.Optional(
                    CONF_GATEWAY_ADDRESS, default=DEFAULT_GATEWAY_ADDRESS
                ): int,
                vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): str,
                vol.Optional(CONF_PASSWORD, default=DEFAULT_PASSWORD): str,
                vol.Optional(
                    CONF_REFRESH_INTERVAL, default=DEFAULT_REFRESH_INTERVAL
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
                        default=self.config_entry.data.get(
                            CONF_PORT, DEFAULT_PORT
                        ),
                    ): cv.port,
                    vol.Optional(
                        CONF_GATEWAY_ADDRESS,
                        default=self.config_entry.data.get(
                            CONF_GATEWAY_ADDRESS, DEFAULT_GATEWAY_ADDRESS
                        ),
                    ): int,
                    vol.Optional(
                        CONF_REFRESH_INTERVAL,
                        default=self.config_entry.data.get(
                            CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL
                        ),
                    ): int,
                }
            ),
        )
