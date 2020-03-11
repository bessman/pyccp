#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Protocol level IO error."""

import can


class CCPError(can.CanError):
    """Indicates an error with the CCP communication."""
