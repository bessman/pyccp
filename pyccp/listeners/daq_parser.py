#!/usr/bin/env python
# -*- coding: utf-8 -*-

__copyright__ = """
    pySART - Simplified AUTOSAR-Toolkit for Python.

   (C) 2009-2016 by Christoph Schueler <cpu12.gems@googlemail.com>

   All Rights Reserved

  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License along
  with this program; if not, write to the Free Software Foundation, Inc.,
  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

import can
import queue
from typing import List

from pyccp.messages.data_acquisition import ObjectDescriptorTable


class DAQParser(can.Listener):
    def __init__(
        self,
        dto_id: int,
        daq_lists: List[List[ObjectDescriptorTable]] = [],
        verbose: bool = False,
    ):
        self.dto_id = dto_id
        self._verbose = verbose
        # Flatten DAQ lists to dict of ODTs
        # self.odt_dict is used for decoding incoming data
        self.odt_dict = {}
        # self.values_dict is a dictionary of queues for holding decoded data
        self.values_dict = {}

        for dl in daq_lists:
            for odt in dl:
                self.odt_dict[odt.number] = odt

                for e in odt.elements:
                    self.values_dict[e.name] = queue.Queue()

    def add_daq_list(self, daq_list: List[ObjectDescriptorTable]):
        for odt in daq_list:
            self.odt_dict[odt.number]: odt

            for e in odt.elements:
                self.values_dict[e.name] = queue.Queue()

    def on_message_received(self, msg: can.Message):
        if msg.arbitration_id == self.dto_id:
            # The message is a Data Transmission Object
            pid = msg.data[0]

            if pid < 0xFE:
                # The DTO is a Data Acquisition Message
                odt_number = pid
                element_values = self.odt_dict[odt_number].decode(msg.data[1:])

                for k, v in element_values.items():
                    self.values_dict[k].put((msg.timestamp, v))

                    if self._verbose:
                        print(k + ": " + str(v))

    def get(self, element_name: str):
        return self.values_dict[element_name].get(timeout=0.5)
