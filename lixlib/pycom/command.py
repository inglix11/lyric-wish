#!/usr/ali/bin/python
# coding=utf-8

'''A simple interface to execute shell commands.

These ideas are taken from fabric/operations.py.

See test_main() for mor examples.
'''

# Can be 'Prototype', 'Development', 'Product'
__status__ = 'Development'
__author__ = 'tuantuan.lv <tuantuan.lv@alibaba-inc.com>'

import os
import re
import sys
import time

import socket
import tempfile

import signal
import errno
import warnings

import Queue
import threading
import subprocess

from pypet.common.storage import Storage
from pypet.common import log
from pypet.common import PetException, PetTimeout

# Default connect timeout
DEFAULT_TIMEOUT = 5

def _reset_sigpipe():
    '''Reset the SIGPIPE signal hander.'''
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

def _prefix_line(line, prefix):
    '''Prefix a line.'''
    if prefix is None:
        return line
    else:
        return '%s: %s' % (prefix, line)

def _get_log_func(logger, prefix = None):
    '''Get the logger function.'''
    if logger == 'print':
        def _debug(line):
            print _prefix_line(line, prefix)
    elif hasattr(logger, 'debug'):
        def _debug(line):
            logger.debug('<%s>' % _prefix_line(line, prefix))
    else:
        def _debug(line):
            pass

    return _debug

class _AsynchronousFileReader(threading.Thread):
    '''Helper class to implement asynchronous reading of a file
    in a separate thread. Pushes read lines on a queue to
    be consumed in another thread.
    '''
    def __init__(self, fd, logger = None, prefix = None):
        threading.Thread.__init__(self)
        self._fd = fd
        self._output = []
        self.debug = _get_log_func(logger, prefix)

    def run(self):
        '''The body of the tread: read lines and put them on the queue.'''
        for line in iter(self._fd.readline, ''):
            self._output.append(line)
            self.debug(line.rstrip('\n'))

        return

    def get_output(self):
        '''Get the output.'''
        output = ''.join(self._output)
        return output.strip()

class _AsynchronousPopenReader(threading.Thread):
    '''Asynchronous popen reader.'''
    def __init__(self, popen, logger):
        threading.Thread.__init__(self)
        self.popen = popen

        self.stdout_reader = _AsynchronousFileReader(popen.stdout, logger, 'stdout')
        self.stdout_reader.setDaemon(True)

        self.stderr_reader = _AsynchronousFileReader(popen.stderr, logger, 'stderr')
        self.stderr_reader.setDaemon(True)

    def run(self):
        '''Run the reader.'''
        self.stdout_reader.start()
        self.stderr_reader.start()

        self.running = True

        while self.running:
            if not self.stdout_reader.isAlive() and not self.stderr_reader.isAlive():
                self.popen.communicate()
                break

            time.sleep(0.1)

        return

    def stop(self):
        '''Stop the reader.'''
        self.running = False
        os.kill(self.popen.pid, signal.SIGTERM)

    def get_output(self):
        '''Get the reader output.'''
        return self.stdout_reader.get_output(), self.stderr_reader.get_output()

def local(cmd, should_succ = False, logger = None, run_timeout = None):
    '''Run command in local host.

    cmd: can be any shell commands, which will be run in remote host through scp.
    should_succ: if set true, raise PetException if command run failed.
    logger: log the command run output asynchronously, the value can be None, 'print',
    callable function with one argument or a Logger object:

    >>> local("uname -r")
    >>> local("uname -r", logger = 'print')

    >>> from pypet.common import log
    >>> local("uname -r", logger = log)

    >>> def x(line):
    ...     print '~~%s~~' %line
    >>> local("uname -r", logger = x)
    '''
    p = subprocess.Popen(cmd, shell = True, stdout = subprocess.PIPE,
            stderr = subprocess.PIPE, preexec_fn = _reset_sigpipe)

    debug = _get_log_func(logger)
    debug('BEFORE RUN COMMAND: %s' % cmd)

    # Reader start and wait
    reader = _AsynchronousPopenReader(p, logger)
    reader.start()
    reader.join(run_timeout)

    # Fill the running output
    out = Storage()
    out.cmd = cmd

    if reader.isAlive():
        reader.stop()
        out.is_timeout = True
        out.return_code = 1
    else:
        out.is_timeout = False
        out.return_code = p.returncode

    out.stdout, out.stderr = reader.get_output()

    if out.return_code != 0:
        out.failed = True
        out.succeeded = False
    else:
        out.failed = False
        out.succeeded = True

    debug('AFTER RUN COMMAND: %s, output: %s' % (cmd, out))

    if out.is_timeout:
        if should_succ:
            raise PetTimeout, 'timeout happened, exceed %s seconds, output: %s' % (run_timeout, out)
        elif out.stderr:
            out.stderr = 'timeout happened, exceed %s seconds, stderr: %s' % (run_timeout, out.stderr)
        else:
            out.stderr = 'timeout happened, exceed %s seconds' % run_timeout

    if should_succ and out.failed:
        raise PetException, '%s' % out

    return out

