import logging
import sys
from inspect import currentframe

from dynaconf import Dynaconf
from loguru import logger

values = Dynaconf(
    envvar_prefix="DYNACONF",
    settings_files=["settings.toml", ".secrets.toml"],
)