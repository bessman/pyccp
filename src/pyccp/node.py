"""CCP master node and related types."""
import enum
import collections
import logging
import pathlib
import queue
from typing import Tuple, Union

import can
import cantools

from pyccp.decoder import CRMDecoder
from pyccp.error import CCPError


_logger = logging.getLogger(__name__)


CCP_VERSION = {"major": 2, "minor": 1}

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


class CommandCodes(enum.IntEnum):
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


class ReturnCodes(enum.IntEnum):
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


MTA = collections.namedtuple("MTA", ["address", "extension"])


class ConnectionStatus(enum.IntEnum):
    DISCONNECTED_PERMANENT = -1
    DISCONNECTED = 0
    CONNECTED = 1


class Node:
    """A CAN Calibration Protocol (CCP) master node."""

    def __init__(
        self,
        transport: can.Bus,
        station_address: int,
        cro_id: int,
        dto_id: int,
        extended_id: bool = True,
        byte_order: str = "little_endian",
    ):
        self.status = ConnectionStatus.DISCONNECTED
        self._transport = transport
        self.station_address = station_address
        self.cro_id = cro_id
        self.dto_id = dto_id
        self.extended_id = extended_id
        mask = 0x1FFFFFFF if extended_id else 0x7FF
        old_filters = [] if self._transport.filters is None else self._transport.filters
        self._transport.set_filters(
            old_filters
            + [{"can_id": dto_id, "can_mask": mask, "extended": extended_id}]
        )
        self.byte_order = byte_order
        self.ctr = 0
        self._decoder = CRMDecoder(
            dto_id=dto_id,
            decoders={k: v for k, v in zip(range(0x100), [None] * 0xFF)},
        )
        self._notifier = can.Notifier(bus=self._transport, listeners=[self._decoder])
        self.add_listener = self._notifier.add_listener
        self.connect()

    def __del__(self):
        """Stop listening on CAN bus."""
        self._notifier.stop()

    def get_data(self, size: int, mta: Union[MTA, None] = None):
        if mta is not None:
            self.set_mta(address=mta.address, extension=mta.extension)

        remaining = size
        data = b""

        while remaining:
            numbytes = min(5, remaining)
            data += self.upload(numbytes).to_bytes(numbytes, "big")
            remaining -= numbytes

        return data

    def _transceive(self, command: CommandCodes, **signals):
        encoder = _COMMAND_DB[self.byte_order].get_message_by_frame_id(command)
        decoder = _RESPONSE_DB[self.byte_order].get_message_by_frame_id(command)
        self._decoder.decoders[self.ctr] = decoder
        signals["command_code"] = command
        signals["ctr"] = self.ctr
        data = encoder.encode(signals)
        cro = can.Message(
            arbitration_id=self.cro_id,
            is_extended_id=self.extended_id,
            data=data,
        )
        self._transport.send(cro)
        _logger.debug(f"Sent CRO: {cro}")
        _logger.debug(signals)

        try:
            crm = self._decoder.queue.get(timeout=1)
        except queue.Empty as exc:
            raise CCPError("No reply from slave") from exc

        if crm["ctr"] == self.ctr:
            self.ctr = (self.ctr + 1) % 0x100
        else:
            raise CCPError(
                f"Counter mismatch: Internal {self.ctr}, received {crm['ctr']}"
            )

        if crm["return_code"] == ReturnCodes.ACKNOWLEDGE:
            return crm
        else:
            raise CCPError(ReturnCodes(crm["return_code"]).name)

    # #
    # Mandatory Commands
    # #

    def connect(self) -> None:
        """Connect to node."""
        if self.status == ConnectionStatus.DISCONNECTED_PERMANENT:
            raise CCPError(
                "Node has been permanently disconnected. "
                "To reconnect, create a new instance."
            )
        self._transceive(CommandCodes.CONNECT, station_address=self.station_address)
        self.status = ConnectionStatus.CONNECTED

    def get_ccp_version(self) -> None:
        """Check that node uses CCP version 2.1."""
        crm = self._transceive(CommandCodes.GET_CCP_VERSION, **CCP_VERSION)
        if crm != CCP_VERSION:
            raise CCPError(f"Unsupported CCP version: {crm}")

    def exchange_id(self, device_info: int = 0) -> Tuple[int, int, int, int]:
        """Exchange ID with slave.

        Parameters
        ----------
        device_info : int, optional
           Implementation specific. The default is 0.

        Returns
        -------
        tuple
             size:         Length of slave device ID in bytes,
             dtype:        Data type qualifier of slave device ID,
             availability: Resource availability mask,
             protection:   Resource protection mask
        """
        crm = self._transceive(CommandCodes.EXCHANGE_ID, device_info=device_info)
        return tuple(crm[k] for k in ("size", "dtype", "availability", "protection"))

    def set_mta(self, address: int, extension: int = 0, mta: int = 0) -> None:
        """Set memory transfer address for subsequent data transfer.

        Parameters
        ----------
        address : int
            Memory address in slave.
        extension : int, optional
            The address extension depends on the slave controller's
            organization and may identify a switchable memory bank
            or a memory segment. The default is 0x00.
        mta : {0, 1}, optional
            The default is 0.
        """
        self._transceive(
            CommandCodes.SET_MTA,
            address=address,
            extension=extension,
            mta=mta,
        )

    def dnload(self, size: int, data: int) -> Tuple[int, int]:
        """Transfer data to node.

        Parameters
        ----------
        size : int
            Number of bytes to be transferred (0 - 5).
        data : int
            Data to be written to MTA0 in the slave.

        Returns
        -------
        tuple
             mta0_ext:  Current MTA0 extension,
             mta0_addr: Current MTA0 address
        """
        crm = self._transceive(CommandCodes.DNLOAD, size=size, data=data)
        return crm["extension"], crm["address"]

    def upload(self, size: int) -> int:
        """Transfer data from node.

        Parameters
        ----------
        size : int
            Number of bytes to be transferred (0 - 5).

        Returns
        -------
        int
            Requested data.
        """
        data = self._transceive(CommandCodes.UPLOAD, size=size)["requested_data"]
        trunc = data.to_bytes(byteorder="big", length=5)[:size]
        return int.from_bytes(trunc, byteorder="big")

    def get_daq_size(self, daq_list_number: int) -> Tuple[int, int]:
        """Return the size of the specified DAQ list.

        Parameters
        ----------
        daq_list_number : int

        Returns
        -------
        tuple
             size: Number of ODTs in DAQ list,
             first_odt: First ODT number in DAQ list
        """
        crm = self._transceive(
            CommandCodes.GET_DAQ_SIZE,
            daq_list_number=daq_list_number,
            dto_id=self.dto_id,
        )
        return crm["size"], crm["first_odt_number"]

    def set_daq_ptr(self, daq_list_number: int, odt_number: int, element_number: int):
        """Initialize the DAQ list pointer for a subsequent write.

        Parameters
        ----------
        daq_list_number : int
        odt_number : int
        element_number : int
        """
        self._transceive(
            CommandCodes.SET_DAQ_PTR,
            daq_list_number=daq_list_number,
            odt_number=odt_number,
            element_number=element_number,
        )

    def write_daq(self, size: int, extension: int, address: int):
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
        self._transceive(
            CommandCodes.WRITE_DAQ,
            size=size,
            extension=extension,
            address=address,
        )

    def start_stop(
        self,
        mode: int,
        daq_list_number: int,
        last_odt_number: int,
        event_channel: int = 0,
        rate_prescaler: int = 1,
    ):
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
        rate_prescaler : int, optinal
            Set to >1 to decrease transmission rate.
        """
        self._transceive(
            CommandCodes.START_STOP,
            mode=mode,
            daq_list_number=daq_list_number,
            last_odt_number=last_odt_number,
            event_channel=event_channel,
            rate_prescaler=rate_prescaler,
        )

    def disconnect(self, permanent: int = 1):
        """Disconnect from slave device.

        Parameters
        ----------
        permanent : {0, 1}
            0 temporary,
            1 permanent.
        """
        try:
            self._transceive(
                CommandCodes.DISCONNECT,
                permanent=permanent,
                station_address=self.station_address,
            )
        finally:
            self.status = ConnectionStatus.DISCONNECTED
            if permanent:
                self._notifier.stop()
                self.status = ConnectionStatus.DISCONNECTED_PERMANENT

    # #
    # Optional Commands
    # #

    def test(self):
        raise NotImplementedError  # pragma: no cover

    def dnload6(self):
        raise NotImplementedError  # pragma: no cover

    def short_up(self, size, address, addressExtension):
        raise NotImplementedError  # pragma: no cover

    def start_stop_all(self):
        raise NotImplementedError  # pragma: no cover

    def set_s_status(self, status_bits: int):
        """Set calibration or data acquisition session state.

        Parameters
        ----------
        status_bits : int
            0x01 CAL:     Calibration data initialized
            0x02 DAQ:     DAQ list(s) initialized
            0x04 RESUME:  Resume session after temporary disconnect
            0x40 STORE:   Save calibration during device shut-down
            0x80 RUN:     Start session
        """
        self._transceive(CommandCodes.SET_S_STATUS, status_bits=status_bits)

    def get_s_status(self):
        raise NotImplementedError  # pragma: no cover

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

    def action_service(self, service_number: int, parameters: int = 0):
        return self._transceive(
            CommandCodes.ACTION_SERVICE,
            action_service_number=service_number,
            parameters=parameters,
        )["size"]
