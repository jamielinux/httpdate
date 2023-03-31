# httpdate

[![PyPi Version][pypi-img]][pypi-url]
[![License][license-img]][license-url]
[![Continuous Integration][ci-img]][ci-url]
[![Code Coverage][coverage-img]][coverage-url]
[![Python Versions][python-img]][python-url]

[pypi-img]: https://img.shields.io/pypi/v/httpdate.svg
[pypi-url]: https://pypi.org/project/httpdate
[license-img]:  https://img.shields.io/github/license/jamielinux/httpdate.svg
[license-url]: https://github.com/jamielinux/httpdate/blob/main/LICENSE
[ci-img]: https://github.com/jamielinux/httpdate/actions/workflows/ci.yml/badge.svg
[ci-url]: https://github.com/jamielinux/httpdate/actions/workflows/ci.yml
[coverage-img]: https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/jamielinux/f3b70fb7174f1a8a87f2185e80cbb2ef/raw/httpdate.covbadge.json
[coverage-url]: https://github.com/jamielinux/httpdate/actions/workflows/ci.yml
[python-img]: https://img.shields.io/pypi/pyversions/httpdate.svg
[python-url]: https://pypi.org/project/httpdate

---

**httpdate** is a Python library for parsing and formatting HTTP date fields that are
used in headers like `Last-Modified` and `If-Modified-Since`. It does so in strict
accordance with [RFC 9110 Section 5.6.7][0].

It has only one dependency, which is my tiny [leapseconds][1] library that just provides
a tuple of official leap seconds.

[0]: https://datatracker.ietf.org/doc/html/rfc9110#section-5.6.7
[1]: https://github.com/jamielinux/leapseconds

## HTTP date formats

All HTTP dates (eg, in `Last-Modified` headers) must be sent in this format:

```console
# IMF-fixdate
Sun, 06 Nov 1994 08:49:37 GMT
```

However, RFC 9110 states that recipients must also accept two other obsolete formats:

```console
# rfc850-date
Sunday, 06-Nov-94 08:49:37 GMT

# asctime-date
Sun Nov  6 08:49:37 1994
```

RFC 9110 criteria for the HTTP date field includes the following:

- It must represent time as an instance of UTC.
- It must represent weekday names and month names in English.
- It is case-sensitive.
- It must not have any additional whitespace.
- It must be semantically correct (eg, the weekday must be the correct weekday).
- It can include leap seconds (eg, `23:59:60`).
- It must represent a year of `1900` or above.

It isn't stated explicitly in the RFCs, but `httpdate` will only consider a leap second
semantically correct if it's an [official leap second][2].

[2]: https://www.ietf.org/timezones/data/leap-seconds.list

## Installation

```console
pip install httpdate
```

## Usage

```python
from httpdate import is_valid_httpdate, httpdate_to_unixtime, unixtime_to_httpdate

# Check if an HTTP date (eg, `Last-Modified` header) is valid:
is_valid_httpdate("Sun, 06 Nov 1994 08:49:37 GMT")

# Parse an HTTP date:
httpdate_to_unixtime("Sun, 06 Nov 1994 08:49:37 GMT")
# Parse an HTTP date (rfc850-date):
httpdate_to_unixtime("Sunday, 06-Nov-94 08:49:37 GMT")
# Parse an HTTP date (asctime-date):
httpdate_to_unixtime("Sun Nov  6 08:49:37 1994")

# Format a Unix timestamp as an HTTP date:
unixtime_to_httpdate(784111777)
```

- **`is_valid_httpdate(httpdate)`**:
  - *Args*
    - `Optional[str]`
  - *Returns*
    - `bool`: True if input is valid, False if invalid or the input is `None`.
  - *Raises*
    - `TypeError` if input is not `str` or `None`.
- **`httpdate_to_unixtime(httpdate)`**:
  - *Args*
    - `Optional[str]`
  - *Returns*
    - `Optional[int]`: A Unix timestamp (`int`) if input is valid, `None` if invalid
      or input is `None`.
  - *Raises*
    - `TypeError` if input is not `str` or `None`.
- **`unixtime_to_httpdate(unixtime)`**:
  - *Args*
    - `int`: A Unix timestamp.
  - *Returns*
    - `Optional[str]`: An HTTP date string. It will return `None` if the input
      represents a year before 1900, or if the input is outside the range supported
      by the operating system.
  - *Raises*
    - `TypeError` if input is not of type `int`.

## Why Unix timestamps?

Unix timestamps are unambiguous, efficient, and can easily be converted to other
date-time formats using only the standard library.

When a `Last-Modified` header is semantically correct, this conversion — from string to
Unix timestamp and back to string — is lossless. (The only exception is leap seconds;
for example `Sat, 31 Dec 2016 23:59:60 GMT` would be returned as `Sun, 01 Jan 2017
00:00:00 GMT`. Recipients should interpret these as being identical anyway.)

If you want to store the original string instead, just use `is_valid_httpdate()` to
validate before storing.

## License

`httpdate` is distributed under the terms of the [MIT][license] license.

[license]: https://spdx.org/licenses/MIT.html
