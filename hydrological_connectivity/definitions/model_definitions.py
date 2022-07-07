from enum import Enum
from typing import Dict


class ModelDefinitions():
    """ Define the types of models and properties that we have """

    def get_model_types():
        return {

            DepthModelType.FwDET: {"attributes": ['']},
            DepthModelType.TVD: {
                "seperation_of_waterbodies": ['all', 'ind']
            },
            DepthModelType.Simple: {
                "seperation_of_waterbodies": ['all', 'ind']
            },
            DepthModelType.HAND: {
                "accumulation_threshold": [100000, 500000, 1000000, 3000000]
            }
        }

    def get_model_definitions():
        types = []
        for (depth_model_type, model_attributes) in ModelDefinitions.get_model_types().items():
            for (attribute, attribute_list) in model_attributes.items():
                for attribute_value in attribute_list:
                    depth_model_definition = ModelDefinition(
                        depth_model_type, {attribute: attribute_value})
                    types.append(depth_model_definition)

        return types


class DepthModelType(Enum):
    """ Define the types of models that we have """
    HAND = 1  # Height Above Nearest Drainage
    TVD = 2  # Teng Vaze Dutta
    Simple = 3
    FwDET = 4  # Floodwater Depth Estimation Tool


class ModelDefinition():
    def __init__(self, depth_model_type, depth_model_params: Dict):
        self.depth_model_type = depth_model_type
        self.depth_model_params = depth_model_params

    def __str__(self) -> str:
        params_str = ", ".join([f"'{att}'='{val}'" for (
            att, val) in self.depth_model_params.items()])
        return f"Definition for {self.depth_model_type} with variables {params_str}"

    __repr__ = __str__
