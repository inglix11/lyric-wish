export PATH=/usr/local/python/bin/:$PATH
PATH=/usr/local/bin/:$PATH
*/5 * * * * cd /root/weibo&&python test_weibo.py -c conf/garden.conf -a get  >> /tmp/xx 2>&1 &
*/5 * * * * cd /root/weibo&&python test_weibo.py -c conf/iamnana.conf -a get >> /tmp/xx 2>&1 &
