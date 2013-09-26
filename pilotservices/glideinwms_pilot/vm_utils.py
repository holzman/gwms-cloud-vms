import os
import sys
import errno
import pwd
import socket
import shutil
import grp
import stat
import time

from errors import PilotError
from errors import ScriptError
from process_handling import execute_cmd

#### BEGIN DAEMON CODE ####

# Copyright: Copyright (C) 2005 Chad J. Schroeder
# This script is one I've found to be very reliable for creating daemons.
# The license is permissible for redistribution.
# I've modified it slightly for my purposes.  -BB
UMASK = 0
WORKDIR = "/"

if (hasattr(os, "devnull")):
    REDIRECT_TO = os.devnull
else:
    REDIRECT_TO = "/dev/null"

def daemonize(pidfile):
    """Detach a process from the controlling terminal and run it in the
    background as a daemon.

    The detached process will return; the process controlling the terminal
    will exit.

    If the fork is unsuccessful, it will raise an exception; DO NOT CAPTURE IT.
    """
    try:
        pid = os.fork()
    except OSError, ex:
        raise Exception("%s [%d]" % (ex.strerror, ex.errno))

    if (pid == 0):       # The first child.
        os.setsid()
        try:
            pid = os.fork()        # Fork a second child.
        except OSError, ex:
            raise Exception("%s [%d]" % (ex.strerror, ex.errno))

        if (pid == 0):    # The second child.
            os.chdir(WORKDIR)
            os.umask(UMASK)
            for i in range(3):
                os.close(i)
            os.open(REDIRECT_TO, os.O_RDWR|os.O_CREAT) # standard input (0)
            os.dup2(0, 1)                        # standard output (1)
            os.dup2(0, 2)                        # standard error (2)
            try:
                fp = open(pidfile, 'w')
                fp.write(str(os.getpid()))
                fp.close()
            except:
                # pylint: disable=W0702
                pass
        else:
            # Exit parent (the first child) of the second child.
            os._exit(0) # pylint: disable=W0212
    else:
        # Exit parent of the first child.
        os._exit(0) # pylint: disable=W0212

#### END DAEMON CODE ####

def shutdown_vm(pid_file):
    # remove the pid file
    if os.path.exists(pid_file):
        rm(pid_file)

    # execute the shutdown command
    os.environ["PATH"] = os.environ["PATH"] + ":/sbin:/usr/sbin"
    cmd = "sudo shutdown -h now"
    os.system(cmd)

def drop_privs(username):
    # check if we are root.  If we are, drop privileges
    start_uid = os.getuid()
    if start_uid == 0:
        # NOTE:  Must set gid first or you will get an 
        #        "Operation not permitted" error
        pwd_tuple = pwd.getpwnam(username)
        pw_uid = pwd_tuple[2]
        pw_gid = pwd_tuple[3]

        os.setregid(pw_gid, pw_gid)
        os.setreuid(pw_uid, pw_uid)
    else:
        # Not root so we can't change privileges so pass
        pass

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError, ex:
        if ex.errno == errno.EEXIST:
            pass
        else:
            raise PilotError("Error creating path (%s): %s\n" % (path, str(ex)))

def chown(user_group, full_path):
    # I can do this through python libs, but this is so much easier!
    rtn = os.system("chown -R %s %s" % (user_group, full_path))
    if rtn != 0:
        raise PilotError("Failed to change ownership of file.  \n" \
                         "Return Code: %s\n" % str(rtn))

def get_host():
    hostname = socket.gethostname()
    ip_addr = socket.gethostbyname(hostname)
    fqdn = socket.getfqdn()
    
    return (hostname, ip_addr, fqdn)

def cp(source, destination):
    shutil.copy2(source, destination)

def cd(path):
    try:
        os.chdir(path)
    except OSError:
        _, exc_value, _ = sys.exc_info()
        raise PilotError("Failed to change directory.  Reason: %s" % exc_value)
    except:
        _, exc_value, _ = sys.exc_info()
        raise PilotError("Unknown Error: %s" % exc_value)


def rm(path, recurse=False):
    """
    Remove file or directory specified by path
    
    @type path: string
    @param path: file to be removed
    @type recurse: boolean
    @param recurse: if true, the function will delete all files and 
    sub-directories as well
    """
    if os.path.isdir(path):
        if recurse:
            shutil.rmtree(path)
        else:
            os.rmdir(path)
    else:
        os.remove(path)

def chmod(mode, path):
    os.chmod(path, mode)

def mv(orig_path, new_path, overwrite_new=False):
    if os.path.exists(new_path) and not overwrite_new:
        raise Exception("Destination path already exists")
    shutil.move(orig_path, new_path)

def safe_write(path, file_data):
    """
    Note: this does *NOT* append
     
    check if path exists, if yes move original to new name
    write path
    """
    if os.path.exists(path):
        directory = os.path.dirname(path)
        filename = os.path.basename(path)
        extension = str(time.time())
        backup_name = "%s/%s.bck_%s" % (directory, filename, extension)
        shutil.copy2(path, backup_name)

    fd = open(path, 'w')
    fd.write(file_data)
    fd.close()

def ls(directory):
    """
    Convenience function for os.listdir; returns a directory listing.
    """
    return os.listdir(directory)

def ls_files(directory):
    files = [f for f in os.listdir(directory) if os.path.isfile("%s/%s" % (directory, f))]
    return files

def ls_files_sorted(directory, reverse=False):
    files = ls_files(directory)
    files.sort(reverse=reverse)
    return files

def getuid(username):
    return pwd.getpwnam(username)[2]

def getgid(groupname):
    return grp.getgrnam(groupname)[2]

def has_permissions(directory, level, perms):
    result = True
    mode = stat.S_IMODE(os.lstat(directory)[stat.ST_MODE])
    for perm in perms:
        if mode & getattr(stat, "S_I" + perm + level):
            continue
        result = False
        break
    return result

def touch(file_path, mode=0600):
    os.fdopen(os.open(file_path, os.O_WRONLY | os.O_CREAT, mode), 'w').close()

def sleep(seconds):
    time.sleep(int(seconds))

def run_scripts(directory, log_writer, max_script_runtime=60, arguments=None):
    try:
        script_list = ls_files_sorted(directory)
    except Exception, e:
        message = "An Error has occured retrieving scripts: %s" % str(e)
        raise ScriptError(message)

    for script in script_list:
        try:
            cmd = "%s/%s" % (directory, script)
            exit_code = execute_cmd(cmd, max_script_runtime, log_writer, 
                                    arguments, os.environ)
        except Exception, e:
            message = "An Error has occured attempting to run script: %s" \
                      "\n\nError: %s" % (cmd, str(e))
            log_writer.log_err(message)

        # have to mod 256 because on some systems, instead of returning 0 on
        # success, 256 is returned
        if not int(exit_code) % 256 == 0:
            message = "A PRE script (%s) has exited with an error. \nExit " \
                      "Code: %s" % (cmd, str(exit_code))
            log_writer.log_err(message)
