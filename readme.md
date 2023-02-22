# Water depth estimation

We undertook detailed analysis of three methods for estimating flood water depth from satellite derived water extent and digital terrain model. The results were validated against hydrodynamic modelling results from 11 river reaches in three Australian regions. This work provides a guideline for future studies that enhance remote sensing-based flood maps with water depth, making use of the growing number of publicly available remote sensing water extent and digital terrain datasets globally. 

This repo contains programs for generating flood products and comparing them.

Caveats: 
* A limited amount of testing has been undertaken - users should familiarise themselves with the original flood models and ensure that the model outputs are inline with their expectations
* The flood models are designed to make use of limited data, at the expense of accuracy. They cannot be used as an alternative to hydraulic models for engineering or design works
* A subset of toy data is provided for learning purposes
* This code has been revised locally based on reviewer comments, and will be updated once local filepaths have been stripped (etc.)

# Murray Darling Basin water depth code
We have developed a two-monthly flood water depth product using FwDET for the Murray Darling 
Basin (MDB), Australia (see https://data.csiro.au/collection/csiro:50243). The code is in the 
[mdb_fwdet](mdb_fwdet/README.md) folder.

A demonstration of how to analyse the two-monthly flood water depth product is provided 
in the notebook [example_water_depth.ipynb](notebooks/example_water_depth.ipynb).

# License
CSIRO/GPL v3 see LICENSE & gpl-3.0.txt

Please visit our [getting started notebook](Getting_Started.ipynb) for further information and use. Or you can launch a [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/csiro-hydroinformatics/water-depth-estimation/main?urlpath=lab/tree/Getting_Started.ipynb) environment to explore the code

