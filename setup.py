""" Setup of Hydrological Connectivity app"""
import setuptools

setuptools.setup(name='hydrology_connectivity',
                 version='0.0.1',
                 description='This package contains a process-based model for hydrology connectivity.',
                 author='C.S.I.R.O.',
                 packages=[
                     'hydrological_connectivity'
                     #'hydrological_connectivity.datatypes',
                     #'hydrological_connectivity.definitions',
                     #'hydrological_connectivity.postprocessing',
                     #'hydrological_connectivity.preprocessing',
                     #'hydrological_connectivity.processing',
                     #'hydrological_connectivity.tests'
                 ],
                 install_requires=[],

                 url='https://bitbucket.csiro.au/projects/MAE/repos/hydrological-connectivity-mdb/browse',
                 zip_safe=False)


# https://packaging.python.org/tutorials/packaging-projects/
# python setup.py sdist bdist_wheel
# conda install --name %my_env_name% jupyterlab ipywidgets jupyter
# jupyter-labextension install @jupyter-widgets/jupyterlab-manager
# python -m ipykernel install --user --name %my_env_name% --display-name "Hydro Con"