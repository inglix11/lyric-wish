#!/usr/ali/bin/python
# coding=utf-8

'''Implements a simple log library.

This module is a simple encapsulation of logging module to provide a more
convenient interface to write log. The log will both print to stdout and
write to log file. It provides a more flexible way to set the log actions,
and also very simple. See examples showed below:

Example 1: Use default settings

    import log

    log.debug('hello, world')
    log.info('hello, world')
    log.error('hello, world')
    log.critical('hello, world')

Result:
Print all log messages to file, and only print log whose level is greater
than ERROR to stdout. The log file is located in '/tmp/xxx.log' if the module
name is xxx.py. The default log file handler is size-rotated, if the log
file's size is greater than 20M, then it will be rotated.

Example 2: Use set_logger to change settings

    # Change limit size in KB of default rotating action
    log.set_logger(limit = 10240) # 10M

    # Use time-rotated file handler, each day has a different log file, see
    # logging.handlers.TimedRotatingFileHandler for more help about 'when'
    log.set_logger(when = 'D', limit = 1)

    # Use normal file handler (not rotated)
    log.set_logger(backup_count = 0)

    # File log level set to INFO, and stdout log level set to DEBUG
    # Stdout log level can be set to QUIET if you don't want to print log to stdout
    log.set_logger(level = 'DEBUG:INFO')

    # Both log level set to INFO
    log.set_logger(level = 'INFO')

    # Change default log file name and log mode
    log.set_logger(filename = 'yyy.log', mode = 'w')

    # Change default log formatter
    log.set_logger(fmt = '[%(levelname)s] %(message)s')

    # Prepend prefix before log line
    log.set_logger(prefix = 'jobuuid:1000'
'''

__author__ = "tuantuan.lv <tuantuan.lv@alibaba-inc.com>"
__status__ = "Development"

import os
import sys
import logging
import traceback
import inspect
import logging.handlers

# Color escape string
COLOR_RED='\033[1;31m'
COLOR_GREEN='\033[1;32m'
COLOR_YELLOW='\033[1;33m'
COLOR_BLUE='\033[1;34m'
COLOR_PURPLE='\033[1;35m'
COLOR_CYAN='\033[1;36m'
COLOR_GRAY='\033[1;37m'
COLOR_WHITE='\033[1;38m'
COLOR_RESET='\033[1;0m'

# Define log color
LOG_COLORS = {
    'DEBUG': '%s',
    'INFO': COLOR_GREEN + '%s' + COLOR_RESET,
    'WARNING': COLOR_YELLOW + '%s' + COLOR_RESET,
    'ERROR': COLOR_RED + '%s' + COLOR_RESET,
    'CRITICAL': COLOR_RED + '%s' + COLOR_RESET,
    'EXCEPTION': COLOR_RED + '%s' + COLOR_RESET,
}

# Make text colorful
def green(text):
    return COLOR_GREEN + text + COLOR_RESET

def red(text):
    return COLOR_RED + text + COLOR_RESET

def blue(text):
    return COLOR_BLUE + text + COLOR_RESET

def yellow(text):
    return COLOR_YELLOW + text + COLOR_RESET

def cyan(text):
    return COLOR_CYAN + text + COLOR_RESET

def purple(text):
    return COLOR_purple + text + COLOR_RESET

def gray(text):
    return COLOR_GRAY + text + COLOR_RESET

def white(text):
    return COLOR_WHITE + text + COLOR_RESET

# Colorful formatter
class ColoredFormatter(logging.Formatter):
    '''A colorful formatter.'''

    def __init__(self, fmt = None, datefmt = None):
        logging.Formatter.__init__(self, fmt, datefmt)

    def format(self, record):
        level_name = record.levelname
        msg = logging.Formatter.format(self, record)

        return LOG_COLORS.get(level_name, '%s') % msg

# Customize the Logger class
class PetLogger(logging.getLoggerClass()):
    '''Pet Logger class.'''
    def findCaller(self):
        '''
        Find the stack frame of the caller so that we can note the source
        file name, line number and function name.
        '''
        f = sys._getframe(2)
        #print f.f_code, self._caller_depth
        rv = "(unknown file)", 0, "(unknown function)"

        while hasattr(f, "f_code"):
            co = f.f_code
            filename = os.path.normcase(co.co_filename)

            if filename == logging._srcfile:
                f = f.f_back
                continue

            rv = (filename, f.f_lineno, co.co_name)
            break

        return rv

