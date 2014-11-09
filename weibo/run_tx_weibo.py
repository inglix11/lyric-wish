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
reload(sys)  
sys.setdefaultencoding('utf8')
from pycom import log
from pycom import util
from pycom import database 
import urllib2
from weibo_util import *


CALLBACK_URL = 'http://www.78fg.com' # callback url
#CALLBACK_URL = 'https://api.weibo.com/oauth2/default.html' # callback url
CLIENT_IP = commands.getoutput("ifconfig eth1 | grep inet|cut -d : -f2|awk '{print $1}'")
AUTH_URL = "https://open.t.qq.com/cgi-bin/oauth2/authorize"
self_ids = ["lessli2013", "subway2013red"]


def get_api_token_manual(key, secret):
    client = APIClient(app_key=key, app_secret=secret, redirect_uri=CALLBACK_URL)
    url = client.get_authorize_url()
    print url
    code = raw_input("input the code: ").strip()
    print code
    r = client.request_access_token(code, CALLBACK_URL) 
    log.debug("key:%s, TOKEN:%s, %s"%(key, r.access_token, r.expires_in))
    return r.access_token, r.expires_in

def login_qq(qq, passwd):
    log.info("login qq:" + qq)
    url1 = "https://ssl.ptlogin2.qq.com/check?uin=" + qq + "&appid=46000101&ptlang=2052&js_type=2&js_ver=10009&r=0.7948186025712065"
    rsp = urllib2.urlopen(url1).read()
    print rsp

def get_api_token(user, key, secret):
    ''' auto auth for tx'''
    client = APIClient(app_key=key, app_secret=secret, redirect_uri=CALLBACK_URL)
    url = client.get_authorize_url()
    print url
    cookies = urllib2.HTTPCookieProcessor()
    opener = urllib2.build_opener(cookies)
    urllib2.install_opener(opener)
    #code = raw_input("input the code: ").strip()
    USERID = user
    PASSWD = '1277dcba'[::-1]
    #login_qq(user, PASSWD)
    u1 = "https://open.t.qq.com/cgi-bin/oauth2/authorize?client_id=801337811&response_type=code&redirect_uri=https%3A%2F%2Fapi.weibo.com%2Foauth2%2Fdefault.html&checkStatus=yes&appfrom=&g_tk=&sessionKey=32e0c905e164424abac18665377be36c&checkType=showAuth&state="
    postdata = {"client_id": key, "redirect_uri": CALLBACK_URL, "u": USERID, "p": PASSWD, "action": "submit", "response_type": "code",'u1':u1} 
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
    keyword = "funny"
    #ids = search_keyword(keyword, 1, 1)
    api_info = {'id' : 'subway2013', 'app_key' : '801337738', 'app_secret' : 'a12018645b29652dbcca457928177798', 'open_id' : '1D6BCF174468C94FFF00EEC9D84A3CBC', 'access_token' : 'c67120797ad666bb01c4c62485c9964d', 'expires_in' : 1365826327 }
    api_info = conf.api_info[0]
    wb = Weibo(api_info)
    #print wb.show_my_weibo()
    id = "258771045327103"
    id = "220259038452517"
    print wb.reply_create(id, "hahaha")
    #res = wb.create_weibo(keyword)

