#!/usr/ali/bin/python
# coding=utf-8

'''Defines some useful util functions

See test_main() for mor examples.
'''

from __future__ import with_statement

import os
import re
import socket
import tempfile
import ipcalc

# Can be 'Prototype', 'Development', 'Product'
__status__ = 'Development'
__author__ = 'tuantuan.lv <tuantuan.lv@alibaba-inc.com>'

def get_local_ip():
    '''Get the local ip address.'''
    return socket.gethostbyname(socket.gethostname()) 

def is_ip(addr):
    '''Check whether the address is a valid ip.'''
    patt = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'

    if addr and re.search(patt, addr):
        return True
    else:
        return False

def is_hostname(hostname):
    '''Check whether the hostname is a valid name.'''
    patt = r'^(?=.{4,255}$)([a-zA-Z0-9][a-zA-Z0-9-]{,61}[a-zA-Z0-9]\.)+[a-zA-Z0-9]{2,5}$'

    if hostname and re.search(patt, hostname):
        return True
    else:
        return False

def in_subnet(ip, subnet):
    '''Check whether the ip address is in given subnet.'''
    return ipcalc.Network(subnet).has_key(ip)

def list_ip(subnet, all = True):
    '''List all ip address in the given subnet.

    all: if set to true, including network and broadcast ip.
    '''
    ip_list = []
    n = ipcalc.Network(subnet)

    if all:
        ip_list.append(str(n.network()))
        ip_list.extend(str(ip) for ip in n)
        ip_list.append(str(n.broadcast()))
    else: # do not include network/broadcast ip
        ip_list = [str(ip) for ip in n]
    
    return ip_list

def ip2long(ip):
    '''Convert ip address to long int.'''
    return long(ipcalc.IP(ip))

def read_file(filename, delim = None):
    '''Read the all contents from the file.
    
    If you specified the delim, the content will be splitted
    into multi items with the delimiter given.
    '''
    with open(filename, 'r') as fp:
        content = fp.read()

    if delim is not None:
        return content.split(delim)
    else:
        return content

def write_file(filename, content = None, mode = 'w'):
    '''Write the content to the file.'''
    with open(filename, mode) as fp:
        if content is None:
            content = ''
        elif isinstance(content, (list, tuple)):
            content = '\n'.join(str(s) for s in content)

        fp.write(content)

def make_tempfile(content = None):
    '''Create a tempfile.'''
    fd, path = tempfile.mkstemp() 

    with os.fdopen(fd, 'w') as fp:
        if content is None:
            content = ''
        elif isinstance(content, (list, tuple)):
            content = '\n'.join(str(s) for s in content)

        fp.write(content)

    return path

def split(string, sep = None, maxsplit = -1):
    '''Split string into arrays using the given separater.'''
    arr = string.split(sep, maxsplit)
    return [s.strip() for s in arr]

def test_main():
    '''Test main entry.'''
    #filename = utils.make_tempfile([1,2,3])
    #print utils.read_file(filename, delim = '\n')
    print in_subnet('10.230.227.16', '10.230.227.0/24')
    print list_ip('10.230.227.0/24')
    print list_ip('10.230.227.0/24', False)
    print ip2long('10.230.227.16')

if __name__ == '__main__':
    test_main()
