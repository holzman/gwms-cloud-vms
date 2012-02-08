import os
import popen2
import select
import errno
import pwd
import socket

from errors import PilotError

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
    except OSError, e:
        raise Exception("%s [%d]" % (e.strerror, e.errno))

    if (pid == 0):       # The first child.
        os.setsid()
        try:
            pid = os.fork()        # Fork a second child.
        except OSError, e:
            raise Exception("%s [%d]" % (e.strerror, e.errno))

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

def shutdown_vm():
    cmd = "sudo shutdown -h now"
    os.system(cmd)

def launch_pilot(command, fdout, fderr):
    try:
        child = popen2.Popen3(command, capturestderr=True)
        child.tochild.close()

        stdout = child.fromchild
        stderr = child.childerr

        outfd = stdout.fileno()
        errfd = stderr.fileno()

        fdlist = [outfd, errfd]
        while fdlist:
            ready = select.select(fdlist, [], [])
            if outfd in ready[0]:
                outchunk = stdout.read()
                if outchunk == '':
                    fdlist.remove(outfd)
                else:
                    fdout.write(outchunk)
                    fdout.flush()
            if errfd in ready[0]:
                errchunk = stderr.read()
                if errchunk == '':
                    fdlist.remove(errfd)
                else:
                    fderr.write(errchunk)
                    fderr.flush()

        exitStatus = child.wait()

        if exitStatus:
            raise PilotError('Command %s exited with %d\n' % (command, os.WEXITSTATUS(exitStatus)))
    except PilotError, ex:
        raise
    except Exception, ex:
        raise PilotError("Unexpected error encountered while running command [%s]: %s\n" % (command, str(ex)))

def drop_privs(username):
    # check if we are root.  If we are, drop privileges
    start_uid = os.getuid()
    if start_uid == 0:
        # NOTE:  Must set gid first or you will get an "Operation not permitted" error
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
            raise PilotError("Error creating path (%s): %s\n" % (path,str(ex)))

def chown(user_group, full_path):
    # I can do this through python libs, but this is so much easier!
    rtn = os.system("chown -R %s %s" % (user_group, full_path))
    if rtn != 0:
        raise PilotError("Failed to change ownership of file.  Return Code: %s\n" % str(rtn))

def get_host():
    hostname = socket.gethostname()
    ip_addr = socket.gethostbyname(hostname)
    fqdn = socket.getfqdn()
    
    return (hostname, ip_addr, fqdn)