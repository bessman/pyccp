#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cantools
import enum
import decimal
from typing import List, Union
from pyccp.messages.data_transmission import DataTransmissionObject


class DataAcquisitionMessage(DataTransmissionObject):
    """
    Data Acquisition Messages (DAQ) are a type of Data Transmission Object
    which is sent periodically from a slave to the master during DAQ sessions.
    They contain data specified by Object Descriptor Tables.
    """

    def __init__(
        self,
        arbitration_id: int,
        odt_number: int,
        daq_data: Union[List[int], bytearray],
        timestamp: float = 0,
        channel: Union[int, str] = None,
        is_extended_id: bool = True,
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
        self.odt_number = odt_number
        self.daq_data = daq_data
        super().__init__(
            arbitration_id=arbitration_id,
            pid=odt_number,
            dto_data=list(daq_data),
            timestamp=timestamp,
            channel=channel,
            is_extended_id=is_extended_id,
        )

    def __repr__(self) -> str:
        args = [
            "timestamp={}".format(self.timestamp),
            "odt_number={:#x}".format(self.odt_number),
        ]

        daq_data = ["{:#02x}".format(byte) for byte in self.daq_data]
        args += ["daq_data=[{}]".format(", ".join(daq_data))]

        return "ccp.DataAcquisitionMessage({})".format(", ".join(args))

    def __str__(self) -> str:
        field_strings = ["Timestamp: {0:>8.6f}".format(self.timestamp)]
        field_strings.append("DAQ")
        field_strings.append(str(self.odt_number))
        field_strings.append(str(list(self.daq_data)))

        return "  ".join(field_strings).strip()


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
            Starting bit of the variable in the ODT. Little endian, i.e. if the
            first byte of the ODT is big endian its starting bit is 7.
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
        name: str = None,
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
        name : str, optional
            Name of the ODT. If none is provided it will default to the ODT
            number as a string.

        Returns
        -------
        None.

        """
        self._number = number

        if name is None:
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
