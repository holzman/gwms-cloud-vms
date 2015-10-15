import os

import ini_handler

from errors import ConfigError

from simple_logging import Logger
from simple_logging import FileWriter
from simple_logging import SyslogWriter
from simple_logging import ConsoleWriter

from contextualization_types import CONTEXT_TYPE_EC2
from contextualization_types import CONTEXT_TYPE_NIMBUS
from contextualization_types import CONTEXT_TYPE_OPENNEBULA

class Config(object):
    valid_context_types = [CONTEXT_TYPE_EC2, CONTEXT_TYPE_NIMBUS, CONTEXT_TYPE_OPENNEBULA]

    def __init__(self, config_ini="/etc/glideinwms/glidein-pilot.ini"):
        if not os.path.exists(config_ini):
            raise ConfigError("%s does not exist" % config_ini)

        self.ini = ini_handler.Ini(config_ini)

        self.default_max_lifetime = self.ini.get("DEFAULT", "default_max_lifetime", "172800") # 48 hours
        self.max_lifetime = self.default_max_lifetime  # can be overridden
        self.disable_shutdown = self.ini.getBoolean("DEFAULT", "disable_shutdown", False)
        self.max_script_runtime = self.ini.get("DEFAULT", "max_script_runtime", "60")

        self.pre_script_dir = self.ini.get("DIRECTORIES", "pre_script_dir", "/usr/libexec/glideinwms_pilot/PRE")
        self.post_script_dir = self.ini.get("DIRECTORIES", "post_script_dir", "/usr/libexec/glideinwms_pilot/POST")

        # home directory is created by the rpm
        self.home_dir = "/home/glidein_pilot"
        self.glidein_user = "glidein_pilot"
        self.scratch_dir = "/home/scratchgwms"

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
        self.log.log_info("Default ini file: %s" % self.ini_file)
        self.log.log_info("Default userdata file: %s" % self.userdata_file)

    def setup_contextualization(self):
        self.contextualization_type = self.ini.get("DEFAULT", "contextualize_protocol")
        self.log.log_info("Contextualization Type identified as: %s" % self.contextualization_type)
        if self.contextualization_type in Config.valid_context_types:
            if self.contextualization_type == CONTEXT_TYPE_EC2:
                self.ec2_url = self.ini.get("DEFAULT", "ec2_url")
            elif self.contextualization_type == CONTEXT_TYPE_NIMBUS:
                self.nimbus_url_file = self.ini.get("DEFAULT", "nimbus_url_file")
            elif self.contextualization_type == CONTEXT_TYPE_OPENNEBULA:
                self.one_user_data_file = self.ini.get("DEFAULT", "one_user_data_file")
        else:
            raise ConfigError("configured context type not valid")

    def setup_logging(self):
        log_writer = None
        log_writer_class = self.ini.get("DEFAULT", "logger_class", None)
        if log_writer_class:
            if log_writer_class == "SyslogWriter":
                facility = self.ini.get("DEFAULT", "syslog_facility", None)
                priority = self.ini.get("DEFAULT", "syslog_priority", None)
                log_writer = SyslogWriter(facility=facility, priority=priority)
            elif log_writer_class == "ConsoleWriter":
                output = self.ini.get("DEFAULT", "console_output", "stdout")
                log_writer = ConsoleWriter(output=output)
            else:
                log_writer = FileWriter(self.home_dir)
        else:
            #log_writer = FileWriter(self.home_dir)
            log_writer = FileWriter('/var/log/glideinwms-pilot')
        self.log = Logger(log_writer)
        self.log.log_info("Pilot Launcher started...")

    def export_custom_env(self):
        """
        @returns: string containing the shell (sh, bash, etc) directives to 
                  export the environment variables
        """
        environment = ""
        try:
            env = self.get_custom_env()
            for option in env:
                environment += "export %s=%s; " % (option, env[option])
        except:
            # pylint: disable=W0702
            pass
        return environment

    def get_custom_env(self):
        """
        Returns a dictionary of the parent process environment plus the custom
        environment variables defined in the pilot config file.

        NOTE: All custom environment variable names will be upper cased.  The 
              values for the custom environment variables will not be modified.

        @returns: dictionary containing the desired process environment
        """
        environment = {}
        # inherit the parent process environment
        for var in os.environ.keys():
            environment[var] = os.environ[var]

        try:
            # add in the custom environment
            for option in self.cp.ini.options("CUSTOM_ENVIRONMENT"):
                environment[str(option).upper()] = self.ini.get("CUSTOM_ENVIRONMENT", option)
        except:
            # pylint: disable=W0702
            pass

        # Add in the pilot proxy
        environment["X509_USER_PROXY"] = self.proxy_file
        environment["HOME"] = self.home_dir
        environment["LOGNAME"] = self.glidein_user
        environment["SCRATCH"] = self.scratch_dir
        return environment
