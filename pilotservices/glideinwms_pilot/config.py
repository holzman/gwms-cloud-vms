import os
import ini_handler

from errors import ConfigError

from simple_logging import Logger
from simple_logging import FileWriter
from simple_logging import SyslogWriter
from simple_logging import ConsoleWriter

from contextualization_types import CONTEXTS
from contextualization_types import is_context_valid
from contextualization_types import valid_contexts

class Config(object):
    """
    Base class for the handling configuration
    Derived class needs to implement contextualization logic
    """

    def __init__(self, config_ini="/etc/glideinwms/glidein-pilot.ini"):
        if not os.path.exists(config_ini):
            raise ConfigError("%s does not exist" % config_ini)

        self.ini = ini_handler.Ini(config_ini)

        self.contextualization_type = self.ini.get("DEFAULT", "contextualize_protocol")
        if self.contextualization_type is not None:
            self.contextualization_type = self.contextualization_type.upper()
        self.default_max_lifetime = self.ini.get("DEFAULT", "default_max_lifetime", "172800") # 48 hours
        self.max_lifetime = self.default_max_lifetime
        self.disable_shutdown = self.ini.getBoolean("DEFAULT", "disable_shutdown", False)
        self.max_script_runtime = self.ini.get("DEFAULT", "max_script_runtime", "60")

        self.pre_script_dir = self.ini.get("DIRECTORIES", "pre_script_dir", "/usr/libexec/glideinwms_pilot/PRE")
        self.post_script_dir = self.ini.get("DIRECTORIES", "post_script_dir", "/usr/libexec/glideinwms_pilot/POST")

        self.glidein_user = "glidein_pilot"
        # home directory is created by the rpm
        self.home_dir = os.path.expanduser('~%s' % self.glidein_user)
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


    def validate_contextualization(self):
        self.log.log_info("Contextualization Type identified as: %s" % self.contextualization_type)
        if not is_context_valid(self.contextualization_type):
            raise ConfigError("context_type %s not in the supported list %s" % (self.contextualization_type, valid_contexts()))


    def setup_contextualization(self):
        raise NotImplementedError('Implementation for contextualize_protocol %s not available' % self.contextualization_type)


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
            for option in self.ini.cp.options("CUSTOM_ENVIRONMENT"):
                environment[str(option).upper()] = self.ini.get("CUSTOM_ENVIRONMENT", option)
        except:
            # pylint: disable=W0702
            pass

        # Add in the pilot proxy
        environment["X509_USER_PROXY"] = self.proxy_file
        #environment["HOME"] = self.home_dir
        #environment["LOGNAME"] = self.glidein_user
        environment["SCRATCH"] = self.scratch_dir
        return environment


class EC2Config(Config):
    """
    Class for AWS EC2 pilot config
    """

    def setup_contextualization(self):
        self.validate_contextualization()
        self.metadata_service = self.ini.get("DEFAULT", "metadata_service")
        self.instance_metadata_url = self.ini.get("DEFAULT", "instance_metadata_url")
        self.instance_userdata_url = self.ini.get("DEFAULT", "instance_userdata_url")


class NimbusConfig(Config):
    """
    Class for Nimbus pilot config
    """

    def setup_contextualization(self):
        self.validate_contextualization()
        self.metadata_service_url_file = self.ini.get("DEFAULT", "metadata_service_url_file")
        with open(self.metadata_service_url_file, 'r') as fd:
            url = fd.read().strip()
        self.metadata_service = url
        self.instance_userdata_url = '%s/current/user-data' % url


class OneConfig(Config):
    """
    Class for OpenNebula pilot config
    """

    def setup_contextualization(self):
        self.validate_contextualization()
        self.one_userdata_file = self.ini.get("DEFAULT", "one_userdata_file")


class GCEConfig(EC2Config):
    """
    Class for Google Compute Engine pilot config
    Currently with unified config, config objects between ec2 and gce are
    identical
    """
    pass


###############################################################################
# Helper functions that do not need to change when supporting new context
# Assumes certain class naming conventions
###############################################################################

def get_config(config_ini='/etc/glideinwms/glidein-pilot.ini'):
    """
    Do a minimal read of the config to identify context type and create
    config object for appropriate context
    """

    if not os.path.exists(config_ini):
        raise ConfigError("%s does not exist" % config_ini)

    ini = ini_handler.Ini(config_ini)
    context_type = ini.get("DEFAULT", "contextualize_protocol")

    context = CONTEXTS.get(context_type)
    if context is None:
        raise ConfigError("context_type %s not in the supported list %s" % (context_type, valid_contexts()))
    config_class = '%sConfig' % context
    if not (config_class in globals()):
        raise NotImplementedError('Implementation for %s not available' % context)
    return (globals()[config_class])(config_ini=config_ini)
