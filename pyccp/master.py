#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CCP master node and related types."""
import can
import enum
import logging
from queue import Empty

from .error import CCPError
from .messages import CommandCodes, ReturnCodes, CommandReceiveObject
from .listeners import MessageSorter


logger = logging.getLogger(__name__)


CCP_VERSION = (2, 1)


class MemoryTransferAddressNumber(enum.IntEnum):
    """The MTA numbers refer to a pair of pointers in the slave device.

    MTA0 is used by the commands DNLOAD, UPLOAD, DNLOAD_6, SELECT_CAL_PAGE,
    CLEAR_MEMORY, PROGRAM and PROGRAM_6.
    MTA1 is used by the MOVE command.
    """

    MTA0_NUMBER = 0
    MTA1_NUMBER = 1


class Master:
    """A CAN Calibration Protocol (CCP) master node."""

    def __init__(
        self, transport: can.Bus, cro_id: int, dto_id: int, is_extended_id: bool
    ):
        self.slaveConnections = {}
        self.cro_id = cro_id
        self.dto_id = dto_id
        self.is_extended_id = is_extended_id
        self._transport = transport
        # Receive both DTOs and CROs, the latter in case local echo is enabled.
        self._transport.set_filters(
            [
                {"can_id": dto_id, "can_mask": 0x1FFFFFFF, "extended": self.is_extended_id},
                {"can_id": cro_id, "can_mask": 0x1FFFFFFF, "extended": self.is_extended_id},
            ]
        )
        self._queue = MessageSorter(dto_id, cro_id)
        self._notifier = can.Notifier(self._transport, [self._queue])
        self.ctr = 0

    def _send(self, command_code: CommandCodes, **kwargs):
        cro = CommandReceiveObject(
            arbitration_id=self.cro_id,
            command_code=command_code,
            is_extended_id=self.is_extended_id,
            ctr=self.ctr,
            **kwargs
        )
        self._transport.send(cro)
        kwargs_str = "  ".join([k.upper() + ": " + hex(v) for k, v in kwargs.items()])
        logger.debug(
            "Sent CRO CTR{}:  %s  %s".format(self.ctr), command_code.name, kwargs_str
        )

    def _receive(self) -> bytearray:
        """Check that the response is what we expect it to be.

        Raises
        ------
        CcpError
            If no Command Return Message is received within 0.5s, or
            if the CRM counter does not match the CRO counter, or
            if the return code is not ACKNOWLEDGE.

        Returns
        -------
        bytearray
            Five data bytes.

        """
        
        try:
            crm = self._queue.get_command_return_message()
        except Empty:
            raise CCPError("No reply from slave")
        if crm.ctr == self.ctr:
            self.ctr = (self.ctr + 1) % 0x100
        else:
            raise CCPError(
                "Counter mismatch: Internal {}, received {}".format(self.ctr, crm.ctr)
            )

        if crm.return_code == ReturnCodes.ACKNOWLEDGE:
            return crm.data[3:]
        else:
            raise CCPError(ReturnCodes(crm.return_code).name)

    def stop(self):
        """Disconnect from CAN bus.

        Returns
        -------
        None.
        """
        self._notifier.stop()
        self._transport.shutdown()

    # #
    # Mandatory Commands
    # #

    def connect(self, station_address: int):
        """Connect to slave specified by station_address.

        Parameters
        ----------
        station_address : int
            Station address of slave ecu (little endian).

        Returns
        -------
        None.
        """
        self._send(CommandCodes.CONNECT, station_address=station_address)
        self._receive()

    def get_ccp_version(
        self, major: int = CCP_VERSION[0], minor: int = CCP_VERSION[1]
    ) -> tuple:
        """Send desired CCP version to slave.

        Parameters
        ----------
        major : int, optional
            Major version number. The default is ccp.CCP_VERSION[0].
        minor : int, optional
             Minor version number. The default is ccp.CCP_VERSION[1].

        Returns
        -------
        tuple
            CCP version implemented by slave as (major, minor).
        """
        self._send(CommandCodes.GET_CCP_VERSION, major=major, minor=minor)
        data = self._receive()
        return data[0], data[1]

    def exchange_id(self, device_info: int = 0) -> tuple:
        """Exchange ID with slave.

        Parameters
        ----------
        device_info : TYPE, optional
           Implementation specific. The default is 0.

        Returns
        -------
        tuple
             size:         Length of slave device ID in bytes,
             dtype:        Data type qualifier of slave device ID,
             availability: Resource availability mask,
             protection:   Resource protection mask
        """
        self._send(CommandCodes.EXCHANGE_ID, device_info=device_info)
        size, dtype, availability, protection, _ = self._receive()
        return size, dtype, availability, protection

    def set_mta(
        self,
        address: int,
        extension: int = 0,
        mta: int = MemoryTransferAddressNumber.MTA0_NUMBER,
    ):
        """Set memory transfer address for subsequent data transfer.

        Parameters
        ----------
        address : int
            Memory address in slave.
        extension : int, optional
            The address extension depends on the slave controller's
            organization and may identify a switchable memory bank
            or a memory segment. The default is 0x00.
        mta : int, optional
            See MemoryTransferAddressNumber. The default is MTA0_NUMBER.

        Returns
        -------
        None.
        """
        self._send(CommandCodes.SET_MTA, address=address, extension=extension, mta=mta)
        self._receive()

    def dnload(self, size: int, data: int) -> tuple:
        """Transfer data from master to slave.

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
        self._send(CommandCodes.DNLOAD, size=size, data=data)
        data = self._receive()
        return data[0], data[1:]

    def upload(self, size: int) -> bytearray:
        """Transfer data from slave to master.

        Parameters
        ----------
        size : int
            Number of bytes to be transferred (0 - 5).

        Returns
        -------
        bytearray
            <size> number of data bytes.
        """
        self._send(CommandCodes.UPLOAD, size=size)
        data = self._receive()
        return data[:size]

    def get_daq_size(self, daq_list_number: int, dto_id: int = None) -> tuple:
        """Return the size of the specified DAQ list.

        Parameters
        ----------
        daq_list_number : int
        dto_id : int
            CAN ID of the DTO dedicated to this DAQ list.

        Returns
        -------
        tuple
             size: Number of ODTs in DAQ list,
             odt0: First ODT number in DAQ list
        """
        dto_id = self.dto_id if dto_id is None else dto_id

        self._send(
            CommandCodes.GET_DAQ_SIZE, daq_list_number=daq_list_number, dto_id=dto_id
        )
        data = self._receive()
        return data[0], data[1]

    def set_daq_ptr(self, daq_list_number: int, odt_number: int, element_number: int):
        """Initialize the DAQ list pointer for a subsequent write.

        Parameters
        ----------
        daq_list_number : int
        odt_number : int
        element_number : int

        Returns
        -------
        None.
        """
        self._send(
            CommandCodes.SET_DAQ_PTR,
            daq_list_number=daq_list_number,
            odt_number=odt_number,
            element_number=element_number,
        )
        self._receive()

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

        Returns
        -------
        None.
        """
        self._send(
            CommandCodes.WRITE_DAQ, size=size, extension=extension, address=address
        )
        self._receive()

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
        ratePrescaler : int, optinal
            Set to >1 to decrease transmission rate.

        Returns
        -------
        None.
        """
        self._send(
            CommandCodes.START_STOP,
            mode=mode,
            daq_list_number=daq_list_number,
            last_odt_number=last_odt_number,
            event_channel=event_channel,
            rate_prescaler=rate_prescaler,
        )
        self._receive()

    def disconnect(
        self, station_address: int, permanent: int = 1,
    ):
        """Disconnect from slave device.

        Parameters
        ----------
        permanent : {0, 1}
            0 temporary,
            1 permanent.
        station_address : int
            Station address of slave device (little endian).

        Returns
        -------
        None.
        """
        self._send(
            CommandCodes.DISCONNECT,
            permanent=permanent,
            station_address=station_address,
        )
        self._receive()

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
        """Inform the slave device about the calibration session state.

        Parameters
        ----------
        status_bits : int
            0x01 CAL:     Calibration data initialized
            0x02 DAQ:     DAQ list(s) initialized
            0x04 RESUME:  Resume session after temporary disconnect
            0x40 STORE:   Save calibration during device shut-down
            0x80 RUN:     Session in progress

        Returns
        -------
        None.
        """
        self._send(CommandCodes.SET_S_STATUS, status_bits=status_bits)
        self._receive()

    def get_s_status(self):
        raise NotImplementedError  # pragma: no cover

    def build_chksum(self):
        raise NotImplementedError  # pragma: no cover

    def clear_memory(self,size: int):
        self._send(CommandCodes.CLEAR_MEMORY,size=size)
        self._receive()

    def program(self, size: int, data: int) -> tuple:
        """Program data from master to slave.

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
        self._send(CommandCodes.PROGRAM, size=size, data=data)
        data = self._receive()
        return data[0], data[1:]

    def program6(self, data: int) -> tuple:
        """Program 6 bytes of data from master to slave.

        Parameters
        ----------
        data : int
            Data to be written to MTA0 in the slave.

        Returns
        -------
        tuple
             mta0_ext:  Current MTA0 extension,
             mta0_addr: Current MTA0 address
        """
        self._send(CommandCodes.PROGRAM_6, size=6, data=data)
        data = self._receive()
        return data[0], data[1:]

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
