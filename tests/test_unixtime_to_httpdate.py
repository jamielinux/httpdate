import pytest
from httpdate import unixtime_to_httpdate


def test_type_none():
    assert unixtime_to_httpdate(None) is None


def test_type_str():
    with pytest.raises(TypeError):
        unixtime_to_httpdate("")  # type: ignore


def test_type_float():
    with pytest.raises(TypeError):
        unixtime_to_httpdate(0.0)  # type: ignore


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (-2208988800, "Mon, 01 Jan 1900 00:00:00 GMT"),
        (0, "Thu, 01 Jan 1970 00:00:00 GMT"),
        (784111777, "Sun, 06 Nov 1994 08:49:37 GMT"),
        (1483228800, "Sun, 01 Jan 2017 00:00:00 GMT"),
        (253402300799, "Fri, 31 Dec 9999 23:59:59 GMT"),
    ],
)
def test_unixtime_good(value, expected):
    assert unixtime_to_httpdate(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        (-2208988801),
        (253402300800),
    ],
)
def test_unixtime_bad(value):
    assert unixtime_to_httpdate(value) is None
