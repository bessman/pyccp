"""CAN Calibration Protocol for Python."""

from .ccp import (
    CCPSlave,
    CCP_VERSION,
    CCPVersion,
    DAQMetadata,
    ServiceMetadata,
    IDMetadata,
    CommandCode,
    ReturnCode,
    Endianness,
    ConnectionStatus,
    SessionStatus,
    SessionInfo,
    CANID,
    MTA,
)
from .daq import DAQList, DAQLists, pack_elements, Element, ODT, DAQCallback, DAQMode


DTO_PID_BYTE = 0


class CCPError(Exception):
    """Indicates an error with the CCP communication."""


__version__ = "0.1.0"
