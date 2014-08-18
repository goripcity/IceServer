#coding=utf-8

import sys
from time import sleep
from functools import partial
from ctypes import *

from define import *

LIBNAME = "libhiredis.so"

#define REDIS_REPLY_STRING 1
#define REDIS_REPLY_ARRAY 2
#define REDIS_REPLY_INTEGER 3
#define REDIS_REPLY_NIL 4
#define REDIS_REPLY_STATUS 5
#define REDIS_REPLY_ERROR 6

REDIS_REPLY_STRING = 1
REDIS_REPLY_ARRAY = 2
REDIS_REPLY_INTEGER = 3
REDIS_REPLY_NIL = 4
REDIS_REPLY_STATUS = 5
REDIS_REPLY_ERROR = 6

#define REDIS_ERR -1
#define REDIS_OK 0

REDIS_ERR = -1
REDIS_OK = 0

#define REDIS_CONNECTED 0x2
REDIS_CONNECTED = 0x2

ConnCBFUNC = CFUNCTYPE(None, POINTER(redisAsyncContext), c_int)
RedisCBFUNC = CFUNCTYPE(None, POINTER(redisAsyncContext), c_void_p, c_void_p)


class Connection(object):
    def __init__(self, context, hiredis):
        self.context = context
        self.hiredis = hiredis
        self.reply = POINTER(redisReply)


    def py_reply(self, reply = None, free = True):
        """ convert c struct to python """

        if reply == None:
            reply = self.reply

        if bool(reply) == False:
            return None

        result = None

        p = reply[0]
        if p.type in [REDIS_REPLY_STRING, REDIS_REPLY_STATUS, REDIS_REPLY_ERROR]:
            result = p.str
        elif p.type == REDIS_REPLY_INTEGER:
            result = p.integer
        elif p.type == REDIS_REPLY_ARRAY:
            result = []
            for i in range(0, p.elements):
                result.append(self.py_reply(p.element[i], False))              

        if free:
            self.hiredis.freeReplyObject(reply)
            self.reply = POINTER(redisReply)

        return result

    
    def command(self, *args):
        self.reply = self.hiredis.redisCommand(self.context, *args)
        return self.py_reply()
        


    def set(self, key, value):
        return self.command("SET %b %b", 
                            key, c_size_t(len(key)), 
                            value, c_size_t(len(value)))


    def get(self, key):
        return self.command("GET %b", key, c_size_t(len(key))) 
        


    def ping(self):
        return self.command("PING")



    def incr(self, counter):
        return self.command("INCR %b", counter, c_size_t(len(counter)))



    def delete(self, key):
        """ return 0/1 """
        return self.command("DEL %b", key, c_size_t(len(key)))


    
    def lpush(self, key, element):
        return self.command("LPUSH %b %b",
                            key, c_size_t(len(key)),
                            element, c_size_t(len(element)))
        

    def lrange(self, key, start, end):
        return self.command("LRANGE %b %d %d", 
                            key, c_size_t(len(key)),
                            start, end)


    def close(self):
        self.hiredis.redisFree(self.context)



class AsyncConnection(Connection):
    def __init__(self, context, hiredis):
        super(AsyncConnection, self).__init__(context, hiredis)


    def set_callback(self, callback, data = NULLPTR):
        self.callback = RedisCBFUNC(callback)
        self.data = data


    def async_command(self, callback, data, *args):
        self.hiredis.redisAsyncCommand(self.context, callback,
                                       data, *args)

    def command(self, *args):
        self.hiredis.redisAsyncCommand(self.context, self.callback,
                                       self.data, *args)
        



class HiRedis(object):
    def __init__(self):
        self.load_library()
        self.func_init() 
        self.store_edata = None


    def load_library(self):
        try:
            self.hiredis = CDLL(LIBNAME)
        except OSError:
            self.hiredis = CDLL("./%s" % LIBNAME)


    def func_init(self):
        restype_map = {
            "redisContext": [
                "redisConnect", "redisConnectWithTimeout",
                "redisConnectNonBlock", "redisConnectBindNonBlock",
                "redisConnectUnix", "redisConnectUnixWithTimeout",
                "redisConnectUnixNonBlock", "redisConnectFd"
            ],

            "redisReply": [
                "redisCommand",
            ],
            "redisAsyncContext": [
                "redisAsyncConnect", "redisAsyncConnectBind",
                "redisAsyncConnectUnix",
            ]
        }
            
        for item in restype_map["redisContext"]:
            self.hiredis.__getattr__(item).restype = POINTER(redisContext)

        for item in restype_map["redisReply"]:
            self.hiredis.__getattr__(item).restype = POINTER(redisReply)

        for item in restype_map["redisAsyncContext"]:
            self.hiredis.__getattr__(item).restype = POINTER(redisAsyncContext)



    def get_func(self, name):
        """ use c func """
        return self.hiredis[name]

    
    @staticmethod
    def get_timeval(timeout):
        tm = Timeval()
        if isinstance(timeout, int):
            tm.tv_sec = timeout
            tm.suseconds_t = 0
        elif isinstance(timeout, float):
            tm.tv_sec = int(timeout)
            tm.suseconds_t = int((timeout - int(timeout))*1000*1000)
        else:
            return None

        return tm
            
        

    def connect(self, host = 'localhost', port = 6379 , timeout = None):
        context = POINTER(redisContext)

        if timeout:
            tm = HiRedis.get_timeval(timeout)        
            context = self.hiredis.redisConnectWithTimeout(host, port, tm)
        else:
            context = self.hiredis.redisConnect(host, port)


        status, err = self.error_context(context, self.hiredis.redisFree)
        if status == False:
            return False, err

        return True, Connection(context, self.hiredis)



    def error_context(self, context, free_c):
        if context == None or context[0].err:
            if context:
                err = "Connection error: %s" % context[0].errstr    
                free_c(context)
            else:
                err = "Connection error: can't allocate context"

            return False, err

        return True, None


    def set_callbacks(self, conn, disconn):
        """
            add connect callback and disconn callback
        """
        self.conn_callback = ConnCBFUNC(conn)                
        self.disconn_callback = ConnCBFUNC(disconn)                



    def attach_poll(self, acn):
        ev = acn.context[0].ev
        el = self.event_handler_list
        # can't assign to function...
        if el[0]:
            ev.addRead = el[0]
        if el[1]:
            ev.delRead = el[1]
        if el[2]:
            ev.addWrite = el[2]
        if el[3]:
            ev.delWrite = el[3]
        if el[4]:
            ev.cleanup = el[4]
        
        if self.store_edata:
            ev.data = cast(self.store_edata(acn), c_void_p)

    def add_event_handler(self, evlist):
        self.event_handler_list = evlist
        

    def edata_store(self, func):
        self.store_edata = func


    def async_connect(self, host = 'localhost', port = 6379):
        context = POINTER(redisAsyncContext)
        context = self.hiredis.redisAsyncConnect(host, port)
        
        status, err = self.error_context(context, self.hiredis.redisAsyncFree)
        if status == False:
            return False, err

        acn = AsyncConnection(context, self.hiredis)
        self.attach_poll(acn)
        self.hiredis.redisAsyncSetConnectCallback(context, self.conn_callback)
        self.hiredis.redisAsyncSetDisconnectCallback(context, self.disconn_callback)
        
        return True, acn


    
