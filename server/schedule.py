#coding=utf-8

from log import log
from uuid import uuid1
from functools import wraps
from util import Timer


class LogicSchedule():
    """
        Single thread logic schedule
    """
    def __init__(self):
        self.logic_streams = {}     
        self.signal_wait = {}
        self.signal_pending = {}
        self.current_uid = None
        self.return_data = None
        self.return_flag = False
        self.log = log 


    def join(self, logic_func, uid = None):
        if uid == None:
            uid = self.current_uid
        else:
            self.current_uid = uid 

        #self.log.debug("[%s]: jion func %s" % (uid, logic_func))
        streams = self.logic_streams.get(uid, []) 
        if streams:
            streams.append(logic_func)
        else:
            self.logic_streams[uid] = [logic_func]



    def creturn(self, data):
        self.return_data = data
        self.return_flag = True
        self.pop()


    def pop(self):
        streams = self.logic_streams.get(self.current_uid, False)

        if streams:
            #self.log.debug('[%s]: pop' % self.current_uid)
            streams.pop()



    def run(self, uid, data):
        #self.log.debug('schedule running')
        if uid == None:
            uid = self.current_uid 
        elif uid == -1:
            return 
        else:
            self.current_uid = uid
    
        streams = self.logic_streams.get(uid, False)
        if not streams:
            return 

        while True:
            if len(streams) == 0:
                self.clear(uid)
                self.return_flag = False
                return
            else:
                logic_func = streams[-1]
                
            #self.log.debug('[%s]: run %s %s' % (uid, logic_func, self.return_flag))

            if self.return_flag:
                data = self.return_data         
                self.return_flag = False

            result = logic_func.send(data)

            #maybe change in every logic_func
            if self.return_flag == False:
                break
                
        return 



    def waitsignal(self, signame):
        if self.signal_wait.has_key(signame):
            self.signal_wait[signame].append(self.current_uid)
        else:
            self.signal_wait[signame] = [self.current_uid]


    def notify(self, signame):
        wlist = self.signal_wait.get(signame)
        if not wlist:
            return 

        uid = wlist.pop()
        self.signal_pending[uid] = signame 
         

    def signal_handle(self):
        if not self.signal_pending:
            return 

        for uid, signame in self.signal_pending.items():
            self.run(uid, signame)    
        self.signal_pending = {}
        


    def clear(self, uid):
        if self.logic_streams.has_key(uid):
            del self.logic_streams[uid]

    

        
g_logic_schedule = LogicSchedule()


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

            #make generator
            generator = func(*args)    

            #gen uid
            uid = None
            if new_logic:
                uid = uuid1().hex

            #join schedule
            g_logic_schedule.join(generator, uid)

            if new_logic:
                result = g_logic_schedule.run(uid, None)
            else: #avoid generator nested
                result = generator.next()

            return result

        return logic_func
    
    return _logic_func



def schedule_sleep(sec):
    return Timer(sec, g_logic_schedule.run, g_logic_schedule.current_uid, None)
    
    
def schedule_waitsignal(signame):
    g_logic_schedule.waitsignal(signame)
    
    
def schedule_notify(signame):
    g_logic_schedule.notify(signame)


def creturn(*args):
    lenth = len(args)
    if lenth == 0:
        data = None 
    elif lenth == 1:
        data = args[0]
    else:
        data = args

    g_logic_schedule.creturn(data)



__all__ = ['logic_schedule', 'creturn', 'g_logic_schedule', 'schedule_sleep', 
            'schedule_waitsignal', 'schedule_notify']
