#!/usr/bin/env python
# -*- coding: utf-8 -*-

import can
import unittest

from ..messages import CommandCodes, ReturnCodes
from ..messages.command_return import CommandReturnMessage
from ..messages.data_acquisition import (
    DataAcquisitionMessage,
    Element,
    ObjectDescriptorTable,
)
from ..messages.command_receive import CommandReceiveObject
from ..master import Master
from ..session import DAQSession


class TestSessions(unittest.TestCase):
    def setUp(self):
        self.master_bus = can.Bus("test", bustype="virtual")
        self.slave_bus = can.Bus("test", bustype="virtual")
        self.test_signal = Element(name="testSignal", size=4, address=0x321,)
        self.master = Master(transport=self.master_bus, cro_id=0x7E1, dto_id=0x321)
        self.daq_session = DAQSession(
            master=self.master, station_address=0x39, elements=[self.test_signal]
        )

    def tearDown(self):
        self.daq_session.stop()
        self.master.stop()

    def test_pack_elements(self):
        self.daq_session._pack_elements()
        expected_odt = ObjectDescriptorTable(elements=[self.test_signal], number=0)
        expected_odt.frame_id = 0
        print(self.daq_session.odts)
        print([expected_odt])
        self.assertEqual(self.daq_session.odts, [expected_odt])
