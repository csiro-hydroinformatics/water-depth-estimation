
import unittest

from hydrological_connectivity.definitions.definitions_generator_factory import DefinitionsGeneratorFactory
import os
from dotenv import load_dotenv
load_dotenv()


class TestDefinitionsGenerator(unittest.TestCase):

    def test_get_generator(self):
        x = DefinitionsGeneratorFactory.get_generator()
        print(x)

    def test_get_output_folder(self):
        print(f"output folder = {os.environ['OUTPUT_FOLDER']}")
