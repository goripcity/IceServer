#! /usr/bin/env python
#coding=utf-8

import os,sys
sys.path.append('../')
from server import *
from test_server import SERVER, MCERR, DBERR
import time
from datetime import datetime


g_connect = 1

request = {}
request['all'] = 0
request['succeed'] = 0
request['fail'] = 0 
request['mcfail'] = 0
request['dbfail'] = 0
request['time'] = 0

last_report = 0

def report():
    global last_report
    now = datetime.now() 
    print 'All', request['all']
    print 'request_succeed', request['succeed']
    print 'request_fail', request['fail']
    print 'request_mcfail',request['mcfail']
    print 'request_dbfail',request['dbfail']
    print 'accuracy: [%f%%]' % (request['succeed']*100.0/request['all'])
    print 'average succeed time: %f' % (request['time'] / request['succeed'])
    if last_report:
        print 'last report', now - last_report
    last_report = now
    


@logic_schedule(True)
def run_clients(srv, client):
    if client.ready == False:
        run_test(srv, client)
        yield creturn()
    
    start = time.time()
    global request
    status, result = yield client.request('test')
    if status == False:
        request['fail'] += 1 
    elif result == MCERR:
        request['mcfail'] += 1        
    elif result == DBERR:
        request['dbfail'] += 1        
    elif result == "testMCDB":
        request['time'] += (time.time()-start)
        request['succeed'] += 1
        
    
    request['all'] += 1
    if request['all'] % g_connect == 0:
        report()

    run_test(srv, client, 0)

    yield creturn()


def run_test(srv, client, time = 1):
    tm = Timer(time, run_clients, srv, client)
    srv.set_timer(tm)





def main():
    global g_connect
    if len(sys.argv) == 2:
        g_connect = int(sys.argv[1])
    srv = IceServer()
    srv.log.set('error', 1)
    client = TcpClientAction(SERVER, 'MC', g_connect)
    srv.add_action(client)
    for i in range(0, g_connect):
        run_test(srv, client)
    srv.run()

    

main()
