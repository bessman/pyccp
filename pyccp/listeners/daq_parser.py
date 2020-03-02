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
from pyccp.listeners.message_sorter import MessageTypeChecker


class DAQParser(can.Listener, MessageTypeChecker):
    def __init__(
        self,
        dto_id: int,
        odts: List[ObjectDescriptorTable] = [],
        verbose: bool = False,
    ):
        self.dto_id = dto_id
        self._verbose = verbose
        # Flatten DAQ lists to dict of ODTs
        # self.odt_dict is used for decoding incoming data
        self.odt_dict = {}
        # self.values_dict is a dictionary of queues for holding decoded data
        self.values_dict = {}

        for odt in odts:
            self.odt_dict[odt.number] = odt

            for e in odt.elements:
                self.values_dict[e.name] = queue.Queue()

    def add_odt(self, odt: ObjectDescriptorTable):
        self.odt_dict[odt.number]: odt

        for e in odt.elements:
            self.values_dict[e.name] = queue.Queue()

    def on_message_received(self, msg: can.Message):
        if self.is_daq(msg):
            odt_number = msg.data[0]
            element_values = self.odt_dict[odt_number].decode(msg.data[1:])
            output = []

            for k, v in element_values.items():
                self.values_dict[k].put((msg.timestamp, v))
                output.append(k + ": " + str(v))

            if self._verbose:
                print("\n".join(output))

    def get(self, element_name: str):
        return self.values_dict[element_name].get(timeout=0.5)
