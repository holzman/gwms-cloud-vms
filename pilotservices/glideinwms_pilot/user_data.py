import urllib
import base64
import tempfile
import ConfigParser
import glideinwms_tarfile

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

def ec2_retrieve_user_data(config):
    try:
        config.userdata_file, _ = urllib.urlretrieve(config.ec2_url, config.userdata_file)
    except Exception, ex:
        raise PilotError("Error retrieving User Data: %s\n" % str(ex))


def extract_user_data(config):
    if config.contextualization_type.upper() == "EC2":
        return ec2_extract_user_data(config)

def ec2_extract_user_data(config):
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
            if cp.has_option("vm_properties", "contextualization_type"):
                config.contextualization_type = cp.get("vm_properties", "contextualization_type")
        else:
            # the only thing expected here is a simple ini file containing:
            #
            # [VM_Properties]
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