def reply_weibo(conf, table = 'txweibo'):
    niches = conf.niches
    dbi = conf.fb_info
    keywords = []
    ks = "("
    j  = 0
    for niche in niches:
        keywords.append(niche[0])
        if j != 0: ks = ks + ','
        j += 1
        ks = ks + "'" + niche[0]  + "'"
    ks = ks + ')'
    index = 0
    #conf.api_info[index]['access_token'], conf.api_info[index]['expires_in'] = get_auth(conf.api_info[index])
    wb = Weibo(conf.api_info[index])
    # Default value
    tfile = '/data/jokes/lengxh_new.txt'
    no_new_sleep = 10
    count = 0
    while True:
        account = conf.api_info[index]['id']
        if conf.tfile:
            dic = get_text(conf.tfile)
        else:
            dic = get_text(tfile)
        wdb = get_db(conf)
        if len(niches) > 0:
            sql = "select * from %s where keyword in %s and status = 0 and src_device in ('andriod客户端','微信','iPhone客户端') order by gmt_create desc limit 1"%(table,ks)
            log.info(sql)
            rds = wdb.query(sql, is_dict = True)
        if len(niches) == 0 or len(rds) == 0:
            log.warning("have no new weibo, all of keyword:%s have been reply"%(str(keywords)))
            sql = "select * from %s where status = 0 order by gmt_create desc limit 1"%table
            log.info(sql)
            rds = wdb.query(sql, is_dict = True)
            if len(rds) == 0:
                log.warning("all finished")
                time.sleep(no_new_sleep)
                no_new_sleep = (no_new_sleep * 2) % 3000
                continue
        id = rds[0].weibo_id
        keyword = rds[0].keyword
        reply_text = rds[0].reply_text
        try:
            no_new_sleep = 10
            log.debug("weibo_id:%d keyword:%s, %s will reply"%(id, keyword, account))
            #tmp_text = get_random_line(tfile)
            i = random.randint(1, len(dic) - 1)
            if conf.tfile:
                tmp_text = dic[i%len(dic)]
            else:
                tmp_text = reply_text 
            print tmp_text
            #tmp_text = dic[i%len(dic)] 
            #tmp_text = dic[i%len(dic)][:100] + "# " + reply_text
            #tmp_text = reply_text 
            res = wb.comments_create(id, tmp_text)
            log.debug("weibo_id:%d result:%s SUCCESS"%(id, res))
            print res
            i += 1
            sql = 'update %s set status = 1, reply_by = "%s", gmt_modify = now() where weibo_id = %d'%(table, account, id)
            wdb.execute(sql)
            time.sleep(interval + random.randint(1,5))
            count += 1
        except:
            res = str(sys.exc_info())
            log.error("weibo_id:%d result:%s FAILURE"%(id, res))
            #sql = 'update weibo set status = 2 where weibo_id = %d'%id
            sql = 'update %s set status = 2, reply_by = "%s", gmt_modify = now()  where weibo_id = %d'%(table, account, id)
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
        if count % 200 == 0:time.sleep(600)

def create_weibo_with_pic_url():
    sql = 'select * from original_weibo where status=1 order by rand() limit 1'
    #sql = 'select * from original_weibo where status=0 order by rand() limit 1'
    wb = Weibo(conf.api_info[0])
    wdb = get_db(conf)
    count = 0
    #time.sleep(1000)
    while True:
        rds = wdb.query(sql, is_dict = True)
        tmp_text = rds[0].text
        print tmp_text
        pic_url = rds[0].pic_url
        print pic_url
        text = tmp_text + u"#家居生活##经验#"
        text = tmp_text 
        try:
            res = wb.create_weibo_with_pic_url(text, pic_url)
            log.debug(res)
        except:
            log.warning("%s"%str(sys.exc_info()))
        u_sql = "update original_weibo set status = 1, gmt_modify = now() where text='%s'"%rds[0].text
        print u_sql
        try:
            wdb.execute(u_sql)
        except:
            print str(sys.exc_info())
        if count%4 == 0 and False:
            time.sleep(40)
            #weibo_id, content = 280076004256725, u"整点开抢了!"
            weibo_id, content = 268302069789193, u"今天是 美食和 保健品专场 "
            #weibo_id, content = 286319054033462, u"天猫大促 最后的优惠: 家装 家纺抄底价 "
            #weibo_id, content = 291343119553906, u"换家具的机会到了！"
            log.info("repost weibo_id %d with: %s"%(weibo_id, content))
            wb.repost_weibo(weibo_id, content)
        count += 1
        time.sleep(1800)
        
