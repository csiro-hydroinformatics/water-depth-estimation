import bom_water
import logging
from pytz import timezone


class HydroData():
    """Get hydrological data from the BoM SOS service"""

    def __init__(self, station_codes):
        self.station_codes = station_codes

    def download(self, t_begin="2016-01-01T00:00:00+10", t_end="2019-12-31T00:00:00+10"):
        # get station data
        bm = bom_water.BomWater()
        response = bm.request(bm.actions.GetCapabilities)
        logging.info(response.status_code)

        streamflow_ts = {}
        for station_code in self.station_codes:
            station_url = 'http://bom.gov.au/waterdata/services/stations/{}'.format(
                station_code)
            try:
                response = bm.request(bm.actions.GetObservation, station_url,
                                      bm.properties.Water_Course_Discharge, bm.procedures.Pat4_C_B_1_DailyMean, t_begin, t_end)
            except response.exceptions.RequestException as e:
                logging.error(f'BoM service failed with RequestException: {e}')

            streamflow_dataframe = bm.parse_get_data(response)
            streamflow_dataframe.index = streamflow_dataframe.index.tz_localize(
                timezone('UTC'))
            streamflow_ts[station_code] = streamflow_dataframe

        return streamflow_ts
