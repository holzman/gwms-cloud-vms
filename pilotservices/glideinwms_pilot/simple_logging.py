import sys
import time
import syslog

"""
Syslog specific code was cribbed and heavily modified from the daemon code 
written by Ray Burr

authors: Ray Burr
license: MIT License
contact: http://www.nightmare.com/~ryb/
"""
_syslogFacilityMap = {
    "auth":   syslog.LOG_AUTH,
    "cron":   syslog.LOG_CRON,
    "daemon": syslog.LOG_DAEMON,
    "kern":   syslog.LOG_KERN,
    "lpr":    syslog.LOG_LPR,
    "mail":   syslog.LOG_MAIL,
    "news":   syslog.LOG_NEWS,
    "user":   syslog.LOG_USER,
    "uucp":   syslog.LOG_UUCP,
    "local0": syslog.LOG_LOCAL0,
    "local1": syslog.LOG_LOCAL1,
    "local2": syslog.LOG_LOCAL2,
    "local3": syslog.LOG_LOCAL3,
    "local4": syslog.LOG_LOCAL4,
    "local5": syslog.LOG_LOCAL5,
    "local6": syslog.LOG_LOCAL6,
    "local7": syslog.LOG_LOCAL7,
}

_syslogPriorityMap = {
    "emerg":  syslog.LOG_EMERG,
    "alert":  syslog.LOG_ALERT,
    "crit":   syslog.LOG_CRIT,
    "err":    syslog.LOG_ERR,
    "warning": syslog.LOG_WARNING,
    "notice": syslog.LOG_NOTICE,
    "info":   syslog.LOG_INFO,
    "debug":  syslog.LOG_DEBUG,
}

class SyslogWriter(object):
    """
    A class for a writable file-like object that calls a function for
    every line of text.  It is intended for replacing stdout/stderr
    and calling a logging function.  A callable object should be
    provided for logFn.
    """
    def __init__(self, facility=None, priority=None, name="glideinwms_pilot"):
        self.name = name
        self._line = ""
        self.softspace = 0

        if facility is None:
            facility = syslog.LOG_USER
        if type(facility) is type(""):
            facility = _syslogFacilityMap[facility]

        if priority is None:
            self.priority = syslog.LOG_INFO
        if type(self.priority) is type(""):
            self.priority = _syslogPriorityMap[self.priority]


    def write(self, s):
        while s:
            i = s.find("\n")
            if i < 0:
                self._line += s
                break
            self._line += s[:i]
            if self._line:
                syslog.syslog(self.priority, self._line)
                self._line = ""
            s = s[i+1:]

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    def flush(self):
        if self._line:
            syslog.syslog(self.priority, self._line)
            self._line = ""

    def _intToUnsignedLong(self, x):
        """
        Reinterpret negative int values as unsigned.  Depending on the OS and
        maybe the Python version, the id() builtin may sometimes return an
        object's address a negative integer.  This can be used to ensure the
        address is always positive.

        >>> '%#x' % id(object())
        '-0x481eabc8'
        >>> '%#x' % _intToUnsignedLong(id(object()))
        '0xb7e15438'
        """
        if x < 0:
            x += (sys.maxint + 1) << 1
        return x

class FileWriter(object):
    def __init__(self, log_dir, file_name="pilot_launcher.log"):
        self.log_file = "%s/%s" % (log_dir, file_name)
        self.log = open(self.log_file, "a")

    def write(self, text_string):
        self.log.write(text_string)

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    def flush(self):
        self.log.flush()

    def fileno(self):
        return self.log.fileno()


class ConsoleWriter(object):
    def __init__(self, output="stdout"):
        if output.lower() == "stderr":
            self.out = sys.stderr
        else:
            self.out = sys.stdout

    def write(self, text_string):
        print >> self.out, text_string

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    def flush(self):
        self.out.flush()

    def fileno(self):
        return self.out.fileno()

class Logger(object):
    def __init__(self, log_writer, datetime_format="%b %d %H:%M:%S %Y %Z", 
                 utc_time=False):

        self.utc_time = utc_time
        self.datetime_format = datetime_format
        self.log = log_writer

    def log_timestamp(self):
        epoch = time.time()
        if self.utc_time:
            time_struct = time.gmtime(epoch)
        else:
            time_struct = time.localtime(epoch)
        
        ts = time.strftime(self.datetime_format, time_struct)
        return ts

    def write(self, message, prefix="INFO"):
        msg_str = "[%s] %s: %s\n" % (self.log_timestamp(), prefix, message)
        self.log.write(msg_str)
        self.log.flush()

    def log_info(self, message):
        self.write(message, prefix="INFO")

    def log_warn(self, message):
        self.write(message, prefix="WARN")

    def log_err(self, message):
        self.write(message, prefix="ERROR")

    def get_logfile_path(self):
        try:
            return self.log.log_file
        except:
            return ""

    def get_logfile(self):
        return self.log

    def get_logfile_fd(self):
        return self.log.fileno()
