#!/usr/bin/python

import signal
import urllib

import glideinwms_pilot.version_info
import glideinwms_pilot.vm_utils

from glideinwms_pilot.glideinwms_email import send_logs
from glideinwms_pilot.errors import PilotError
from glideinwms_pilot.errors import TimeoutError
from glideinwms_pilot.simple_logging import Logger
from glideinwms_pilot.user_data import retrieve_user_data
from glideinwms_pilot.user_data import extract_user_data

# Pilot Environment class
class PilotEnvironment(dict):
    """
    Customized dictionary for defining the environment that will be used for
    launching the glideinWMS pilot
    """
    def __init__(self, config):
        dict.__init__(self)

        self["OSG_GRID"] = "/usr/local/osg/wn_client/current"
        self["OSG_APP"] = "/mnt/app"
        self["OSG_DATA"] = "/mnt/data"
        self["VOMS_PROXY_INFO_DONT_VERIFY_AC"] = "1"
        self["GLIDEIN_Condor_IDS"] = config.user_ids
        self["X509_USER_PROXY"] = config.proxy_file

    def export(self):
        environment = ""
        try:
            for key, value in self.items():
                environment += "export %s=%s; " % (key, value)
        except:
            pass
        return environment

    def __repr__(self): return self.export()

class Config(object):
    def __init__(self):
        self.version = glideinwms_pilot.version_info.SERVICE_VERSION
        self.release = glideinwms_pilot.version_info.SERVICE_RELEASE
        self.glidein_user = "glidein_pilot"
        self.user_ids = "91234.91234"
        self.home_dir = "/mnt/%s" % self.glidein_user
        self.ini_file = "%s/glidein_userdata" % self.home_dir
        self.userdata_file = "%s/userdata_file" % self.home_dir

        self.default_max_lifetime = 172800 # 48 hours
        self.max_lifetime = self.default_max_lifetime  # can be overriden
        self.disable_shutdown = False

        self.contextualization_type = glideinwms_pilot.version_info.CONTEXTUALIZE_TYPE
        self.ec2_url = "http://169.254.169.254/latest/user-data"

        self.log = Logger(self.home_dir)

        self.admin_email = ""
        self.debug = False

        # glidein_startup.sh specific attributes
        self.factory_url = ""
        self.pilot_args = ""
        self.proxy_file = ""
        self.pilot_args = ""

    def __str__(self):
        repr_str = """Config Object %s.%s
    glidein_user: %s
    user_ids: %s
    home_dir: %s
    ini_file: %s
    userdata_file: %s
    default_max_lifetime: %s
    max_lifetime: %s
    disable_shutdown: %s
    contextualization_type: %s
    admin_email: %s
    debug: %s
    factory_url: %s
    pilot_args: %s
    proxy_file: %s
"""
        return repr_str % (str(self.version), str(self.release),
                str(self.glidein_user), str(self.user_ids), str(self.home_dir),
                str(self.ini_file), str(self.userdata_file), str(self.default_max_lifetime),
                str(self.max_lifetime), str(self.disable_shutdown),
                str(self.contextualization_type), str(self.admin_email),
                str(self.debug), str(self.factory_url), str(self.pilot_args),
                str(self.proxy_file))


def shutdown_ami(config):
    disable_shutdown = config.disable_shutdown
    if disable_shutdown:
        config.log.logit("Shutdown has been disabled")
    else:
        if config.email_logs:
            send_logs(config)
        glideinwms_pilot.vm_utils.shutdown_vm()

def define_cmd(config):
    try:
        pilot_env = PilotEnvironment(config)
        cmd = 'su %s -c "%s cd %s; sh glidein_startup.sh %s"' % (config.glidein_user, pilot_env.export(), config.home_dir, config.pilot_args)
    except Exception, ex:
        raise PilotError("Error defining pilot launch command: %s\n" % str(ex))

    return cmd

def retrieve_glidein_startup(config):
    try:
        url = "%s/glidein_startup.sh" % config.factory_url
        script = "%s/glidein_startup.sh" % config.home_dir
        script, _ = urllib.urlretrieve(url, script)
    except Exception, ex:
        raise PilotError("Error retrieving glidein_startup.sh: %s\n" % str(ex))

def handler_max_lifetime(signum, frame):
    raise TimeoutError("Max lifetime has been exceeded, shutting down...")

def main():
    """
        Perform all the work necessary to launch a glideinWMS pilot which will
        attempt to connect back to the user pool.

        1)  daemonize this script.  This script is lauched via the *nix service
            mechanisms.  We don't want to make it wait forever and we don't
            want it to be attached to a console.
        2)  Get the user data that was passed to the AMI - Currently it is a
            tarball.
        3)  untar the tarball.  The tarball will contain a proxy, the
            glidein_startup.sh script and an ini file containing all the extra
            information needed
        4)  read the ini file
        5)  get the arguments for the glidein_startup.sh script
        6)  create an environment string to pass with final command
        7)  launch the glidein pilot with the appropriate environment
    """
    glideinwms_pilot.vm_utils.daemonize("/tmp/pilot.pid")

    config = Config()
    # Make GLIDEIN_HOME
    glideinwms_pilot.vm_utils.mkdir_p(config.home_dir)
    glideinwms_pilot.vm_utils.chown(config.user_ids, config.home_dir)

    config.log.logit("Pilot Launcher started...")
    config.log.logit("Pilot launcher has already been daemonized...")
    config.log.logit("Home directory (%s) created." % config.home_dir)

    try:
        # get the user data - should be a tar file
        config.log.logit("Retrieving user data")
        retrieve_user_data(config)

        # untar the user data
        config.log.logit("Extracting user data")
        extract_user_data(config)

        # Set up a safety switch that will automatically terminate this VM if
        # something went wrong and it runs for longer than config.max_lifetime
        signal.signal(signal.SIGALRM, handler_max_lifetime)
        config.log.logit("Setting alarm to %s seconds" % config.max_lifetime)
        signal.alarm(int(config.max_lifetime))

        # ensure that the proxy is owned by the correct user
        config.log.logit("Chowning the VO proxy")
        glideinwms_pilot.vm_utils.chown(config.user_ids, config.proxy_file)

        # get the glidein_startup.sh script
        config.log.logit("Retrieving glidein_startup.sh")
        retrieve_glidein_startup(config)

        # generate the pilot launch command
        config.log.logit("Generating the pilot launch command")
        cmd = define_cmd(config)

        # launch the pilot
        config.log.logit("About to execute command: \n%s" % cmd)
        config.log.logit("===== BEGIN LOGGING EXTERNAL (non-formatted) DATA ======")

        glideinwms_pilot.vm_utils.launch_pilot(cmd, config.log.get_logfile_fd(), config.log.get_logfile_fd())

        config.log.logit("===== END LOGGING EXTERNAL (non-formatted) DATA ======")

    except PilotError, ex:
        message = "A PilotError has occured: %s" % str(ex)
        config.log.log_err(message)
    except TimeoutError, ex:
        message = "Timeout Error occurred.  The Pilot has been running for more than %s seconds" % str(config.max_lifetime)
        config.log.log_err(message)
    except Exception, ex:
        config.log.log_err("Error launching pilot: %s" % str(ex))

    # turn off the alarm signal since the very next step is to shutdown the VM anyway
    signal.alarm(0)

    # need to figure out how to set up glidein_pilot user to be able to sudo
    shutdown_ami(config)

if __name__ == "__main__":
    main()