def create_weibo_with_pic():
    # Get images
    sql = 'select * from images where status=0 limit 1'
    wdb = get_db(conf)
    tfile = '/data/jokes/lengxh_new.txt'
    #dic = get_text(tfile)
    count = 0
    while True:
        #i = random.randint(1, len(dic) - 1)
        print sql
        rds = wdb.query(sql, is_dict = True)
        path = rds[0].path 
        if not os.path.exists(path):
            wdb.execute('delete from images where path="%s"'%path)
            continue
        bin = open(path).read()
        tmp_text = get_random_line(tfile)
        text = tmp_text + "#美女##搞笑#"
        text = tmp_text 
        wb = Weibo(conf.api_info[0])
        #res = wb.create_weibo_with_pic(text, pic_url, 1)
        image = open(path,'rb')
        try:
            res = wb.create_weibo_with_pic(text, image)
            u_sql = 'update images set status = 1 where path="%s"'%path
            wdb.execute(u_sql)
            log.debug(res)
        except:
            print str(sys.exc_info())
            
            
        if count%4 == 0 and False:
            time.sleep(40)
            #weibo_id, content = 286319054033462, u"天猫年中大促 最后一天: 家具 家纺 化妆品 "
            weibo_id, content = 268302069789193, u"今天是 美食和 保健品专场 "
            log.info("repost weibo_id %d with: %s"%(weibo_id, content))
            wb.repost_weibo(weibo_id, content)
        count += 1
        #res = wb.upload_pic(pic = image)
        #res = wb.upload_pic(pic_url, 1)
        time.sleep(1800)
    # Get joke
    # create new weibo

def search_keyword(keyword, page_start = 1, count = 1):
    ''' just for tx api '''
    all_ids = []
    #api_info = {'id' : 'subway2013', 'app_key' : '801337738', 'app_secret' : 'a12018645b29652dbcca457928177798', 'open_id' : '1D6BCF174468C94FFF00EEC9D84A3CBC', 'access_token' : 'c67120797ad666bb01c4c62485c9964d', 'expires_in' : 1365826327 }
    api_info = conf.api_info[0]
    wb = Weibo(api_info)
    for i in range(page_start, page_start + count):
        #time.sleep(5)
        text = wb.search_weibo(keyword, i)
        if text is null:continue
        text = eval(str(text))
        log.info("search:%s, page:%d, result:%s"%(keyword, i, "too large"))
        if 'data' not in text.keys() :
            log.warning("get nothing:%s",str(text))
            break
        all_ids.extend( get_weibo_ids(text) )
    all_ids = list(set(all_ids))
    print "all_ids",all_ids
    #reply_text = "good luck! 天天开心!"
    #print wb.comments_create(int(id), reply_text)
    return all_ids

def get_weibo_ids(text):
    ''' only for tencent'''
    weibo_ids = []
    reload(sys)
    sys.setdefaultencoding('utf-8')
    for weibo in text['data']['info']:
        if weibo['type'] == 1:
            print weibo['from'], weibo['fromurl']
            #if "t.qq" in weibo['fromurl']:
            weibo_ids.append(weibo['id'])
    return weibo_ids

def get_bible_text(fn = 'bible.txt'):
    dic = [] 
    for line in open(fn):
        dic.append(line)
    return dic


