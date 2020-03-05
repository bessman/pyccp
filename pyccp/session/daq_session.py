#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import List
from itertools import zip_longest

from .. import SessionStatus, CCPError
from ..master import Master
from ..messages import CommandCodes
from ..messages.data_acquisition import Element, ObjectDescriptorTable


class DAQSession:
    def __init__(self, master: Master, station_address: int, elements: List[Element]):
        self.master = master
        self.station_address = station_address
        self.four_byte_elements = [e for e in elements if e.size == 4]
        self.two_byte_elements = [e for e in elements if e.size == 2]
        self.one_byte_elements = [e for e in elements if e.size == 1]
        self.odts = []

    @staticmethod
    def _grouper(iterable, n, fillvalue=None):
        "Collect data into fixed-length chunks or blocks"
        # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
        args = [iter(iterable)] * n
        return zip_longest(*args, fillvalue=fillvalue)

    def _distribute_four_byte_elements(self):
        # We need at least one ODT per four-byte element
        for e4 in self.four_byte_elements:
            e4.start_byte = 0
            self.odts.append([e4])

    def _distribute_two_byte_elements(self):
        for e2, odt in zip(self.two_byte_elements, self.odts):
            e2.start_byte = 4

            odt.append(e2)

        chunks = self._grouper(self.two_byte_elements[len(self.odts) :], 3)

        for e2x3 in chunks:
            for enum, e2 in enumerate(e2x3):
                if e2 is not None:
                    e2.start_byte = 2 * enum  # Byte 0, 2, or 4

            self.odts.extend(e2x3)

    def _distribute_one_byte_elements(self):
        for e1, odt in zip(self.one_byte_elements, self.odts):
            e1.start_byte = sum([e.size for e in odt])
            odt.append(e1)

        chunks = self._grouper(self.one_byte_elements[len(self.odts) :], 7)

        for e1x7 in chunks:
            for enum, e1 in enumerate(e1x7):
                if e1 is not None:
                    e1.start_byte = enum  # Byte 0, 1, 2, 3, 4, 5, or 6

            self.odts.extend(e1x7)

    def initialize(self):
        """Set up ODTs and send them to slave.
        """
        self.master.send(CommandCodes.CONNECT, station_address=self.station_address)
        self.master.receive()
        # Elements can be 1, 2, or 4 bytes long, and ODTs can hold up tp 7 bytes
        # data. The _distribute* functions sort the elements into lists to use
        # as few ODTs as possible. Could be optimized.
        self._distribute_four_byte_elements()
        self._distribute_two_byte_elements()
        self._distribute_one_byte_elements()

        self.master.send(CommandCodes.SET_S_STATUS, status_bits=SessionStatus.CAL)
        self.master.receive()

        daq_list_number = 0
        self.master.send(
            CommandCodes.GET_DAQ_SIZE, daq_list_number=daq_list_number, dto_id=0
        )
        daq_list_size, first_odt_number = self.master.receive()[0:2]

        odt_number = 0
        for odt in self.odts:
            if odt_number == daq_list_size + first_odt_number:
                daq_list_number += 1
                self.master.send(
                    CommandCodes.GET_DAQ_SIZE, daq_list_number=daq_list_number, dto_id=0
                )
                daq_list_size, first_odt_number = self.master.receive()[0:2]

                continue
            elif odt_number > daq_list_size + first_odt_number:
                raise CCPError("DAQ lists full, cannot add ODT#{}.".format(odt_number))

            odt = ObjectDescriptorTable(odt, odt_number)
            odt.register()

            for i, e in enumerate(odt.elements):
                self.master.send(
                    CommandCodes.SET_DAQ_PTR,
                    daq_list_number=daq_list_number,
                    odt_number=odt.number,
                    element_number=i,
                )
                self.master.receive()
                self.master.send(
                    CommandCodes.WRITE_DAQ,
                    element_size=e.size,
                    extension=e.extension,
                    address=e.address,
                )
                self.master.receive()

            odt_number += 1

        self.master.send(
            CommandCodes.SET_S_STATUS, status_bits=SessionStatus.CAL | SessionStatus.DAQ
        )
        self.master.receive()

    def run(self):
        pass

    def stop(self):
        pass