def _add_handler(logger, cls, level, fmt, colorful, **kwargs):
    '''Add a configured handler to the logger.'''
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.DEBUG)

    handler = cls(**kwargs)
    handler.setLevel(level)

    if colorful:
        formatter = ColoredFormatter(fmt)
    else:
        formatter = logging.Formatter(fmt)

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return handler

def _add_streamhandler(logger, level, fmt):
    '''Add a stream handler to the logger.'''
    return _add_handler(logger, logging.StreamHandler, level, fmt, True)

def _get_default_logfile():
    '''Get the default log file.'''
    filename = getattr(sys.modules['__main__'], '__file__', 'log.py')
    filename = os.path.basename(filename.replace('.py', '.log'))
    filename = os.path.join('/tmp', filename)

    return filename

def _add_filehandler(logger, level, fmt, filename , mode, backup_count,
                     limit, when, colorful = False):
    '''Add a file handler to the logger.'''
    kwargs = {}

    # If the filename is not set, use the default filename
    if filename is None:
        filename = _get_default_logfile()

    kwargs['filename'] = filename

    # Choose the filehandler based on the passed arguments
    if backup_count == 0: # Use FileHandler
        cls = logging.FileHandler
        kwargs['mode' ] = mode
    elif when is None:  # Use RotatingFileHandler
        cls = logging.handlers.RotatingFileHandler
        kwargs['maxBytes'] = limit * 1024
        kwargs['backupCount'] = backup_count
        kwargs['mode' ] = mode
    else: # Use TimedRotatingFileHandler
        cls = logging.handlers.TimedRotatingFileHandler
        kwargs['when'] = when
        kwargs['interval'] = limit
        kwargs['backupCount'] = backup_count

    return _add_handler(logger, cls, level, fmt, colorful, **kwargs)

def _reload_logger():
    '''Reload the global logger.'''
    logging.setLoggerClass(PetLogger)
    pet_logger = logging.getLogger('pet')

    if len(pet_logger.handlers) != 0:
        logging.shutdown()

        # Remove empty default log file if we set another log file
        filename = _get_default_logfile()

        if os.path.isfile(filename) and os.path.getsize(filename) == 0:
            os.remove(filename)

        pet_logger.handlers = []

    # Set logger level
    pet_logger.setLevel(logging.DEBUG)

    return pet_logger

def exception(msg, *args, **kwargs):
    '''Custom exception function.'''
    error('Exception type: %s, message: %s' % (msg.__class__.__name__, str(msg)))
    error('Traceback (most recent call last):')

    for file, lineno, funcname, text in traceback.extract_tb(sys.exc_info()[2]):
        error('  File: %s Line: %s in %s' % (file, lineno, funcname))
        error('    %s' % text)

    error('')
    error('Calling stack (most recent call last):')

    tracebk = traceback.format_stack()
    tracebk = ''.join(tracebk[:-1]).split('\n')

    for i in tracebk[:-1]: error(i)

def get_logfile():
    '''Get the log filename.'''
    pet_logger = logging.getLogger('pet')

    for handler in pet_logger.handlers:
        name = handler.stream.name

        if os.path.isfile(name):
            return name

    return None

def set_logger(filename = None, mode = 'a', level = 'DEBUG', fmt = \
        '[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s',
        prefix = None, backup_count = 5, limit = 20480, when = None,
        file_colorful = False):
    '''Configure the global logger.'''
    level = level.split(':')

    if len(level) == 1: # Both set to the same level
        s_level = f_level = level[0]
    else:
        s_level = level[0]  # StreamHandler log level
        f_level = level[1]  # FileHandler log level

    # Prepend prefix to log line
    if prefix: fmt = '[%s] %s' % (prefix, fmt)

    # Reload the logger
    pet_logger = _reload_logger()

    if s_level != 'QUIET':
        _add_streamhandler(pet_logger, s_level, fmt)

    # File log level could not be set to QUIET
    if f_level == 'QUIET':
        f_level = 'DEBUG'

    _add_filehandler(pet_logger, f_level, fmt, filename, mode,
                     backup_count, limit, when, file_colorful)

    # Import the common log functions for convenient
    curr_mod = sys.modules[__name__]
    log_funcs = ['debug', 'info', 'warning', 'error', 'critical']

    for func_name in log_funcs:
        func = getattr(pet_logger, func_name)
        setattr(curr_mod, func_name, func)

    # Alias for warning method
    warning = getattr(curr_mod, 'warning')
    setattr(curr_mod, 'warn', warning)

# Set a default logger
set_logger()

# vim: set expandtab smarttab shiftwidth=4 tabstop=4:
