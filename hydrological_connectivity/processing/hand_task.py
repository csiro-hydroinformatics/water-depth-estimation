import logging
import os
import numpy
from numpy.ma import compress
from pysheds.grid import Grid
import rasterio
from rasterio.enums import Resampling
from rasterio.io import DatasetReader
from rasterio.vrt import WarpedVRT
import scipy
import scipy.ndimage
from shapely.geometry.polygon import Polygon
from hydrological_connectivity.datatypes.hand_outputs import HandOutputs
import time
import rasterio.mask
import rasterio.warp
from rasterio.windows import from_bounds


class HandTask():
    """Caculate flood depth using HAND method (Rennó et al, 2008)

    Attributes:
        accumulation_threshold: Contributing Area Threshold. The paper 
            defines this term and provides some discussion, "For this reason, we decided to
            use the contributing area threshold as one of the main criteria to
            define the drainage network, validating channel heads with field data.
            To define the channel heads we used an additional criteria based on
            simplifications of horizontal and vertical geomorphic curvatures.
            Firstly, the channel head element should represent a convergent point,
            meaning it should have two or more overland flux paths converging to
            it (horizontal curvature). Secondly, the channel profile should be
            concave, i.e. where the channel head profile point has a smaller
            change of elevation than the mean of the elements located uphill and
            downhill of it (vertical curvature)."
    """

    def __init__(self, hand_outputs: HandOutputs):
        self.WOfS_nodata_value = 0
        self.WOfS_dry_value = 2
        self.WOfS_wet_value = 3

        self.accumulation_threshold = 1000  # range 10000 15000 30000

        self.hand_outputs = hand_outputs

    def execute(self):
        self.dem_to_hand()
        self.save_to_disk()

    def dem_to_hand(self):
        # expand bounds to avoid stream network issues
        (x1, y1, x2, y2) = self.hand_outputs.region_of_interest_albers.bounds
        x_amp = (x2-x1)*0.75  # Add 25% to each side
        y_amp = (y2-y1)*0.75  # Add 25% to each side
        x_mean = (x2+x1)/2
        y_mean = (y2+y1)/2
        new_bounds = (x_mean-x_amp, y_mean-y_amp,
                      x_mean+x_amp, y_mean+y_amp)

        left, bottom, right, top = new_bounds
        logging.info(f"{left} {bottom} {right} {top}")

        # with rasterio.open(self.hand_outputs.dem_path) as src_dem:
        #    window = from_bounds(
        #        left, bottom, right, top, src_dem.transform)
        #    logging.info(f'{window}')
        #    dem = src_dem.read(1, masked=True, window=window)

        self.grid = Grid()

        logging.info("loading {0}".format(self.hand_outputs.dem_path))
        self.grid.read_raster(self.hand_outputs.dem_path, data_name='dem', window=tuple(
            new_bounds))

        logging.info(self.grid.affine)
        # Fill dead end depressions
        logging.info("Fill dead end depressions")
        self.grid.fill_depressions(data='dem', out_name='nopits_dem')
        # Inflate the DEM to resolve the drainage network over flat terrain
        del self.grid.dem
        logging.info(
            "Inflate the DEM to resolve the drainage network over flat terrain")
        self.grid.resolve_flats(data='nopits_dem', out_name='inflated_dem')
        del self.grid.nopits_dem
        # Calculate flow direction
        logging.info("Calculate flow direction")
        self.grid.flowdir(data='inflated_dem', out_name='dir')
        # Compute flow accumulation based on computed flow direction
        logging.info(
            "Compute flow accumulation based on computed flow direction")
        self.grid.accumulation(data='dir', out_name='acc')
        # Compute HAND
        self.stream_network = self.grid.acc > self.accumulation_threshold

        logging.info("Compute HAND")
        self.grid.compute_hand('dir', 'inflated_dem',
                               self.stream_network, 'hand')

        # self.dem for
        self.depth = self.hand_outputs.flood_depth - self.grid.hand
        self.depth[self.depth < 0] = numpy.nan

        # We have height above nearest drainage (main stream). Add depth

    def save_to_disk(self):
        hand_path = self.hand_outputs.output_path.replace(
            '.tif', f'_hand_{str(self.accumulation_threshold)}.tif')
        logging.info(f"Saving to disk: {hand_path}")
        with rasterio.open(
                hand_path, 'w',
                driver='COG',
                compress='LZW',
                dtype=self.grid.hand.dtype,
                count=1,
                nodata=numpy.nan,
                transform=self.grid.affine,
                width=self.grid.shape[1],
                height=self.grid.shape[0],
                resampling='average',
                overview_resampling='average') as dst:
            dst.write(self.grid.hand, indexes=1)

        stream_path = self.hand_outputs.output_path.replace(
            '.tif', f'_str_{str(self.accumulation_threshold)}.tif')
        logging.info(f"Saving to disk: {stream_path}")
        with rasterio.open(
                stream_path, 'w',
                driver='COG',
                compress='LZW',
                crs='EPSG:3577',
                dtype=numpy.int8,  # raster io doesn't know to convert bool to int
                count=1,
                nodata=numpy.nan,
                transform=self.grid.affine,
                width=self.grid.shape[1],
                height=self.grid.shape[0],
                resampling='average',
                overview_resampling='average') as dst:
            dst.write(self.stream_network, indexes=1)

        depth_path = self.hand_outputs.output_path.replace(
            '.tif', f'_dep_{str(self.accumulation_threshold)}.tif')
        logging.info(f"Saving to disk: {depth_path}")
        with rasterio.open(
                depth_path, 'w',
                driver='COG',
                compress='LZW',
                crs='EPSG:3577',
                dtype=self.depth.dtype,  # raster io doesn't know to convert bool to int
                count=1,
                nodata=numpy.nan,
                transform=self.grid.affine,
                width=self.grid.shape[1],
                height=self.grid.shape[0],
                resampling='average',
                overview_resampling='average') as dst:
            dst.write(self.depth, indexes=1)
