#! /usr/bin/env python
#coding=utf-8

import os,sys
sys.path.append('../')
from server import *
from client import *
import time
from datetime import datetime

LOOP = True
CONNECT = 1

@logic_schedule(True)
def run_clients(srv, client):
    if client.ready == False:
        run_test(srv, client)
        yield creturn()
    
    ac = yield client.pop_client()
    
    ac.command("SET key %s", "test set")
    value = yield client.schedule_wait(ac.context)
    assert value == 'OK'
    
    
    ac.command("GET key")
    value = yield client.schedule_wait(ac.context)
    assert value == 'test set'


    ac.ping()
    result = yield client.schedule_wait(ac.context)
    assert result == "PONG"
    print "PING %s" % result

    ac.set("key", "value is v")
    result = yield client.schedule_wait(ac.context)
    assert result == "OK"
    print "SET key: [value is v] %s" % result

    ac.get("key")
    result = yield client.schedule_wait(ac.context)
    assert result == "value is v"
    print "GET key [%s]" % result


    ac.incr("my counter")
    result = yield client.schedule_wait(ac.context)
    assert result > 0
    print "Incr [my counter] %s" % (result)


    ac.delete("my list")
    result = yield client.schedule_wait(ac.context)
    assert result in [0, 1]
    print "Del [my list] %s" % (['none', 'ok'][result])

    for i in range(0,10):
        ac.lpush("my list", "element %d" % i)
        result = yield client.schedule_wait(ac.context)
        assert result >= 1

    ac.lrange("mylist", 0, -1)
    result = yield client.schedule_wait(ac.context)
    assert len(result) == 10
    print "Lrange [my list] ok"

    


    client.push_client(ac)

    yield creturn()


def run_test(srv, client, time = 1):
    tm = Timer(time, run_clients, srv, client)
    srv.set_timer(tm)




REDIS = ('localhost', 6379)

def main():
    srv = IceServer()
    client = RedisClientAction(REDIS, 'Client', 1)
    srv.add_action(client)
    for i in range(CONNECT):
        run_test(srv, client)
    srv.run()

    

main()
