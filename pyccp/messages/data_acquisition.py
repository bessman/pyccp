#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""CCP DAQ-DTO and associated data types."""

import cantools
import enum
import decimal
from typing import Dict, List, Union

from . import MAX_DLC
from .data_transmission import DataTransmissionObject


class DataAcquisitionMessage(DataTransmissionObject):
    """A DTO sent from slave to master during a data acquisition session."""

    def __init__(
        self,
        arbitration_id: int = 0,
        odt_number: int = 0,
        data: bytearray = bytearray(MAX_DLC),
    ):
        """Create a DAQ message.

        Parameters
        ----------
        odt_number : int
            The number of the Object Descriptor Table which describes the data
            in this DAQ message.
        daq_data : list of int or bytearray
            Data, the meaning of which is described in the Object Descriptor
            Table specified by odt_number.

        Returns
        -------
        None.
        """
        super().__init__(
            arbitration_id=arbitration_id, pid=odt_number, data=data,
        )

    def decode(self) -> Dict[str, int]:
        """Decode the message data.

        Raises
        ------
        KeyError
            If this error is raised, it usually means that no ODT corresponding
            to odt_number has been registered with DAQ_DB.

        Returns
        -------
        Dict[str, int]
            A dictionary with {name: decoded value}-pairs for all Elements in
            this message.
        """
        try:
            return DAQ_DB.get_message_by_name(str(self.odt_number)).decode(
                self.data[1:]
            )
        except KeyError as e:
            raise KeyError("No ODT with number {}".format(e))

    @property
    def odt_number(self) -> int:
        """Get the ODT number of this DAQ message, held in data[0].

        Returns
        -------
        int
        """
        return self.pid

    @odt_number.setter
    def odt_number(self, value: int):
        self.pid = value


class Element(cantools.database.Signal):
    """Elements hold pointers to variables in the slave device."""

    def __init__(
        self,
        name: str,
        size: int,
        address: int,
        extension: int = 0,
        byte_order: str = "big_endian",
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
        self._address = address
        self._extension = extension
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
    def address(self):
        """Get the element's memory address in the slave device."""
        return self._address

    @address.setter
    def address(self, value):
        self._address = value

    @property
    def extension(self):
        """Get the element's address extension."""
        return self._extension

    @extension.setter
    def extension(self, value):
        self._extension = value

    @property
    def size(self):
        """Get the element's length in bytes."""
        # cantool.database.Signal.length is in bits
        return self._length // 8

    @size.setter
    def size(self, value):
        self._length = value * 8

    @property
    def start_byte(self):
        """Translate from starting bit to starting byte."""
        return self._start // 8

    @start_byte.setter
    def start_byte(self, value):
        """Translate from starting byte to starting bit.

        See cantools.database.can.Signal for details on the byte order stuff.
        """
        self._start = value * 8 + 7 if self.byte_order == "big_endian" else value * 8


class ObjectDescriptorTable(cantools.database.Message):
    """Object Descriptor Tables (ODT) describe the layout of DAQ messages."""

    def __init__(
        self, elements: List[Element], number: int, length: int = 7,
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
        self.elements = elements
        self._assign_element_numbers()
        self._get_frame_id()
        name = str(number)
        super().__init__(
            frame_id=self.frame_id, name=name, length=length, signals=self.elements,
        )

    def _get_frame_id(self):
        if len(DAQ_DB.messages) == 0:
            self.frame_id = 0
        else:
            self.frame_id = max([f.frame_id for f in DAQ_DB.messages]) + 1

    def _assign_element_numbers(self):
        start_byte = 0

        for e in self.elements:
            e.start_byte = start_byte
            start_byte += e.size

    def register(self):
        """Register this ODT with DAQ_DB."""
        DAQ_DB.messages.append(self)
        DAQ_DB.refresh()

    def deregister(self):
        """Remove this ODT from DAQ_DB."""
        DAQ_DB.messages.remove(self)
        DAQ_DB.refresh()

    @property
    def number(self):
        """Get the ODT number."""
        return self._number

    @property
    def elements(self):
        """Get Element in the ODT."""
        return self._signals

    @elements.setter
    def elements(self, value):
        self._signals = value


DAQ_DB = cantools.database.Database()
