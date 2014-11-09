#! coding=utf-8
import sys
import os
import urllib
import time
import getopt
import random
import commands
import base64
sys.path.append('/usr/local/lixlib')
import urllib2
import weibo
from pycom import log
from weibo import APIClient
from pycom import util
from pycom import database 
#import ts
APP_KEY = '244126556' # app key
APP_SECRET = 'b6fcbf1dd875a525d5123c36555d1da2' # app secret
CALLBACK_URL = 'https://api.weibo.com/oauth2/default.html' # callback url
AUTH_URL = 'https://api.weibo.com/oauth2/authorize'

def get_api_token(user, key, secret):
    ''' auto auth for sina '''
    client = APIClient(app_key=key, app_secret=secret, redirect_uri=CALLBACK_URL)
    url = client.get_authorize_url()
    print url
    cookies = urllib2.HTTPCookieProcessor()
    opener = urllib2.build_opener(cookies)
    urllib2.install_opener(opener)
    #code = raw_input("input the code: ").strip()
    USERID = user
    PASSWD = '1277dcba'[::-1]
    postdata = {"client_id": key, "redirect_uri": CALLBACK_URL, "userId": USERID, "passwd": PASSWD, "isLoginSina": "0","action": "submit", "response_type": "code",} 
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; rv:11.0) Gecko/20100101 Firefox/11.0","Host": "api.weibo.com","Referer": url} 
    req = urllib2.Request(url = AUTH_URL, data = urllib.urlencode(postdata), headers = headers)
    try:
        resp = urllib2.urlopen(req)
        print "callback url is : %s" % resp.geturl()
        code = resp.geturl()[-32:]
        print "code is : %s" % code 
    except Exception, e:
        print e
    r = client.request_access_token(code, CALLBACK_URL) 
    log.debug("user:%s, key:%s, TOKEN:%s, %s"%(user, key, r.access_token, r.expires_in))
    return r.access_token, r.expires_in
    
def test_api():
    client = APIClient(app_key=APP_KEY, app_secret=APP_SECRET)
    access_token = "2.00GfdIUD0GT1WQa8798bf753u_VKnB"
    expires_in = "1522394792"
    client.set_access_token(access_token, expires_in)
    print client.post.comments__create(id=3561507327156882, comment=u'娃哈哈哈哈')

def search_keyword(keyword, page_start = 1, count = 1):
    all_ids = []
    for i in range(page_start, page_start + count):
        url = "http://s.weibo.com/weibo/%s&page=%d"%(keyword, i)
        #url = "http://s.weibo.com/weibo/%s&Refer=index"%keyword
        print url 
        log.debug(url)
        #it = urllib.urlopen(url)
        it = urllib2.urlopen(url)
        text = it.read()
        it.close()
        time.sleep(5)
        all_ids.extend( get_weibo_ids(text) )
    all_ids = list(set(all_ids))
    return all_ids

def get_weibo_ids(text):
    ls = text.split('&')
    weibo_ids = []
    for it in ls:
        if it.find("mid=") == 0:
            it = it.split('\\')[0]
            id = it.split('=')[1]
            if id not in weibo_ids:
                weibo_ids.append(id)
    return weibo_ids


class Weibo:
    
    def __init__(self, api_info):
        self.client = APIClient(app_key = api_info['app_key'], app_secret = api_info['app_secret'])
        self.client.set_access_token(api_info['access_token'], api_info['expires_in'])

    def get_user_weibo(self, username, page_no, count = 100):
        return self.client.get.statuses__user_timeline(uid = username, count = count, page = page_no)



    def create_weibo(self, text):
        return self.client.post.statuses__update(status = text)

    def create_weibo_with_pic(self, text, pic):
        return self.client.upload.statuses__upload(status = text, pic = pic)

    def repost_weibo(self, id, text, is_comment = 0):
        return self.client.post.statuses__repost(id = id, status = text, is_comment = is_comment)
    
    def follow_you(self, uid):
        return self.friendships__create(uid = uid)

    def comments_show(self, id):
        ''' list all the reply of one weibo '''
        return self.client.get.comments__show(id = id)
        
    def comments_create(self, id, text):
        return self.client.post.comments__create(id = id, comment = text)

    def comments_reply(self, id, cid, text):
        return self.client.post.comments__reply(id = id , cid = cid, comment = text)

