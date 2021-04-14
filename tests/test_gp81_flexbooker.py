"""

"""

import datetime

import pytest

from src import gp81_flexbooker


@pytest.mark.parametrize('input, output',
                         [(datetime.datetime(2021, 4, 13, 23, 20, 25), (datetime.date(2021, 4, 13), datetime.date(2021, 4, 24))),
                          (datetime.datetime(2021, 4, 14, 11, 59, 59), (datetime.date(2021, 4, 14), datetime.date(2021, 4, 24))),
                          (datetime.datetime(2021, 4, 14, 12, 00, 00), (datetime.date(2021, 4, 14), datetime.date(2021, 5, 1)))])
def test_get_current_booking_date_range(input, output):
    assert gp81_flexbooker.get_current_booking_date_range(today=input) == output
