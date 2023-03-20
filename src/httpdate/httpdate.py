# SPDX-FileCopyrightText: Copyright © 2023 Jamie Nguyen <j@jamielinux.com>
# SPDX-License-Identifier: MIT

"""Parse and format HTTP dates, such as Last-Modified and If-Modified-Since headers."""

__all__ = (
    "httpdate_to_unixtime",
    "unixtime_to_httpdate",
    "is_valid_httpdate",
    "MIN_YEAR",
    "MAX_YEAR",
    "RFC9110",
    "MONTHS",
    "WEEKDAYS",
)

import calendar
import datetime
import re
import time
from typing import Dict, Optional, Tuple

from leapseconds import LEAP_SECONDS

# Minimum year accepted by RFC 9110.
MIN_YEAR: int = 1900
# Maximum year supported by the `calendar` module.
MAX_YEAR: int = 9999

# The regexes need not be bulletproof, as we're checking for semantic correctness
# later. The vital part is `GMT` because `time.strptime()` isn't timezone aware and
# the behaviour of %Z is platform-specific. (`datetime` is more timezone-aware but
# it doesn't support leap seconds, and %Z has the same issue.) We drop the original
# weekday when parsing so that `time.strptime()` can auto-calculate the weekday,
# which we later use to check the semantic correctness of the original weekday.
RFC9110: Dict[str, Dict[str, str]] = {
    "IMF-fixdate": {
        # Sun, 06 Nov 1994 08:49:37 GMT
        # group1=weekday, group2=day, group3=month, group4=remainder
        "regex": r"^(\w{3}), (\d{2}) (\w{3}) (\d{4} \d{2}:\d{2}:\d{2} GMT)$",
        "strptime": "%d %m %Y %H:%M:%S %Z",
    },
    "rfc850-date": {
        # Sunday, 06-Nov-94 08:49:37 GMT
        # group1=weekday, group2=date, group3=time
        "regex": r"^(\w+), (\d{2}-\w{3}-\d{2}) (\d{2}:\d{2}:\d{2}) GMT$",
        "strptime": "%d-%m-%Y %H:%M:%S %Z",  # use %Y instead of %y (see below)
    },
    "asctime-date": {
        # Sun Nov  6 08:49:37 1994
        # group1=weekday, group2=month, group3=remainder
        "regex": r"^(\w{3}) (\w{3}) ((\d{2}| \d{1}) \d{2}:\d{2}:\d{2} \d{4})$",
        "strptime": "%m %d %H:%M:%S %Y",
    },
}

# We need to parse English month and weekday names. The %a, %A and %b format codes
# for these are locale-dependent. In our case, we're only handling 26 words so we
# can just use dicts to avoid locale issues altogether (and avoid messing around
# with the `locale` module, which can fail if the desired locale isn't present).
# NB: `calendar` can auto-generate similar dicts, but it's also locale-dependent.
MONTHS: Dict[str, int] = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}
WEEKDAYS: Dict[int, Tuple[str, str]] = {
    0: ("Monday", "Mon"),
    1: ("Tuesday", "Tue"),
    2: ("Wednesday", "Wed"),
    3: ("Thursday", "Thu"),
    4: ("Friday", "Fri"),
    5: ("Saturday", "Sat"),
    6: ("Sunday", "Sun"),
}