def get_comments_cids(weibo_id):
    return [] 


# deprecated code
def get_old_weibo_ids():
    cmd="cat /tmp/test_weibo.log |grep weibo_id | grep -v result| grep -v all|awk '{print $4}'|cut -d : -f 2| sort -u"
    ids = commands.getoutput(cmd).split()
    return ids

def get_bible_text(fn = 'bible.txt'):
    dic = [] 
    for line in open(fn):
        dic.append(line)
    return dic

def save_to_db(wb_ids, keyword, reply_text):
    dbi = conf.fb_info
    wdb = database.DB(auto_commit = True, host = dbi['pi'][::-1], user = dbi['resu'][::-1], passwd = base64.decodestring(dbi['dwssap']), db = 'weibo')
    sql = 'select weibo_id from weibo'
    res = wdb.query(sql)
    old = [ row[0] for row in res ]
    for id in wb_ids:
        if int(id) in old: continue
        sql = "insert into weibo(weibo_id, keyword, reply_text, gmt_create, gmt_modify) value(%d, '%s', '%s', now(), now())"%(int(id), keyword, reply_text)
        print sql
        try:
            rd  = wdb.execute(sql)
        except:
            print str(sys.exc_info())

def get_from_db(keyword):
    dbi = conf.fb_info
    wdb = database.DB(auto_commit = True, host = dbi['pi'][::-1], user = dbi['resu'][::-1], passwd = base64.decodestring(dbi['dwssap']), db = 'weibo')
    sql = 'select * from weibo where keyword = "%s" and status = 0'%keyword
    #sql = 'select * from weibo where keyword like "%%%s%%" and status = 0'%keyword
    print sql
    res = wdb.query(sql, is_dict = True)
    return res

def run_work_old(niches, action):
    #niche = ("我要瘦", "生命在于运动，我要瘦成一道闪电! http://955.cc/cNHn http://955.cc/cNHu")
    #niche = ("我要减肥", "嗯！ 生命在于运动，我要瘦成一道闪电! http://955.cc/cNHn http://955.cc/cNHu")
    #niche = ("入住新房", "恭喜入住，新房除甲醛 净化空气很有必要 http://955.cc/cQth")
    #niche = ("肩颈", "有按摩椅有空可以随时按一下， 舒服很多, 这两个还不错 http://955.cc/cR4w http://955.cc/cM9f")
    #niche = ("老爸老妈", "送份关爱吧   http://955.cc/cR4w http://955.cc/cM9f")
    #niche = ("打扫房间", "轻松搞定 http://fangzuzong.com/?p=44")
    #niche = ("遛狗", "狗狗好伴侣 http://fangzuzong.com/?p=44")
    #keyword = niche[0]
    #reply_text = niche[1]
    #page = niche[2:]
    api_info = conf.api_info[0]
    if action == 'get':
        prepare_weibo(niches)
    elif action == 'put':
        reply_weibo(niches)
    elif action == 'create':
        create_weibo()
    elif action == 'auth':
        print get_auth(api_info)
    else:
        print "do nothing"
    #res = get_from_db(keyword)
    #ids = [ r.weibo_id for r in res ] 

def save_to_original_weibo(text, pic_url):
    table = 'original_weibo'
    sql = "insert into %s(text, pic_url, gmt_create, gmt_modify) value('%s', '%s', now(), now())"%(table, text, pic_url)
    wdb = get_db(conf)
    try:
        wdb.execute(sql)
    except:
        print str(sys.exc_info())


def get_user_weibo(conf):
    ''' save to db and file '''
    user_name = conf.src_weibo['user_name']
    page_num  = conf.src_weibo['page_num']
    f = open(conf.tfile, 'a')
    wb = Weibo(conf.api_info[0])
    log.info("get weibo from user:%s"%user_name)
    reload(sys)
    sys.setdefaultencoding('utf-8')
    for i in range(1, page_num):
        result = wb.get_user_weibo(user_name, i)
        print "res:",result
        for weibo in result.statuses:
            if not weibo.original_pic:continue
            pic_url = weibo.original_pic    
            print weibo.text, pic_url, weibo.user.screen_name
            save_to_original_weibo(weibo.text, pic_url)
            f.write(weibo.text + '\n')
    #keep order and unique
    os.system('sort -u %s -o %s'%(conf.tfile, conf.tfile))
 
