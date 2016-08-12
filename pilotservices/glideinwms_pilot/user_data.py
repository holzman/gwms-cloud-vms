import urllib
import urllib2
import subprocess
import vm_utils
import ini_handler
import platform
import string
import re
import gzip
import os
import base64

from errors import PilotError
from errors import UserDataError

from contextualization_types import CONTEXTS

def smart_bool(s):
    if s is True or s is False:
        return s

    s = str(s).strip().lower()
    return not s in ['false', 'f', 'n', '0', '']


class MetadataManager(object):
    """
    Base class responsible for interacting with the metadata service
    """

    def __init__(self, config):
        self.config = config
        self.userdata_attributes = (
            'glideinwms_metadata',
            'glidein_credentials'
        )
        self.config.log.log_info('Created MetadataManager object for contextualize_protocol %s' % self.config.contextualization_type)


    def write_userdata_file(self):
        # Retrieve the userdata in string format
        userdata = self.retrieve_instance_userdata()
        # Remove the userdata_attributes from the string
        for attribute in self.userdata_attributes:
            userdata = userdata.replace('%s='%attribute, '')
        try:
            with open(self.config.userdata_file, 'w') as fd:
                fd.write(userdata)
        except Exception, ex:
            raise UserDataError("Error writing to userdata file %s: %s\n" % (self.config.userdata_file, str(ex)))


    def retrieve_instance_userdata(self):
        raise NotImplementedError('Implementation for contextualize_protocol %s not available' % self.config.contextualization_type)


class EC2MetadataManager(MetadataManager):
    """
    Class to interact with the EC2 metadata service
    """

    def retrieve_instance_userdata(self):
        self.config.log.log_info('Retrieving instance_userdata for contextualize_protocol %s' % self.config.contextualization_type)
        try:
            # touch the file so that it exists with proper permissions
            vm_utils.touch(self.config.userdata_file, mode=0600)
            # Now retrieve userdata into the file
            request = urllib2.Request(self.config.instance_userdata_url)
            response = urllib2.urlopen(request)
            userdata = response.read()
        except Exception, ex:
            raise UserDataError("Error retrieving instance userdata contextualize_protocol %s: %s\n" % (self.config.contextualization_type, str(ex)))
        return userdata


class OneMetadataManager(MetadataManager):
    """
    Class to interact with the OpenNebula metadata service
    """

    def retrieve_instance_userdata(self):
        self.config.log.log_info('Retrieving instance_userdata for contextualize_protocol %s' % self.config.contextualization_type)
        context_disk = self.one_context_disk()
        try:
            # Mount cdrom drive... OpenNebula contextualization unmounts it
            self.config.log.log_info('Mounting opennebula context disk %s' % context_disk)
            mount_cmd = ["mount", "-t", "iso9660", context_disk, "/mnt"]
            subprocess.call(mount_cmd)

            # copy the OpenNebula userdata file
            self.config.log.log_info('Reading context file: %s' % self.config.one_userdata_file)
            vm_utils.touch(self.config.userdata_file, mode=0600)
            userdata = base64.b64decode(self.read_one_userdata())
            umount_cmd = ["umount", "/mnt"]
            subprocess.call(umount_cmd)
        except Exception, ex:
            raise UserDataError("Error retrieving instance userdata contextualize_protocol %s: %s\n" % (self.config.contextualization_type, str(ex)))
        return userdata


    def one_context_disk(self):
        context_disk = "/dev/sr0"
        distname_pattern = [
            'red hat*',
            'redhat*',
            'scientific linux*',
            'centos*',
        ]

        version_map = {
            '5': '/dev/hdc',
            '6': '/dev/sr0',
            '7': '/dev/sr0',
        }

        try:
            distro = platform.linux_distribution()
        except:
            distro = platform.dist()

        regex = "(" + ")|(".join(distname_pattern) + ")"
        if re.match(regex, distro[0].lower()):
            context_disk = version_map.get(distro[1][0], context_disk)

        return context_disk


    def read_one_userdata(self):
        userdata = ''
        with open(self.config.one_userdata_file, 'r') as fd:
            for line in fd.readlines():
                if line.startswith('EC2_USER_DATA='):
                    userdata = line[(line.find('=')+1):].strip()
                    break
        return userdata


