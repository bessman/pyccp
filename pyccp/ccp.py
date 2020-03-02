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
import enum


MAX_CTO = 0x0008
MAX_DTO = 0x0008

CCP_VERSION = (2, 1)


class MemoryTransferAddressNumber(enum.IntEnum):
    """
    The MTA number (handle) is used to identify different transfer address
    locations (pointers). MTA0 is used by the commands DNLOAD, UPLOAD, DNLOAD_6,
    SELECT_CAL_PAGE, CLEAR_MEMORY, PROGRAM and PROGRAM_6. MTA1 is used by the
    MOVE command. See also command ‘MOVE’.
    """

    MTA0_NUMBER = 0
    MTA1_NUMBER = 1


class State(enum.IntEnum):
    pass


class Memory(object):
    def __init__(self):
        pass


class CcpError(can.CanError):
    """Indicates an error with the CCP communication.
    """
