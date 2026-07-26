"""ZhongHong Integration Initialization."""

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import ZhongHongGateway
from .const import (
    CONF_IP_ADDRESS,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_REFRESH_INTERVAL,
    CONF_USERNAME,
    DEFAULT_PASSWORD,
    DEFAULT_PORT,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_USERNAME,
    DOMAIN,
    PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Zhonghong component from a config entry."""
    # 从 entry.data 和 entry.options 中优先提取配置
    # 严格匹配 CONF_IP_ADDRESS ("ip_address")
    ip_address = entry.data.get(CONF_IP_ADDRESS) or entry.options.get(CONF_IP_ADDRESS)
    
    if not ip_address:
        _LOGGER.error("ZhongHong setup failed: Missing IP address in Config Entry data: %s", entry.data)
        return False

    port = entry.options.get(
        CONF_PORT, entry.data.get(CONF_PORT, DEFAULT_PORT)
    )
    username = entry.options.get(
        CONF_USERNAME, entry.data.get(CONF_USERNAME, DEFAULT_USERNAME)
    )
    password = entry.options.get(
        CONF_PASSWORD, entry.data.get(CONF_PASSWORD, DEFAULT_PASSWORD)
    )
    scan_interval = entry.options.get(
        CONF_REFRESH_INTERVAL,
        entry.data.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL),
    )

    _LOGGER.info("Setting up ZhongHong Gateway entry with IP: %s:%s", ip_address, port)

    coordinator = ZhongHongDataCoordinator(
        hass, ip_address, port, username, password, scan_interval
    )

    # 获取硬件品牌与型号信息
    try:
        await coordinator.client.async_get_device_info()
    except Exception as err:
        _LOGGER.warning("Failed to fetch device info from %s: %s", ip_address, err)

    # 首次拉取数据（如果获取不到空调，自动触发重试）
    await coordinator.async_config_entry_first_refresh()

    # 存入 hass.data，以 entry_id 隔离不同网关
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # 转发加载 climate, sensor 等平台
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # 启动后台 TCP 监听
    coordinator.client.start_listen()

    # 添加选项更改监听器
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


class ZhongHongDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching ZhongHong data."""

    def __init__(self, hass, ip_address, port, username, password, scan_interval):
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{ip_address}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.ip_address = ip_address
        self.client = ZhongHongGateway(ip_address, port, username, password)
        self.client.register_update_callback(self._on_client_devices_updated)

    def _unregister_update_callback(self):
        """Unregister callback and stop listening."""
        self.client.unregister_update_callback(self._on_client_devices_updated)
        self.client.stop_listen()

    def _on_client_devices_updated(self):
        """Callback from client when TCP socket receives new data."""
        if self.hass and self.hass.loop:
            self.hass.loop.call_soon_threadsafe(
                self.async_set_updated_data, self.client.devices
            )

    async def _async_update_data(self):
        """Fetch data from Gateway via HTTP API."""
        await self.client.async_ac_list()
        if not self.client.devices:
            raise UpdateFailed(f"Error fetching ac list from gateway {self.ip_address}")
        return self.client.devices


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        coordinator._unregister_update_callback()

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
