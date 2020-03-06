#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import List
import binpacking

from .. import SessionStatus, CCPError
from ..master import Master
from ..messages.data_acquisition import Element, ObjectDescriptorTable


class DAQSession:
    def __init__(self, master: Master, station_address: int, elements: List[Element]):
        self.master = master
        self.station_address = station_address
        self.elements = elements
        self.odts = []
        self.daq_lists = []
        self._initialized = False
        self._running = False

    def _pack_elements(self):
        """Pack elements into ODTs using greedy approximation:
            https://en.wikipedia.org/wiki/Bin_packing_problem
        """
        elements_dict = {e: e.size for e in self.elements}
        MAX_ODT_LENGTH = 7
        element_bins = binpacking.to_constant_volume(elements_dict, MAX_ODT_LENGTH)
        element_bins = [list(d.keys()) for d in element_bins]

        for i, b in enumerate(element_bins):
            odt = ObjectDescriptorTable(elements=b, number=i)
            odt.register()
            self.odts.append(odt)

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

    def _send_daq_lists(self):
        self.master.set_s_status(status_bits=SessionStatus.CAL)

        j = 0
        for i, dl in enumerate(self.daq_lists):
            for j, odt in enumerate(self.odts, start=j):
                if j == sum(dl):
                    break

                for k, e in enumerate(odt.elements):
                    self.master.set_daq_ptr(
                        daq_list_number=i, odt_number=j, element_number=k
                    )
                    self.master.write_daq(e.size, e.extension, e.address)

        self.master.set_s_status(status_bits=SessionStatus.CAL | SessionStatus.DAQ)

    def initialize(self):
        """Set up ODTs and send them to slave.
        """
        if self._initialized:
            self.stop()

        self.master.connect(self.station_address)
        self._pack_elements()
        self._get_daq_lists()
        self._ensure_odts_fit()
        self._send_daq_lists()
        self._initialized = True

    def _start_stop_all(self, mode: int):
        for i, dl in enumerate(self.daq_lists):
            last_odt_number = min(sum(dl), len(self.odts)) - 1
            self.master.start_stop(
                mode=mode, daq_list_number=i, last_odt_number=last_odt_number
            )

    def run(self):
        if self._initialized:
            START = 1
            self._start_stop_all(mode=START)
            self._running = True
        else:
            self.initialize()
            self.run()

    def stop(self):
        if self._running:
            STOP = 0
            self._start_stop_all(mode=STOP)
            self._running = False

        if self._initialized:
            self.master.disconnect(station_address=self.station_address)

            for odt in self.odts:
                odt.deregister()

            self._initialized = False
