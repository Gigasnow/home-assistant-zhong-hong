"""Constants for the ZhongHong HVAC integration."""

from typing import Final
from homeassistant.const import Platform
import logging

_LOGGER = logging.getLogger(__name__)

DOMAIN: Final = "zhong_hong"

# 配置参数 key
CONF_IP_ADDRESS: Final = "ip_address"
CONF_PORT: Final = "port"
CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password"
CONF_REFRESH_INTERVAL: Final = "refresh_interval"
CONF_GATEWAY_ADDRESS: Final = "gateway_address"  # 补全缺失的常量

# 默认值
DEFAULT_USERNAME: Final = "admin"
DEFAULT_PASSWORD: Final = ""
DEFAULT_PORT: Final = 9999
DEFAULT_REFRESH_INTERVAL: Final = 60
DEFAULT_GATEWAY_ADDRESS: Final = 1  # 补全默认网关地址

# 平台注册
PLATFORMS: Final = [
    Platform.SENSOR,
    Platform.CLIMATE,
]
