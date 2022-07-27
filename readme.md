# Water depth estimation

We undertook detailed analysis of three methods for estimating flood water depth from satellite derived water extent and digital terrain model. The results were validated against hydrodynamic modelling results from 11 river reaches in three Australian regions. This work provides a guideline for future studies that enhance remote sensing-based flood maps with water depth, making use of the growing number of publicly available remote sensing water extent and digital terrain datasets globally. 

This repo contains programs for generating flood products and comparing them.

Caveats: 
* A limited amount of testing has been undertaken - users should familiarise themselves with the original flood models and ensure that the model outputs are inline with their expectations
* The flood models are designed to make use of limited data, at the expense of accuracy. They cannot be used as an alternative to hydraulic models for engineering or design works
* A subset of toy data is provided for learning purposes
* This code has been revised locally based on reviewer comments, and will be updated once local filepaths have been stripped (etc.)

# License
CSIRO/GPL v3 see LICENSE & gpl-3.0.txt



## Getting Started

The notebooks folder contains example logic for TVD, HAND, etc. flood models. There are simple demonstration notebooks for each of the algorithms.

| Notebook | Description |
|---|---|
| water_depth_estimation_HAND | Height Above Nearest Drainage (from Rennó et al, 2008)|
| water_depth_estimation_RS_DEM | Floodwater Depth Estimation Tool (Cohen et al. 2017, 2019)|
| water_depth_estimation_simplistic | Simplistic bathtub method |
| water_depth_estimation_TVD | Teng-Vaze-Dutta (Teng et al, 2013)|

The notebooks folder also contains logic for comparing various flood models to observed hydraulic models. For running the hydrological_connectivity modules, please set the "Notebook File Root" to the $workspaceFolder (run Jupyter notebook from the root directory rather than the notebooks folder to keep it part of the same package). An example patch is provided and can be customised with .env file parameters.

Notebooks to run in order are:

1. [calculate_spot_heights.ipynb](./notebooks/calculate_spot_heights.ipynb) - Establishes HAND levels: Extract from hydraulic model levels at upstream and downstream points in reach *not needed if hand levels have already been defined
2. [compare_hydraulic_model.ipynb](./notebooks/compare_hydraulic_model.ipynb) - Runs models and compares outputs with hydraulic model outputs
3. [generate_report_data.ipynb](./notebooks/generate_report_data.ipynb) - Produces aggregated results: Analyse output grids from comparison and produce statistics for reports
4. [generate_reports.ipynb](./notebooks/generate_reports.ipynb) - Generates reports for the comparison data set
5. [generate_individual_reports.ipynb](./notebooks/generate_individual_reports.ipynb) - Generate detailed reports on the combined statistics for a model

You can either click this button [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/csiro-hydroinformatics/water-depth-estimation/HEAD) which launches a hosted lab or build it yourself (see below detials for self hosting).  Please note that the environment utilises many additional packages which will be downloaded and installed.  The build process will take sometime to complete and issues may arise over time as packages change version and unfortunately no longer work together.

## Jupyter Lab setup

### Jupyter Lab

If it has not already been installed you will require [Jupyter Lab](https://jupyterlab.readthedocs.io/en/stable/)

### Environment setup
When comparing large high resolution datasets numpy can consume reasonable amounts of memory. 32GB of RAM was sufficient when comparing two floodplain products on a 5m resolution grid for a 60km long stretch of floodplain.

### Prerequisites
Does your computer have `conda` installed and available from a command prompt (check with `where conda` on windows and `which conda` on Linux)? Update it if you need to. ```conda update --all ``` and ```conda update -n base -c defaults conda```

Ensure that conda is in the path. For instance, if you installed anaconda3 into ```C:\Anaconda3```, you will need to add ```C:\Anaconda3``` as well as ```C:\Anaconda3\Scripts\``` to your path variable, e.g. ```set PATH=%PATH%;C:\Anaconda3;C:\Anaconda3\Scripts\```.

### Env Setup
- ```init_refresh_env.bat``` file is used to initialise the environment and refresh it if packages are added.  
- Please update the ```environment.yml``` file if utilising new python packages and rerun the ```.bat``` file.

- ```start_jupyter.bat``` file is used to activate and start your Jupyter session
