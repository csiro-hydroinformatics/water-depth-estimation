from datetime import datetime, timedelta
import pandas
from datacube.api.query import _to_datetime


class BimonthTimeRange():
    """The TimeRange helper class provides a Year-Month text string for every bimonth in a period"""

    def __init__(self, start='1988-01-01', end='2022-06-30'):
        self.start = start
        self.end = end
        self.full_date_range = self._calculate_date_range()
        """ A list of bimonthly text strings of the form YEAR_MONTH - e.g. 2022_05"""
        self.time_query_periods = self._calculate_time_periods()
        """ A list of python bimonthly datetimes"""

    TEST_SUITE_COMPARISON_PAPER_RANGES = [
        "1988_01", "1996_01", "1998_07", "2008_01", "2011_01", "2012_01", "2013_09", "2016_11"]

    def _calculate_date_range(self):
        two_month_start = pandas.date_range(self.start, self.end, freq='2MS')
        full_date_range = [f"{x:%Y_%m}" for x in two_month_start]
        return full_date_range

    def _calculate_time_periods(self):
        delta_tz = timedelta(hours=+10)
        delta_1 = timedelta(days=1)
        two_month_start = pandas.date_range(self.start, self.end, freq='2MS')
        time_query_periods = [
            (
                _to_datetime(
                    f'{pandas.to_datetime(x):%Y-%m-%d}T01:00:00+1000'),
                _to_datetime(
                    f'{pandas.to_datetime(y-delta_1):%Y-%m-%d}T22:59:59+1000')
            ) for (x, y) in
            zip(two_month_start[0:len(two_month_start)-1], two_month_start[1:len(two_month_start)])]
        return time_query_periods
