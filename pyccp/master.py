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

from pyccp import ccp
from pyccp.listeners.message_sorter import MessageSorter
from pyccp.messages.command_receive import CommandReceiveObject
from pyccp.logger import Logger


class Master:
    def __init__(
        self, transport: can.Bus, cro_id: int, dto_id: int, verbose: bool = False
    ):
        self.slaveConnections = {}
        self.cro_id = cro_id
        self.dto_id = dto_id
        self._transport = transport
        # Receive both DTOs and CROs, the latter in case local echo is enabled.
        self._transport.set_filters(
            [
                {"can_id": dto_id, "can_mask": 0x1FFFFFFF, "extended": True},
                {"can_id": cro_id, "can_mask": 0x1FFFFFFF, "extended": True},
            ]
        )
        self._queue = MessageSorter(dto_id, cro_id, verbose=verbose)
        self._notifier = can.Notifier(self._transport, [self._queue])
        self.ctr = 0x00
        self.mta0_extension = 0
        self.mta0_address = 0
        self.endianess = "big"
        self.logger = Logger("pyccp.master")

    def _send(self, command_code: ccp.CommandCodes, **kwargs):
        cro = CommandReceiveObject(
            arbitration_id=self.cro_id,
            command_code=command_code,
            ctr=self.ctr,
            **kwargs
        )
        self._transport.send(cro)

    def _receive(self) -> bytearray:
        """
        Raises
        ------
        CcpError

        If no Command Return Message is received within 0.5s, or
        if the CRM counter does not match the CRO counter, or
        if the return code is not ACKNOWLEDGE.

        Returns
        -------
        bytearray
            Five data bytes.
        """

        crm = self._queue.get_command_return_message()
        if crm.ctr == self.ctr:
            self.ctr = (self.ctr + 1) % 0x100

            if crm.return_code == ccp.ReturnCodes.ACKNOWLEDGE:
                return crm.crm_data
            else:
                raise ccp.CcpError(ccp.ReturnCodes(crm.return_code).name)
        else:
            raise ccp.CcpError("Counter mismatch")

    def stop(self):
        self._notifier.stop()
        self._transport.shutdown()
