#! /usr/bin/env python
#coding=utf-8

import os,sys
sys.path.append('../')
from server import *
from client import *
import time
from datetime import datetime

LOOP = False
CONNECT = 1

@logic_schedule(True)
def run_clients(srv, client):
    if client.ready == False:
        run_test(srv, client)
        yield creturn()
    
    ac = yield client.pop_client()
    
    ac.command("SET key %s", "test set")
    client.schedule_wait(ac.context)
    value = yield 
    print value
    
    ac.command("GET key")
    client.schedule_wait(ac.context)
    value = yield 
    print value


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