def pymain():
    redis = HiRedis()
    status, client = redis.connect()

    result = client.ping()  
    assert result == "PONG"
    print "PING %s" % result

    result = client.set("key", "value is v")
    assert result == "OK"
    print "SET key: [value is v] %s" % result

    result = client.get("key")
    assert result == "value is v"
    print "GET key [%s]" % result


    result = client.incr("my counter")
    assert result > 0
    print "Incr [my counter] %s" % (result)
    

    result = client.delete("my list")
    assert result in [0, 1] 
    print "Del [my list] %s" % (['none', 'ok'][result])
    

    for i in range(0,10):
        result = client.lpush("my list", "element %d" % i)
        assert result >= 1

    result = client.lrange("mylist", 0, -1)
    assert len(result) == 10
    print "Lrange [my list] ok"

    client.close()
    


def cmain():
    hiredis = CDLL("./libhiredis.so")
    hiredis.redisConnect.restype = POINTER(redisContext)
    hiredis.redisCommand.restype = POINTER(redisReply)

    c = POINTER(redisContext)
    reply = POINTER(redisReply)


    c = hiredis.redisConnect('localhost', 6379)
    print c[0].err, c[0].errstr

    reply = hiredis.redisCommand(c, "PING")
    print reply[0].str
    hiredis.freeReplyObject(reply)
    reply = hiredis.redisCommand(c, "SET %s %s", "bar", "xxx")
    print reply[0].str
    hiredis.freeReplyObject(reply)

    hiredis.redisFree(c)
    
    
aread = 0

def asyncmain():
    #hiredis = CDLL("./libhiredis.so")
    hiredis = CDLL("libhiredis.so")
    c = POINTER(redisAsyncContext)
    hiredis.redisAsyncConnect.restype = POINTER(redisAsyncContext)

    c = hiredis.redisAsyncConnect('localhost', 6379)

    ConnCBFUNC = CFUNCTYPE(None, POINTER(redisAsyncContext), c_int)
    RedisCBFUNC = CFUNCTYPE(None, POINTER(redisAsyncContext), c_void_p, c_void_p)

    def conn_callback(ac, status):
        if status == REDIS_OK:
            print "Connnect ok"
        else:
            print "Connnect error"
            sys.exit(-1)

    
    def wr_func(data):
        c = cast(data, POINTER(redisAsyncContext))
        print 'Wait Write'
        sleep(0.1)
        print 'Able to Write'
        print 'Write done'
        hiredis.redisAsyncHandleWrite(c)


    def rd_func(data):
        global aread
        c = cast(data, POINTER(redisAsyncContext))
        print 'Wait Read'
        sleep(0.1)
        if aread == 1:
            aread = 0
            print 'Able to Read'
            print 'Read done'
            hiredis.redisAsyncHandleRead(c)

        

    def getcallback(ac, r, p):
        print cast(p, c_char_p).value
        r = cast(r, POINTER(redisReply))
        print r[0].str



    global aread
    c[0].ev.addWrite = EVFUNC(wr_func)
    d = cast(c, c_void_p)
    c[0].ev.data = d
    c[0].ev.addRead = EVFUNC(rd_func)
    hiredis.redisAsyncSetConnectCallback(c, ConnCBFUNC(conn_callback))
    aread = 1
    hiredis.redisAsyncCommand(c, NULLPTR, NULLPTR, "SET key %s", "async set")
    aread = 1
    hiredis.redisAsyncCommand(c, RedisCBFUNC(getcallback), "Getcallback", "GET key")
    




if __name__ == "__main__":
    #pymain()
    #cmain()
    asyncmain()
