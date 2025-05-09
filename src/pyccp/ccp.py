"""CAN Calibration Protocol."""

from __future__ import annotations

import logging
import pathlib
import queue
from dataclasses import asdict, dataclass
from enum import IntEnum, IntFlag
from typing import Final, Literal, Optional
from types import TracebackType

import can
import cantools
from cantools.database.conversion import BaseConversion
from cantools.database.can import Message, Signal

import pyccp

_logger = logging.getLogger(__name__)

_COMMAND_DB = {
    "big_endian": cantools.database.load_file(
        pathlib.Path(__file__).parent / "commands_big_endian.dbc"
    ),
    "little_endian": cantools.database.load_file(
        pathlib.Path(__file__).parent / "commands_little_endian.dbc"
    ),
}

_RESPONSE_DB = {
    "big_endian": cantools.database.load_file(
        pathlib.Path(__file__).parent / "responses_big_endian.dbc"
    ),
    "little_endian": cantools.database.load_file(
        pathlib.Path(__file__).parent / "responses_little_endian.dbc"
    ),
}


@dataclass(frozen=True)
class CCPVersion:
    """CCP version returned by GET_CCP_VERSION."""

    major: int = 2
    minor: int = 1


@dataclass(frozen=True)
class DAQMetadata:
    """DAQ list metadata returned by GET_DAQ_SIZE.

    Parameters
    ----------
    size : int
        Number of ODTs which fit in DAQ list.
    first_pid : int
        PID of DAQ-DTO associated with first ODT in DAQ list.
    """

    size: int
    first_pid: int


@dataclass(frozen=True)
class ServiceMetadata:
    """Metadata returned by ACTION_SERVICE and DIAG_SERVICE.

    Parameters
    ----------
    length : int
        Size of result data in bytes.
    dtype : int
        Implementation defined result data type information.
    """

    length: int
    dtype: int


class ResourceMask(IntFlag):
    """Bits of resource availability and protection masks."""

    CAL = 0x1
    DAQ = 0x2
    PGM = 0x40


@dataclass(frozen=True)
class IDMetadata(ServiceMetadata):
    """Metadata returned by EXCHANGE_ID.

    Parameters
    ----------
    availability : ResourceMask
        Bit mask of features available in slave.
    protection : ResourceMask
        Bit mask of features which require unlocking before use.
    """

    availability: ResourceMask
    protection: ResourceMask


@dataclass(frozen=True)
class SessionInfo:
    """Implementation defined 'additional information' returned by GET_S_STATUS."""

    additional_information_qualifier: int
    additional_information: int


class CommandCode(IntEnum):
    # Mandatory commands
    CONNECT = 0x01
    GET_CCP_VERSION = 0x1B
    EXCHANGE_ID = 0x17
    SET_MTA = 0x02
    DNLOAD = 0x03
    UPLOAD = 0x04
    GET_DAQ_SIZE = 0x14
    SET_DAQ_PTR = 0x15
    WRITE_DAQ = 0x16
    START_STOP = 0x06
    DISCONNECT = 0x07
    # Optional commands
    GET_SEED = 0x12
    UNLOCK = 0x13
    DNLOAD_6 = 0x23
    SHORT_UP = 0x0F
    SELECT_CAL_PAGE = 0x11
    SET_S_STATUS = 0x0C
    GET_S_STATUS = 0x0D
    BUILD_CHKSUM = 0x0E
    CLEAR_MEMORY = 0x10
    PROGRAM = 0x18
    PROGRAM_6 = 0x22
    MOVE = 0x19
    TEST = 0x05
    GET_ACTIVE_CAL_PAGE = 0x09
    START_STOP_ALL = 0x08
    DIAG_SERVICE = 0x20
    ACTION_SERVICE = 0x21


_TIMEOUT_DEFAULT = 0.025
_TIMEOUT = {
    CommandCode.BUILD_CHKSUM: 30,
    CommandCode.CLEAR_MEMORY: 30,
    CommandCode.PROGRAM: 0.1,
    CommandCode.PROGRAM_6: 0.1,
    CommandCode.MOVE: 30,
    CommandCode.DIAG_SERVICE: 0.5,
    CommandCode.ACTION_SERVICE: 5,
}
"""Timeout values in seconds for CRM-DTOs.

Most CRMs timeout after 25 ms.
"""


