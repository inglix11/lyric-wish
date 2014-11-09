#!/usr/ali/bin/python
# coding=utf-8

import os
import sys

from pypet.common import storage
from pypet.common import utils
from pypet.common import PetException

class Env:
    def __init__(self, conf = None, valid_keys = [], define = {}):
        '''Initialize the environment.'''
        if conf is None:
            content = []
            self.conf = '[NOT SET]'
        else:
            self.conf = os.path.expanduser(conf)

            if not os.path.isfile(self.conf):
                raise IOError, 'Environ file not found: %s' % self.conf

            # Parse the settings from environ config file
            content = utils.read_file(self.conf, delim = '\n')

        settings = {}

        for line in content:
            line = line.strip()

            if not line: # blank lines
                continue
            elif line.startswith('#'): # comment lines
                continue

            key, value = line.split('=', 1)

            key = key.strip()
            value = value.strip()

            # Raise error when the key is not set, which means the value is empty
            if not value:
                raise ValueError, 'Key "%s" is not set in environ file: %s' % (key,
                        self.conf)

            # Raise error when invalid key is added
            if valid_keys and key not in valid_keys:
                raise KeyError, 'Invalid key "%s" in environ file: %s' % (key,
                        self.conf)

            settings[key] = value

        # Add constants definition
        settings['define'] = define
        self.__settings = storage.Storage(settings, create = False)

    def __getattr__(self, key):
        try:
            return self.__settings.__getitem__(key)
        except KeyError:
            raise KeyError, 'No such key "%s" existed in environ file: %s' % (key,
                    self.conf)

    def __str__(self):
        return 'Config: %s\nSettings: %s' % (self.conf, self.__settings)

    def __repr__(self):
        return 'Config: %s\nSettings: %s' % (self.conf, self.__settings)

def test_main():
    '''The test main entry.'''
    env = Env(
        conf = '~/pet/trunk/conf.d/environ/luorigong.conf',  # environ config file
        valid_keys = [],  # valid keys
        define = { # constants definitions
            'X': 1,
            'Y': 2 
        })

    print env
    print env.define.X
    print env.LRG_LOG_FILE

    try:
        print env.X # throw keyerror exception
    except KeyError, e:
        print e

if __name__ == '__main__':
    test_main()
