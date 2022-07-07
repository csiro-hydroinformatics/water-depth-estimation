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

The notebooks folder contains example logic for TVD, HANDS, etc. flood modelling. There are simple demonstration notebooks for each of the algorithms.

| Notebook | Description |
|---|---|
| water_depth_estimation_HAND | Height Above Nearest Drainage (from Rennó et al, 2008)|
| water_depth_estimation_RS_DEM | Floodwater Depth Estimation Tool (Cohen et al. 2017, 2019)|
| water_depth_estimation_simplistic | Simplistic bathtub method |
| water_depth_estimation_TVD | Teng-Vaze-Dutta (Teng et al, 2013)|

The notebooks folder also contains logic for comparing various flood models to observed hydraulic models. For running the hydrological_connectivity modules, please set the "Notebook File Root" to the $workspaceFolder (run Jupyter notebook from the root directory rather than the notebooks folder to keep it part of the same package). An example patch is provided and can be customised with .env file parameters.

Notebooks to run in order are:

1. [calculate_spot_heights.ipynb](./notebooks/calculate_spot_heights.ipynb) - Establishes levels
1. [compare_hydraulic_model.ipynb](./notebooks/compare_hydraulic_model.ipynb) - Runs models and compares outputs with hydraulic outputs
1. [generate_report_data.ipynb](./notebooks/generate_report_data.ipynb) - Produces aggregated results

| Notebook | Description |
|---|---|
| calculate_spot_heights | Extract from hydraulic model levels at upstream and downstream points in reach *not needed if hand levels have already been defined (this should be run first)|
| compare_hydraulic_model | Compare all the hydraulic model/rs models and produce output grids (this should be run second) |
| generate_report_data | Analyse output grids from comparison and produce statistics for reports |
| generate_reports | Generate reports for the comparison data set | 
| generate_individual_reports | Generate detailed reports on the combined statistics for a model |

## Jupyter Lab setup

### Jupyter Lab

If not already installed you will require [Jupyter Lab](https://jupyterlab.readthedocs.io/en/stable/)

### Environment setup

### Prerequisites
Does your computer has `conda` installed and available from a command prompt (check with `where conda` on windows and `which conda` on Linux). Update it if need too. ```conda update --all ``` and ```conda update -n base -c defaults conda```

Ensure that conda is in the path.

For me, I installed anaconda3 into ```C:\Anaconda3```. Therefore you need to add ```C:\Anaconda3``` as well as ```C:\Anaconda3\Scripts\``` to your path variable, e.g. ```set PATH=%PATH%;C:\Anaconda3;C:\Anaconda3\Scripts\```.

### Env Setup
- ```init_refresh_env.bat``` file is used to initialise the environment and refresh it if packages are added.  
- Please update the ```environment.yml``` file if utilising new python packages and rerun the ```.bat``` file.

- ```start_jupyter.bat``` file is used to activate and start your Jupyter session