class ReturnCode(IntEnum):
    ACKNOWLEDGE = 0x00
    DAQ_PROCESSOR_OVERLOAD = 0x01  # C0
    COMMAND_PROCESSOR_BUSY = 0x10  # C1 NONE (wait until ACK or timeout)
    DAQ_PROCESSOR_BUSY = 0x11  # C1 NONE (wait until ACK or timeout)
    INTERNAL_TIMEOUT = 0x12  # C1 NONE (wait until ACK or timeout)
    KEY_REQUEST = 0x18  # C1 NONE (embedded seed&key)
    SESSION_STATUS_REQUEST = 0x19  # C1 NONE (embedded SET_S_STATUS)
    COLD_START_REQUEST = 0x20  # C2 COLD START
    CAL_DATA_INIT_REQUEST = 0x21  # C2 cal. data initialization
    DAQ_LIST_INIT_REQUEST = 0x22  # C2 DAQ list initialization
    CODE_UPDATE_REQUEST = 0x23  # C2 (COLD START)
    UNKNOWN_COMMAND = 0x30  # C3 (FAULT)
    COMMAND_SYNTAX = 0x31  # C3 FAULT
    PARAMETER_OUT_OF_RANGE = 0x32  # C3 FAULT
    ACCESS_DENIED = 0x33  # C3 FAULT
    OVERLOAD = 0x34  # C3 FAULT
    ACCESS_LOCKED = 0x35  # C3 FAULT
    RESOURCE_FUNCTION_NOT_AVAILABLE = 0x36  # C3 FAULT


class DTOType(IntEnum):
    COMMAND_RETURN_MESSAGE = 0xFF
    EVENT_MESSAGE = 0xFE
    # Anything else is a DAQ-DTO.


Endianness = Literal["little_endian", "big_endian"]


class ConnectionStatus(IntEnum):
    NEVER_CONNECTED = 0
    CONNECTED = 1
    DISCONNECTED_TEMPORARY = 2
    DISCONNECTED_PERMANENT = 3


class SessionStatus(IntFlag):
    """Status bits for the SET_S_STATUS command."""

    CAL = 0x01
    DAQ = 0x02
    RESUME = 0x04
    STORE = 0x40
    RUN = 0x80


class CANID(int):
    """A CAN ID is an 11-bit (standard) or 29-bit (extended) integer.

    Parameters
    ----------
    is_extended_id : bool, default=True
    """

    MAX_STANDARD = 0x7FF
    MAX_EXTENDED = 0x1FFFFFFF

    def __new__(cls, *args, **kwargs) -> None:
        is_extended_id: bool | None = kwargs.pop("is_extended_id", None)
        value = super().__new__(cls, *args, **kwargs)
        is_extended_id = (
            is_extended_id
            if is_extended_id is not None
            else getattr(args[0], "is_extended_id", None)
        )

        if not isinstance(is_extended_id, bool | None):
            raise TypeError(f"'is_extended_id' must be boolean, got {is_extended_id}")

        if value < 0:
            raise ValueError(f"CAN ID cannot be negative, got {value}")
        elif value <= CANID.MAX_STANDARD:
            is_extended_id = bool(is_extended_id)
        elif CANID.MAX_STANDARD < value <= CANID.MAX_EXTENDED:
            if is_extended_id is None:
                is_extended_id = True
            elif is_extended_id:
                pass
            else:
                raise ValueError(
                    f"Standard CAN ID cannot exceed 0x{CANID.MAX_STANDARD:X}, "
                    f"got 0x{value:X}"
                )
        else:
            raise ValueError(
                f"CAN ID cannot exceed 0x{CANID.MAX_EXTENDED:X}, " f"got 0x{value:X}"
            )

        value.is_extended_id = is_extended_id
        return value

    def __eq__(self, other: int) -> bool:
        return int.__eq__(self, other) and (
            self.is_extended_id == CANID(other).is_extended_id
        )


