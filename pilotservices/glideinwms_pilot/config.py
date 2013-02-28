import os

import ini_handler

from errors import ConfigError

from simple_logging import Logger
from simple_logging import FileWriter
from simple_logging import SyslogWriter
from simple_logging import ConsoleWriter

from contextualization_types import CONTEXT_TYPE_EC2
from contextualization_types import CONTEXT_TYPE_NIMBUS

class Config(object):
    valid_context_types = [CONTEXT_TYPE_EC2, CONTEXT_TYPE_NIMBUS]

    def __init__(self, config_ini="/etc/glideinwms/glidein-pilot.ini"):
        if not os.path.exists(config_ini):
            raise ConfigError("%s does not exist" % config_ini)

        self.ini = ini_handler.Ini(config_ini)

        self.default_max_lifetime = self.ini.get("DEFAULTS", "default_max_lifetime", "172800") # 48 hours
        self.max_lifetime = self.default_max_lifetime  # can be overridden
        self.disable_shutdown = self.ini.getBoolean("DEFAULTS", "disable_shutdown", False)
        self.max_script_runtime = self.ini.getBoolean("DEFAULTS", "max_script_runtime", "60")

        self.pre_script_dir = self.ini.get("DIRECTORIES", "pre_script_dir", "/var/glideinwms_pilot/PRE")
        self.post_script_dir = self.ini.get("DIRECTORIES", "post_script_dir", "/var/glideinwms_pilot/POST")

        # home directory is created by the rpm
        self.home_dir = "/home/glidein_pilot"

        # glidein_startup.sh specific attributes
        self.factory_url = ""
        self.pilot_args = ""
        self.proxy_file = ""
        self.pilot_args = ""

    def setup(self):
        self.setup_logging()
        self.setup_pilot_files()
        self.setup_contextualization()

    def setup_pilot_files(self):
        self.ini_file = "%s/glidein_userdata" % self.home_dir
        self.userdata_file = "%s/userdata_file" % self.home_dir

    def setup_contextualization(self):
        self.contextualization_type = self.ini.get("DEFAULTS", "contextualize_protocol")
        if self.contextualization_type in Config.valid_context_types:
            if self.contextualization_type == CONTEXT_TYPE_EC2:
                self.ec2_url = self.ini.get("DEFAULTS", "ec2_url")
            elif self.contextualization_type == CONTEXT_TYPE_NIMBUS:
                self.nimbus_url_file = self.ini.get("DEFAULTS", "nimbus_url_file")
        else:
            raise ConfigError("configured context type not valid")

    def setup_logging(self):
        log_writer = None
        log_writer_class = self.ini.get("DEFAULTS", "logger_class", None)
        if log_writer_class:
            if log_writer_class == "SyslogWriter":
                facility = self.ini.get("DEFAULTS", "syslog_facility", None)
                priority = self.ini.get("DEFAULTS", "syslog_priority", None)
                log_writer = SyslogWriter(facility=facility, priority=priority)
            elif log_writer_class == "ConsoleWriter":
                output = self.ini.get("DEFAULTS", "console_output", "stdout")
                log_writer = ConsoleWriter(output=output)
            else:
                log_writer = FileWriter(self.home_dir)
        else:
            log_writer = FileWriter(self.home_dir)
        self.log = Logger(log_writer)
        self.log.log_info("Pilot Launcher started...")

    def export_grid_env(self):
        environment = ""
        try:
            for option in self.ini.cp.options("GRID_ENV"):
                environment += "export %s=%s; " % (str(option).upper(), self.ini.get("GRID_ENV", option))

            environment += "export X509_USER_PROXY=%s;" % self.proxy_file

        except:
            # pylint: disable=W0702
            pass
        return environment

    def get_grid_env(self):
        """
        Returns a dictionary of the parent process environment plus the "grid"
        specific environment variables defined in the pilot config file.

        @returns: dictionary containing the desired process environment
        """
        environment = {}
        try:
            # inherit the parent process environment
            for var in os.environ.keys():
                environment[var] = os.environ[var]

            # add in the "grid" specific environment
            for option in self.cp.ini.options("GRID_ENV"):
                environment[str(option).upper()] = self.ini.get("GRID_ENV", option)

            environment["X509_USER_PROXY"] = self.proxy_file

        except:
            # pylint: disable=W0702
            pass
        return environment