def run_work(conf, action):
    api_info = conf.api_info[0]
    if action == 'search':
        # search keyword in niches and store in db
        search_weibo(conf.niches)
    elif action == 'get_weibo':
        # Get a target user's all weibo  and store in ?
        get_user_weibo(conf)
    elif action == 'reply':
        # Reply these target weibo from db 
        reply_weibo(conf)
    elif action == 'create_joke':
        # Create new weibo with joke and image 
        create_weibo_with_pic()
    elif action == 'create_expr':
        # Create new weibo with expr and image url
        create_weibo_with_pic_url()
    elif action == 'auth':
        # Get auth token  
        print get_auth(api_info)
    else:
        print "do nothing"


def search_weibo(niches):
    for niche in niches:
        keyword = niche[0]
        reply_text = niche[1]
        page = niche[2:]
        ids = search_keyword(keyword, page[0], page[1])
        print ids
        save_to_db(ids, keyword, reply_text) 
        
def reply_weibo(conf):
    #坐月子,产假结束
    niches = conf.niches
    dbi = conf.fb_info
    keywords = []
    ks = "("
    j  = 0
    reply_text = niches[0][1]
    for niche in niches:
        keywords.append(niche[0])
        if j != 0: ks = ks + ','
        j += 1
        ks = ks + "'" + niche[0]  + "'"
    ks = ks + ')'
    #log.info("all weibo id:%s"%str(ids))
    index = 0
    conf.api_info[index]['access_token'], conf.api_info[index]['expires_in'] = get_auth(conf.api_info[index])
    wb = Weibo(conf.api_info[index])
    tfile = '/data/jokes/lengxh_new.txt'
    if conf.tfile:
        dic = get_text(conf.tfile)
    else:
        dic = get_text(tfile)
    no_new_sleep = 10
    while True:
        account = conf.api_info[index]['id']
        wdb = database.DB(auto_commit = True, host = dbi['pi'][::-1], user = dbi['resu'][::-1], passwd = base64.decodestring(dbi['dwssap']), db = 'weibo')
        if len(niches) > 0:
            sql = "select * from weibo where keyword in %s and status = 0 order by gmt_create desc limit 1"%ks
            log.info(sql)
            rds = wdb.query(sql, is_dict = True)
        if len(niches) == 0 or len(rds) == 0:
            log.warning("have no new weibo, all of keyword:%s have been reply"%(str(keywords)))
            sql = "select * from weibo where status = 0 order by gmt_create desc limit 1"
            log.info(sql)
            rds = wdb.query(sql, is_dict = True)
            if len(rds) == 0:
                log.warning("all finished")
                time.sleep(no_new_sleep)
                no_new_sleep = (no_new_sleep * 2) % 3000
                continue
        id = rds[0].weibo_id
        keyword = rds[0].keyword
        # text from db
        #reply_text = rds[0].reply_text
        try:
            no_new_sleep = 10
            log.debug("weibo_id:%d keyword:%s, %s will reply"%(id, keyword, account))
            i = random.randint(1, len(dic) - 1)
            if conf.tfile:
                tmp_text = dic[i%len(dic)]
            else:
                #tmp_text = dic[i%len(dic)][:100] + "# " + reply_text
                tmp_text = reply_text 
            print tmp_text
            res = wb.comments_create(id, tmp_text)
            log.debug("weibo_id:%d result:%s SUCCESS"%(id, res))
            print res
            i += 1
            sql = 'update weibo set status = 1, reply_by = "%s", gmt_modify = now() where weibo_id = %d'%(account, id)
            wdb.execute(sql)
            time.sleep(interval + random.randint(1,15))
        except:
            res = str(sys.exc_info())
            log.error("weibo_id:%d result:%s FAILURE"%(id, res))
            #sql = 'update weibo set status = 2 where weibo_id = %d'%id
            sql = 'update weibo set status = 2, reply_by = "%s", gmt_modify = now()  where weibo_id = %d'%(account, id)
            if "only author's attention user can comment" in res or "only trust user can comment" in res:
                i += 1
                wdb.execute(sql)
                time.sleep(30)
            elif "update weibo too fast" in res:
                time.sleep(3600*3)
            elif "out of rate limit" in res or 'repeat similar content' in res or 'User does not exists' in res:
                #change a weibo_id
                index = ( index + 1 ) % len(conf.api_info)
                log.warning("switch weibo account to:%s"%account)
                if index == 0: time.sleep(3601)
                wb = Weibo(conf.api_info[index])
            elif "expired_token" in res:
                conf.api_info[index]['access_token'], conf.api_info[index]['expires_in']  = get_auth(conf.api_info[index])
                wb = Weibo(conf.api_info[index])
                time.sleep(15)
            else:
                wdb.execute(sql)
                i += 1
                time.sleep(15)

