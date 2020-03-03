#!/usr/bin/env python
# -*- coding: utf-8 -*-

import can
import unittest

from ..master import Master
from ..messages.command_return import CommandReturnMessage
from ..messages import CommandCodes, ReturnCodes


class TestMaster(unittest.TestCase):
    def setUp(self):
        transport = can.Bus("test", bustype="virtual")
        self.slave_bus = can.Bus("test", bustype="virtual")
        self.master = Master(transport, cro_id=0x7E1, dto_id=0x321)
        self.master.ctr = 0x27
        self.acknowledge = CommandReturnMessage(
            arbitration_id=0x321,
            return_code=ReturnCodes.ACKNOWLEDGE,
            ctr=self.master.ctr,
        )

    def tearDown(self):
        self.master.stop()
        self.slave_bus.shutdown()
        del self.master

    def runTest(self, command_code, expected_result, **kwargs):
        self.master._queue.on_message_received(self.acknowledge)
        self.master._send(command_code, **kwargs)
        message = self.slave_bus.recv(timeout=1)
        addr_fmt = "08X" if message.is_extended_id else "04X"
        result = (
            f"{message.arbitration_id:{addr_fmt}}"
            + "  "
            + " ".join([f"{i:02X}" for i in message.data])
        )
        self.assertEqual(result, expected_result)

    def testConnect(self):
        self.runTest(
            CommandCodes.CONNECT,
            "000007E1  01 27 39 00 00 00 00 00",
            station_address=0x39,
        )

    def testGetCCPVersion(self):
        self.runTest(
            CommandCodes.GET_CCP_VERSION,
            "000007E1  1B 27 02 01 00 00 00 00",
            major=2,
            minor=1,
        )

    def testExchangeID(self):
        self.runTest(
            CommandCodes.EXCHANGE_ID, "000007E1  17 27 00 00 00 00 00 00", device_info=0
        )

    def testSetMta(self):
        self.runTest(
            CommandCodes.SET_MTA,
            "000007E1  02 27 00 02 34 00 20 00",
            address=0x34002000,
            extension=0x02,
            mta=0,
        )

    def testDnload(self):
        self.runTest(
            CommandCodes.DNLOAD,
            "000007E1  03 27 05 10 11 12 13 14",
            size=5,
            data=0x1011121314,
        )

    def testUpload(self):
        self.runTest(CommandCodes.UPLOAD, "000007E1  04 27 04 00 00 00 00 00", size=4)

    def testGetDaqSize(self):
        self.runTest(
            CommandCodes.GET_DAQ_SIZE,
            "000007E1  14 27 03 00 01 02 03 04",
            daq_list_number=3,
            dto_id=0x01020304,
        )

    def testSetDaqPtr(self):
        self.runTest(
            CommandCodes.SET_DAQ_PTR,
            "000007E1  15 27 03 05 02 00 00 00",
            daq_list_number=3,
            odt_number=5,
            element_number=2,
        )

    def testWriteDaqPtr(self):
        self.runTest(
            CommandCodes.WRITE_DAQ,
            "000007E1  16 27 02 01 02 00 42 00",
            element_size=2,
            extension=0x01,
            address=0x02004200,
        )

    def testStartStopPtr(self):
        self.runTest(
            CommandCodes.START_STOP,
            "000007E1  06 27 01 03 07 02 00 01",
            mode=0x01,
            daq_list_number=0x03,
            last_odt_number=0x07,
            event_channel=0x02,
            rate_prescaler=0x01,
        )

    def testDisconnect(self):
        self.runTest(
            CommandCodes.DISCONNECT,
            "000007E1  07 27 00 00 08 02 00 00",
            permanent=0x00,
            station_address=0x0208,
        )

    def testSetSStatus(self):
        self.runTest(
            CommandCodes.SET_S_STATUS,
            "000007E1  0C 27 01 00 00 00 00 00",
            status_bits=0x01,
        )


if __name__ == "__main__":
    unittest.main()
