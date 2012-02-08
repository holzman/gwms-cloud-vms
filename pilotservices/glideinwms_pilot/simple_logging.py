import time

class Logger(object):
    def __init__(self, log_dir, datetime_format="%b %d %H:%M:%S %Y %Z", utc_time=False):
        self.log_dir = log_dir
        self.log = open("%s/pilot_launcher.log" % self.log_dir, "a")
        self.utc_time = utc_time
        self.datetime_format = datetime_format

    def log_timestamp(self):
        epoch = time.time()
        if self.utc_time:
            time_struct = time.gmtime(epoch)
        else:
            time_struct = time.localtime(epoch)
        
        ts = time.strftime(self.datetime_format, time_struct)
        return ts

    def logit(self, message, prefix="INFO"):
        msg_str = "[%s] %s: %s\n" % (self.log_timestamp(), prefix, message)
        self.log.write(msg_str)
        self.log.flush()

    def log_warn(self, message):
        self.logit(message, prefix="WARN")

    def log_err(self, message):
        self.logit(message, prefix="ERROR")

    def get_logfile(self):
        return "%s/pilot_launcher.log" % self.log_dir

    def get_logfile_fd(self):
        return self.log
