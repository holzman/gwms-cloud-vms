import urllib
import base64
import tempfile
import subprocess
import ConfigParser
import glideinwms_tarfile
import vm_utils

from errors import PilotError
from errors import UserDataError

def smart_bool(s):
    if s is True or s is False:
        return s

    s = str(s).strip().lower()
    return not s in ['false', 'f', 'n', '0', '']

def retrieve_user_data(config):
    if config.contextualization_type.upper() == "EC2":
        return ec2_retrieve_user_data(config)
    elif config.contextualization_type.upper() == "FERMI-ONE":
        return fermi_one_retrieve_user_data(config)
    elif config.contextualization_type.upper() == "NIMBUS":
        return nimbus_retrieve_user_data(config)

def ec2_retrieve_user_data(config):
    try:
        config.userdata_file, _ = urllib.urlretrieve(config.ec2_url, config.userdata_file)
    except Exception, ex:
        raise UserDataError("Error retrieving User Data(context type: EC2): %s\n" % str(ex))

def fermi_one_retrieve_user_data(config):
    try:
        # Mount cdrom drive... OpenNebula contextualization unmounts it
        mount_cmd = ["mount", "-t", "iso9660", "/dev/hdc", "/mnt"]
        subprocess.call(mount_cmd)
         
        # copy the OpenNebula userdata file
        vm_utils.cp(config.one_user_data_file, config.userdata_file)
    except Exception, ex:
        raise UserDataError("Error retrieving User Data (context type: FERMI-ONE): %s\n" % str(ex))

def nimbus_retrieve_user_data(config):
    try:
        url_file = open(config.nimbus_url_file, 'r')
        url = url_file.read().strip()
        user_data_url = "%s/2007-01-19/user-data" % url
        config.userdata_file, _ = urllib.urlretrieve(user_data_url, config.userdata_file)
    except IOError, ex:
        raise UserDataError("Could not open Nimbus meta-data url file (context type: NIMBUS): %s\n" % str(ex))
    except Exception, ex:
        raise UserDataError("Error retrieving User Data (context type: NIMBUS): %s\n" % str(ex))

def extract_user_data(config):
    delimiter = "####"
    # need to add max lifetime
    # need to add alternate formats
    # need to be more robust
    try:
        # The user data has the following format:
        #     base64data####extra args
        # OR
        #     ini file

        # Split the user data
        userdata = open(config.userdata_file, 'r').read()
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
                tar.extract(tarinfo, config.home_dir)

            # now that the tarball is extracted, we expect to have an x509 proxy
            # and an ini file waiting for us to use
            cp = ConfigParser.ConfigParser()
            cp.read(config.ini_file)

            config.pilot_args = cp.get("glidein_startup", "args")
            config.factory_url = cp.get("glidein_startup", "webbase")
            proxy_file_name = cp.get("glidein_startup", "proxy_file_name")
            config.proxy_file = "%s/%s" % (config.home_dir, proxy_file_name)

            # now add the extra args to the main arg list
            config.pilot_args += " %s" % extra_args

            # check to see if the "don't shutdown" flag has been set
            config.disable_shutdown = False
            if cp.has_option("vm_properties", "disable_shutdown"):
                config.disable_shutdown = smart_bool(cp.get("vm_properties", "disable_shutdown"))
            if cp.has_option("vm_properties", "home_dir"):
                config.home_dir = cp.get("vm_properties", "home_dir")
            if cp.has_option("vm_properties", "max_lifetime"):
                config.max_lifetime = cp.get("vm_properties", "max_lifetime")
        else:
            # the only thing expected here is a simple ini file containing:
            #
            # [vm_properties]
            # disable_shutdown = False

            fd = open(config.ini_file, 'w')
            fd.write(userdata)
            fd.close()

            cp = ConfigParser.ConfigParser()
            cp.read(config.ini_file)

            if cp.has_option("vm_properties", "disable_shutdown"):
                config.disable_shutdown = smart_bool(cp.get("vm_properties", "disable_shutdown"))
                config.debug = True
            else:
                raise UserDataError("Invalid ini file in user data.\nUser data contents:\n%s" % userdata)

    except Exception, ex:
        raise PilotError("Error extracting User Data: %s\n" % str(ex))

