#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import List

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

    def _pack_elements(self, volume: int = 7) -> List[List[Element]]:
        """This function implements the First Fit Descending (FFD) algorithm to
        pack Elements (https://en.wikipedia.org/wiki/Bin_packing_problem).
        Parameters
        ----------
        volume : int, optional
            The volume into which to pack the elements. Defaults to 7, which
            is the maximum length of an ODT.
        
        Returns
        -------
        bins : List[List[Element]]
            List of lists of elements, packed so that the sum of their size
            does not exceed the specified volume.
        """
        sorted_elements = {e for e in sorted(self.elements, reverse=True, key=lambda e: e.size)}
        bins = []
    
        for se in sorted_elements:
            for b in bins:
                if sum([e.size for e in b]) + se.size <= volume:
                    # The item fits in an existing bin
                    b.append(se)
                    break
            else:
                # The item did not fit in an existing bin, put it in a new bin
                bins.append([se])
    
        return bins

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
        bins = self._pack_elements()

        for i, b in enumerate(bins):
            odt = ObjectDescriptorTable(elements=b, number=i)
            odt.register()
            self.odts.append(odt)

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
