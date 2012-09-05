import os
import pwd
import ConfigParser

from errors import ConfigError

from vm_utils import mkdir_p
from vm_utils import chown

from simple_logging import Logger
from simple_logging import FileWriter
from simple_logging import SyslogWriter
from simple_logging import ConsoleWriter

class Config(object):
    valid_context_types = ["EC2", "NIMBUS", "OPENNEBULA"]

    def __init__(self, config_ini="/etc/glideinwms/glidein-pilot.ini"):
        if not os.path.exists(config_ini):
            raise ConfigError("%s does not exist" % config_ini)
        self.cp = ConfigParser.ConfigParser()
        self.cp.read(config_ini)

        self.default_max_lifetime = self.cp_get("DEFAULTS", "default_max_lifetime", "172800") # 48 hours
        self.max_lifetime = self.default_max_lifetime  # can be overridden
        self.disable_shutdown = self.cp_getBoolean("DEFAULTS", "disable_shutdown", False)

        # glidein_startup.sh specific attributes
        self.factory_url = ""
        self.pilot_args = ""
        self.proxy_file = ""
        self.pilot_args = ""

    def setup(self):
        # must call setup_user to get the home directory for logging
        self.setup_user()
        self.setup_logging()
        self.setup_pilot_files()
        self.setup_contextualization()

    def setup_pilot_files(self):
        self.ini_file = "%s/glidein_userdata" % self.home_dir
        self.userdata_file = "%s/userdata_file" % self.home_dir

    def setup_contextualization(self):
        self.contextualization_type = self.cp_get("DEFAULTS", "contextualize_protocol")
        if self.contextualization_type in Config.valid_context_types:
            if self.contextualization_type == "EC2":
                self.ec2_url = self.cp_get("DEFAULTS", "ec2_url")
            elif self.contextualization_type == "NIMBUS":
                self.nimbus_url_file = self.cp_get("DEFAULTS", "nimbus_url_file")
            elif self.contextualization_type == "OPENNEBULA":
                self.one_user_data_file = self.cp_get("DEFAULTS", "one_user_data_file")
        else:
            raise ConfigError("configured context type not valid")

    def setup_user(self):
        self.glidein_user = self.cp_get("GLIDEIN_USER", "user_name")
        self.user_ids = self.cp_get("GLIDEIN_USER", "user_ids")
        # The home directory may or may not exist yet, if not, it will be created
        self.home_dir = self.cp_get("GLIDEIN_USER", "user_home")
        self.validate_user(self.glidein_user, self.user_ids)
        self.make_directories()

    def setup_logging(self):
        log_writer = None
        log_writer_class = self.cp_get("DEFAULTS", "logger_class", None)
        if log_writer_class:
            if log_writer_class == "SyslogWriter":
                facility = self.cp_get("DEFAULTS", "syslog_facility", None)
                priority = self.cp_get("DEFAULTS", "syslog_priority", None)
                log_writer = SyslogWriter(facility=facility, priority=priority)
            elif log_writer_class == "ConsoleWriter":
                output = self.cp_get("DEFAULTS", "console_output", "stdout")
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
            for option in self.cp.options("GRID_ENV"):
                environment += "export %s=%s; " % (str(option).upper(), self.cp.get("GRID_ENV", option))

            environment += "export GLIDEIN_Condor_IDS=%s;" % self.user_ids
            environment += "export X509_USER_PROXY=%s;" % self.proxy_file

        except:
            # pylint: disable=W0702
            pass
        return environment

    def get_grid_env(self):
        environment = {}
        try:
            # inherit the parent process environment
            for var in os.environ.keys():
                environment[var] = os.environ[var]

            # add in the "grid" specific environment
            for option in self.cp.options("GRID_ENV"):
                environment[str(option).upper()] = self.cp.get("GRID_ENV", option)

            environment["GLIDEIN_Condor_IDS"]= self.user_ids
            environment["X509_USER_PROXY"] = self.proxy_file

        except:
            # pylint: disable=W0702
            pass
        return environment

    def make_directories(self):
        # Make GLIDEIN_HOME
        mkdir_p(self.home_dir)
        chown(self.user_ids, self.home_dir)
        try:
            for option in self.cp.options("DIRECTORIES"):
                directory = self.cp.get("DIRECTORIES", option)
                mkdir_p(directory)
                chown(self.user_ids, directory)
        except:
            # pylint: disable=W0702
            pass

    def validate_user(self, username, user_ids):
        try:
            pwd_tuple = pwd.getpwnam(username)
            pw_uid = pwd_tuple[2]
            pw_gid = pwd_tuple[3]
            ids = user_ids.split(".")
            if not int(ids[0]) == int(pw_uid):
                msg = "User specified in configuration present on system, but "\
                      "the uids don't match. (system uid: %s, configured uid: "\
                      "%s" % (str(pw_uid), str(ids[0]))
                raise ConfigError(msg)
            if not int(ids[1]) == int(pw_gid):
                msg = "User specified in configuration present on system, but "\
                      "the gids don't match. (system gid: %s, configured gid: "\
                      "%s" % (str(pw_gid), str(ids[1]))
                raise ConfigError(msg)
        except:
            raise ConfigError("User specified in configuration not on system")


    def cp_get(self, section, option, default=""):
        """
        Helper function for ConfigParser objects which allows setting the default.

        ConfigParser objects throw an exception if one tries to access an option
        which does not exist; this catches the exception and returns the default
        value instead.

        @param section: Section of config parser to read
        @param option: Option in section to retrieve
        @param default: Default value if the section/option is not present.
        @returns: Value stored in CP for section/option, or default if it is not
            present.
        """
        if not isinstance(self.cp, ConfigParser.ConfigParser):
            raise RuntimeError('cp_get called without a proper cp as first arg')

        try:
            return self.cp.get(section, option)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return default

    def cp_getBoolean(self, section, option, default=True):
        """
        Helper function for ConfigParser objects which allows setting the default.
    
        If the cp object has a section/option of the proper name, and if that value
        has a 'y' or 't', we assume it's supposed to be true.  Otherwise, if it
        contains a 'n' or 'f', we assume it's supposed to be true.
        
        If neither applies - or the option doesn't exist, return the default
    
        @param section: Section of config parser to read
        @param option: Option in section to retrieve
        @param default: Default value if the section/option is not present.
        @returns: Value stored in CP for section/option, or default if it is not
            present.
        """
        val = str(self.cp_get(section, option, default)).lower()
        if val.find('t') >= 0 or val.find('y') >= 0 or val.find('1') >= 0:
            return True
        if val.find('f') >= 0 or val.find('n') >= 0 or val.find('0') >= 0:
            return False
        return default