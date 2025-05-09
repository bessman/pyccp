"""Data Acquisition (DAQ) over CCP."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from enum import IntEnum
from itertools import islice
from typing import Callable, Literal, Optional, overload

import can
import cantools
from cantools.typechecking import DecodeResultType

import pyccp


_logger = logging.getLogger(__name__)


class DAQMode(IntEnum):
    """DAQ list mode.
    
    STOP: DAQ list inactive.
    START: DAQ active.
    SYNC: DAQ list ready for synchronized start.
    """
    STOP = 0x00
    START = 0x01
    SYNC = 0x02


DAQCallback = Callable[[float, DecodeResultType], None]
"""A DAQCallback may be set on an Element. When that Element is received in a DAQ
   session, the callback is called with the following arguments:
       timestamp : float
           The timestamp of the DAQ-DTO CAN message holding the Element.
       decoded : dict[str, int | float, str]
           A dictionary with a single key-value pair of "element_name": decoded_value.
"""


@dataclass(frozen=True)
class Element:
    """An Element is a pointer to a variable in the slave device.

    Parameters
    ----------
    name : str
        A unique name identifying the variable.
    address : int
        Address of the variable. Four bytes.
    size : {1, 2, 4}, default=1
        Size of the variable in bytes
    extension : int, default=0
        Address extension. One byte.
    is_signed : bool, default=False
    is_float : bool, default=False
    scale : int, default=1
    offset : int, default=0
    choices : dict[int, str], default=None
        Mapping of integer values to strings.
    on_received : DAQCallback, default None
        An optional callback function which is called when this element is received in a
        DAQ session.
    """

    name: str
    address: int
    size: Literal[1, 2, 4] = 1
    extension: int = 0
    is_signed: bool = False
    is_float: bool = False
    scale: int | float = 1
    offset: int | float = 0
    choices: Optional[dict[int, str]] = None
    on_received: Optional[DAQCallback] = None


class _Element(cantools.database.can.Signal):
    def __init__(
            self, 
            on_received: Optional[DAQCallback] = None, 
            *args, 
            **kwargs
        ) -> None:
        super().__init__(*args, **kwargs)
        self._on_received = on_received
    
    @property
    def on_received(self) -> DAQCallback:
        def default(timestamp: float, decoded: DecodeResultType):
            pass
        return self._on_received or default


class ODT:
    """Object Descriptor Tables (ODT) describe the layout of DAQ-DTO messages.

    A DAQ-DTO message contains a PID (1 byte) and an ODT (7 bytes). The PID identifies
    the ODT that follows it. The ODT contains Element values that the slave has been
    configured to transmit during a DAQ session.
    
    Parameters
    ----------
    elements : list[Element]
    """

    MAX_SIZE = 7

    def __init__(self, elements: list[Element]) -> None:
        if sum(e.size for e in elements) > ODT.MAX_SIZE:
            raise pyccp.CCPError(
                "Total size of elements in ODT may not exceed seven bytes"
            )

        self._elements = {}
        previous = None

        for e in elements:
            key = list(self._elements.keys())[-1] + previous.size if previous else 0
            self._elements[key] = e
            previous = e

    def __repr__(self) -> str:
        return f"ODT({self.elements})"

    @property
    def elements(self) -> dict[int, Element]:
        """Elements in ODT as a dictionary of location_in_odt: Element."""
        return self._elements


class _DAQListener(can.Listener):
    """Listen for and decode incoming DAQ messages.

    Parameters
    ----------
    daq_dto : cantools.database.can.Message
        A cantools Message instance used to decode received DAQ DTOs.
    """

    def __init__(
        self,
        daq_dto: cantools.database.can.Message,
    ) -> None:
        self.daq_dto = daq_dto

    @property
    def _known_pids(self) -> set[int]:
        return set(
            [
                s.multiplexer_ids[0]
                for s in self.daq_dto.signals
                if s.multiplexer_ids is not None
            ]
        )

    def on_message_received(self, msg: can.Message) -> None:
        """Decode an incoming message.

        Parameters
        ----------
        msg : can.Message
        """
        if (
            msg.arbitration_id == self.daq_dto.frame_id
            and msg.data[pyccp.DTO_PID_BYTE] in self._known_pids
        ):
            _logger.debug(f"{self} received DAQ-DTO: {msg}")
            decoded = self.daq_dto.decode(msg.data)
            _logger.debug(f"{self} decoded DAQ-DTO: {decoded}")
            decoded.pop("pid")

            for k, v in decoded.items():
                if isinstance(e := self.daq_dto.get_signal_by_name(k), _Element):
                    e.on_received(msg.timestamp, {k: v})

    def __repr__(self) -> str:
        return f"DAQListener(DTO 0x{self.daq_dto.frame_id:X}, PIDs {self._known_pids})"


class DAQList(Sequence):
    """Model of a DAQ list on the slave.

    Parameters
    ----------
    number : int
        DAQ list number.
    size : int
        Number of ODTs the DAQ list can hold.
    first_pid : int
        PID of the DTO frame containing the first ODT in the DAQ list.
    """

    def __init__(
        self,
        node: pyccp.CCPSlave,
        number: int,
        size: int,
        first_pid: int,
    ):
        self._node = node
        self._number = number
        self._size = size
        self._first_pid = first_pid
        self._mode = DAQMode.STOP
        self._event_channel: int | None = None
        self._odts = []
        self._listener = _DAQListener(self._daq_dto)
        self.node.add_listener(self._listener)

    @property
    def node(self) -> pyccp.CCPSlave:
        """The slave node to which this DAQ list belongs. (read only)"""
        return self._node

    @property
    def number(self) -> int:
        """DAQ list number. (read only)"""
        return self._number

    @property
    def size(self) -> int:
        """Number of ODTs the DAQ list can hold.. (read only)"""
        return self._size

    @property
    def first_pid(self) -> int:
        """PID of the DTO frame containing the first ODT in the DAQ list. (read only)
        
        PIDs of DTOs holding subsequent ODTs increment by one per ODT.
        """
        return self._first_pid

    @property
    def mode(self) -> DAQMode:
        """DAQ list mode, either STOP or START. (read only)"""
        return self._mode

    @property
    def event_channel(self) -> int | None:
        """Currently active event channel. (read only)"""
        return self._event_channel

    @property
    def _pid(self) -> cantools.database.can.Signal:
        return cantools.database.can.Signal(
            name="pid",
            start=7 * (self.node.byte_order == "big_endian"),
            length=8,
            byte_order=self.node.byte_order,
            is_multiplexer=True,
        )

    @overload
    def __getitem__(self, idx: int) -> ODT:
        ...
    @overload
    def __getitem__(self, idx: slice) -> list[ODT]:
        ...
    def __getitem__(self, idx):
        return self._odts[idx]

    @overload
    def __setitem__(self, idx: int, value: ODT) -> None:
        ...
    @overload
    def __setitem__(self, idx: slice, value: list[ODT]) -> None:
        ...
    def __setitem__(self, idx, value):
        if self.mode == DAQMode.START:
            raise pyccp.CCPError("Cannot modify active DAQ list")

        if isinstance(idx, slice):
            start = idx.start or 0
            
            if len(value) > self.size - start:
                raise IndexError(f"ODTs do not fit in DAQ list (size={self.size})")
            
            for i, v in zip(range(*idx.indices(len(self))), value):
                # recurse
                self[i] = v

            return

        self._odts[idx] = value
        self._listener.daq_dto = self._daq_dto

        for i, e in enumerate(value.elements.values()):
            _logger.debug(f"Writing element to DAQList#{self.number}[{idx}][{i}]")
            self.node.set_daq_ptr(
                daq_list_number=self.number,
                odt_number=idx,
                element_number=i,
            )
            self.node.write_daq(e.size, e.extension, e.address)

    def __len__(self) -> int:
        return len(self._odts)

    def __repr__(self) -> str:
        return (
            f"DAQList#{self.number}(mode={self.mode.name}, "
            f"first_pid={self.first_pid}, "
            f"length={self.size}) "
            f"{self._odts}"
        )
    
    def append(self, value: ODT) -> None:
        """Append an ODT to DAQ list.
        
        Raises
        ------
        IndexError
            If DAQ list is full.
        """
        if len(self) + 1 > self.size:
            raise IndexError(f"DAQ list full (size={self.size})")
        self._odts.append(None)
        self[-1] = value
    
    def extend(self, value: list[ODT]) -> None:
        """Extend DAQ list with a list of ODTs.
        
        Raises
        ------
        IndexError
            If the total length of the current DAQ list plus the length of the new ODTs
            would exceed the DAQ list size.
        """
        if len(self) + len(value) > self.size:
            raise IndexError(f"ODTs do not fit in DAQ list (size={self.size})")
        self._odts.extend([None] * len(value))
        self[-len(value):] = value

    def start(self, event_channel: int = 0, rate_prescaler: int = 1) -> None:
        """Start data acquisition of this DAQ list.
        
        Parameters
        ----------
        event_channel : int, default=0
            An implementation defined signal source.
        rate_prescaler : int, default=1
            Transmission rate is decreased by this factor.
        """
        self._event_channel = event_channel
        self._start_stop(DAQMode.START, event_channel, rate_prescaler)

    def stop(self) -> None:
        """Stop data acquisition of this DAQ list."""
        self._start_stop(DAQMode.STOP, event_channel=self.event_channel)
        self._event_channel = None

    def sync(self, event_channel: int = 0, rate_prescaler: int = 1) -> None:
        """Prepare DAQ list for synchronized start."""
        self._event_channel = event_channel
        self._start_stop(DAQMode.SYNC, event_channel, rate_prescaler)

    def _start_stop(
        self,
        mode: DAQMode,
        event_channel: int = 0,
        rate_prescaler: int = 1,
    ) -> None:
        if mode and all(odt is None for odt in self):
            _logger.warning(f"Not starting empty DAQList#{self.number}")
            return

        self._mode = mode
        last_odt_number = [i for i, odt in enumerate(self) if odt is not None][-1]
        action = f"{('Stopp', 'Start', 'Sync')[mode]}ing"
        odts = f"ODT{'s#0-' if last_odt_number else '#'}{last_odt_number}"
        _logger.debug(
            f"{action} {odts} of DAQList#{self.number} on channel#{event_channel}"
        )

        self.node.session_status |= pyccp.SessionStatus.DAQ
        self.node.start_stop(
            mode=mode,
            daq_list_number=self.number,
            last_odt_number=last_odt_number,
            event_channel=event_channel,
            rate_prescaler=rate_prescaler,
        )

    def clear(self) -> None:
        """Remove all ODTs from DAQ list.
        
        CCP does not support removing individual ODTs.
        """
        _logger.debug(f"Clearing DAQList#{self.number}")
        daq_metadata = self.node.get_daq_size(self.number)
        self._size = daq_metadata.size
        self._first_pid = daq_metadata.first_pid
        self._mode = DAQMode.STOP
        self._odts = []
        self._listener.daq_dto = self._daq_dto

    @property
    def _daq_dto(self) -> cantools.database.can.Message:
        """A cantools.database.can.Message able to decode all DAQ-DTOs of DAQ list."""
        pid = cantools.database.can.Signal(
            name="pid",
            start=7 * (self.node.byte_order == "big_endian"),
            length=8,
            byte_order=self.node.byte_order,
            is_multiplexer=True,
        )
        muxed = [
            _Element(
                name=e.name,
                start=(k + 1) * 8 + 7 * (self.node.byte_order == "big_endian"),
                length=e.size * 8,
                byte_order=self.node.byte_order,
                is_signed=e.is_signed,
                conversion=cantools.database.conversion.BaseConversion.factory(
                    choices=e.choices,
                    is_float=e.is_float,
                    scale=e.scale,
                    offset=e.offset,
                ),
                multiplexer_signal="pid",
                multiplexer_ids=[self.first_pid + i],
                on_received = e.on_received,
            )
            for i, odt in enumerate(self) if odt is not None
            for k, e in odt.elements.items()
        ]

        return cantools.database.can.Message(
            name="DAQ_DTO",
            frame_id=self.node.dto_id,
            length=8,
            signals=[pid] + muxed,
        )

    def pack_elements_into(self, elements: list[Element]) -> None:
        """Pack elements into DAQ list.

        Any already configured elements will be cleared.

        Parameters
        ----------
        elements : list[Element]

        Raises
        ------
        CCPError
            If elements do not fit in DAQ list.
        """
        odts = pack_elements(elements)
        
        if len(odts) > self.size:
            raise pyccp.CCPError("Elements to not fit in DAQ list")
        
        if self:
            self.clear()
        
        self.extend(odts)


class DAQLists(Sequence):
    """Aggregate of DAQList."""
    
    def __init__(self, daq_lists: list[DAQList]) -> None:
        nodes = set(dl.node for dl in daq_lists)

        if len(nodes) > 1:
            raise pyccp.CCPError(
                "All DAQ lists in DAQLists instance must belong to same slave"
            )

        self._node: pyccp.CCPSlave | None = nodes.pop() if nodes else None
        self._daq_lists = daq_lists

    @property
    def node(self) -> pyccp.CCPSlave | None:
        return self._node

    @overload
    def __getitem__(self, key: int) -> DAQList:
        ...
    @overload
    def __getitem__(self, key: slice) -> DAQLists:
        ...
    def __getitem__(self, key):
        if isinstance(key, slice):
            return DAQLists(self._daq_lists[key])
        return self._daq_lists[key]

    def __len__(self) -> int:
        return len(self._daq_lists)
    
    def __repr__(self) -> str:
        return f"{[str(dl) for dl in self]}"

    def start(self, event_channel: int = 0, rate_prescaler: int = 1) -> None:
        """Start all configured DAQ lists simultaneously.
        
        This starts all DAQ lists on slave which have been prepared for synchronized
        start, including lists which are not part of this aggregate.
        """
        for dl in self:
            if dl:
                dl.sync(event_channel, rate_prescaler)

        self.node.session_status |= pyccp.SessionStatus.DAQ
        self.node.start_stop_all(DAQMode.START)

    def stop(self) -> None:
        """Stop all DAQ lists.
        
        This stops all DAQ lists on slave, including lists which are not part of this
        aggregate.
        """
        self.node.start_stop_all(DAQMode.STOP)

    def clear(self) -> None:
        """Clear DAQ lists."""
        for dl in self:
            if dl:
                dl.clear()
        self.node.session_status &= ~pyccp.SessionStatus.DAQ

    def pack_elements_into(self, elements: list[Element]) -> None:
        """Pack elements into DAQ lists.

        Parameters
        ----------
        elements : list[Element]

        Raises
        ------
        CCPError
            If elements do not fit in DAQ lists.
        """
        odts = iter(pack_elements(elements))
        self.clear()

        for dl in self:
            dl.extend(list(islice(odts, dl.size)))

        try:
            next(odts)
        except StopIteration:
            pass
        else:
            raise pyccp.CCPError("Elements do not fit in available DAQ lists")


def pack_elements(elements: list[Element]) -> list[ODT]:
    """Pack elements according to the First Fit Descending (FFD) algorithm.

    See https://en.wikipedia.org/wiki/Bin_packing_problem

    Parameters
    ----------
    elements : list[Element]
        List of Elements to be packed into ODTs.

    Returns
    -------
    list[ODT]
        ODTs which can be placed in DAQ lists.
    """
    packed = []

    # Pack into bins.
    for se in sorted(elements, reverse=True, key=lambda e: e.size):
        for p in packed:
            if sum([e.size for e in p]) + se.size <= ODT.MAX_SIZE:
                # The item fits in an existing bin.
                p.append(se)
                break
        else:
            # The item did not fit in an existing bin, put it in a new bin.
            packed.append([se])

    return [ODT(elements=b) for b in packed]
