#!/usr/ali/bin/python
# coding=utf-8

'''__init__.py for pypet.common package
'''

__author__ = "tuantuan.lv <tuantuan.lv@alibaba-inc.com>"
__status__ = "Development"

import os
import sys
import ConfigParser

from pypet.common import storage

# Pet exception class
class PetException(Exception):
    """Base PetException

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.

    """
    message = "An unknown exception occurred."
    code = 10000

    def __init__(self, message=None, **kwargs):

        self.kwargs = kwargs

        if 'code' not in self.kwargs:
            try:
                self.kwargs['code'] = self.code
            except AttributeError:
                pass
        else:
            PetException.code = self.kwargs['code']

        if not message:
            try:
                message = self.message % kwargs

            except Exception, e:
                # kwargs doesn't match a variable in the message
                # log the issue and the kwargs
                #for name, value in kwargs.iteritems():
                #    self.logger.error("%s: %s" % (name, value))
                # at least get the core message out if something happened
                message = self.message
        else:
            PetException.message = message

        super(PetException, self).__init__(message)

class PetTimeout(PetException):
    '''Timeout exception'''
    pass

class PetConfig(storage.Storage):
    '''A simple wrapper of ConfigParser to allow access sections/options
    with attribute dot operator.

    Examples:

    >>> pc = PetConfig('xx.conf')
    >>> pc.section1.keys()
    >>> pc.section1.option1
    >>> pc.section2.items()
    '''
    def __init__(self, conf):
        cp = ConfigParser.ConfigParser()
        cp.optionxform = str # preserve case

        conf = os.path.expanduser(conf)
        cp.read(conf)

        dic = {}

        for section in cp.sections():
            # Replace hyphen with underline
            # Because attribute name can't contains it
            std_section = section.replace('-', '_')
            dic[std_section] = {}

            for k, v in cp.items(section):
                dic[std_section][k] = v

        storage.Storage.__init__(self, dic, False)
