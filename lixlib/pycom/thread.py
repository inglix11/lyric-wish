#!/usr/ali/bin/python

'''
A simple interface to utilize the multithreading library.

See test_main() for mor examples.
'''

# Can be 'Prototype', 'Development', 'Product'
__status__ = 'Development'
__author__ = 'tuantuan.lv <tuantuan.lv@alibaba-inc.com>'

import Queue
import threading

def _run(func, inq, ouq, *args):
    '''Simple threading target functions.'''
    while not inq.empty():
        item = inq.get()

        out = func(item, *args)
        ouq.put(out)

        inq.task_done()

def threads(num, func, inl, *args):
    '''Run function in multi-threading.

    num: the maximum threads number.
    func: your work function, the first argument is read from inl list.
    inl: the input list.
    args: extra arguments for work function.

    Return a list of values returned from work function.
    '''
    inq = Queue.Queue()
    ouq = Queue.Queue()

    for item in inl:
        inq.put(item)

    _args = [func, inq, ouq]
    _args.extend(list(args))
    args = tuple(_args)
    del _args

    for i in range(0, num):
        worker = threading.Thread(target = _run, args = args)
        worker.setDaemon(True)
        worker.start()

    inq.join()
    oul = []

    while not ouq.empty():
        item = ouq.get()
        oul.append(item)

    return oul

def test_main():
    inl = range(0, 1000)

    def test(item, times):
        print item, times
        return item

    print "===init==="
    oul = threads(50, test, inl, 10)
    print "===results==="
    print oul

if __name__ == '__main__':
    test_main()
