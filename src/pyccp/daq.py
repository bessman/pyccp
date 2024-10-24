import decimal
import enum
import logging
from typing import Callable, Dict, Iterator, List, Union

import cantools

from pyccp.decoder import DAQDecoder
from pyccp.node import Node


_logger = logging.getLogger(__name__)


class SessionStatus(enum.IntEnum):
    """Status bits for the SET_S_STATUS command."""

    CAL = 0x01
    DAQ = 0x02
    RESUME = 0x04
    STORE = 0x40
    RUN = 0x80


class DAQMode(enum.IntEnum):
    STOP = 0
    START = 1


class Element(cantools.database.can.Signal):
    """Elements hold pointers to variables in the slave device."""

    def __init__(
        self,
        name: str,
        size: int,
        address: int,
        extension: int = 0,
        event_channel: int = 0,
        on_receive: Union[Callable[[float, int], None], None] = None,
        byte_order: str = "little_endian",
        is_signed: bool = False,
        initial: Union[int, float] = None,
        scale: int = 1,
        offset: Union[int, float] = 0,
        minimum: Union[int, float] = None,
        maximum: Union[int, float] = None,
        unit: str = None,
        choices: enum.IntEnum = None,
        comment: str = None,
        is_float: bool = False,
        decimal: decimal.Decimal = None,
    ):
        """Create a DAQ Element.

        Parameters
        ----------
        name : str
            Name of the slave internal variable.
        size : int
            Size of the variable in bytes.
        address : int
            Memory address of the variable in the slave.
        extension : int, optional
            Address extension in slave. The default is 0.

        Returns
        -------
        None.
        """
        self.address = address
        self.extension = extension
        self.event_channel = event_channel
        self.on_receive = on_receive
        super().__init__(
            name=name,
            start=0,
            length=size * 8,  # Bytes -> bits
            byte_order=byte_order,
            is_signed=is_signed,
            initial=initial,
            scale=scale,
            offset=offset,
            minimum=minimum,
            maximum=maximum,
            unit=unit,
            choices=choices,
            comment=comment,
            is_float=is_float,
            decimal=decimal,
        )

    @property
    def size(self):
        """Get the element's length in bytes."""
        # cantool.database.Signal.length is in bits
        return self.length // 8

    @size.setter
    def size(self, value):
        self.length = value * 8

    @property
    def start_byte(self):
        """Translate from starting bit to starting byte."""
        return self.start // 8

    @start_byte.setter
    def start_byte(self, value):
        """Translate from starting byte to starting bit.

        See cantools.database.can.Signal for details on the byte order stuff.
        """
        self.start = value * 8 + 7 if self.byte_order == "big_endian" else value * 8


class ObjectDescriptorTable(cantools.database.Message):
    """Object Descriptor Tables (ODT) describe the layout of DAQ messages."""

    def __init__(
        self,
        elements: List[Element],
        number: int,
        length: int = 7,
    ):
        """Create an ODT.

        Parameters
        ----------
        elements : list of Element
            List of Element objects which point to slave internal data.
        number : int
            ODT number.
        length : int, optional
            Number of bytes in ODT. The default is 7.

        Returns
        -------
        None.
        """
        self._number = number
        self.elements = {e.name: e for e in elements}
        self._assign_element_numbers()
        super().__init__(
            frame_id=number,
            name=str(number),
            length=length,
            signals=elements,
        )

    def _assign_element_numbers(self):
        start_byte = 0
        for e in self.elements.values():
            e.start_byte = start_byte
            start_byte += e.size

    @property
    def number(self):
        """Get the ODT number."""
        return self._number


