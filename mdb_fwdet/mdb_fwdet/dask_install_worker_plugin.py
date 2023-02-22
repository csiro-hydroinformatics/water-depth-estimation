from distributed.diagnostics.plugin import WorkerPlugin
import uuid 
import os

import logging
import socket
import subprocess
import re
import sys
import glob
from typing import List, Optional, Union
from distributed import UploadFile, Client
from distributed.diagnostics.plugin import WorkerPlugin
from dask_gateway import Gateway
import importlib.util
import numpy as np
import time

class DaskInstallWorkerPlugin(WorkerPlugin):
    """A Worker Plugin to pip install a set of packages

    This accepts a set of packages to install on all workers.
    You can also optionally ask for the worker to restart itself after
    performing this installation.

    .. note::

    This will increase the time it takes to start up
    each worker. If possible, we recommend including the
    libraries in the worker environment or image. This is
    primarily intended for experimentation and debugging.

    Additional issues may arise if multiple workers share the same
    file system. Each worker might try to install the packages
    simultaneously.

    Parameters
    ----------
    packages : List[str]
        A list of strings to place after "pip install" command
    pip_options : List[str]
        Additional options to pass to pip.
    restart : bool, default False
        Whether or not to restart the worker after pip installing
        Only functions if the worker has an attached nanny process

    Examples
    --------
    >>> from dask.distributed import DaskInstallWorkerPlugin
    >>> plugin = DaskInstallWorkerPlugin(packages=["scikit-learn"], pip_options=["--upgrade"])

    >>> client.register_worker_plugin(plugin)
    """
    def install_package(client, local_packages):
        class DaskInstallWorkerPluginLocal(WorkerPlugin):
            name = "pip"

            def __init__(self, packages, pip_options=None, restart=False):
                self.uuid = str(uuid.uuid4())
                self.name = 'pip-{0}'.format(self.uuid)

                _init_packages = []
                for p in packages:
                    if os.path.isfile(p):
                        with open(p, "rb") as f:
                            data = f.read()
                        _init_packages.append((os.path.basename(p), data))
                    elif isinstance(p, str):
                        _init_packages.append(p)

                self.packages = _init_packages
                self.restart = restart
                if pip_options is None:
                    pip_options = []
                self.pip_options = pip_options

            async def setup(self, worker):
                logger = logging.getLogger("distributed.worker") 
                # from distributed.lock import Lock
                packages = []
                for package in self.packages:
                    if isinstance(package, tuple):
                        if isinstance(package[0], str) and isinstance(package[1], bytes):
                            wheel_path = os.path.join(worker.local_directory, package[0])
                            with open(wheel_path, 'wb') as whl:
                                whl.write(package[1])
                            packages.append(wheel_path)
                    else:
                        packages.append(package)
                
                # BUG currently some processes end up in a deadlock and this will not go through
                # with Lock('pip' + socket.gethostname()):  # don't clobber one installation
                logger.info("Pip installing the following packages: %s", packages)
                proc = subprocess.Popen(
                    [sys.executable, "-m", "pip", "install"]
                    + self.pip_options
                    + packages,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                stdout, stderr = proc.communicate()
                returncode = proc.wait()

                if returncode:
                    logger.error("Pip install failed with '%s'", stderr.decode().strip())
                    return
                else:
                    logger.info(stdout.decode().strip())

                if self.restart and worker.nanny:
                    lines = stdout.strip().split(b"\n")
                    if not all(
                        line.startswith(b"Requirement already satisfied") for line in lines
                    ):
                        worker.loop.add_callback(
                            worker.close_gracefully, restart=True
                        )  # restart


        plugin = DaskInstallWorkerPluginLocal(packages=local_packages) # use wheel, consider , pip_options= ["--upgrade"]
        client.register_worker_plugin(plugin)
