#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""A can.Listener which sorts incoming CCP messages by type."""

import can
import queue
import logging

from pyccp import messages


logger = logging.getLogger(__name__)


class MessageSorter(can.Listener):
    """A can.Listener which sorts incoming CCP messages by type."""

    def __init__(
        self, dto_id: int, cro_id: int,
    ):
        self.dto_id = dto_id
        self.cro_id = cro_id

        self._crm_queue = queue.Queue()
        self._evm_queue = queue.Queue()
        self._daq_queue = queue.Queue()
        self._cro_queue = queue.Queue()

    def _hexlist(self, data: bytearray) -> str:
        return " ".join([format(b, "x") for b in data])

    def on_message_received(self, msg: can.Message):
        """Sort an incoming message.

        Parameters
        ----------
        msg : can.Message

        Returns
        -------
        None.
        """
        if messages.is_crm(msg=msg, dto_id=self.dto_id):
            msg = messages.CommandReturnMessage.from_can_message(msg)
            self._crm_queue.put(msg)
            ctr = msg.data[messages.MessageByte.CRM_CTR]
            return_code = messages.ReturnCodes(
                msg.data[messages.MessageByte.DTO_ERR]
            ).name
            data = self._hexlist(msg.data[3:])
            logger.debug("Received CRM {}:  %s  %s".format(ctr), return_code, data)

        elif messages.is_evm(msg=msg, dto_id=self.dto_id):
            msg = messages.EventMessage.from_can_message(msg)
            self._evm_queue.put(msg)
            return_code = messages.ReturnCodes(
                msg.data[messages.MessageByte.DTO_ERR]
            ).name
            logger.debug("Received EVM:  %s", return_code)

        elif messages.is_daq(msg=msg, dto_id=self.dto_id):
            msg = messages.DataAcquisitionMessage().from_can_message(msg)
            self._daq_queue.put(msg)
            odt_number = msg.data[messages.MessageByte.DTO_PID]
            data = self._hexlist(msg.data[1:])
            logger.info("Received DAQ#%s:  {}".format(msg.decode()), odt_number)

        elif messages.is_cro(msg=msg, cro_id=self.cro_id):
            msg = messages.CommandReceiveObject().from_can_message(msg)
            self._cro_queue.put(msg)
            # CROs are logged by master

    def get_command_return_message(
        self, timeout: float = 0.5
    ) -> messages.CommandReturnMessage:
        """Return the first CRM in the queue.

        Parameters
        ----------
        timeout : float, optional
            Time in seconds to wait before raising Empty. The default is 0.5.

        Returns
        -------
        CommandReturnMessage
            The first CRM in the queue.

        Raises
        ------
        queue.Empty if no message can be returned within timeout seconds.
        """
        return self._crm_queue.get(timeout=timeout)

    def get_event_message(self, timeout=0.5) -> messages.EventMessage:
        """Return the first EVM in the queue.

        Parameters
        ----------
        timeout : TYPE, optional
            Time in seconds to wait before raising Empty. The default is 0.5.

        Returns
        -------
        EventMessage
            The first EVM in the queue.

        Raises
        ------
        queue.Empty if no message can be returned within timeout seconds.
        """
        return self._evm_queue.get(timeout=timeout)

    def get_data_acquisition_message(
        self, timeout: float = 0.5
    ) -> messages.DataAcquisitionMessage:
        """Return the first DAQ in the queue.

        Parameters
        ----------
        timeout : TYPE, optional
            Time in seconds to wait before raising Empty. The default is 0.5.

        Returns
        -------
        EventMessage
            The first DAQ in the queue.

        Raises
        ------
        queue.Empty if no message can be returned within timeout seconds.
        """
        return self._daq_queue.get(timeout=timeout)

    def get_command_receive_object(
        self, timeout: float = 0.5
    ) -> messages.CommandReceiveObject:
        """Return the first CRO in the queue.

        Parameters
        ----------
        timeout : TYPE, optional
            Time in seconds to wait before raising Empty. The default is 0.5.

        Returns
        -------
        EventMessage
            The first CRO in the queue.

        Raises
        ------
        queue.Empty if no message can be returned within timeout seconds.
        """
        return self._cro_queue.get(timeout=timeout)
