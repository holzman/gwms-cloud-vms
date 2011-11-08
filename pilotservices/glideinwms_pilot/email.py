import smtplib
from email.MIMEText import MIMEText

class SendMail(object):
    def __init__(self, subject, email_recipient, email_sender="pilot_launcher@localhost"):
        self.email_to = email_recipient
        self.email_from = email_sender
        self.subject = subject

    def get_log_contents(self, log_file_path):
        # Open a plain text file for reading.  For this example, assume that
        # the text file contains only ASCII characters.
        fd = open(log_file_path, 'rb')
        # Create a text/plain message
        msg = MIMEText(fd.read())
        fd.close()

        return msg

    def send_mail(self, mime_text_obj):
        mime_text_obj['Subject'] = self.subject
        mime_text_obj['From'] = self.email_from 
        mime_text_obj['To'] = self.email_to

        # Send the message via our own SMTP server, but don't include the envelope header.
        s = smtplib.SMTP()
        s.connect()
        s.sendmail(self.email_from, [self.email_to], mime_text_obj.as_string())
        s.close()

def email_logs(config):
    pass