def remote(addr, cmd, timeout = DEFAULT_TIMEOUT, should_succ = False,
           logger = None, run_timeout = None):
    '''Run command on remote host through ssh.

    addr is the remote host address, which can be hostname or ip address.
    cmd can be any shell commands, which will be run in remote host through
    ssh protocol.

    If set timeout to a positive integer, it will change the default connect timeout.
    '''
    ssh = "ssh -o StrictHostKeyChecking=no -o LogLevel=quiet -o BatchMode=yes"

    if isinstance(timeout, int) and timeout > 0:
        ssh += ' -o ConnectTimeout=%d' % timeout

    cmd = '%s %s "%s"' % (ssh, addr, cmd)

    return local(cmd, should_succ, logger, run_timeout)

def remote_copy(addr, src, dst, timeout = DEFAULT_TIMEOUT, owner = None,
        indirect = False, should_succ = False, logger = None):
    '''Copy file from src to dst on remote host.

    addr is the remote host address, which can be hostname or ip address.
    src and dest are the source and the destination when copy.
    owner is the ownership of files, default is current user.
    indirect controls the copy behavior, if set true, copy file to /tmp first and then copy to dst.

    If set timeout to a positive integer, it will change the default connect timeout.
    '''
    scp = "scp -o StrictHostKeyChecking=no -o LogLevel=quiet -o BatchMode=yes -pr"

    if isinstance(timeout, int) and timeout > 0:
        scp += ' -o ConnectTimeout=%d' % timeout

    if indirect: # copy to /tmp first, then copy to dst
        basename = os.path.basename(src)
        timestamp = int(time.time())
        tmpfile = '/tmp/%s.%d' % (basename, timestamp)

        cmd = '%s %s %s:%s' % (scp, src, addr, tmpfile)
        ret = local(cmd, should_succ, logger)

        # If copy files failed, do not go ahead
        if ret.return_code != 0:
            return ret

        if os.path.isfile(src): # copy normal file with archive mode
            cmd = 'sudo cp -arf %s %s' % (tmpfile, dst)
        else: # copy directory in override mode
            cmd = 'if [ ! -d "%s" ]; then sudo cp -arf %s %s; else sudo cp -arf %s/* %s; fi' % (
                    dst, tmpfile, dst, tmpfile, dst)

        cmd = '%s && sudo rm -rf %s' % (cmd, tmpfile)

        if owner is not None:
            cmd = 'sudo chown -R %s %s && %s' % (owner, tmpfile, cmd)

        return remote(addr, cmd, timeout, should_succ, logger)
    else:
        cmd = '%s %s %s:%s' % (scp, src, addr, dst)
        return local(cmd, should_succ, logger)

def remote_get(addr, dst, src, timeout = DEFAULT_TIMEOUT,
               should_succ = False, logger = None):
    '''Get a file from remote host.

    addr is the remote host address, which can be hostname or ip address.
    dest is the destination file in remote host.
    src is the output file in current host.
    '''
    scp = "scp -o StrictHostKeyChecking=no -o LogLevel=quiet -o BatchMode=yes -pr"

    if isinstance(timeout, int) and timeout > 0:
        scp += ' -o ConnectTimeout=%d' % timeout

    cmd = '%s %s:%s %s' % (scp, addr, dst, src)
    return local(cmd, should_succ, logger)

