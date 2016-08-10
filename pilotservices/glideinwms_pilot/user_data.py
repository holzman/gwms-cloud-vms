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

from contextualization_types import CONTEXT_TYPE_EC2
from contextualization_types import CONTEXT_TYPE_NIMBUS
from contextualization_types import CONTEXT_TYPE_OPENNEBULA
from contextualization_types import CONTEXT_TYPE_GCE

def smart_bool(s):
    if s is True or s is False:
        return s

    s = str(s).strip().lower()
    return not s in ['false', 'f', 'n', '0', '']


def opennebula_context_disk():
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


def one_ec2_user_data(contextfile):
    ec2_user_data = ''
    fd = None
    try:
        fd = open(contextfile, 'r')
        for line in fd.readlines():
            if line.startswith('EC2_USER_DATA='):
                ec2_user_data = line[(line.find('=')+1):].strip()
                break
    finally:
        if fd:
            fd.close()

    return ec2_user_data


class UserData(object):
    def __init__(self, config):
        self.config = config
        self.config.log.log_info('Created UserData object')

    def retrieve(self):
        context_type = self.config.contextualization_type.upper()
        self.config.log.log_info('Retrieving ec2_user_data for %s' % context_type)
        if context_type == CONTEXT_TYPE_EC2:
            self.ec2_retrieve_user_data()
        elif context_type == CONTEXT_TYPE_NIMBUS:
            self.nimbus_retrieve_user_data()
        elif context_type == CONTEXT_TYPE_OPENNEBULA:
            self.one_retrieve_user_data()
        elif context_type == CONTEXT_TYPE_GCE:
            self.gce_retrieve_user_data()


    def ec2_retrieve_user_data(self):
        try:
            user_data_url = self.config.ec2_url
            # touch the file so that it exists with proper permissions
            vm_utils.touch(self.config.userdata_file, mode=0600)
            # Now retrieve userdata into the file
            self.config.userdata_file, _ = urllib.urlretrieve(user_data_url, self.config.userdata_file)
        except Exception, ex:
            raise UserDataError("Error retrieving User Data(context type: EC2): %s\n" % str(ex))


    def one_retrieve_user_data(self):
        try:
            # Mount cdrom drive... OpenNebula contextualization unmounts it
            self.config.log.log_info('Mounting opennebula context disk %s' % opennebula_context_disk())
            mount_cmd = ["mount", "-t", "iso9660", opennebula_context_disk(), "/mnt"]
            subprocess.call(mount_cmd)

            # copy the OpenNebula userdata file
            self.config.log.log_info('Reading context file: %s' % self.config.one_user_data_file)
            vm_utils.touch(self.config.userdata_file, mode=0600)
            fd = open(self.config.userdata_file, 'w')
            user_data = base64.b64decode(one_ec2_user_data(self.config.one_user_data_file))
            self.config.log.log_info('Writing User data')
            # Only write to logs for debugging purposes.
            # Writing ec2_user_data to logs is a security issue.
            #self.config.log.log_info('Writing User data %s' % user_data)
            fd.write(user_data)
            fd.close()
            umount_cmd = ["umount", "/mnt"]
            subprocess.call(umount_cmd)
        except Exception, ex:
            raise UserDataError("Error retrieving User Data (context type: OPENNEBULA): %s\n" % str(ex))


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


    def gce_retrieve_user_data(self):
        try:
            metadata_url = self.config.metadata_url
            # touch the file so that it exists with proper permissions
            vm_utils.touch(self.config.userdata_file, mode=0600)
            # Now retrieve userdata 
            for attribute in ('glideinwms_metadata', 'glidein_credentials'):
                request = urllib2.Request('%s/%s' % (metadata_url, attribute),
                                          None, {'Metadata-Flavor': 'Google'})
                response = urllib2.urlopen(request)
                results = response.read()
                with open(self.config.userdata_file, 'a') as userdata_fd:
                    userdata_fd.write(results)
        except Exception, ex:
            raise UserDataError("Error retrieving User Data(context type: GCE): %s\n" % str(ex))


class GlideinWMSUserData(UserData):
    def __init__(self, config):
        super(GlideinWMSUserData, self).__init__(config)
        self.retrieve()
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
                log_msg = "Extracting ini file from the EC2_USER_DATA"
                self.config.log.log_info(self.template % log_msg)
                pilot_ini = base64.b64decode(userdata[0])
                vm_utils.touch(self.config.ini_file, mode=0600)
                ini_fd = open(self.config.ini_file, 'w')
                ini_fd.write(pilot_ini)
                ini_fd.close()

                ini = ini_handler.Ini(self.config.ini_file)

                # get the initial set of arguments for the glidein_startup.sh script
                log_msg = "Extracting arguments from the EC2_USER_DATA"
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
               
                log_msg = "Extracting pilot proxy: from the EC2_USER_DATA"
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

