# MDB_FwDET
This folder contains code to calculate flood water depth using a variation 
of FwDET v2.0 (Cohen et al, 2018) with Thin Plate Splines. This version was
applied to the Murray Darling Basin (MDB), Australia. This code is provided to explain 
the steps used to create the product archived on CSIRO's Data Access Portal 
(https://data.csiro.au/collection/csiro:50243).

The inputs are defined through a configuration file located: 
mdb_fwdet/configuration.py. It takes as input flood extent maps, DEM, channel 
correction layer and outline of 23 regions of the MDB. The bounding box for
each region are hard coded in mdb_fwdet/region_definition.py

# Installation
The library was installed and run on CSIRO EASI-HUB. It expects a jupyter-hub
environment with a dask cluster for computation and AWS s3 for storage. 

pandas requires postgres client library: `sudo apt-get install libpq-dev`

Use `python -m pip install .` to install python dependencies.

# Execution
The code is executed through python's unit test framework. Unit tests are 
included on mock data in mdb_fwdet/tests. The test for the full workflow is
mdb_fwdet/tests/test_fwdet_dask/test_fwdet_large_process