def pssh(iplist, cmd, par = 100, timeout = DEFAULT_TIMEOUT,
         logger = None, should_succ = False, run_timeout = None):
    '''Copy files in scp in parallel.

    iplist: set the ip list, which can be a filename or a list.
    par: the max number of process.
    cmd: the command to be run.

    Return a tuple of (success_list, failed_list).
    '''
    # Generates ip range by mklist script
    ip_queue = Queue.Queue()
    out_queue = Queue.Queue()

    # Read the ip list
    if isinstance(iplist, str):
        if os.path.isfile(os.path.expanduser(iplist)):
            # Open the iplist file and read
            fp = open(os.path.expanduser(iplist))
            iplist = fp.read()
            fp.close()
            iplist = iplist.split('\n')
        else: # get ip list from string
            iplist = iplist.split(' ,')
    elif isinstance(iplist, list) or isinstance(iplist, tuple):
        pass

    # Remove empty or duplicate ip
    iplist = list(set(iplist))
    iplist = filter(lambda x: x.strip(), iplist)
    iplist.sort()

    for ip in iplist:
        ip_queue.put(str(ip))

    def _remote(ip_queue, out_queue):
        while not ip_queue.empty():
            ip = ip_queue.get()
            ret = remote(ip, cmd, timeout, logger = logger, run_timeout = run_timeout)
            out_queue.put((ret, ip))
            ip_queue.task_done()

    for i in range(0, par):
        worker = threading.Thread(target = _remote,
                args = (ip_queue, out_queue))
        worker.setDaemon(True)
        worker.start()

    ip_queue.join()

    success_dict = Storage()
    failed_dict = Storage()

    while not out_queue.empty():
        ret, ip = out_queue.get()

        if ret.succeeded:
            success_dict[ip] = ret
        else:
            failed_dict[ip] = ret

    if should_succ and len(failed_dict):
        raise PetException,"pssh run command error on %s" % failed_dict.keys()

    return success_dict, failed_dict

def pscp(iplist, src, dst, par = 100, timeout = DEFAULT_TIMEOUT,
        owner = None, indirect = False, logger = None, should_succ = False):
    '''Copy files in scp in parallel.

    iplist: set the ip list, which can be a filename or a list.
    par: the max number of process.
    others: see remote_copy method.

    Return a tuple of (success_list, failed_list).
    '''
    # Generates ip range by mklist script
    ip_queue = Queue.Queue()
    out_queue = Queue.Queue()

    # Read the ip list
    if isinstance(iplist, str):
        if os.path.isfile(os.path.expanduser(iplist)):
            # Open the iplist file and read
            fp = open(os.path.expanduser(iplist))
            iplist = fp.read()
            fp.close()
            iplist = iplist.split('\n')
        else: # get ip list from string
            iplist = iplist.split(' ,')
    elif isinstance(iplist, list) or isinstance(iplist, tuple):
        pass

    # Remove empty or duplicate ip
    iplist = list(set(iplist))
    iplist = filter(lambda x: x.strip(), iplist)
    iplist.sort()

    for ip in iplist:
        ip_queue.put(str(ip))

    # Arguments for remote_copy
    args = {
        'src': src, 'dst': dst, 'timeout': timeout,
        'owner': owner, 'indirect': indirect,
        'logger': logger
    }

    def _remote_copy(ip_queue, out_queue):
        while not ip_queue.empty():
            ip = ip_queue.get()
            ret = remote_copy(ip, **args)
            out_queue.put((ret.succeeded, ip))
            ip_queue.task_done()

    for i in range(0, par):
        worker = threading.Thread(target = _remote_copy,
                args = (ip_queue, out_queue))
        worker.setDaemon(True)
        worker.start()

    ip_queue.join()

    success_list = []
    failed_list = []

    while not out_queue.empty():
        succeeded, ip = out_queue.get()

        if succeeded:
            success_list.append(ip)
        else:
            failed_list.append(ip)

    success_list.sort()
    failed_list.sort()

    if should_succ and len(failed_list):
        raise PetException,"pscp error on %s" % failed_list

    return success_list, failed_list

# Rsync modules
_rsync_modules = {
    "/home/admin": "homeadmin",
    "/apsara": "apsara",
    "/apsarapangu": "apsarapangu",
}

def _get_rsync_module(path):
    '''Get the rsync module information based on the path.

    Return a tuple of (module_path, module_name, relative_path).
    '''
    for k, v in _rsync_modules.items():
        if path.startswith(k):
            return k, v, path[len(k):].lstrip('/')

    return ('', '')