#def get_auth(api_info):
#    key = api_info['app_key']
#    secret = api_info['app_secret']
#    user = api_info['id']
#    return get_api_token(user, key, secret)

    #niche = ("我要减肥", "嗯！ 生命在于运动，我要瘦成一道闪电! http://955.cc/cNHn http://955.cc/cNHu")
    #niche = ("入住新房", "恭喜入住，新房除甲醛 净化空气很有必要 http://955.cc/cQth")
    #niche = ("肩颈", "有按摩椅有空可以随时按一下， 舒服很多, 这两个还不错 http://955.cc/cR4w http://955.cc/cM9f")
    #niche = ("老爸老妈", "关爱 http://955.cc/cR4w http://955.cc/cM9f")
    #坐月子,产假结束
    ##niche = ("买跑步机", "嗯！ 生命在于运动, 锻炼从现在开始: http://955.cc/cNHn http://955.cc/cNHu")
    ##niche = ("圣经", "嗯！ 生命在于运动, 锻炼从现在开始: http://955.cc/cNHn http://955.cc/cNHu")
    #niche = ("打扫房间", "轻松搞定卫生 http://fangzuzong.com/?p=44")
    #niche = ("打扫房间", " http://955.cc/cYVy  take it easy ")
    #niche = ("准备买跑步机"," http://955.cc/cNHn http://955.cc/cNHu  生命在于运动!")
    ##niche = ("打扫房间", "轻松搞定卫生 http://fangzuzong.com/?p=44")
    ##niche = ("打扫房间", " http://955.cc/cYVy  goodluck! ")
    #niche = ("买吸尘器", "http://fangzuzong.com/?p=44 旋转 ")
    #niche = ("搬新家", "")
    
def create_new_account():
    api_info = conf.api_info[0]
    key = api_info['app_key']
    secret = api_info['app_secret']
    get_api_token_manual(key, secret)

def save_to_original_weibo(text, pic_url):
    table = 'original_weibo'
    sql = "insert into %s(text, pic_url, gmt_create, gmt_modify) value('%s', '%s', now(), now())"%(table, text, pic_url)
    wdb = get_db(conf)
    try:
        wdb.execute(sql)
    except:
        print str(sys.exc_info())

def save_to_db(wb_infos, keyword, reply_text, table = 'txweibo'):
#def save_to_db(wb_ids, keyword, reply_text, table = 'txweibo'):
    wdb = get_db(conf)
    sql = 'select weibo_id from %s'%table
    res = wdb.query(sql)
    old = [ row[0] for row in res ]
    print wb_infos
    for wb in wb_infos:
        id = wb['id']
        user_name = str(wb['name'])
        print id, user_name
        if int(id) in old: continue
        if 'from' in wb.keys():
            src_device = str(wb['from'])
        else:
            src_device = "unknow"
        if 'create_time' in wb.keys():
            create_time = wb['create_time']
            sql = "insert into %s(weibo_id,user_name, keyword, reply_text, gmt_create, gmt_modify, src_device) value(%d, '%s', '%s', '%s', '%s', now(),'%s')"%(table,int(id), user_name, keyword, reply_text, create_time, src_device)
        else:
            sql = "insert into %s(weibo_id,user_name, keyword, reply_text, gmt_create, gmt_modify, src_device) value(%d, '%s', '%s', '%s', now(), now(),'%s')"%(table,int(id), user_name, keyword, reply_text, src_device)
        print sql
        try:
            rd  = wdb.execute(sql)
        except:
            print str(sys.exc_info())


def search_weibo(niches):
    for niche in niches:
        keyword = niche[0]
        reply_text = niche[1]
        page = niche[2:]
        print keyword, page[0], page[1]
        ids = search_keyword(keyword, page[0], page[1])
        print 'res',ids
        save_to_db(ids, keyword, reply_text) 
 
   
