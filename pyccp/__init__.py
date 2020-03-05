import can
import enum


CCP_VERSION = (2, 1)


class MemoryTransferAddressNumber(enum.IntEnum):
    """
    The MTA number (handle) is used to identify different transfer address
    locations (pointers). MTA0 is used by the commands DNLOAD, UPLOAD, DNLOAD_6,
    SELECT_CAL_PAGE, CLEAR_MEMORY, PROGRAM and PROGRAM_6. MTA1 is used by the
    MOVE command. See also command ‘MOVE’.
    """

    MTA0_NUMBER = 0
    MTA1_NUMBER = 1


class SessionStatus(enum.IntEnum):
    CAL = 0x01
    DAQ = 0x02
    RESUME = 0x04
    STORE = 0x40
    RUN = 0x80


class CCPError(can.CanError):
    """Indicates an error with the CCP communication.
    """