@dataclass(frozen=True)
class MTA:
    """A Memory Transfer Address (MTA) is the location of a subsequent data transfer.

    The slave has two MTAs, MTA0 and MTA1. MTA0 is used for all memory transfer commands
    except MOVE, i.e. the following commands:
        DNLOAD
        UPLOAD
        DNLOAD_6
        SELECT_CAL_PAGE
        CLEAR_MEMORY
        PROGRAM
        PROGRAM_6

    MOVE uses both MTA0 and MTA1, where MTA0 is the source address to move data from,
    and MTA1 is the destination address to move data to.
    """

    address: int
    extension: int = 0


CCP_VERSION: Final[CCPVersion] = CCPVersion()


class _CRMListener(can.Listener):
    """Receives and decodes Command Return Messages.

    Parameters
    ----------
    dto_id : int
        CAN ID of DTO frames.

    Attributes
    ----------
    decoder : cantools.database.can.Message | None
        A Message object, which is used to decode a received CRM. The decoder must be
        set each time a CRO is sent. The pyccp._RESPONSE_DB database contains decoders
        for all supported CRMs, for both little- and big endian slaves.
    queue : queue.Queue
        Decoded CRMs are placed here awaiting processing.
    """

    def __init__(self, dto_id: int) -> None:
        self.dto_id = dto_id
        self.decoder: cantools.database.can.Message | None = None
        self.queue = queue.Queue()

    def on_message_received(self, msg: can.Message) -> None:
        """Decode an incoming CRM and put it in the receive queue for processing.

        Parameters
        ----------
        msg : can.Message
        """
        if (
            msg.arbitration_id == self.dto_id
            and msg.data[pyccp.DTO_PID_BYTE] == DTOType.COMMAND_RETURN_MESSAGE
        ):
            _logger.debug(f"Received CRM: {msg}")

            if not self.decoder:
                raise pyccp.CCPError("CRMListener has no decoder")

            decoded = self.decoder.decode(msg.data)
            _logger.debug(f"Decoded CRM: {decoded}")
            self.queue.put(decoded)

    def stop(self) -> None:
        self.queue.shutdown()

    def __repr__(self) -> str:
        return f"CRMListener(dto_id=0x{self.dto_id:X}, decoder={self.decoder.name})"