def get_user_weibo(conf):
    ''' save to db and file '''
    user_name = conf.src_weibo['user_name']
    page_num  = conf.src_weibo['page_num']
    f = open(conf.tfile, 'a')
    wb = Weibo(conf.api_info[0])
    #text = wb.get_user_weibo(user_name)
    log.info("get weibo from user:%s"%user_name)
    reload(sys)
    sys.setdefaultencoding('utf-8')
    page_flag, last_id, page_time = 0,0,0
    for i in range(1, page_num):
        text = wb.get_user_weibo(user_name, page_flag, page_time, last_id)
        for weibo in text.data.info:
            if not weibo.image:continue
            if "http" in weibo.text:continue
            pic_url = weibo.image[0]
            for url in weibo.image[1:]:
                pic_url = pic_url + ',' + url
            print weibo.text, pic_url, weibo.name
            # Store text and url into db
            save_to_original_weibo(weibo.text, pic_url)
            # Write text into db For reply usage
            f.write(weibo.text + '\n')
            #f.write(weibo.text + '*' + pic_url + '\n')
            #f.write(pic_url + '\n')
            # Download image to local and store path into image
            # if(i>2):save_weibo_image(pic_url, "/data/images/meinv")
        
        page_flag, last_id, page_time = 1, text.data.info[-1].id, text.data.info[-1].timestamp
    #keep order and unique
    #os.system('sort -u %s -o %s'%(conf.tfile, conf.tfile))
        
def save_weibo_image(pic_url, local_dir):
    tmp_name = os.path.basename(pic_url) 
    path = local_dir + "/" + tmp_name + ".jpg"
    pic_url += "/460"
    urllib.urlretrieve(pic_url, path) 
    sql = "insert into images(path) value('%s')"%path
    wdb = get_db(conf)
    try:
        wdb.execute(sql)
    except:
        print str(sys.exc_info())
    
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
        # Create new weibo with joke and image 
        create_weibo_with_pic_url()
    elif action == 'auth':
        # Get auth token  
        print get_auth(api_info)
    elif action == 'search_active':
        # Follow some body 
        search_active(conf)
    elif action == "reply_famous":
        # Reply some famous people's weibo
        reply_famous(conf)
    else:
        # Get auth token  
        print "do nothing"
    # TODO:create new adv and remove old one

def reply_famous(conf):
    count = 200000
    wait_time = 300
    for i in range(1, count):
        reply_famous_people(conf)
        log.info("will sleep %d s...."%wait_time)
        time.sleep(wait_time)

# Reply famous people's new weibo
def reply_famous_people(conf):
    page_flag, last_id, page_time = 0,0,0
    wb = Weibo(conf.api_info[0])
    for obj in conf.obj_userlist:
        user_name = obj['user_name']
        keyword   = obj['keyword']
        weibo_num = obj['weibo_num']
        reply_num = 200
        try:
            res = wb.get_user_weibo(user_name, page_flag, page_time, last_id)
        except:
            log.error(str(sys.exc_info()))
            time.sleep(10)
            continue
        for weibo in res.data.info[0:weibo_num]:
            # Maybe will need to reply this hot weibo direct
            weibo_id = int(weibo.id)
            tmp_text = get_random_line(conf.tfile)
            x = time.localtime(weibo.timestamp)
            time_str = str(time.strftime('%Y-%m-%d %H:%M:%S',x))
            log.info("FROM:%s user %s's  weibo: text:%s weibo_id:%d  at:%s"%(weibo['from'], user_name, weibo.text, weibo_id, time_str))
            try:
                all_reply = wb.get_all_reply_list(weibo_id, max_num = reply_num)
                need_reply = True
                for inf in all_reply:
                    if inf.name in self_ids:
                        need_reply = False
                        break
                if need_reply != True:
                    log.warning("cold weibo, not need relpy")
                    continue
                time.sleep(6)
                res = wb.comments_create(weibo_id, tmp_text)
            except:
                log.error(str(sys.exc_info()))
            log.info("reply text:%s"%tmp_text)
            time.sleep(40)


def search_active(conf):
    count = 200000
    wait_time = 1800
    for i in range(1, count):
        search_active_userlist(conf)
        log.info("will sleep %d s...."%wait_time)
        time.sleep(wait_time)

