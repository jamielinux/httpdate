# SPDX-FileCopyrightText: Copyright © 2023 Jamie Nguyen <j@jamielinux.com>
# SPDX-License-Identifier: MIT

"""Parse and format HTTP dates, such as Last-Modified and If-Modified-Since headers."""

from .httpdate import (
    MAX_YEAR,
    MIN_UNIXTIME,
    MIN_YEAR,
    MONTHS,
    RFC9110,
    WEEKDAYS,
    httpdate_to_unixtime,
    is_valid_httpdate,
    unixtime_to_httpdate,
)

__all__ = [
    "MAX_YEAR",
    "MIN_UNIXTIME",
    "MIN_YEAR",
    "MONTHS",
    "RFC9110",
    "WEEKDAYS",
    "httpdate_to_unixtime",
    "is_valid_httpdate",
    "unixtime_to_httpdate",
]

__version__ = "1.0.0"