def md_pscp(iplist, src_path, dest_dir, par = 200, speed = 10,
        timeout = DEFAULT_TIMEOUT, logger = None, should_succ = False):
    '''Copy files with multiphasic-duplicate in parallel.

    iplist: set the ip list, which can be a filename or a list.
    src_path: set the source file path, must be under /home/admin, /apsara or /apsarapangu.
    dest_dir: set the destination directory, MUST be a directory
    par: set the number of process, default 200.
    speed: set the bandwidth limit in MB, default 10MB.

    Return a tuple of (dest_path, success_list, failed_list).
    '''
    mdbin = '/home/tops/bin/multiphasic-duplicate'
    mklist = '/home/tops/bin/mklist.pl'

    if not os.access(mdbin, os.X_OK):
        raise PetException, 'multiphasic-duplicate not found or not executable: %s' % mdbin

    if not os.access(mklist, os.X_OK):
        raise PetException, 'mklist not found or not executable: %s' % mklist

    # Transfer bandwidth limit, conver to KB
    speed = speed * 1024

    # Generates ip range by mklist script
    if isinstance(iplist, str):
        if os.path.isfile(os.path.expanduser(iplist)):
            mklist_cmd = 'cat %s | %s' % (iplist, mklist)
        else:
            mklist_cmd = 'echo "%s" | %s' % (iplist, mklist)
    elif isinstance(iplist, list) or isinstance(iplist, tuple):
        mklist_cmd = 'echo "%s" | %s' % (','.join(iplist), mklist)

    ret = local(mklist_cmd)

    # Exit if mklist failed
    if ret.failed:
        raise PetException, 'mklist failed: %s' % ret

    range = ret.stdout.strip()

    # Extra arguments passed to rsync
    if isinstance(timeout, int) and timeout > 0:
        args = "--extra='--bwlimit=%s --contimeout=%s' --verbose -m=%s -r='%s'" % (
                speed, timeout, par, range)
    else:
        args = "--extra='--bwlimit=%s' --verbose -m=%s -r='%s'" % (speed, par, range)

    # Make up the source arguments
    src_basename = os.path.basename(src_path).rstrip('/')
    src_module_path, src_module_name, src_rel_path = _get_rsync_module(src_path)

    if src_module_name == '':
        raise PetException, 'source path must locate under %s' % _rsync_modules.keys()

    src_args = '--source=%s::%s/%s' % (get_local_ip(), src_module_name, src_rel_path)

    # Make up the dest arguments
    dest_module_path, dest_module_name, dest_rel_path = _get_rsync_module(dest_dir)

    if dest_module_name == '':
        raise PetException, 'dest dir must locate under %s' % _rsync_modules.keys()

    if os.path.isfile(src_path):
        dest_args = "--dest=%s/%s" % (dest_dir.rstrip('/'), src_basename)
    else:
        dest_args = "--dest=%s" % dest_dir.rstrip('/')

    # Make up the remote source arguments
    rsrc_args = "--rsource=::%s/%s/%s" % (dest_module_name, dest_rel_path, src_basename)
    rsrc_args = rsrc_args.replace('//', '/')
    dest_path = os.path.join(dest_dir, src_basename)

    md_cmd = '%s %s %s %s %s' % (mdbin, args, src_args, dest_args, rsrc_args)
    ret = local(md_cmd, logger = logger)

    # Running ip list
    run_list = []
    run_patt = re.compile('INFO: ([0-9.]+) completed$')

    # Failed ip list
    failed_list = []
    failed_patt = re.compile('^ERROR: ([0-9.]+) completed with error code (\d+)$')

    for line in ret.stderr.split('\n'):
        line = line.strip()
        if not line: continue

        m = run_patt.search(line)

        if m:
            run_list.append(m.group(1))
            continue

        m = failed_patt.search(line)

        if m:
            failed_list.append(m.group(1))
            continue

    if not run_list:
        raise PetException, "Error, Rultiphasic-duplicate Running Error"

    run_list = set(run_list)
    failed_list = set(failed_list)
    success_list = run_list - failed_list

    success_list = list(success_list)
    success_list.sort()

    failed_list = list(failed_list)
    failed_list.sort()

    if should_succ and len(failed_list):
        raise PetException, "md_pscp error on %s" % failed_list

    return dest_path, success_list, failed_list

def mkdir_p(path):
    '''Create directory like 'mkdir -p' in shell.'''
    try:
        os.makedirs(path)

    except OSError, exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

    return os.path.isdir(path)

def get_local_ip():
    '''Get the local ip address.'''
    return socket.gethostbyname(socket.gethostname()) 

def service_ctl(serv_name, action, host = None, args = None,
                logger = None, as_sudo = True, should_succ = False):
    '''Control the system service.'''
    if as_sudo:
        cmd = "sudo /etc/init.d/%s %s" % (serv_name, action)
    else:
        cmd = "/etc/init.d/%s %s" % (serv_name, action)

    if args is not None:
        cmd = '%s %s' % (cmd, args)

    if host is None:
        return local(cmd, should_succ, logger = logger)
    else:
        return remote(host, cmd, should_succ = should_succ, logger = logger)

def pssh_service_ctl(serv_name, action, iplist, args = None, logger = None,
                     as_sudo = True, par = 100, timeout = DEFAULT_TIMEOUT):
    '''Control the system service in parallel.'''
    if as_sudo:
        cmd = "sudo /etc/init.d/%s %s" % (serv_name, action)
    else:
        cmd = "/etc/init.d/%s %s" % (serv_name, action)

    if args is not None:
        cmd = '%s %s' % (cmd, args)

    return pssh(iplist, cmd, par, timeout, logger)

