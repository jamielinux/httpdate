import pytest
from httpdate import is_valid_httpdate


def test_type_none():
    assert not is_valid_httpdate(None)


def test_type_str():
    assert not is_valid_httpdate("")


def test_type_int():
    with pytest.raises(TypeError):
        assert is_valid_httpdate(0)  # type: ignore


@pytest.mark.parametrize(
    "value",
    [
        # IMF-fixdate
        ("Sun, 06 Nov 1994 08:49:37 GMT"),
        # rfc850-date
        ("Sunday, 06-Nov-94 08:49:37 GMT"),
        # asctime-date
        ("Sun Nov  6 08:49:37 1994"),
    ],
)
def test_good(value):
    assert is_valid_httpdate(value)


@pytest.mark.parametrize(
    "value",
    [
        # IMF-fixdate
        ("Snn, 06 Nov 1994 08:49:37 GMT"),
        # rfc850-date
        ("Snnday, 06-Nov-94 08:49:37 GMT"),
        # asctime-date
        ("Snn Nov  6 08:49:37 1994"),
    ],
)
def test_bad(value):
    assert not is_valid_httpdate(value)
