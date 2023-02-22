from typing import Dict, List
from xarray import DataArray

from mdb_fwdet.region import Region


class RegionDefinition():
    """Describes the spatial bounding box of each region"""

    def __init__(self, region_bounds: List[Region], region_grid: DataArray):
        self.region_bounds = region_bounds
        self.region_grid = region_grid

    def generate_mock_spatial_array(regions: List[Region], spatial_template: DataArray) -> DataArray:
        region_template = spatial_template.copy()
        for region in regions:
            mask_bounds = region.bounding_box
            region_template[mask_bounds[0]:mask_bounds[1],
                            mask_bounds[2]:mask_bounds[3]] = region.region_number
        return region_template

    def dict_to_regions(region_bounds: Dict[int, tuple]) -> List[Region]:
        return [Region(index, bounds_tuple) for (index, bounds_tuple) in region_bounds.items()]

    MOCK_REGIONS: Dict[int, tuple] = {0: (0, 12, 0, 8), 1: (12, 25, 8, 25),
                                      2: (0, 12, 8, 25), 3: (12, 25, 0, 8)}
    MDB_REGIONS: Dict[int, tuple] = {0: (23967, 35491, 12410, 19489),
                                     1: (34097, 45151, 28775, 41294),
                                     2: (38537, 48592, 21375, 36884),
                                     3: (32962, 40056, 16950, 31319),
                                     4: (16967, 30731, 14085, 23104),
                                     5: (5342, 16231, 40465, 51668),
                                     6: (757, 13731, 32275, 42614),
                                     7: (12057, 23596, 35865, 45649),
                                     8: (10302, 22721, 27670, 40414),
                                     9: (28632, 39916, 27845, 43064),
                                     10: (26567, 35566, 16680, 29344),
                                     11: (37487, 48376, 10750, 24564),
                                     12: (27942, 44726, 0, 9159),
                                     13: (31552, 45446, 7360, 19759),
                                     14: (24652, 34426, 5125, 14264),
                                     15: (17562, 28816, 21240, 29374),
                                     16: (0, 11301, 21630, 35354),
                                     17: (9657, 19246, 19575, 26404),
                                     18: (20517, 33311, 35850, 49034),
                                     19: (20622, 32036, 31725, 39519),
                                     20: (13317, 22201, 42850, 50689),
                                     21: (8947, 20356, 24245, 34399),
                                     22: (19577, 30981, 25710, 34154)}
