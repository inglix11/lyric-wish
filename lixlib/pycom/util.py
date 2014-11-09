#!/usr/ali/bin/python
# coding=utf-8
import sys
def my_log(msg, flag=0):                                                                                                                
    if flag == 1:#red                                                                                                                   
        msg = "\033[1;31;40m%s\033[0m"%msg                                                                                              
    if flag == 2:#green                                                                                                                 
        msg = "\033[1;32;40m%s\033[0m"%msg                                                                                              
    print msg                                                                                                                           
    #logger.debug(msg)                                                                                                                   
                                                                                                                                        
def load_cfg(cfg_file):                                                                                                                 
    text = open(cfg_file).read()                                                                                                        
    module = type(sys)                                                                                                                  
    m = module(cfg_file)                                                                                                                
    exec compile(text,"",'exec') in m.__dict__                                                                                          
    return m            
