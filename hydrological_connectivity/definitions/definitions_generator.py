import pkgutil
import logging
import re
import geopandas
import pandas
from hydrological_connectivity.datatypes.fwdet_outputs import FwdetOutputs
from hydrological_connectivity.datatypes.hand_outputs import HandOutputs
from hydrological_connectivity.datatypes.simple_outputs import SimpleOutputs
from hydrological_connectivity.datatypes.tvd_outputs import TvdOutputs
from hydrological_connectivity.datatypes.water_observations import WaterObservations
import os
import io
from dotenv import load_dotenv
load_dotenv()


class DefinitionsGenerator():
    """DefinitionsGenerator is a base class - inherting classes define the hydraulic model & zone definitions."""

    def __init__(self, exclude=[]):
        self.exclude = exclude
        self.simple_outputs = []
        self.hand_outputs = []
        self.tvd_outputs = []
        self.fwdet_outputs = []
        self.models = {}
        self.zones = {}
        self.global_elevation = ""
        self.elevation_region = {}
        self.elevation_location = {}

        self.water_observations = WaterObservations({})
        self.get_peak_events()
        self.output_path_root = os.environ['OUTPUT_FOLDER_ROOT'].replace(
            "{", "{{").replace("}", "}}")

        self.zone_raster_albers = os.environ['ZONE_DEF_ALBERS_RASTER']

    def generate(self):
        pass

    def get_peak_events(self):

        peak_event_df = pandas.read_csv(
            f"{os.environ['INPUT_FOLDER']}{os.path.sep}peak-events.csv", index_col=0, parse_dates=[1])

        self.peak_events = peak_event_df.to_dict()['PeakEvent']

        satellite_df = pandas.read_csv(
            f"{os.environ['INPUT_FOLDER']}{os.path.sep}satellite-events.csv", index_col=0, parse_dates=[1])
        self.satellite_events = satellite_df.to_dict()['PeakObserved']

    def create_model_outputs(self):
        df = geopandas.read_file(self.zone_definition_albers_shape)

        df_wgs84_t = geopandas.read_file(
            self.zone_definition_wgs84_shape).transpose()

        self.simple_outputs = []
        self.hand_outputs = []
        self.tvd_outputs = []
        self.fwdet_outputs = []

        rows = df.transpose()
        for segment_index in rows:
            row = rows[segment_index]
            region = row.loc['Region']
            location = row.loc['Location']
            short_location_label = row.loc['Short_Loc']
            if short_location_label in self.exclude:
                continue

            if not(region in self.models):
                logging.warning(
                    f"Region '{region}' was not found in the list of models, SKIPPING")
                continue
            hydraulic_model = self.models[region]

            for ts in hydraulic_model.get_contiguous_date_ranges():
                ts_start = ts['start']
                ts_end = ts['end']
                ts_step = ts['timestep']
                ts_mean = ts_start + ((ts_end+ts_step)-ts_start)/2

                closest_nat_date = self.water_observations.get_closest_date(
                    ts_mean)

                short_nat_identifier = f'{short_location_label} {closest_nat_date:%Y-%m}'

                if short_nat_identifier in self.satellite_events:
                    sat_date = self.satellite_events[short_nat_identifier]
                else:
                    logging.warning(
                        f'Could not find {short_nat_identifier} in satellite csv')

                    sat_date = ts_mean

                closest_date = self.water_observations.get_closest_date(
                    sat_date)

                short_identifier = f'{short_location_label} {ts_start:%Y-%m}'
                if short_identifier in self.peak_events:
                    ts['peak-event'] = self.peak_events[short_identifier]
                else:
                    ts['peak-event'] = ts_end

                presentation_date = "{0:%Y-%m}".format(closest_date)
                short_location = '{0:02}_{1:%Y%m%d}_{2}'.format(row.name, closest_date, re.sub(
                    '[^a-zA-Z]+', '_', location[0:20]))

                output_path = self.output_path_root + \
                    f'{os.path.sep}simple{os.path.sep}simple_{0}.tif'
                self.simple_outputs.append(SimpleOutputs(
                    f"{short_location_label} - {presentation_date}",
                    closest_date,
                    self.water_observations.date_to_observation_file[closest_date],
                    self.global_elevation.elevation_filename,
                    hydraulic_model,
                    ts,
                    row.loc['geometry'],  # albers
                    df_wgs84_t[segment_index].loc['geometry'],
                    segment_index,
                    output_path.format(short_location)))

                output_path = self.output_path_root + \
                    f'{os.path.sep}hands{os.path.sep}hand_{{0}}.tif'

                hand_level = HandOutputs.get_hand_level(f"{os.environ['INPUT_FOLDER']}{os.path.sep}hand-levels.csv",
                                                        str(short_location_label), '{0:%Y-%m-%d}'.format(ts['peak-event']))

                if hand_level < 0:
                    logging.error(
                        f"Hand level was not found for date {ts['peak-event']:%Y-%m-%d} in {short_location_label} - {presentation_date}")
                self.hand_outputs.append(HandOutputs(
                    f"{short_location_label} - {presentation_date}",
                    self.water_observations.date_to_observation_file[closest_date],
                    self.global_elevation.elevation_filename,
                    hydraulic_model,
                    ts,
                    hand_level,  # HAND value
                    row.loc['geometry'],  # albers
                    df_wgs84_t[segment_index].loc['geometry'],
                    segment_index,
                    output_path.format(short_location)))

                output_path = self.output_path_root + \
                    f'{os.path.sep}tvd{os.path.sep}tvd_{{0}}.tif'
                self.tvd_outputs.append(TvdOutputs(
                    f"{short_location_label} - {presentation_date}",
                    self.water_observations.date_to_observation_file[closest_date],
                    self.global_elevation.elevation_filename,
                    hydraulic_model,
                    ts,
                    [(row.loc['TVD_St_X'], row.loc['TVD_St_Y']),
                     (row.loc['TVD_End_X'], row.loc['TVD_End_Y'])],
                    row.loc['geometry'],  # albers
                    df_wgs84_t[segment_index].loc['geometry'],
                    segment_index,
                    output_path.format(short_location)))

                output_path = self.output_path_root + \
                    f'{os.path.sep}fwdet{os.path.sep}fwdet_{{0}}.tif'
                channel_path = None
                self.fwdet_outputs.append(FwdetOutputs(
                    f"{short_location_label} - {presentation_date}",
                    self.water_observations.date_to_observation_file[closest_date],
                    self.global_elevation.elevation_filename,
                    channel_path,
                    hydraulic_model,
                    ts,
                    row.loc['geometry'],  # albers
                    df_wgs84_t[segment_index].loc['geometry'],
                    segment_index,
                    output_path.format(short_location)))
