from typing import Dict
from hydrological_connectivity.definitions.model_definitions import DepthModelType, ModelDefinition
from hydrological_connectivity.processing.fwdet_task import FwdetTask
from hydrological_connectivity.definitions.definitions_generator import DefinitionsGenerator
from hydrological_connectivity.processing.compare_flood_rasters_rasterio import CompareFloodRastersRasterIo
from hydrological_connectivity.processing.produce_stats import ProduceStats
import logging
import os


class ModelResultAggregator():
    """ Aggregate model results for a particular model """

    def __init__(self, definition: DefinitionsGenerator, model_type: ModelDefinition):
        self.definition = definition
        self.model_type = model_type

        if os.environ['COMPARE_BY_ELEVATION'] == 'TRUE':
            self.by_elev = ['LBS - Culgoa FP South',
                        'LBS - Culgoa FP North',
                        'LBS - Narran River',
                        'LBS - St George',
                        'SA - Weir Pool 3',
                        'SA - Weir Pool 4',
                        'SA - Weir Pool 5',
                        'Namoi - DS Mollee',
                        'Namoi - DS Gunidgera',
                        'Namoi - Merah North',
                        'Namoi - Boolcarroll'
                        ]
        else:
            self.by_elev = []

        self.prepare_stats()
        logging.debug(
            f"Comparison File Names = '{self.comparison_raster_names}'")

    def produce_stats(self):
        tasks = []
        for output in self.identified_outputs:
            try:
                logging.info(f"Processing: {output}")

                # if any([e in output.short_description for e in self.by_elev]):
                #    hydr_model_output = output.hydraulic_model.elevation_outputs[
                #        output.simulation_timespan['peak-event']]
                # else:
                hydr_model_output = output.hydraulic_model.depth_outputs[
                    output.simulation_timespan['peak-event']]

                stats = ProduceStats(
                    self.comparison_raster_names[output],
                    hydr_model_output,
                    self.definition.zone_raster_albers,
                    output.segment_index,
                    output.region_of_interest_albers
                )
                stats.execute()
                tasks.append({"input": output, "stats": stats})
            except:
                logging.exception(f"Raised an error with {output}")
        return tasks

    def prepare_stats(self):
        if (self.model_type.depth_model_type == DepthModelType.FwDET):
            self.prepare_fwdet_stats()
        if (self.model_type.depth_model_type == DepthModelType.Simple):
            self.prepare_simple_stats(
                self.model_type.depth_model_params['seperation_of_waterbodies'])
        if (self.model_type.depth_model_type == DepthModelType.TVD):
            self.prepare_tvd_stats(
                self.model_type.depth_model_params['seperation_of_waterbodies'])
        if (self.model_type.depth_model_type == DepthModelType.HAND):
            self.prepare_hand_stats(
                self.model_type.depth_model_params['accumulation_threshold'])

    def prepare_fwdet_stats(self):
        self.prepare_stats_generic(self.definition.fwdet_outputs)

    def prepare_simple_stats(self, ext='all'):
        self.prepare_stats_generic(self.definition.simple_outputs, ext)

    def prepare_tvd_stats(self, ext='all'):
        self.prepare_stats_generic(self.definition.tvd_outputs, ext)

    def prepare_hand_stats(self, accumulation_threshold):
        self.identified_outputs = []
        self.comparison_raster_names = {}
        for output in self.definition.hand_outputs:
            self.identified_outputs.append(output)

            if any([e in output.short_description for e in self.by_elev]):
                elev = "_elev"  # Compare by elevation
            else:
                elev = ""  # Compare by depth

            if type(accumulation_threshold) is dict:
                accumulation_threshold_value = list(
                    accumulation_threshold.values())[0][output]
            else:
                accumulation_threshold_value = accumulation_threshold
            self.comparison_raster_names[output] = output.output_path.replace(
                ".tif", f"_dep_comparison{elev}_{str(accumulation_threshold_value)}.tif")

    def prepare_stats_generic(self, output_list, ext=None):
        self.identified_outputs = []
        self.comparison_raster_names = {}
        for output in output_list:
            infix = ""
            if ext is not None:
                infix = "_" + ext
            self.identified_outputs.append(output)
            if any([e in output.short_description for e in self.by_elev]):
                elev = "_elev"  # Compare by elevation
            else:
                elev = ""  # Compare by depth

            self.comparison_raster_names[output] = output.output_path.replace(
                ".tif", infix + f"_comparison{elev}.tif")