class CCPSlave:
    """Interface to a CCP slave node.

    Parameters
    ----------
    bus : can.Bus
        A CAN interface on the same bus as the slave ECU.
    station_address : int
        A station address is a two-byte address which uniquely identifies the CCP slave.
        Note that the station address is always little-endian, regardless of the slave's
        own endianness.
    cro_id : int | pyccp.CANID
        The CAN ID of the slave's Command Return Object (CRO) message. If the type of
        this value is a regular `int`, the ID is assumed to be extended (29-bits). If
        the ID is standard (11-bits), its type must be `pyccp.CANID`, e.g.
        `CANID(0x10, is_extended_id=False)`.
    dto_id : int | pyccp.CANID
        The CAN ID of the slave's Data Transmission Object (DTO) message. The same note
        as for the CRO message applies.
    byte_order : {'little_endian', 'big_endian'}, default='little_endian'
        Endianness of the slave.
    master_id : int, default=0
        Implementation defined master node ID information.
    """

    def __init__(
        self,
        bus: can.Bus,
        station_address: int,
        cro_id: CANID | int,
        dto_id: CANID | int,
        byte_order: Endianness = "little_endian",
    ):
        self._bus = bus
        self._station_address = station_address
        self._cro_id = CANID(cro_id)
        self._dto_id = CANID(dto_id)
        self._byte_order = byte_order
        self._ctr = 0
        self._connection_status = ConnectionStatus.NEVER_CONNECTED
        self._set_filter()
        # Incoming CRMs are decoded asynchronously and placed in a queue.
        self._crm_listener = _CRMListener(dto_id=self.dto_id)
        self._notifier: can.Notifier | None = None

        self._daq_lists = pyccp.DAQLists([])
        self._session_status = SessionStatus(0)
        self._id_meta = IDMetadata(0)
        self._id = b""
        self.login()

    def login(self) -> None:
        """Connect to slave and ask what it can do."""
        self.connect()
        self._id_meta = self.exchange_id(0)
        self._id = self.upload_block(self._id_meta.length)
        _logger.debug(f"Connected to slave with ID {self._id}")

        if self._id_meta.protection & ResourceMask.DAQ:
            _logger.warning("DAQ requires UNLOCK")
            # TODO: seed&key
            return

        if self._id_meta.availability & ResourceMask.DAQ:
            _logger.debug("Slave supports DAQ")
            self._get_daq_lists()

        # TODO: CAL

    def _set_filter(self) -> None:
        # Filter incoming CAN messages to only receive DTO frames.
        mask = CANID.MAX_EXTENDED if self.dto_id.is_extended_id else CANID.MAX_STANDARD
        old_filters = [] if self._bus.filters is None else self._bus.filters
        self._bus.set_filters(
            old_filters
            + [
                {
                    "can_id": self.dto_id,
                    "can_mask": mask,
                    "extended": self.dto_id.is_extended_id,
                }
            ]
        )

    def __enter__(self) -> None:
        _logger.debug("Enter context")
        self.connect()

    def __exit__(
        self,
        exctype: Optional[type[BaseException]],
        excinst: Optional[BaseException],
        exctb: Optional[TracebackType],
    ) -> bool:
        # If slave has been temporarily disconnected, it is necessary to reconnect
        # before disconnecting permanently.
        try:
            if self.connection_status == ConnectionStatus.DISCONNECTED_TEMPORARY:
                self.connect()
        finally:
            self.disconnect()
            _logger.debug("Exit context")

        return False

    def __repr__(self) -> str:
        return (
            f"CCPSlave(station_address=0x{self.station_address:X}, "
            f"id={self.id}, "
            f"connection_status={self.connection_status.name})"
        )

    @property
    def station_address(self) -> int:
        """Slave station address (read only)."""
        return self._station_address

    @property
    def cro_id(self) -> CANID:
        """Slave CRO ID (read only)."""
        return self._cro_id

    @property
    def dto_id(self) -> CANID:
        """Slave DTO ID (read only)."""
        return self._dto_id

    @property
    def byte_order(self) -> Endianness:
        """Slave endianness (read only)."""
        return self._byte_order

    @property
    def id(self) -> bytes:
        return self._id

    @property
    def connection_status(self) -> ConnectionStatus:
        """Slave connection status (read only)."""
        return self._connection_status

    @property
    def daq_lists(self) -> pyccp.DAQLists:
        """DAQ lists available on slave (read only)."""
        return self._daq_lists

    @property
    def session_status(self) -> SessionStatus:
        """Current session status.

        Returns
        -------
        SessionStatus
        """
        if self.connection_status == ConnectionStatus.CONNECTED:
            self._session_status = self.get_s_status()[0]
        elif self.connection_status == ConnectionStatus.DISCONNECTED_TEMPORARY:
            pass
        else:
            self._session_status = SessionStatus(0)
        return self._session_status

    @session_status.setter
    def session_status(self, s_status: SessionStatus) -> None:
        if s_status != self._session_status:
            self.set_s_status(s_status)
            self._session_status = s_status

    @property
    def resources(self) -> dict[str, ResourceMask]:
        """Availability / protection status of CAL, DAQ, and PGM resources (read only).

        Returns
        -------
        dict[str, ResourceMask]
            Dictionary with keys "available" and "protected", each with a ResourceMask
            value indicating whether that function is available and/or locked.
        """
        return {
            "available": ResourceMask(self._id_meta.availability),
            "protected": ResourceMask(self._id_meta.protection),
        }

    def _exchange(self, command: CommandCode, **parameters):
        if not self._notifier:
            raise pyccp.CCPError(f"Cannot {command.name} on disconnected node")

        encoder = _COMMAND_DB[self.byte_order].get_message_by_frame_id(command)
        decoder = _RESPONSE_DB[self.byte_order].get_message_by_frame_id(command)
        self._crm_listener.decoder = decoder
        parameters = {"command_code": command, "ctr": self._ctr} | parameters
        _logger.debug(f"Encoding CRO: {parameters}")
        data = encoder.encode(parameters)
        cro = can.Message(
            arbitration_id=self.cro_id,
            is_extended_id=self.cro_id.is_extended_id,
            data=data,
        )
        _logger.debug(f"Sending CRO: {cro}")
        self._bus.send(cro)

        try:
            crm = self._crm_listener.queue.get(
                timeout=_TIMEOUT.get(
                    command,
                    _TIMEOUT_DEFAULT,
                )
            )
        except queue.Empty as exc:
            raise pyccp.CCPError("CRM timeout") from exc

        if crm["ctr"] == self._ctr:
            self._ctr = (self._ctr + 1) % 0x100
        else:
            raise pyccp.CCPError(
                f"Counter mismatch: Internal {self._ctr}, received {crm['ctr']}"
            )

        if crm["return_code"] == ReturnCode.ACKNOWLEDGE:
            return {
                k: v for k, v in crm.items() if k not in {"pid", "return_code", "ctr"}
            }
        else:
            raise pyccp.CCPError(ReturnCode(crm["return_code"]).name)

    def poll(self, element: pyccp.Element) -> cantools.typechecking.DecodeResultType:
        """Fetch the value of an Element.

        Parameters
        ----------
        element : pyccp.Element

        Returns
        -------
        result : dict[str, int | float | str]
        """
        self.set_mta(address=element.address, extension=element.extension)
        return Message(
            name="decoder",
            frame_id=0,
            length=element.size,
            signals=[
                Signal(
                    name=element.name,
                    start=7 * (self.byte_order == "big_endian"),
                    length=element.size * 8,
                    byte_order=self.byte_order,
                    is_signed=element.is_signed,
                    conversion=BaseConversion.factory(
                        choices=element.choices,
                        is_float=element.is_float,
                        scale=element.scale,
                        offset=element.offset,
                    ),
                ),
            ],
        ).decode(self.upload(element.size))

    def upload_block(self, size: int, mta: Optional[MTA] = None) -> bytes:
        """Fetch a block of data from the slave.

        Parameters
        ----------
        size : int
            Number of bytes to fetch from slave.
        mta : MTA, default=None
            MTA0 will be set to this value prior to fetching the data. If not set, data
            will be fetched from the current location´ of MTA0.

        Returns
        -------
        data : bytes
            Raw bytes of length `size`, starting from MTA0.
        """
        if mta is not None:
            self.set_mta(address=mta.address, extension=mta.extension)

        remaining = size
        data = b""

        while remaining:
            numbytes = min(5, remaining)
            data += self.upload(numbytes)
            remaining -= numbytes

        return data

    def _get_daq_lists(self) -> None:
        """Query slave for available DAQ lists."""
        daq_lists = []
        _logger.debug("Initializing DAQ lists")

        # Ask slave for the size of its DAQ lists until we get one with size zero.
        while True:
            number = len(daq_lists)
            daq_metadata = self.get_daq_size(number)

            if daq_metadata.size:
                daq_lists.append(
                    pyccp.DAQList(
                        node=self,
                        number=number,
                        size=daq_metadata.size,
                        first_pid=daq_metadata.first_pid,
                    )
                )
            else:
                break

        self._daq_lists = pyccp.DAQLists(daq_lists)

    def add_listener(self, listener: can.Listener) -> None:
        """Add a can.Listener to the slave.

        The Listener will receive all incoming DTOs until the slave is permanently
        disconnected. This can be used to configure custom DTO handling of e.g.
        implementation-defined events.

        Parameters
        ----------
        listener : can.Listener
            A custom can.Listener.
        """
        self._notifier.add_listener(listener)

    def _cleanup(self) -> None:
        _logger.debug("Cleaning up CCP resources")
        if self._notifier:
            _logger.debug("Stopping CAN notifier and listeners")
            self._notifier.stop()
            self._notifier.listeners = []

        self._notifier = None
        self._ctr = 0
        self._daq_lists = []

    # #
    # Mandatory Commands
    # #

    def connect(self) -> None:
        """Connect to slave."""
        if self.connection_status == ConnectionStatus.CONNECTED:
            _logger.debug("Node is already connected")
            return

        if self.connection_status in (
            ConnectionStatus.NEVER_CONNECTED,
            ConnectionStatus.DISCONNECTED_PERMANENT,
        ):
            _logger.debug("Connecting")
            self._crm_listener = _CRMListener(dto_id=self.dto_id)
            self._notifier = can.Notifier(self._bus, [self._crm_listener])

        if self.connection_status == ConnectionStatus.DISCONNECTED_TEMPORARY:
            _logger.debug("Reconnecting")

        self._exchange(CommandCode.CONNECT, station_address=self.station_address)
        self._connection_status = ConnectionStatus.CONNECTED

    def get_ccp_version(self) -> CCPVersion:
        """Get the CCP version implemented by slave.

        Raises a warning if the reported version is not 2.1.

        Returns
        -------
        CCPVersion
        """
        crm = self._exchange(CommandCode.GET_CCP_VERSION, **asdict(CCP_VERSION))
        version = CCPVersion(**crm)

        if version != CCP_VERSION:
            _logger.warning(f"Unsupported CCP version: {version}")

        return version

    def exchange_id(self, device_info: int = 0) -> IDMetadata:
        """Exchange ID with slave.

        Parameters
        ----------
        device_info : int, default=0
            Implementation defined.

        Returns
        -------
        IDMetadata
        """
        crm = self._exchange(CommandCode.EXCHANGE_ID, device_info=device_info)
        return IDMetadata(**crm)

    def set_mta(self, address: int, extension: int = 0, mta: int = 0) -> None:
        """Set memory transfer address for subsequent data transfer.

        Parameters
        ----------
        address : int
        extension : int, default=0
            The address extension depends on the slave controller's
            organization and may identify a switchable memory bank
            or a memory segment.
        mta : {0, 1}, default=0
        """
        self._exchange(
            CommandCode.SET_MTA,
            address=address,
            extension=extension,
            mta=mta,
        )

    def dnload(self, size: int, data: int) -> MTA:
        """Download data to slave.

        Parameters
        ----------
        size : int
            Number of bytes to be downloaded (0 - 5).
        data : int
            Data to be written to MTA0.

        Returns
        -------
        MTA
            Location of MTA0 after download operation.
        """
        crm = self._exchange(CommandCode.DNLOAD, size=size, data=data)
        return MTA(**crm)

    def upload(self, size: int) -> bytes:
        """Transfer data from slave.

        Parameters
        ----------
        size : int
            Number of bytes to be uploaded (0 - 5).

        Returns
        -------
        bytes
            Requested data.
        """
        data = self._exchange(CommandCode.UPLOAD, size=size)["requested_data"]
        trunc = data.to_bytes(byteorder="big", length=5)[:size]
        return trunc

    def get_daq_size(self, daq_list_number: int) -> DAQMetadata:
        """Return the size of the specified DAQ list.

        Parameters
        ----------
        daq_list_number : int

        Returns
        -------
        DAQMetadata
        """
        crm = self._exchange(
            CommandCode.GET_DAQ_SIZE,
            daq_list_number=daq_list_number,
            dto_id=self.dto_id,
        )
        return DAQMetadata(**crm)

    def set_daq_ptr(
        self, daq_list_number: int, odt_number: int, element_number: int
    ) -> None:
        """Initialize the DAQ list pointer for a subsequent write.

        Parameters
        ----------
        daq_list_number : int
        odt_number : int
        element_number : int
        """
        self._exchange(
            CommandCode.SET_DAQ_PTR,
            daq_list_number=daq_list_number,
            odt_number=odt_number,
            element_number=element_number,
        )

    def write_daq(self, size: int, extension: int, address: int) -> None:
        """Write a DAQ element to the DAQ list set by set_daq_ptr.

        Parameters
        ----------
        size : {1, 2, 4}
            Size of DAQ element in bytes.
        extension : int
            Address extension of DAQ element.
        address : int
            Memory address of DAQ element in slave.
        """
        self._exchange(
            CommandCode.WRITE_DAQ,
            size=size,
            extension=extension,
            address=address,
        )

    def start_stop(
        self,
        mode: Literal[0, 1, 2],
        daq_list_number: int,
        last_odt_number: int,
        event_channel: int = 0,
        rate_prescaler: int = 1,
    ) -> None:
        """Start or to stop data acquisition.

        Parameters
        ----------
        mode : {0, 1, 2}
            0 stop specified DAQ list,
            1 start specified DAQ list,
            2 prepare DAQ list for synchronised start.
        daq_list_number : int
        last_odt_number : int
            Acquire data from ODTs up to and including last_odt_number.
        event_channel : int, optional
            Data transmission timing. Implementation defined. The default value is 0.
        rate_prescaler : int, optinal
            Set to >1 to decrease transmission rate. The default value is 1.
        """
        self._exchange(
            CommandCode.START_STOP,
            mode=mode,
            daq_list_number=daq_list_number,
            last_odt_number=last_odt_number,
            event_channel=event_channel,
            rate_prescaler=rate_prescaler,
        )

    def disconnect(self, permanent: bool = True) -> None:
        """Disconnect from slave device.

        Parameters
        ----------
        permanent : {0, 1}
            0 temporary,
            1 permanent.
        """
        _logger.debug(f"{self} disconnecting ({permanent=})")

        try:
            self._exchange(
                CommandCode.DISCONNECT,
                permanent=permanent,
                station_address=self.station_address,
            )
        finally:
            if permanent:
                self._connection_status = ConnectionStatus.DISCONNECTED_PERMANENT
                self._cleanup()
            else:
                self._connection_status = ConnectionStatus.DISCONNECTED_TEMPORARY

    # #
    # Optional Commands
    # #

    def test(self):
        raise NotImplementedError  # pragma: no cover

    def dnload6(self):
        raise NotImplementedError  # pragma: no cover

    def short_up(self):
        raise NotImplementedError  # pragma: no cover

    def start_stop_all(self, mode: pyccp.DAQMode) -> None:
        self._exchange(CommandCode.START_STOP_ALL, mode=mode)

    def set_s_status(self, status_bits: SessionStatus) -> None:
        """Set calibration or data acquisition session state.

        Parameters
        ----------
        status_bits : SessionStatus
        """
        self._exchange(CommandCode.SET_S_STATUS, status_bits=status_bits)

    def get_s_status(self) -> tuple[SessionStatus, SessionInfo]:
        """Get session status.

        Returns
        -------
        status_bits : SessionStatus
        additional_information : SessionInfo
        """
        crm = self._exchange(CommandCode.GET_S_STATUS)
        s_status = SessionStatus(crm.pop("status"))
        s_info = SessionInfo(**crm)
        return s_status, s_info

    def build_chksum(self):
        raise NotImplementedError  # pragma: no cover

    def clear_memory(self):
        raise NotImplementedError  # pragma: no cover

    def program(self):
        raise NotImplementedError  # pragma: no cover

    def program6(self):
        raise NotImplementedError  # pragma: no cover

    def move(self):
        raise NotImplementedError  # pragma: no cover

    def get_active_cal_page(self):
        raise NotImplementedError  # pragma: no cover

    def select_cal_page(self):
        raise NotImplementedError  # pragma: no cover

    def unlock(self):
        raise NotImplementedError  # pragma: no cover

    def get_seed(self):
        raise NotImplementedError  # pragma: no cover

    def action_service(
        self,
        service_number: int,
        parameters: int = 0,
    ) -> ServiceMetadata:
        """Instruct slave to carry out an implementation defined service.

        MTA0 is set to the address of the result data, if any.

        Parameters
        ----------
        service_number : int
        parameters : int, default=0
            Parameters for the requested service, encoded as a 32-bit unsigned
            integer.

        Return
        ------
        ServiceMetadata
        """
        crm = self._exchange(
            CommandCode.ACTION_SERVICE,
            action_service_number=service_number,
            parameters=parameters,
        )
        return ServiceMetadata(**crm)
