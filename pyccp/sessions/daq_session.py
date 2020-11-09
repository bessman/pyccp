#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""A Data Acquisition Session."""

from typing import List
import enum

from pya2l import model

from ..error import CCPError
from ..master import Master
from ..messages import Element, ObjectDescriptorTable


class SessionStatus(enum.IntEnum):
    """Status bits for the SET_S_STATUS command."""

    CAL = 0x01
    DAQ = 0x02
    RESUME = 0x04
    STORE = 0x40
    RUN = 0x80


class DAQSession:
    """During a DAQ session, the slave periodically sends internal variable values."""

    def __init__(self, master: Master, station_address: int):
        self.master = master
        self.get = self.master._queue.get_data_acquisition_message
        self.station_address = station_address
        self.odts = []
        self.daq_lists = []
        self._initialized = False
        self._running = False

    @staticmethod
    def _make_elements(measurements: List[model.Measurement]) -> List[Element]:
        elements = []

        for m in measurements:
            elements.append(
                Element(
                    name=m.name, address=m.ecu_address.address, datatype=m.datatype,
                )
            )

        return elements

    @staticmethod
    def _pack_elements(elements: List[Element], volume: int = 7) -> List[List[Element]]:
        """Pack elements according to the First Fit Descending (FFD) algorithm.

        See https://en.wikipedia.org/wiki/Bin_packing_problem

        Parameters
        ----------
        elements : List[Element]
            List of element objects to the packed into ODTs.
        volume : int, optional
            The volume into which to pack the elements. Defaults to 7, which
            is the maximum length of an ODT.

        Returns
        -------
        bins : List[List[Element]]
            List of lists of elements, packed so that the sum of their size
            does not exceed the specified volume.
        """
        sorted_elements = sorted(elements, reverse=True, key=lambda e: e.size)
        packed = []

        for se in sorted_elements:
            for p in packed:
                if sum([e.size for e in p]) + se.size <= volume:
                    # The item fits in an existing bin
                    p.append(se)
                    break
            else:
                # The item did not fit in an existing bin, put it in a new bin
                packed.append([se])

        return packed

    def _get_daq_lists(self):
        daq_list_size = None

        i = 0
        while daq_list_size != 0:
            daq_list_size, first_odt_number = self.master.get_daq_size(
                daq_list_number=i
            )

            if daq_list_size > 0:
                self.daq_lists.append((first_odt_number, daq_list_size))
            else:
                break

            i += 1

    def _ensure_odts_fit(self):
        if len(self.odts) > sum(self.daq_lists[-1]):
            raise CCPError("Not enough space in DAQ lists.")

    def _set_daq_lists(self):
        self.master.set_s_status(status_bits=SessionStatus.CAL)

        j = 0
        for i, dl in enumerate(self.daq_lists):
            for j, odt in enumerate(self.odts[j:], start=j):
                if j == sum(dl):
                    break

                for k, e in enumerate(odt.elements):
                    self.master.set_daq_ptr(
                        daq_list_number=i, odt_number=j, element_number=k
                    )
                    self.master.write_daq(e.size, e.extension, e.address)

        self.master.set_s_status(status_bits=SessionStatus.CAL | SessionStatus.DAQ)

    def initialize(self, measurements: List[model.Measurement]):
        """Set up ODTs and send them to slave."""
        if self._initialized:
            self.stop()
            self.initialize(measurements)

        self.master.connect(self.station_address)
        elements = self._make_elements(measurements)
        bins = self._pack_elements(elements)

        for i, b in enumerate(bins):
            odt = ObjectDescriptorTable(elements=b, number=i)
            odt.register()
            self.odts.append(odt)

        self._get_daq_lists()
        self._ensure_odts_fit()
        self._set_daq_lists()
        self._initialized = True

    def _start_stop_all(self, mode: int):
        for i, dl in enumerate(self.daq_lists):
            last_odt_number = min(sum(dl), len(self.odts)) - 1
            self.master.start_stop(
                mode=mode, daq_list_number=i, last_odt_number=last_odt_number
            )

    def run(self):
        """Start the DAQ session."""
        if self._initialized:
            START = 1
            self._start_stop_all(mode=START)
            self._running = True
        else:
            self.initialize()
            self.run()

    def stop(self):
        """Stop the DAQ session."""
        if self._running:
            STOP = 0
            self._start_stop_all(mode=STOP)
            self._running = False

        if self._initialized:
            self.master.disconnect(station_address=self.station_address)

            for odt in self.odts:
                odt.deregister()

            self._initialized = False
