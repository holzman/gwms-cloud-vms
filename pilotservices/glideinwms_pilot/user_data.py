import urllib
import base64
import tempfile
import subprocess
import glideinwms_tarfile
import vm_utils
import ini_handler

from errors import PilotError
from errors import UserDataError

from contextualization_types import CONTEXT_TYPE_EC2
from contextualization_types import CONTEXT_TYPE_NIMBUS

def smart_bool(s):
    if s is True or s is False:
        return s

    s = str(s).strip().lower()
    return not s in ['false', 'f', 'n', '0', '']


class UserData(object):
    def __init__(self, config):
        self.config = config

    def retrieve(self):
        context_type = self.config.contextualization_type.upper()
        if context_type == CONTEXT_TYPE_EC2:
            self.ec2_retrieve_user_data()
        elif context_type == CONTEXT_TYPE_NIMBUS:
            self.nimbus_retrieve_user_data()

    def ec2_retrieve_user_data(self):
        try:
            user_data_url = self.config.ec2_url
            # touch the file so that it exists with proper permissions
            vm_utils.touch(self.config.userdata_file, mode=0600)
            # Now retrieve userdata into the file
            self.config.userdata_file, _ = urllib.urlretrieve(user_data_url, self.config.userdata_file)
        except Exception, ex:
            raise UserDataError("Error retrieving User Data(context type: EC2): %s\n" % str(ex))

    def fermi_one_retrieve_user_data(self):
        try:
            # Mount cdrom drive... OpenNebula contextualization unmounts it
            mount_cmd = ["mount", "-t", "iso9660", "/dev/hdc", "/mnt"]
            subprocess.call(mount_cmd)

            # copy the OpenNebula userdata file
            vm_utils.cp(self.config.one_user_data_file, self.config.userdata_file)
        except Exception, ex:
            raise UserDataError("Error retrieving User Data (context type: FERMI-ONE): %s\n" % str(ex))

    def nimbus_retrieve_user_data(self):
        try:
            url_file = open(self.config.nimbus_url_file, 'r')
            url = url_file.read().strip()
            user_data_url = "%s/2007-01-19/user-data" % url
            self.config.userdata_file, _ = urllib.urlretrieve(user_data_url, self.config.userdata_file)
        except IOError, ex:
            raise UserDataError("Could not open Nimbus meta-data url file (context type: NIMBUS): %s\n" % str(ex))
        except Exception, ex:
            raise UserDataError("Error retrieving User Data (context type: NIMBUS): %s\n" % str(ex))

class GlideinWMSUserData(UserData):
    def __init__(self, config):
        super(GlideinWMSUserData, self).__init__(config)
        self.retrieve()

    def extract_user_data(self):
        """
        The user data has the following format:
        base64data####extra args
        OR
        ini file
        """
        delimiter = "####"

        try:
            # Split the user data
            userdata = open(self.config.userdata_file, 'r').read()

            if userdata.find(delimiter) > 0:
                userdata = userdata.split(delimiter)
                extra_args = userdata[1]
                extra_args = extra_args.replace("\\", "")

                # handle the tarball
                tardata = base64.b64decode(userdata[0])
                temp = tempfile.TemporaryFile()
                temp.write(tardata)
                temp.seek(0)
                tar = glideinwms_tarfile.open(fileobj=temp, mode="r:gz")
                for tarinfo in tar:
                    tar.extract(tarinfo, self.config.home_dir)
                    vm_utils.chmod(0400, tarinfo.name)

                # now that the tarball is extracted, we expect to have an x509 proxy
                # and an ini file waiting for us to use
                ini = ini_handler.Ini(self.config.ini_file)

                self.config.pilot_args = ini.get("glidein_startup", "args")
                self.config.factory_url = ini.get("glidein_startup", "webbase")
                proxy_file_name = ini.get("glidein_startup", "proxy_file_name")
                self.config.proxy_file = "%s/%s" % (self.config.home_dir, proxy_file_name)

                # now add the extra args to the main arg list
                self.config.pilot_args += " %s" % extra_args

                # check to see if the "don't shutdown" flag has been set
                self.config.disable_shutdown = False
                if ini.has_option("vm_properties", "disable_shutdown"):
                    self.config.disable_shutdown = smart_bool(ini.get("vm_properties", "disable_shutdown"))
                if ini.has_option("vm_properties", "home_dir"):
                    self.config.home_dir = ini.get("vm_properties", "home_dir")
                if ini.has_option("vm_properties", "max_lifetime"):
                    self.config.max_lifetime = ini.get("vm_properties", "max_lifetime")
            else:
                # the only thing expected here is a simple ini file containing:
                #
                # [vm_properties]
                # disable_shutdown = False

                fd = open(self.config.ini_file, 'w')
                fd.write(userdata)
                fd.close()

                ini = ini_handler.Ini(self.config.ini_file)

                if ini.has_option("vm_properties", "disable_shutdown"):
                    self.config.disable_shutdown = smart_bool(ini.get("vm_properties", "disable_shutdown"))
                    self.config.debug = True
                else:
                    raise UserDataError("Invalid ini file in user data.\nUser data contents:\n%s" % userdata)

        except Exception, ex:
            raise PilotError("Error extracting User Data: %s\n" % str(ex))

