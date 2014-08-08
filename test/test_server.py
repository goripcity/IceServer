#! /usr/bin/env python
#coding=utf-8

"""
    Test server, get memcache, get db, return 
"""


import os,sys
sys.path.append('../')
from server import *
from time import sleep, time


CACHE = ('localhost', 10000)
DB = ('localhost', 20000)
SERVER = ('localhost', 7777)

MCERR = 'mcerr'
DBERR = 'dberr'

class FakeDbServerLogic(BaseLogic):
    def __init__(self):
        super(FakeDbServerLogic, self).__init__()


    @logic_schedule()
    def dispatch(self, result, fd):
        data = self.db_opt()
        yield creturn(data) 


    def db_opt(self):
        sleep(0.01) 
        return "DB"
    

class FakeMcServerLogic(BaseLogic):
    def __init__(self):
        super(FakeMcServerLogic, self).__init__()


    @logic_schedule()
    def dispatch(self, result, fd):
        data = self.mc_opt()
        yield creturn(data) 


    def mc_opt(self):
        sleep(0.01) 
        return "MC"
    
    

class TestLogic(BaseLogic):
    def __init__(self):
        super(TestLogic, self).__init__()
    
    @logic_schedule()
    def dispatch(self, result, fd):
        mc = conn.get('MC')
        status, mc_result = yield mc.request(result)
        if status == False:
            yield creturn(MCERR) 

        db = conn.get('DB')
        status, db_result = yield db.request(result)
        if status == False:
            yield creturn(DBERR) 

        yield creturn(result + mc_result + db_result)


def fakemc_server():
    pid = os.fork()
    if pid == 0:
        srv = IceServer()
        srv.log.set('error', 1)
        sa = TcpServerAction(CACHE)    
        logic = FakeMcServerLogic()
        sa.reg_logic(logic)
        srv.add_action(sa)
        srv.run()
    else:
        sleep(0.1)



def fakedb_server():
    pid = os.fork()
    if pid == 0:
        srv = IceServer()
        srv.log.set('error', 1)
        sa = TcpServerAction(DB)    
        logic = FakeDbServerLogic()
        sa.reg_logic(logic)
        srv.add_action(sa)
        srv.run()
    else:
        sleep(0.1)

        


def test_server(num):
    srv = IceServer()
    srv.log.set('error', 1)
    logic = TestLogic()
    sa = TcpServerAction(SERVER)
    sa.reg_logic(logic)
    mc = TcpClientAction(CACHE, 'MC', num)
    db = TcpClientAction(DB, 'DB', num)
    srv.add_action(sa)
    srv.add_action(mc)
    srv.add_action(db)
    srv.run()



if __name__ == '__main__':
    fakemc_server()
    fakedb_server()
    if len(sys.argv) == 2:
        num = int(sys.argv[1])
    test_server(num)

