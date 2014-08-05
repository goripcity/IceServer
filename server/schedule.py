
#coding=utf-8

import sys, errno
from log import log
from uuid import uuid1
from functools import wraps


class LogicSchedule():
    def __init__(self):
        self.logic_streams = {}     
        self.current_uid = None
        self.return_data = None
        self.log = log 


    def join(self, logic_func, uid = None):
        if uid == None:
            uid = self.current_uid
        else:
            self.current_uid = uid 

        self.log.debug("[%s]: jion func %s" % (uid, logic_func))
        streams = self.logic_streams.get(uid, []) 
        if streams:
            streams.append(logic_func)
        else:
            self.logic_streams[uid] = [logic_func]



    def creturn(self, data):
        self.return_data = data
        self.pop()


    def pop(self):
        streams = self.logic_streams.get(self.current_uid, False)

        if streams:
            self.log.debug('[%s]: pop' % self.current_uid)
            streams.pop()



    def run(self, uid, data):
        self.log.debug('schedule running')
        if uid == None:
            uid = self.current_uid 
        else:
            self.current_uid = uid
    
        streams = self.logic_streams.get(uid, False)

        while True:
            if len(streams) == 0:
                del self.logic_streams[self.current_uid]
                self.return_data = None
                return
            else:
                logic_func = streams[-1]
                
            self.log.debug('[%s]: run %s' % (uid, logic_func))

            if self.return_data:
                data = self.return_data         
                self.return_data = None

            result = logic_func.send(data)

            if self.return_data == None:
                break
                
        return 



g_logic_schedule = LogicSchedule()


def schedule_init(log):
    g_logic_schedule.init(log)


def coroutine(func):
    @wraps(func)
    def ret(*args):
        f = func(*args)
        r = f.next()
        return f, r
    return ret 


def logic_schedule(new_logic = False):
    def _logic_func(func):
        @wraps(func)        
        def logic_func(*args):

            generator = func(*args)    

            uid = None
            if new_logic:
                uid = uuid1().hex

            g_logic_schedule.join(generator, uid)

            if new_logic:
                result = g_logic_schedule.run(uid, None)
            else:
                result = generator.next()

            return result

        return logic_func
    
    return _logic_func



def creturn(*args):
    lenth = len(args)
    if lenth == 0:
        data = True 
    elif lenth == 1:
        data = args[0]
    else:
        data = args

    g_logic_schedule.creturn(data)