def _normalize_for_strptime(fmt: str, matches: re.Match) -> str:
    if fmt == "rfc850-date":
        # When `time.strptime()` parses a 2-digit year, the year is converted as per the
        # POSIX and ISO C standards (which the `time` docs currently state means values
        # 69-99 are mapped to 1969-1999 and values 0-68 are mapped to 2000-2068).

        # RFC 9110 instead says we should assume the year is from this century, unless
        # that would make the date-time more than 50 years in the future; in that case
        # use the previous century. A simple way to check this is to convert the %b
        # month string to an int, create an int 6-tuple (yyyy, mm, dd, hh, mm, ss), and
        # compare that with an int 6-tuple of the current date-time with year=year+50

        # Since we're not converting into a Python date-time format to calculate this,
        # we conveniently avoid having to handle invalid dates (such as Feb 29th in a
        # non-leap year) until after we've decided which century to use.

        now: datetime.datetime = datetime.datetime.now(datetime.timezone.utc)
        year: int = max(now.year, MIN_YEAR)

        lm_dmy: list[str] = matches.group(2).split("-")
        lm_dd: int = int(lm_dmy[0])
        lm_month: str = lm_dmy[1]
        lm_yy: str = lm_dmy[2]

        if lm_month not in MONTHS:
            raise ValueError(lm_month)

        this_c: str = str(year // 100)
        last_c: str = str(int(this_c) - 1)

        lm_tuple: Tuple[int, int, int, int, int, int] = (
            int(f"{this_c}{lm_yy}"),
            MONTHS[lm_month],
            lm_dd,
            *[int(x) for x in matches.group(3).split(":")],
        )

        future_tuple: Tuple[int, int, int, int, int, int] = (
            year + 50,
            now.month,
            now.day,
            now.hour,
            now.minute,
            now.second,
        )

        yyyy: str = (
            f"{last_c}{lm_yy}" if lm_tuple > future_tuple else f"{this_c}{lm_yy}"
        )
        return f"{lm_dd:02}-{MONTHS[lm_month]:02}-{yyyy} {matches.group(3)} GMT"

    if fmt == "asctime-date":
        month: str = matches.group(2)
        if month not in MONTHS:
            raise ValueError(month)
        return f"{MONTHS[month]:02} {matches.group(3).strip()}"

    # IMF-fixdate
    month: str = matches.group(3)
    if month not in MONTHS:
        raise ValueError(month)
    return f"{matches.group(2)} {MONTHS[month]:02} {matches.group(4)}"


def _string_to_unixtime(fmt: str, httpdate: str, wday: str) -> int:
    # `time.struct_time` is a suitable intermediate type before converting to a Unix
    # timestamp: it supports leap seconds, it raises ValueError for (most) semantically
    # incorrect date-time values (we do more validation below), and it doesn't matter
    # that it isn't timezone aware because Last-Modified is always UTC.
    try:
        struct_time: time.struct_time = time.strptime(
            httpdate,
            RFC9110[fmt]["strptime"],
        )
    except ValueError as exc:
        raise ValueError(httpdate) from exc

    expected_wday: str = WEEKDAYS[struct_time.tm_wday][0 if fmt == "rfc850-date" else 1]
    if (
        # RFC 5322, Section 3.3: "day-of-week MUST be the day implied by the date".
        wday != expected_wday
        # `time.strptime()` accepts `61` seconds for historical reasons related to an
        # erroneous notion of "double leap seconds" in earlier versions of the POSIX
        # standard. `61` isn't accepted by either RFC 9110 or the `calendar` module.
        or struct_time.tm_sec > 60
        # See comments at the top of this file.
        or struct_time.tm_year < MIN_YEAR
        or struct_time.tm_year > MAX_YEAR
    ):
        raise ValueError(struct_time)

    # No try/except block here. Due to the validation we do above, it's impossible to
    # pass a `time.struct_time` object to `calendar.timegm()` that it can't handle.
    timestamp: int = calendar.timegm(struct_time)

    if struct_time.tm_sec == 60 and timestamp not in LEAP_SECONDS:
        raise ValueError(struct_time)

    return timestamp


def httpdate_to_unixtime(httpdate: Optional[str]) -> Optional[int]:
    """Parse an HTTP date (eg, `Last-Modified`) into a Unix timestamp.

    All HTTP dates (eg, in `Last-Modified` headers) must be sent in this format:

      # IMF-fixdate
      Sun, 06 Nov 1994 08:49:37 GMT

    However, RFC 9110 states that recipients must also accept two other obsolete
    formats:

      # rfc850-date
      Sunday, 06-Nov-94 08:49:37 GMT

      # asctime-date
      Sun Nov  6 08:49:37 1994

    RFC 9110 criteria for the HTTP date field includes the following:

      - It must be in one of the three accepted formats.
      - It must represent time as an instance of UTC.
      - It must represent weekday names and month names in English.
      - It is case-sensitive.
      - It must not have any additional whitespace.
      - It must be semantically correct (eg, the weekday must be the correct weekday).
      - It can include leap seconds (eg, `23:59:60`).
      - It must represent a year of `1900` or above.

    It isn't stated explicitly in the RFCs, but this method will only consider a leap
    second semantically correct if it's an official leap second.

    RFC 9110 states that when receiving an rfc850-date, which uses a two-digit year, an
    HTTP date that appears to be more than 50 years in the future must be interpreted as
    being the most recent year in the past that had the same last two digits.

    Args:
        httpdate (Optional[str]): The HTTP date field (eg, `Last-Modified`).

    Returns:
        Optional[int]: A Unix timestamp representing the HTTP date, or None if the input
            is None or the HTTP date is invalid.

    Raises:
        TypeError: If the input is not of type `str` or `None`.
    """
    if httpdate is None:
        return None

    if not isinstance(httpdate, str):
        msg: str = "httpdate must be of type str or None"
        raise TypeError(msg)

    for key, fields in RFC9110.items():
        matches: Optional[re.Match] = re.match(fields["regex"], httpdate)
        if matches:
            try:
                _httpdate: str = _normalize_for_strptime(key, matches)
            except ValueError:
                return None

            try:
                unixtime: int = _string_to_unixtime(key, _httpdate, matches.group(1))
            except ValueError:
                return None

            return unixtime

    return None


def unixtime_to_httpdate(unixtime: Optional[int]) -> Optional[str]:
    """Format a Unix timestamp as an HTTP date (eg, for an `If-Modified-Since` header).

    According to RFC 9110 Section 5.6.7, the `IMF-fixdate` format must be used when
    sending an HTTP date:

      # IMF-fixdate
      Sun, 06 Nov 1994 08:49:37 GMT

    See docstring for httpdate_to_unixtime() for more information on RFC 9110 criteria.

    Args:
        unixtime (Optional[int]): A Unix timestamp.

    Returns:
        Optional[str]: A valid IMF-fixdate header, or None if the input was None.

    Raises:
        TypeError: If the input is not of type `int` or `None`.
        ValueError: If the input represents a date outside of the acceptable range
            (Jan 1st, 1900 to Dec 31st, 9999).
    """
    if unixtime is None:
        return None

    if not isinstance(unixtime, int):
        msg: str = "unixtime must be of type int or None"
        raise TypeError(msg)

    # -2208988800   = Jan  1st, 1900, 00:00:00  (RFC 9110 / RFC 5322 minimum)
    #  253402300799 = Dec 31st, 9999, 23:59:59  (the datetime module maximum)
    if unixtime < -2208988800 or unixtime > 253402300799:
        return None

    # No try/except block here. The input is guaranteed to be an int within the range
    # specified above, so the only way this fails is if something is borked with the
    # `datetime` module; we probably don't want to silently continue in that scenario.
    date: datetime.datetime = datetime.datetime.fromtimestamp(
        unixtime,
        tz=datetime.timezone.utc,
    )

    # IMF-fixdate format.
    return date.strftime("%a, %d %b %Y %H:%M:%S GMT")


def is_valid_httpdate(httpdate: Optional[str]) -> bool:
    """Check if an HTTP date field (eg, `Last-Modified`) is valid.

    See docstring for httpdate_to_unixtime() for more information on RFC 9110 criteria.

    Args:
        httpdate (Optional[str]): An HTTP date field.

    Returns:
        bool: True if the input is valid, False if the input is None or invalid.

    Raises:
        TypeError: If the input is not of type `str` or `None`.
    """
    if httpdate is None:
        return False

    if not isinstance(httpdate, str):
        msg: str = "httpdate must be of type str or None"
        raise TypeError(msg)

    return httpdate_to_unixtime(httpdate) is not None