class NimbusMetadataManager(EC2MetadataManager):
    """
    Class to interact with the Nimbus metadata service
    """
    pass


class GCEMetadataManager(MetadataManager):
    """
    Class to interact with the Nimbus metadata service
    """

    def retrieve_instance_userdata(self):
        self.config.log.log_info('Retrieving instance_userdata for contextualize_protocol %s' % self.config.contextualization_type)
        try:
            userdata_base_url = self.config.instance_userdata_url
            # touch the file so that it exists with proper permissions
            vm_utils.touch(self.config.userdata_file, mode=0600)
            # Now retrieve userdata 
            userdata = {}
            for attribute in self.userdata_attributes:
                request = urllib2.Request('%s/%s' % (userdata_base_url, attribute),
                                          None, {'Metadata-Flavor': 'Google'})
                response = urllib2.urlopen(request)
                userdata[attribute] = response.read()
        except Exception, ex:
            raise UserDataError("Error retrieving instance userdata contextualize_protocol %s: %s\n" % (self.config.contextualization_type, str(ex)))
        return userdata['glideinwms_metadata'] + userdata['glidein_credentials']


class GlideinWMSUserData:
    def __init__(self, config):
        self.config = config
        md_manager = get_metadata_manager(config)
        md_manager.write_userdata_file()
        self.template = "GlideinWMSUserData :: %s"

    def extract_user_data(self):
        """
        The user data has the following format:
        pilot ini file####extra args####compressed glidein proxy
        OR
        ini file
        """
        delimiter = "####"

        try:
            # Split the user data
            userdata = open(self.config.userdata_file, 'r').read()

            if userdata.find(delimiter) > 0:
                log_msg = "Delimiter found.  Assuming we have been launched from glideinWMS"
                self.config.log.log_info(self.template % log_msg)

                # split userdata into usable chunks
                userdata = userdata.split(delimiter)

                # get and process the pilot ini file
                log_msg = "Extracting ini file from the USERDATA"
                self.config.log.log_info(self.template % log_msg)
                pilot_ini = base64.b64decode(userdata[0])
                vm_utils.touch(self.config.ini_file, mode=0600)
                ini_fd = open(self.config.ini_file, 'w')
                ini_fd.write(pilot_ini)
                ini_fd.close()

                ini = ini_handler.Ini(self.config.ini_file)

                # get the initial set of arguments for the glidein_startup.sh script
                log_msg = "Extracting arguments from the USERDATA"
                self.config.log.log_info(self.template % log_msg)
                self.config.pilot_args = ini.get("glidein_startup", "args")
                log_msg = "pilot_args : %s" % self.config.pilot_args
                self.config.log.log_info(self.template % log_msg)

                # set the factory location so that we can download glidein_startup.sh
                self.config.factory_url = ini.get("glidein_startup", "webbase")
                log_msg = "factory_url : %s" % self.config.factory_url
                self.config.log.log_info(self.template % log_msg)

                # now get and add the extra args to the main arg list
                extra_args = userdata[1]
                extra_args = extra_args.replace("\\", "")

                # add the extra arguments to the arg list for glidein_startup.sh
                self.config.pilot_args += " %s" % extra_args
                log_msg = "Full config.pilot_args : %s" % self.config.pilot_args
                self.config.log.log_info(self.template % log_msg)

                # check to see if the "don't shutdown" flag has been set
                self.config.disable_shutdown = False
                if ini.has_option("vm_properties", "disable_shutdown"):
                    self.config.disable_shutdown = smart_bool(ini.get("vm_properties", "disable_shutdown"))
                    log_msg = "config.disable_shutdown : %s" % self.config.disable_shutdown
                    self.config.log.log_info(self.template % log_msg)

                # set the max_lifetime if available
                if ini.has_option("vm_properties", "max_lifetime"):
                    self.config.max_lifetime = ini.get("vm_properties", "max_lifetime")
                    log_msg = "config.max_lifetime : %s" % self.config.max_lifetime
                    self.config.log.log_info(self.template % log_msg)

                # get the proxy file name from the ini file
                proxy_file_name = ini.get("glidein_startup", "proxy_file_name")
                log_msg = "proxy_file_name : %s" % proxy_file_name
                self.config.log.log_info(self.template % log_msg)

                # set the full path to the proxy.  The proxy will be written to this path
                self.config.proxy_file = "%s/%s" % (self.config.home_dir, proxy_file_name)
                log_msg = "config.proxy_file : %s" % self.config.proxy_file
                self.config.log.log_info(self.template % log_msg)

                # Get the compressed proxy and write it to a tmp file.
                # The tmp file name is completely predictable, but this
                # isn't an interactive node and the lifetime of the node is
                # very short so the risk of attack on this vector is minimal
                # HTCondor will attach proxy file passed using the 
                # ec2_userdata_file at the end. Accessing it as the last
                # token rather than a fixed positional token gives us
                # the flexibility to append custom info after the second
                # token, i.e the extra args token
               
                log_msg = "Extracting pilot proxy: from the USERDATA"
                self.config.log.log_info(self.template % log_msg)
                compressed_proxy = base64.b64decode(userdata[-1])
                fd = os.open("%s.gz" % self.config.proxy_file,
                             os.O_CREAT|os.O_WRONLY, 0600)
                try:
                    os.write(fd, compressed_proxy)
                finally:
                    os.close(fd)

                # modified by Anthony Tiradani from tmp to gz
                proxy_fd = gzip.open("%s.gz" % self.config.proxy_file, 'rb')
                proxy_content = proxy_fd.read()
                proxy_fd.close()

                fd = os.open(self.config.proxy_file, os.O_CREAT|os.O_WRONLY, 0600)
                try:
                    os.write(fd, proxy_content)
                finally:
                    os.close(fd)
            else:
                # the only thing expected here is a simple ini file containing:
                #
                # [vm_properties]
                # disable_shutdown = False
                log_msg = "Delimiter not found.  Assuming we have been launched manually"
                self.config.log.log_info(self.template % log_msg)

                vm_utils.touch(self.config.ini_file, mode=0600)
                fd = open(self.config.ini_file, 'w')
                fd.write(userdata)
                fd.close()

                ini = ini_handler.Ini(self.config.ini_file)
                contents = ini.dump()
                log_msg = "Ini file contents:\n%s" % contents
                self.config.log.log_info(self.template % log_msg)

                if ini.has_option("vm_properties", "disable_shutdown"):
                    self.config.disable_shutdown = smart_bool(ini.get("vm_properties", "disable_shutdown"))
                    self.config.debug = True
                elif ini.has_option("DEFAULT", "disable_shutdown"):
                    self.config.disable_shutdown = smart_bool(ini.get("vm_properties", "disable_shutdown"))
                    self.config.debug = True
                else:
                    raise UserDataError("Invalid ini file in user data.\nUser data contents:\n%s" % userdata)

        except Exception, ex:
            raise PilotError("Error extracting User Data: %s\n" % str(ex))


################################################################################
# Helper functions that do not need to change when supporting new context
# Assumes certain class naming conventions
################################################################################

def get_metadata_manager(config):
    """
    Do a minimal read of the config to identify context type and create
    config object for appropriate context
    """

    context = config.contextualization_type
    metadata_manager_class = '%sMetadataManager' % context
    if not (metadata_manager_class in globals()):
        raise NotImplementedError('Implementation for %s not available' % context)
    return (globals()[metadata_manager_class])(config)
