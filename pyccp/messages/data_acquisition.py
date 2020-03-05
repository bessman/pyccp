#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cantools
import enum
import decimal
from typing import Dict, List, Union

from . import MAX_DLC
from .data_transmission import DataTransmissionObject


class DataAcquisitionMessage(DataTransmissionObject):
    """
    Data Acquisition Messages (DAQ) are a type of Data Transmission Object
    which is sent periodically from a slave to the master during DAQ sessions.
    They contain data specified by Object Descriptor Tables.
    """

    def __init__(
        self,
        arbitration_id: int = 0,
        odt_number: int = 0,
        data: bytearray = bytearray(MAX_DLC),
    ):
        """
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
        try:
            return DAQ_DB.get_message_by_name(str(self.odt_number)).decode(
                self.data[1:]
            )
        except KeyError as e:
            raise KeyError("No ODT with number {}".format(e))

    @property
    def odt_number(self) -> int:
        return self.pid

    @odt_number.setter
    def odt_number(self, value: int):
        self.pid = value


class Element(cantools.database.Signal):
    """
    Elements are the contents of Object Descriptor Tables. They are pointers
    to variables inside a slave.
    """

    def __init__(
        self,
        name: str,
        start: int,
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
        """
        Parameters
        ----------
        name : str
            Name of the slave internal variable.
        start : int
            Starting bit of the variable in the ODT. Meaning is
            counter-intuitive for big endian data. See
            cantools.database.can.Signal for details.
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
            start=start,
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
        """The element's memory address in the slave ECU.
        """

        return self._address

    @address.setter
    def address(self, value):
        self._address = value

    @property
    def extension(self):
        """The element's address extension.
        """

        return self._extension

    @extension.setter
    def extension(self, value):
        self._extension = value

    @property
    def size(self):
        """The element's length in bytes.
        """
        # cantool.database.Signal.length is in bits
        return self._length // 8

    @size.setter
    def size(self, value):
        self._length = value * 8


class ObjectDescriptorTable(cantools.database.Message):
    """
    Object Descriptor Tables (ODT) describe the layout of DAQ messages. ODTs
    contain Elements which refer to memory addresses in a slave. ODTs are
    sent from the master to a slave during session configuration with the
    SET_DAQ_PTR and WRITE_DAQ commands, and then used by the master to parse
    data received from a slave during a DAQ session.
    """

    def __init__(
        self,
        frame_id: int,
        length: int,
        elements: List[Element],
        number: int,
        comment: str = None,
        is_extended_frame: bool = True,
    ):
        """
        Parameters
        ----------
        elements : list of Element
            List of Element objects which point to slave internal data.
        number : int
            ODT number.

        Returns
        -------
        None.

        """
        self._number = number
        name = str(number)
        super().__init__(
            frame_id=frame_id,
            name=name,
            length=length,
            signals=elements,
            comment=comment,
            is_extended_frame=is_extended_frame,
        )
        self._elements = self._signals

    def register(self):
        DAQ_DB.messages.append(self)
        DAQ_DB.refresh()

    def deregister(self):
        DAQ_DB.messages.remove(self)
        DAQ_DB.refresh()

    @property
    def number(self):
        """ODT number.
        """

        return self._number

    @property
    def elements(self):
        """Elements of the ODT.
        """

        return self._elements


DAQ_DB = cantools.database.Database()
