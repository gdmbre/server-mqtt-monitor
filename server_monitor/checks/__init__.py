from .cpu_load import CpuLoadCheck
from .cpu_temp import CpuTempCheck
from .interfaces import InterfacesCheck
from .last_login import LastLoginCheck
from .network_speed import NetworkSpeedCheck
from .reboot_required import RebootRequiredCheck
from .rpi_throttled import RpiThrottledCheck
from .services import ServicesCheck
from .smart import SmartCheck
from .usb_warnings import UsbWarningsCheck
from .trivy_check import TrivyCheck


AVAILABLE_CHECKS = [
    CpuTempCheck,
    CpuLoadCheck,
    NetworkSpeedCheck,
    ServicesCheck,
    InterfacesCheck,
    RebootRequiredCheck,
    LastLoginCheck,
    RpiThrottledCheck,
    UsbWarningsCheck,
    SmartCheck,
    TrivyCheck
]
