#!/usr/ali/bin/python
# coding=utf-8

'''Send a email.

See test_main method for mor examples.
'''

# Can be 'Prototype', 'Development', 'Product'
__status__ = 'Development'
__author__ = 'tuantuan.lv <tuantuan.lv@alibaba-inc.com>'
__all__ = ['send_mail']

import os
import sys
import socket

import smtplib
import mimetypes

from email import encoders
from email.Header import Header
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.Utils import formatdate

from pypet.common import storage

def get_attachment(filepath):
    '''Get attachment from file.'''
    ctype, encoding = mimetypes.guess_type(filepath)

    if ctype is None or encoding is not None:
        ctype = 'application/octet-stream'

    maintype, subtype = ctype.split('/', 1)

    if maintype == 'text':
        fp = open(filepath)
        msg = MIMEText(fp.read(), subtype, 'utf-8')
        fp.close()
    elif maintype == 'image':
        fp = open(filepath, 'rb')
        msg = MIMEImage(fp.read(), _subtype = subtype)
        fp.close()
    else:
        fp = open(filepath, 'rb')

        msg = MIMEBase(maintype, subtype)
        msg.set_payload(fp.read())
        encoders.encode_base64(msg)

        fp.close()

    filename = os.path.basename(filepath)
    msg.add_header('Content-Disposition', 'attachment', filename=filename)

    return msg

def send_mail(header, content = '', files = [], server = 'smtp.ops.aliyun-inc.com:25',
              account = None):
    '''Send a text&html email with smtp.

    header: Header part of email, this is a dict:
        {
            'subject': 'email subject' # required
            'from': 'from address',    # required
            'to': [to address list],   # optional
            'cc': [cc address list],   # optional
        }

    content: Body part of email, this is a list or string:
        ['email text', 'email html'] or 'email text'

    files: Attachments of email, this is a list:
        ['file1', 'file2']

    server: SMTP server, this is a string:
        'hostname:port', default is 'smtp.ops.aliyun-inc.com:25'

    account: SMTP account, this is a string:
        'username:password', default is None

    Return an object of storage.Stroage, which contains 'return_code' and 'msg'
    attribute. The former indicates the return code(0 for succceded, 1 for failed),
    the latter contains the fail information.
    '''

    # Do nothing if header is empty
    if not header:
        return

    if not content:
        content = ''

    # Create a multipart/mixed message container
    msg_mixed = MIMEMultipart()

    # Fill the mail header part
    msg_mixed['subject'] = Header(header['subject'], 'utf-8')
    msg_mixed['from'] = header['from']
    msg_mixed['to'] = ';'.join(header.get('to', []))
    msg_mixed['cc'] = ';'.join(header.get('cc', []))
    msg_mixed['date'] = formatdate(localtime = True)

    msg_mixed.preamble = 'You will not see this in a MIME-aware mail reader.'

    to_address_list = []
    to_address_list.extend(header.get('to', []))
    to_address_list.extend(header.get('cc', []))

    if isinstance(content, list):
        msg_alternative = MIMEMultipart('alternative')
        msg_mixed.attach(msg_alternative)

        # Attach html and text part with specified charset
        msg_text = MIMEText(content[0], 'plain', 'utf-8')
        msg_alternative.attach(msg_text)

        msg_html = MIMEText(content[1], 'html', 'utf-8')
        msg_alternative.attach(msg_html)
    else:
        msg_text = MIMEText(content, 'plain', 'utf-8')
        msg_mixed.attach(msg_text)

    # Add attachments in the email
    for file in files:
        attachment = get_attachment(file)

        if attachment:
            msg_mixed.attach(attachment)

    ret = storage.Storage()

    ret.return_code = 0
    ret.msg = ""

    try:
        # Create a SMTP instance
        smtp_server = smtplib.SMTP()
        #smtp_server.set_debuglevel(1)  # Added by tuantuan.lv for debug
        smtp_server.connect(server)

        # Login the SMTP server if needed
        if account is not None:
            username, password = account.split(':', 1)
            smtp_server.login(username, password)

        smtp_server.sendmail(header['from'], to_address_list, msg_mixed.as_string())
        smtp_server.quit()

    except smtplib.SMTPException, e:
        ret.return_code = 1
        ret.msg = str(e)

    except socket.error, e:
        ret.return_code = 1
        ret.msg = str(e)

    return ret

def test_main():
    your_email = ''

    while not your_email:
        your_email = raw_input('Please input your email address: ')

    header = {
        'from': 'houyi@ops.aliyun-inc.com', 
        'subject': 'hello wrold',
        'to': [your_email],
        'cc': []
    }

    content = ['hello', '<p>hello</p>']

    ret =  send_mail(header, content)
    #ret = send_mail(header, content, server='mail.aliyun-inc.com:465')

    print ret.return_code
    print ret.msg

if __name__ == '__main__':
    test_main()
