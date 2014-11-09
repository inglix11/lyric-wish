#!/usr/bin/env python
#! coding=utf-8

from qqweibo import APIClient
import qqweibo as weibo
import commands
import os
import sys
import time
from pycom import database 
from pycom import log
import random
import base64
import urllib2

CALLBACK_URL = 'https://api.weibo.com/oauth2/default.html' # callback url
CLIENT_IP = commands.getoutput("ifconfig eth1 | grep inet|cut -d : -f2|awk '{print $1}'")
def get_text(fn):
    dic = [] 
    for line in open(fn):
        dic.append(line)
    return dic

def set_proxy(proxy):
    log.info("set proxy:%s"%proxy)
    proxy_handler = urllib2.ProxyHandler({'http': proxy,'https': proxy})
    #proxy = urllib2.ProxyHandler({'https': proxy})
    proxy_auth_handler = urllib2.HTTPBasicAuthHandler()
    proxy_auth_handler.add_password(None, '', 'admin', 'hell05a')
    opener = urllib2.build_opener(proxy_handler, proxy_auth_handler)
    urllib2.install_opener(opener)
    #weibo.urllib2.install_opener(opener)
    #weibo.set_proxy(proxy)
    weibo.weibo_proxy = proxy


def get_random_line(fn):
    ''' must less than 140 '''
    dic = get_text(fn)
    while True:
        i = random.randint(1, len(dic) - 1)
        if len(dic[i]) < 140*3:break
    return dic[i]

def get_db(conf):
    dbi = conf.fb_info
    wdb = database.DB(auto_commit = True, host = dbi['pi'][::-1], user = dbi['resu'][::-1], passwd = 'Hello7721', db = 'weibo')
    #wdb = database.DB(auto_commit = True, host = dbi['pi'][::-1], user = dbi['resu'][::-1], passwd = base64.decodestring(dbi['dwssap']), db = 'weibo')
    return wdb

# For QQ
class Weibo:
    
    def __init__(self, api_info):
        self.client = APIClient(app_key = api_info['app_key'], app_secret = api_info['app_secret'])
        self.client.set_access_token(api_info['access_token'], api_info['open_id'],api_info['expires_in'])

    def search_weibo(self, text, page = 1, page_size = 30):
        return self.client.get.search__t(keyword = text, page = page, pagesize = page_size)

    def show_my_weibo(self):
        return self.client.post.statuses__broadcast_timeline()
    
    def get_users_weibo(self, username_list, page_flag = 1, page_time = 0, last_id = 0 ):
        return self.client.get.statuses__users_timeline_ids(names = username_list, type = 1, contenttype = 0, pageflag = page_flag, pagetime = page_time, lastid = last_id, reqnum = 70)

    def get_user_weibo(self, username, page_flag = 1, page_time = 0, last_id = 0 ):
        return self.client.get.statuses__user_timeline(name = username, type = 1, contenttype = 0, pageflag = page_flag, pagetime = page_time, lastid = last_id, reqnum = 70)

    def create_weibo(self, text):
        return self.client.post.t__add(content = "hello world！", clientip = CLIENT_IP)
        #return self.client.post.statuses__update(status = text)

    def upload_pic(self, pic):
        return self.client.upload.t__upload_pic(pic = pic, pic_url = "")
        #if pic_type == 1:
        #    return self.client.upload.t__upload_pic(pic_url = pic_url, pic_type = pic_type)
        #elif pic_type == 2:
        #    return self.client.upload.t__upload_pic(pic = pic, pic_type = pic_type)

    def create_weibo_with_pic(self, text, pic):
        return self.client.upload.t__add_pic(content = text, pic = pic )

    def create_weibo_with_pic_url(self, text, pic_url):
        return self.client.upload.t__add_pic_url(content = text, pic_url = pic_url )

    def repost_weibo(self, id, text):
        return self.client.post.t__re_add(reid = id, content = text)
        #return self.client.post.statuses__repost(id = id, status = text, is_comment = is_comment)
    
    def comments_show(self, id):
        ''' list all the reply of one weibo '''
        return self.client.get.comments__show(id = id)
        
    def comments_create(self, id, text):
        return self.client.post.t__comment(reid = id, content = text)

    def reply_create(self, id, text):
        return self.client.post.t__reply(reid = id, content = text)

    def comments_reply(self, id, cid, text):
        return self.client.post.comments__reply(id = id , cid = cid, comment = text)

    def get_reply_list(self, id, flg = 2, page_flag = 0, twitter_id = 0, req_num = 10, page_time = 0):
        return self.client.get.t__re_list(rootid = id, reqnum = req_num, flag = flg, pageflag = page_flag, pagetime = page_time, twitterid = twitter_id)
    def get_all_reply_list(self, id, max_num = 100):
        all_reply = []
        page_flag = 0
        twitter_id = 0
        page_time = 0
        get = 0
        res = None
        while True:
            try:
                res = self.get_reply_list(id, page_flag = page_flag, twitter_id = twitter_id, page_time = page_time)
                data = res.data
                last_weibo = data.info[-1]
            except:
                time.sleep(10)
                log.error("get reply failed " + str(sys.exc_info()))
                if res:log.error(str(res))
                break
                #continue
            page_time = last_weibo.timestamp
            twitter_id = last_weibo.id
            page_flag = 1
            all_reply.extend(data.info)
            get += len(data.info)
            print get, max_num, data.hasnext, twitter_id, page_time
            #if data.hasnext == 0: break
            if get >= max_num: break
        return all_reply