def stop_service(serv_name, host = None, args = None, logger = None,
                 as_sudo = True, should_succ = False):
    '''Stop the system service.'''
    return service_ctl(serv_name, 'stop', host, args, logger, as_sudo,
                       should_succ)

def start_service(serv_name, host = None, args = None, logger = None,
                  as_sudo = True, should_succ = False):
    '''Start the system service.'''
    return service_ctl(serv_name, 'start', host, args, logger, as_sudo,
                      should_succ)

def status_service(serv_name, host = None, args = None, logger = None,
                   as_sudo = True, should_succ = False):
    '''Status the system service.'''
    return service_ctl(serv_name, 'status', host, args, logger, as_sudo,
                      should_succ)

def restart_service(serv_name, host = None, args = None, logger = None,
                    as_sudo = True, should_succ = False):
    '''Start the system service on remote host.'''
    return service_ctl(serv_name, 'restart', host, args, logger, as_sudo,
                      should_succ)

def uninstall_rpm(package_name, host = None, logger = None,
                  should_succ = False):
    '''Uninstall rpm package.'''
    package_name = os.path.basename(package_name)
    cmd = 'sudo rpm -e %s' % package_name

    if host is None:
        ret = local(cmd, should_succ, logger = logger)
    else:
        ret = remote(host, cmd, should_succ = should_succ, logger = logger)

    return ret

def update_rpm(package_name, host = None, logger = None,
               downgrade = False, should_succ = False):
    '''Update rpm package on remote host.

    Set downgrade flag to true value if you want to rollback rpm
    to an old version. true values contain 1, '1', 'yes', True or
    'true'.
    '''
    if downgrade in [1, '1', 'yes', True, 'true']:
        downgrade == True
    else:
        downgrade = False 

    if downgrade:
        cmd = 'sudo rpm -Uvh --force --oldpackage %s' % package_name
    else:
        cmd = 'sudo rpm -Uvh --force %s' % package_name

    if host is None:
        ret = local(cmd, should_succ, logger = logger)
    else:
        ret = remote(host, cmd, should_succ = should_succ, logger = logger)

    return ret

def wget(url, target, md5 = None, timeout = DEFAULT_TIMEOUT,
        should_succ = False, logger = None):
    '''Download a file using wget.'''
    from urlparse import urlparse

    # Get the filename from url
    # Fixed me: redirect url happened?
    filename = urlparse(url).path # /x/x/file.ext
    filename = os.path.basename(filename) # file.ext

    if os.path.isdir(target):
        target = os.path.join(target, filename)

    if md5 is None: md5 = ''

    cmd = 'wget -c --connect-timeout=%d -nv %s -O %s && md5sum %s | grep -w "%s"'
    cmd = cmd % (timeout, url, target, target, md5)

    return local(cmd, should_succ, logger = logger)

def ping(addr, timeout = 2, logger = None):
    '''Running ping to host.'''
    cmd = 'ping -W %s -c 1 -q %s &> /dev/null' % (timeout, addr)
    ret = local(cmd, logger = logger)

    return ret.succeeded

def check_port(addr, port, timeout = 2, logger = None):
    '''Scan the port of server.'''
    cmd = 'nc -w %d -z %s %s &>/dev/null' % (timeout, addr, port)
    ret = local(cmd, logger = logger)

    return ret.succeeded

def make_tempfile(content = ""):
    '''Create a tempfile.'''
    warnings.warn("utils.make_tempfile is recommended", DeprecationWarning)
    fd, path = tempfile.mkstemp() 

    fp = os.fdopen(fd, 'w')
    fp.write(content)
    fp.close()

    return path

def test_main():
    '''Test main entry.'''
    # Run local command
    out = local('uname -r')

    if out.succeeded:
        print "stdout:", out.stdout
    else:
        print "stderr: %s", out.stderr

    # Execute command in remote host through ssh
    out = remote('houyi-vm07.dev.sd.aliyun.com', 'uname -r')

    if out.succeeded:
        print "stdout:", out.stdout
    else:
        print "stderr:", out.stderr

    # Copy file from local to remote through scp
    host = 'houyi-vm07.dev.sd.aliyun.com'
    out = remote_copy(host, '/var/log/messages', '/tmp')

    if out.succeeded:
        print "stdout:", out.stdout
    else:
        print "stderr:", out.stderr

    try:
        local('uname -r && exit 1', should_succ = True)
    except Exception, e:
        from pypet.common import log
        log.exception(e)

if __name__ == '__main__':
    test_main()
