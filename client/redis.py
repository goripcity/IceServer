import os,sys
sys.path.append('../')
from server import *
from hiredis import *

_redisname = None

        


class RedisClientAction(TcpClientAction):
    def __init__(self, connect_addr, name, num = 3):
        super(RedisClientAction, self).__init__(connect_addr, name, num)
        global _redisname
        _redisname = name
        self.contexts = {}
        self.sd_wait = {}


    @staticmethod
    def get_self(): 
        return conn.get(_redisname)
        


    @staticmethod
    def add_write(data):
        print "add_write"
        self = RedisClientAction.get_self()
        p = cast(data, c_char_p)
        fd, acn = self.contexts[p.value]
        self.server.wait_write(fd, self.write_event, acn.context)


    @staticmethod
    def add_read(data):
        print "add_read"
        self = RedisClientAction.get_self()
        p = cast(data, c_char_p)
        fd, acn = self.contexts[p.value]
        self.server.wait_read(fd, self.read_event, acn.context)


    @staticmethod
    def del_write(data):
        print "del_write"
        self = RedisClientAction.get_self()
        p = cast(data, c_char_p)
        fd, acn = self.contexts[p.value]
        self.server.del_write(fd)


    @staticmethod
    def clean_up(data):
        print "clean_up"
        self = RedisClientAction.get_self()
        p = cast(data, c_char_p)
        fd, acn = self.contexts[p.value]
        self.server.clean_up(fd)


    @staticmethod
    def conn_callback(ac, status):
        self = RedisClientAction.get_self()
        fd = ac[0].c.fd
        suid = self.sd_wait[fd]
        del self.sd_wait[fd]

        if status == 0:
            status = True
        else:
            status = False

        self.server.schedule.run(suid, status)
        


    @staticmethod
    def disconn_callback(ac, status):
        self = RedisClientAction.get_self()
        fd = ac[0].c.fd
        suid = self.sd_wait.get(fd)
        if suid:
            del self.sd_wait[fd]
            self.server.schedule.run(suid, None)
        
        p = cast(ac[0].ev.data, c_char_p)
        del self.contexts[p.value]
        self.repair()



    @staticmethod
    def redis_callback(ac, r, p):
        self = RedisClientAction.get_self()
        fd = ac[0].c.fd
        suid = self.sd_wait[fd]
        del self.sd_wait[fd] 
        p = cast(ac[0].ev.data, c_char_p)
        fd, acn = self.contexts[p.value]
        r = cast(r, POINTER(redisReply))

        res = acn.py_reply(r, False)
        self.server.schedule.run(suid, res)
        
        
        
        
    def write_event(self, context):
        self.redis.hiredis.redisAsyncHandleWrite(context)
            
        
    def read_event(self, context):
        self.redis.hiredis.redisAsyncHandleRead(context)


    def save_conn(self, acn):
        uid = get_uid()
        fd = acn.context[0].c.fd
        self.contexts[uid] = (fd, acn)
        return c_char_p(uid)


    def init(self):
        redis = HiRedis()
        redis.set_callbacks(self.conn_callback, self.disconn_callback)
        redis.add_event_handler([EVFUNC(self.add_read), '', 
                                 EVFUNC(self.add_write), EVFUNC(self.del_write),
                                 EVFUNC(self.clean_up)])
        #save aysnc conn here, return uid, find context from uid when running callbacks
        redis.edata_store(self.save_conn) 

        self.redis = redis



    def schedule_wait(self, ac):
        self.sd_wait[ac[0].c.fd] = self.server.schedule.current_uid


    @logic_schedule()
    def connect(self, addr):
        status, acn = self.redis.async_connect(addr[0], addr[1])
        if status == False:
            self.log.error("[%s] : connect %s error" % (self.name, addr))
            yield creturn(-1)
            
        self.schedule_wait(acn.context)
        status = yield 

        if status == False:
            self.log.error("[%s] : connect %s error" % (self.name, addr))
            yield creturn(-1)


        self.log.debug("[%s] : Connect to %s success" % (self.name, addr))

        acn.set_callback(self.redis_callback)

        yield creturn(acn)



    @logic_schedule()
    def pop_client(self):
        while len(self.conn_pool) == 0:
            yield schedule_waitsignal(self.signame)
            continue

        ac = self.conn_pool.pop()
        yield creturn(ac)



    def push_client(self, ac):
        schedule_notify(self.signame)
        self.conn_pool.append(ac)