def get_auth(api_info):
    key = api_info['app_key']
    secret = api_info['app_secret']
    user = api_info['id']
    return get_api_token(user, key, secret)
    
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

def get_db(conf):
    dbi = conf.fb_info
    wdb = database.DB(auto_commit = True, host = dbi['pi'][::-1], user = dbi['resu'][::-1], passwd = base64.decodestring(dbi['dwssap']), db = 'weibo')
    return wdb

def get_text(fn):
    dic = [] 
    for line in open(fn):
        dic.append(line)
    return dic

def create_weibo_with_pic():
    # Get images
    sql = 'select * from images where status<2 limit 1'
    wdb = get_db(conf)
    tfile = '/data/jokes/lengxh_new.txt'
    dic = get_text(tfile)
    conf.api_info[0]['access_token'], conf.api_info[0]['expires_in'] = get_auth(conf.api_info[0])
    while True:
        i = random.randint(1, len(dic) - 1)
        print sql
        rds = wdb.query(sql, is_dict = True)
        path = rds[0].path 
        print path
        if not os.path.exists(path):
            wdb.execute('delete from images where path="%s"'%path)
            continue
        bin = open(path).read()
        text = dic[i%len(dic)] + "#美女##搞笑#"
        wb = Weibo(conf.api_info[0])
        print path
        try:
            image = open(path,'rb')
            res = wb.create_weibo_with_pic(text, image)
        except:
            res = str(sys.exc_info())
            log.error("image:%s result:%s FAILURE"%(path, res))
        
            if "expired_token" in res:
                conf.api_info[0]['access_token'], conf.api_info[0]['expires_in']  = get_auth(conf.api_info[0])
                wb = Weibo(conf.api_info[0])
        u_sql = 'update images set status = 2 where path="%s"'%path
        wdb.execute(u_sql)
        time.sleep(600)
 
if __name__ == '__main__':
    try:
        opts, args = getopt.getopt(sys.argv[1:], "c:a:h", [ "action=", "cfgfile=",'help']) 
        cfg_file = None
        action = ""
        for a,o in opts:
            if a in ('-c','--cfgfile'):
                cfg_file = o
            elif a in ('-a','--action'):
                action = o
            else:
                print HELP_MSG
                exit(0)
    except getopt.GetoptError,err:
        print str(err)
        exit(-1)
    if not cfg_file:
        print "cfg file: -c is need"
        exit(-1)
    global conf
    conf = util.load_cfg(cfg_file)
    # preprocess 
    if 'tfile' not in dir(conf):
        conf.tfile = None
    print conf.api_info
    print dir(conf)
    print dir(weibo)
    if 'proxy' in dir(conf):
        set_proxy(conf.proxy)
        #set_proxy("42.120.49.114:31290")
    global interval
    interval = 300
    if 'interval' in dir(conf):
        interval = conf.interval
    run_work(conf, action)
    #from ts import *
    #test_proxy()
    #wb = Weibo(api_info)
    #create_new_account()
    #get_weibo()
    #test_api()