class DAQList:
    def __init__(
        self,
        node: Node,
        number: int,
        size: int,
        first_odt_number: int,
        odts: Union[List[ObjectDescriptorTable], None] = None,
    ):
        self._node = node
        self.number = number
        self.size = size
        self.first_odt_number = first_odt_number
        self.odts = [] if odts is None else odts
        self.update()
        self.apply()

    def update(self):
        elements = (e for odt in self.odts for e in list(odt.elements.values()))
        self.event_channels = {e.event_channel for e in elements}

    def apply(self):
        self.update()
        for i, odt in enumerate(self.odts):
            for j, e in enumerate(list(odt.elements.values())):
                self._node.set_daq_ptr(
                    daq_list_number=self.number,
                    odt_number=i,
                    element_number=j,
                )
                self._node.write_daq(e.size, e.extension, e.address)

    def start(self):
        self._start_stop(DAQMode.START)

    def stop(self):
        self._start_stop(DAQMode.STOP)

    def _start_stop(self, start_or_stop: DAQMode) -> None:
        if self.odts:
            for event_channel in self.event_channels:
                last = min(self.first_odt_number + self.size, len(self.odts)) - 1
                self._node.start_stop(
                    mode=start_or_stop,
                    daq_list_number=self.number,
                    last_odt_number=last,
                    event_channel=event_channel,
                )


class DAQSession:
    """During a DAQ session, the node periodically sends internal data."""

    def __init__(self, node: Node):
        self._node = node
        self._elements: List[Element] = []
        self._daq_lists: List[DAQList] = []
        self._get_daq_lists()
        self._odts: List[ObjectDescriptorTable] = []
        self._decoder = DAQDecoder(node.dto_id, self._odts)
        self._node.add_listener(self._decoder)
        self.queue = self._decoder.queue
        self._running: bool = False

    def __iter__(self) -> Iterator[Dict[str, float]]:
        for d in self._decoder:
            yield d

    def configure(self, elements: List[Element]) -> None:
        self._elements = elements
        self._pack_elements()
        self._decoder.decoders = self._odts
        self._node.set_s_status(status_bits=SessionStatus.CAL)
        for daq_list in self._daq_lists:
            daq_list.apply()

    def start(self):
        """Start the DAQ session."""
        if self._running:
            return

        self._node.set_s_status(status_bits=SessionStatus.DAQ)

        for daq_list in self._daq_lists:
            daq_list.start()

        self._running = True

    def stop(self):
        """Stop the DAQ session."""
        if not self._running:
            return
        for daq_list in self._daq_lists:
            daq_list.stop()
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def _pack_elements(self, volume: int = 7) -> Dict[int, List[List[Element]]]:
        """Pack elements according to the First Fit Descending (FFD) algorithm.

        See https://en.wikipedia.org/wiki/Bin_packing_problem

        Parameters
        ----------
        elements : List[Element]
            List of element objects to the packed into ODTs.
        volume : int, optional
            The volume into which to pack the elements. Defaults to 7, which
            is the maximum length of an ODT.
        """
        packed = []

        # Pack into bins.
        sorted_elements = sorted(self._elements, reverse=True, key=lambda e: e.size)

        for se in sorted_elements:
            for p in packed:
                if sum([e.size for e in p]) + se.size <= volume:
                    # The item fits in an existing bin
                    p.append(se)
                    break
            else:
                # The item did not fit in an existing bin, put it in a new bin
                packed.append([se])

        # Create ODTs and pack into DAQ lists.
        daq_list_iterator = iter(self._daq_lists)
        daq_list = next(daq_list_iterator)

        for b in packed:
            odt = ObjectDescriptorTable(
                elements=b,
                number=len(self._odts),
            )
            self._odts.append(odt)
            if len(daq_list.odts) == daq_list.size:
                daq_list = next(daq_list_iterator)
            daq_list.odts.append(odt)

    def _get_daq_lists(self) -> None:
        self._daq_lists = []
        size = None
        i = 0

        while size != 0:
            size, first = self._node.get_daq_size(daq_list_number=i)
            if size > 0:
                daq_list = DAQList(
                    node=self._node,
                    number=i,
                    size=size,
                    first_odt_number=first,
                )
                self._daq_lists.append(daq_list)
            i += 1
