# SPDX-FileCopyrightText: Copyright © 2023 Jamie Nguyen <j@jamielinux.com>
# SPDX-License-Identifier: MIT

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from httpdate import httpdate_to_unixtime

#
# input types


def test_type_none():
    with pytest.raises(TypeError):
        httpdate_to_unixtime(None)  # type: ignore


def test_type_int():
    with pytest.raises(TypeError):
        httpdate_to_unixtime(0)  # type: ignore


def test_type_str():
    with pytest.raises(ValueError, match="Invalid HTTP-date:"):
        httpdate_to_unixtime("")


#
# IMF-fixdate


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Sun, 06 Nov 1994 08:49:37 GMT", 784111777),
        ("Fri, 01 Sep 2000 00:00:00 GMT", 967766400),
        ("Sat, 29 Feb 2020 00:00:00 GMT", 1582934400),
        ("Sat, 31 Dec 2016 23:59:60 GMT", 1483228800),
    ],
)
def test_imffixdate_good(value, expected):
    assert httpdate_to_unixtime(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        ("06 Nov 1994 00:00:00 GMT"),
        ("Snn, 06 Nov 1994 00:00:00 GMT"),
        ("Sun, 31 Nov 1994 00:00:00 GMT"),
        ("Sun, 06 Nvv 1994 00:00:00 GMT"),
        ("Sun, 06 Nov -994 00:00:00 GMT"),
        ("Sun, 06 Nov 1994 25:00:00 GMT"),
        ("Sun, 06 Nov 1994 00:61:00 GMT"),
        ("Sun, 06 Nov 1994 00:00:61 GMT"),
        ("Sun, 06 Nov 1994 00:00:00 BST"),
        ("Sun, 06 Nov 1994 00:00:00"),
        ("Sun, 31 Dec 1899 23:59:59 GMT"),
        ("Sun, 31 Dec 10000 23:59:59 GMT"),
        ("Mon, 29 Feb 2021 00:00:00 GMT"),  # not a leap year
    ],
)
def test_imffixdate_bad(value):
    with pytest.raises(ValueError, match="Invalid HTTP-date:"):
        httpdate_to_unixtime(value)


def test_imffixdate_bad_leap_second():
    with pytest.raises(ValueError, match="Invalid leap second:"):
        httpdate_to_unixtime("Thu, 31 Dec 2015 23:59:60 GMT")


def test_timegm_exception():
    with patch("calendar.timegm", side_effect=ValueError):
        with pytest.raises(ValueError, match="Out of range:"):
            httpdate_to_unixtime("Fri, 31 Dec 9999 23:59:60 GMT")


#
# rfc850-date


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Sunday, 06-Nov-94 08:49:37 GMT", 784111777),
        ("Friday, 01-Sep-00 00:00:00 GMT", 967766400),
        ("Saturday, 29-Feb-20 00:00:00 GMT", 1582934400),
        ("Saturday, 31-Dec-16 23:59:60 GMT", 1483228800),
    ],
)
def test_rfc850date_good(value, expected):
    class MockDatetime:
        @classmethod
        def now(cls, *args, **kwargs):
            del args, kwargs
            return datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    with patch("httpdate.httpdate.datetime", new=MockDatetime):
        assert httpdate_to_unixtime(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        ("06-Nov-94 00:00:00 GMT"),
        ("Snnday, 06-Nov-94 00:00:00 GMT"),
        ("Sunday, 31-Nov-94 00:00:00 GMT"),
        ("Sunday, 06-Nvv-94 00:00:00 GMT"),
        ("Sunday, 06-Nov--4 00:00:00 GMT"),
        ("Sunday, 06-Nov-94 25:00:00 GMT"),
        ("Sunday, 06-Nov-94 00:61:00 GMT"),
        ("Sunday, 06-Nov-94 00:00:61 GMT"),
        ("Sunday, 06-Nov-94 00:00:00 BST"),
        ("Sunday, 06-Nov-94 00:00:00"),
        ("Monday, 29-Feb-21 00:00:00 GMT"),  # not a leap year
    ],
)
def test_rfc850date_bad(value):
    class MockDatetime:
        @classmethod
        def now(cls, *args, **kwargs):
            del args, kwargs
            return datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    with patch("httpdate.httpdate.datetime", new=MockDatetime):
        with pytest.raises(ValueError, match="Invalid HTTP-date:"):
            httpdate_to_unixtime(value)


def test_rfc850date_bad_leap_second():
    with pytest.raises(ValueError, match="Invalid leap second:"):
        httpdate_to_unixtime("Thursday, 31-Dec-15 23:59:60 GMT")


def test_rfc850date_1949():
    class MockDatetime:
        @classmethod
        def now(cls, *args, **kwargs):
            del args, kwargs
            return datetime(1949, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

    with patch("httpdate.httpdate.datetime", new=MockDatetime):
        # year == 1999
        assert httpdate_to_unixtime("Friday, 31-Dec-99 23:59:59 GMT") == 946684799
        # year == 1899
        with pytest.raises(ValueError, match="Invalid HTTP-date:"):
            httpdate_to_unixtime("Friday, 31-Dec-99 23:59:60 GMT")


def test_rfc850date_1899():
    class MockDatetime:
        @classmethod
        def now(cls, *args, **kwargs):
            del args, kwargs
            return datetime(1899, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

    with patch("httpdate.httpdate.datetime", new=MockDatetime):
        # year == 1899
        with pytest.raises(ValueError, match="Invalid HTTP-date:"):
            httpdate_to_unixtime("Sunday, 31-Dec-99 23:59:59 GMT")
        # year == 1949
        assert httpdate_to_unixtime("Saturday, 31-Dec-49 23:59:59 GMT") == -631152001


#
# asctime-date


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Sun Nov  6 08:49:37 1994", 784111777),
        ("Fri Sep  1 00:00:00 2000", 967766400),
        ("Sat Feb 29 00:00:00 2020", 1582934400),
        ("Sat Dec 31 23:59:60 2016", 1483228800),
    ],
)
def test_asctimedate_good(value, expected):
    assert httpdate_to_unixtime(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        ("Nov  6 00:00:00 1994"),
        ("Sun Nov  6 00:00:00 1994 GMT"),
        ("Snn Nov  6 00:00:00 1994"),
        ("Sun Nvv  6 00:00:00 1994"),
        ("Sun Nov 31 00:00:00 1994"),
        ("Sun Nov  6 25:00:00 1994"),
        ("Sun Nov  6 00:61:00 1994"),
        ("Sun Nov  6 00:00:61 1994"),
        ("Sun Nov  6 00:00:61 -994"),
        ("Sun Dec 31 23:59:59 1899"),
        ("Sun Dec 31 23:59:59 10000"),
        ("Mon Feb 29 00:00:00 2021"),  # not a leap year
    ],
)
def test_asctimedate_bad(value):
    with pytest.raises(ValueError, match="Invalid HTTP-date:"):
        httpdate_to_unixtime(value)


def test_asctimedate_bad_leap_second():
    with pytest.raises(ValueError, match="Invalid leap second:"):
        httpdate_to_unixtime("Thu Dec 31 23:59:60 2015")
