#!/usr/bin/env python
# -*- coding: utf-8 -*-

import can
import unittest

from pyccp import ccp
from pyccp.messages.command_return import CommandReturnMessage
from pyccp.master import Master


class TestMaster(unittest.TestCase):
    def setUp(self):
        transport = can.Bus("test", bustype="virtual")
        self.slave_bus = can.Bus("test", bustype="virtual")
        self.master = Master(transport, cro_id=0x7E1, dto_id=0x321)
        self.master.ctr = 0x27
        self.acknowledge = CommandReturnMessage(
            arbitration_id=0x321,
            return_code=ccp.ReturnCodes.ACKNOWLEDGE,
            ctr=self.master.ctr,
            crm_data=5 * [0],
        )

    def tearDown(self):
        self.master.stop()
        self.slave_bus.shutdown()
        del self.master

    def runTest(self, func, expectedResult, *params):
        self.master._queue.on_message_received(self.acknowledge)
        getattr(self.master, func)(*params)
        message = self.slave_bus.recv(timeout=1)
        addrFmt = "08X" if message.is_extended_id else "04X"
        result = (
            f"{message.arbitration_id:{addrFmt}}"
            + "  "
            + " ".join([f"{i:02X}" for i in message.data])
        )
        self.assertEqual(result, expectedResult)

    def testConnect(self):
        self.runTest("connect", "000007E1  01 27 39 00 00 00 00 00", 0x39)

    def testGetCCPVersion(self):
        self.runTest("getCCPVersion", "000007E1  1B 27 02 01 00 00 00 00")

    def testExchangeID(self):
        self.runTest("exchangeId", "000007E1  17 27 00 00 00 00 00 00")

    def testSetMta(self):
        self.runTest(
            "setMta", "000007E1  02 27 00 02 34 00 20 00", 0x34002000, 0x02, 0x00
        )

    def testDnload(self):
        self.runTest("dnload", "000007E1  03 27 05 10 11 12 13 14", 5, 0x1011121314)

    def testUpload(self):
        self.runTest("getDaqSize", "000007E1  14 27 03 00 01 02 03 04", 3, 0x01020304)

    def testSetDaqPtr(self):
        self.runTest("setDaqPtr", "000007E1  15 27 03 05 02 00 00 00", 3, 5, 2)

    def testWriteDaqPtr(self):
        self.runTest(
            "writeDaq", "000007E1  16 27 02 01 02 00 42 00", 0x02, 0x01, 0x02004200
        )

    def testStartStopPtr(self):
        self.runTest(
            "startStop",
            "000007E1  06 27 01 03 07 02 00 01",
            0x01,
            0x03,
            0x07,
            0x02,
            0x01,
        )

    def testDisconnect(self):
        self.runTest("disconnect", "000007E1  07 27 00 00 08 02 00 00", 0x00, 0x0208)

    def testSetSStatus(self):
        self.runTest("setSStatus", "000007E1  0C 27 01 00 00 00 00 00", 0x01)


if __name__ == "__main__":
    unittest.main()
