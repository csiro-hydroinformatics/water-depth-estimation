set mypath=%cd%
@echo %mypath%
cd %mypath%

set env_name=hydrocon_env
set display_name="HydroCon"

CALL conda deactivate

CALL conda env remove --name %env_name%
CALL jupyter kernelspec remove %env_name% -y

CALL conda env create -f=./environment.yml

CALL activate %env_name%

::CALL jupyter-labextension install @jupyter-widgets/jupyterlab-manager

CALL python -m ipykernel install --user --name %env_name% --display-name %display_name%


jupyter lab