# observer an famous people's relpy
def search_active_userlist(conf):
    page_flag, last_id, page_time = 0,0,0
    wb = Weibo(conf.api_info[0])
    for obj in conf.obj_userlist:
        user_name = obj['user_name']
        keyword   = obj['keyword']
        weibo_num = obj['weibo_num']
        reply_num = obj['reply_num']
        try:
            res = wb.get_user_weibo(user_name, page_flag, page_time, last_id)
        except:
            log.warning("%s"%str(sys.exc_info()))
            continue
        for weibo in res.data.info[0:weibo_num]:
            # Maybe will need to reply this hot weibo direct
            weibo_id = int(weibo.id)
            #tmp_text = get_random_line(conf.tfile)
            
            x = time.localtime(weibo.timestamp)
            time_str = str(time.strftime('%Y-%m-%d %H:%M:%S',x))
            log.info("FROM:%s user %s's  weibo: text:%s weibo_id:%d  at:%s"%(weibo['from'], user_name, weibo.text, weibo_id, time_str))
            search_active_weibo(weibo_id, keyword, reply_num)

def search_active_weibo(weibo_id, keyword, reply_num):
    # Get all reply
    reply_text = ""
    wb = Weibo(conf.api_info[0])
    #all_reply = wb.get_reply_list(weibo_id)
    all_reply = wb.get_all_reply_list(weibo_id, max_num = reply_num)
    # Get Active user list
    user_list = []
    log.info("get reply num:%d"%len(all_reply))
    for inf in all_reply:
        if inf.name in self_ids: continue
        if inf.name not in user_list:user_list.append(inf.name) 
        #log.info("user:%s reply:%s from:%s at:%s"%(inf.name, inf.text, inf['from'], inf.timestamp))
    # Get the user's latest weibo and store into db
    page_flag, last_id, page_time = 0,0,0
    ids = []
    wb_infos = []
    i = 0
    #while i < len(user_list):
    wdb = get_db(conf)
    sql = "select distinct user_name from txweibo"
    res = wdb.query(sql)
    all_user_in_db = [ it[0] for it in res ] 
    for username in user_list:
        '''end = i + 30 - 1
        if end  > len(user_list): end = -1
        usernames_str = str(user_list[i])
        username_list = user_list[i+1:end]
        for name in username_list:
            usernames_str = usernames_str + ',' + str(name)
        print usernames_str
        i = end + 1
        '''
        new_weibo = {} 
        res = None
        if username in all_user_in_db: 
            log.warning("the same user:%s"%username)
            continue
        try:
            #res = wb.get_users_weibo(usernames_str, page_flag, page_time, last_id)
            res = wb.get_user_weibo(username, page_flag, page_time, last_id)
            latest = res.data.info[0]
        except:
            log.warning("%s"%str(sys.exc_info()))
            if res:log.error("res:%s"%str(res))
            #break
            continue
        time.sleep(2)
        weibo_id = int(latest.id)
        new_weibo['name'] = username
        new_weibo['id'] = weibo_id
        new_weibo['from'] = latest['from']
        #for latest in res.data.info[0:1]:
        x = time.localtime(latest.timestamp)
        time_str = str(time.strftime('%Y-%m-%d %H:%M:%S',x))
        new_weibo['create_time'] = time_str
        print new_weibo
        #log.info("the newest weibo: weibo_id:%d at:%s"%(weibo_id, time_str))
        log.info("#FROM:%s user %s's the newest weibo: text:%s weibo_id:%d  at:%s"%(latest['from'],username, latest.text, weibo_id, time_str))
        ids.append(weibo_id)
        wb_infos.append(new_weibo)
        all_user_in_db.append(username)
        #if end == -1: break
    save_to_db(wb_infos, keyword, reply_text) 
        

def get_auth(api_info):
    key = api_info['app_key']
    secret = api_info['app_secret']
    user = api_info['id']
    return get_api_token_manual(key, secret)
    #return get_api_token(user, key, secret)

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
    global interval
    interval = 300
    print conf.api_info
    print dir(conf)
    if 'proxy' in dir(conf):
        set_proxy(conf.proxy)
        #set_proxy("42.120.49.114:31290")
    if 'interval' in dir(conf):
        interval = conf.interval
    run_work(conf, action)

