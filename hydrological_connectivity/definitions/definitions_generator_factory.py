from pydoc import locate

import os
from dotenv import load_dotenv
load_dotenv()


class DefinitionsGeneratorFactory():
    """Create a class that can generate file paths and zone definitions for running bulk
    model comparisons 
    """
    def get_generator(args=None):
        """ Get an instance of the DefinitionsGenerator

        Returns:
            DefinitionsGenerator: A class that contains definitions of file paths and zones
        """
        definition_generator_class = locate(os.environ['DEFINITION_GENERATOR'])
        if args is None:
            return definition_generator_class()

        return definition_generator_class(args)
