import os
import pwd
import ConfigParser
import vm_utils

from errors import ConfigError
from simple_logging import Logger

class Config(object):
    def __init__(self, config_ini="/etc/glideinwms/glidein-pilot.ini"):
        self.config_ini = config_ini
        if not os.path.exists(self.config_ini):
            raise ConfigError("%s does not exist" % self.config_ini)
        self.cp = ConfigParser.ConfigParser()
        self.cp.read(self.config_ini)

        self.glidein_user = self.cp_get("GLIDEIN_USER", "user_name")
        self.user_ids = self.cp_get("GLIDEIN_USER", "user_ids")
        # The home directory may or may not exist yet, if not, it will be created
        self.home_dir = self.cp_get("GLIDEIN_USER", "user_home")
        self.validate_user(self.glidein_user, self.user_ids)

        self.default_max_lifetime = self.cp_get("DEFAULTS", "default_max_lifetime", "172800") # 48 hours
        self.max_lifetime = self.default_max_lifetime  # can be overriden
        self.disable_shutdown = False

        self.valid_context_types = ["EC2", "NIMBUS", "OPENNEBULA"]
        self.contextualization_type = self.cp_get("DEFAULTS", "contextualize_protocol")
        if self.contextualization_type in self.valid_context_types:
            if self.contextualization_type == "EC2":
                self.ec2_url = self.cp_get("DEFAULTS", "ec2_url")
            elif self.contextualization_type == "NIMBUS":
                self.nimbus_url_file = self.cp_get("DEFAULTS", "nimbus_url_file")
            elif self.contextualization_type == "OPENNEBULA":
                self.one_user_data_file = self.cp_get("DEFAULTS", "one_user_data_file")
        else:
            raise ConfigError("configured context type not valid")

        self.ini_file = "%s/glidein_userdata" % self.home_dir
        self.userdata_file = "%s/userdata_file" % self.home_dir

        self.log = Logger(self.home_dir)
        self.log.logit("Pilot Launcher started...")

        self.admin_email = ""
        self.debug = False

        # glidein_startup.sh specific attributes
        self.factory_url = ""
        self.pilot_args = ""
        self.proxy_file = ""
        self.pilot_args = ""

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

    def make_directories(self):
        # Make GLIDEIN_HOME
        vm_utils.mkdir_p(self.home_dir)
        vm_utils.chown(self.user_ids, self.home_dir)
        self.log.logit("Home directory (%s) created." % self.home_dir)
        try:
            for option in self.cp.options("DIRECTORIES"):
                directory = self.cp.get("DIRECTORIES", option)
                vm_utils.mkdir_p(directory)
                vm_utils.chown(self.user_ids, directory)
                self.log.logit("Created directory (%s)." % directory)
        except:
            # pylint: disable=W0702
            pass

    def validate_user(self, username, user_ids):
        try:
            pwd_tuple = pwd.getpwnam(username)
            pw_uid = pwd_tuple[2]
            pw_gid = pwd_tuple[3]
            ids = user_ids.split(".")
            if not ids[0] == pw_uid:
                msg = "User specified in configuration present on system, but "\
                      "the uids don't match. (system uid: %s, configured uid: "\
                      "%s" % (str(pw_uid), str(ids[0]))
                raise ConfigError(msg)
            if not ids[1] == pw_gid:
                msg = "User specified in configuration present on system, but "\
                      "the gids don't match. (system gid: %s, configured gid: "\
                      "%s" % (str(pw_gid), str(ids[1]))
                raise ConfigError(msg)
        except:
            raise ConfigError("User specified in configuration not on system")


    def cp_get(self, cp, section, option, default=""):
        """
        Helper function for ConfigParser objects which allows setting the default.

        ConfigParser objects throw an exception if one tries to access an option
        which does not exist; this catches the exception and returns the default
        value instead.

        @param cp: ConfigParser object
        @param section: Section of config parser to read
        @param option: Option in section to retrieve
        @param default: Default value if the section/option is not present.
        @returns: Value stored in CP for section/option, or default if it is not
            present.
        """
        if not isinstance(cp, ConfigParser.ConfigParser):
            raise RuntimeError('cp_get called without a proper cp as first arg')

        try:
            return cp.get(section, option)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return default
