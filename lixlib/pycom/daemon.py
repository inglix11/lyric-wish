#!/usr/ali/bin/python
# coding=utf-8

'''Detach a process from the controlling terminal and run it in the
background as a daemon.

Example:
     >>> from pypet.common import daemon
     
     # Create a daemon instance
     >>> myd = daemon.Daemon(pidfile = '/tmp/your.pid', run = your_func)

     # Control the daemon
     >>> myd.start()
     >>> myd.status()
     >>> myd.restart()
     >>> myd.stop()
'''

# Can be 'Prototype', 'Development', 'Product'
__status__ = 'Development'
__author__ = 'lixing.lix <lixing.lix@alibaba-inc.com>'
__modifier__ = 'tuantuan.lv <tuantuan.lv@alibaba-inc.com>'

import os
import sys
import time
import atexit

from signal import SIGTERM, SIGKILL

KILL_TIMEOUT = 1

# Taken from http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
class Daemon:
    '''A generic daemon class.
    
    Usage: subclass the Daemon class and override the _run() method
    '''
    def __init__(self, pidfile, run, stdin = '/dev/null',
                 stdout = '/dev/null', stderr = '/dev/null'):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile
        self.attach_run(run)

    def _daemonize(self):
        '''Do the UNIX double-fork magic, see Stevens's "Advanced Programming
        in the UNIX Environment" for details (ISBN 0201563177)

        Reference: http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        '''

        # Do first fork, detach from parent process
        try:
            pid = os.fork()

            if pid > 0:
                sys.exit(0)

        except OSError, e:
            sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # decouple from parent environment
        os.setsid()
        os.chdir("/")
        os.umask(0)

        # Do second fork, 
        try:
            pid = os.fork()

            if pid > 0:
                sys.exit(0)

        except OSError, e:
            sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # Redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # Write pidfile
        atexit.register(self.delpid)  # clear pidfile when prog exit
        pid = str(os.getpid())
        file(self.pidfile, 'w+').write("%s\n" % pid)

    def delpid(self):
        '''Remove pidfile.'''
        os.remove(self.pidfile)

    def start(self):
        '''Start the daemon.'''
        # Check for a pidfile to see if the daemon already runs
        try:
            pf = file(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()

        except IOError:
            pid = None

        if pid:
            message = "pidfile %s already exist. Daemon already running?\n"
            sys.stderr.write(message % self.pidfile)
            sys.exit(1)

        # Start the daemon
        self._daemonize()
        self._run()

    def stop(self):
        '''Stop the daemon.'''
        # Get the pid from the pidfile
        try:
            pf = file(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()

        except IOError:
            pid = None

        if not pid:
            message = "pidfile %s does not exist. Daemon not running?\n"
            sys.stderr.write(message % self.pidfile)
            return # not an error in a restart

        # Try killing the daemon process    
        try:
            timeout = 0

            while timeout < KILL_TIMEOUT:
                os.kill(pid, SIGTERM)
                time.sleep(0.1)
                timeout += 0.1

            while 1:
                os.kill(pid, SIGKILL)
                time.sleep(0.1)

        except OSError, err:
            err = str(err)

            # If no such process, remove old pidfile
            if err.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print str(err)
                sys.exit(1)

    def status(self):
        '''Return the daemon state.'''
        # Check for a pidfile to see if the daemon is already running
        try:
            pf = file(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()

        except IOError:
            pid = None
    
        if pid:
            message = "%s (%s:%d) is running.\n"
            sys.stdout.write(message % (self.__class__.__name__, self.pidfile, pid))
        else:
            message = "pidfile %s does not exist. %s not running.\n"
            sys.stdout.write(message % (self.pidfile, self.__class__.__name__))

    def restart(self):
        '''Restart the daemon.'''
        self.stop()
        self.start()
    
    def attach_run(self, func):
        '''Attach func as the run method.'''
        self._run = func

    def _run(self):
        '''You should override this method when you subclass Daemon. It will
        be called after the process has been daemonized by start() or restart().'''
        dead_loop()

def dead_loop():
    while True:
        time.sleep(1)

def test_main(*argv):
    def test_loop():
        sys.stdout.write('Test loop!!\n')
        dead_loop()

    daemon = Daemon('/tmp/daemon-example.pid', run = test_loop)

    if len(argv) != 2:
        print 'Usage: %s <start|stop|restart|status>' % argv[0]
        sys.exit(1)

    cmd = argv[1]
    method = getattr(daemon, cmd, None)

    if method is None:
        print "Unknown command '%s'!" % cmd
        print 'Usage: %s <start|stop|restart|status>' % argv[0]
        sys.exit(2)

    method()
        
if __name__ == '__main__':
    test_main(*sys.argv)
