#coding=utf-8

from log import log
from schedule import *
from protocol import Protocol
from logic import *
from conn import *

class TcpServerAction(object):
    def __init__(self, listen_addr, name = ''):
        self.addr = listen_addr
        self.server = None
        self.name = name if name else 'Port-%s' % listen_addr[1] 
        self.log = log
        self.protocol = Protocol()
        self.logic = BaseLogic()

    def reg_protocol(self, protocol):
        self.protocol = protocol


    def reg_logic(self, logic):
        self.logic = logic


    def tcp_listen(self):
        fd = self.server.tcp_listen(self.addr)
        self.server.wait_read(fd, self.event_tcplisten)


    def event_tcplisten(self, fd):
        fd, addr = self.server.event_tcplisten(fd)
        if fd == -1:
            return 

        conn.save_fd(fd, self)
        self.log.debug("%s: Accept connection from %s, %d, fd = %d" \
                        % (self.name, addr[0], addr[1], fd)) 
        
        self.new_connection(fd)


    @logic_schedule()
    def recving(self, fd):
        data = yield self.server.event_read(fd)
        self.log.debug("[%s] fd :[%s] received :%s" % (self.name, fd, data[0]))
        yield creturn(data)
        

    @logic_schedule()
    def sending(self, fd, data):
        status = yield self.server.event_write(fd, self.protocol.packet(data))
        if status:
            self.log.debug("[%s] fd :[%s] send done :%s" % (self.name, fd, data))
        yield creturn(status)



    @logic_schedule(True)
    def new_connection(self, fd):
        status = yield self.protocol.handshake(fd)
        if status == False:
            yield creturn()

        recvdata = ''
 
        while 1:
            data, isclosed = yield self.recving(fd)
            recvdata += data
            
            if isclosed:
                self.logic.close(fd)
                break

            loop = 1
            while loop:
                result, recvdata, loop = self.protocol.parse(recvdata)
                    
                data = yield self.logic.dispatch(result, fd)
                if data:
                    yield self.sending(fd, data)
                
        
        yield self.protocol.close(fd)

        yield creturn()

    

class TcpClientAction(object):
    def __init__(self, connect_addr, name, num = 3):
        self.addr = connect_addr
        self.server = None
        self.name = name
        self.num = num
        self.log = log
        self.protocol = Protocol()
        self.logic = BaseLogic()
        self.conn_pool = []
        self.wait_list = []
        conn.save(self)


    def reg_protocol(self, protocol):
        self.protocol = protocol


    def reg_logic(self, logic):
        self.logic = logic


    @logic_schedule(True)
    def create_pool(self):
        while len(self.conn_pool) < self.num:
            fd = yield self.connect(self.addr)
            if fd == -1:
                #TODO wait event
                import time
                time.sleep(10)

            status = yield self.protocol.handshake(fd)
            if status == False:
                #TODO
                pass

            self.conn_pool.append(fd)

        yield creturn()

    
    @logic_schedule()
    def connect(self, addr):
        fd = self.server.reg_tcp_connect(self.addr)

        if fd == -1: 
            self.log.error("[%s] fd: [%d] connect %s error" % (self.name, fd, addr))
            yield creturn(fd)

        self.log.debug("[%s] fd: [%d] Try to connect %s" % (self.name, fd, addr))
        conn.save_fd(fd, self)
        err_no = yield fd

        if err_no in (errno.ECONNREFUSED, errno.ETIMEDOUT):
            self.log.error("%s %s Connection refused. Let's wait a moment to retry..." \
                            % (self.name, self.addr))
            yield creturn(-1)

        self.log.debug("[%s] fd: [%d] Connect to %s success" % (self.name, fd, addr))
     
        yield creturn(fd)


    @logic_schedule()
    def request(self, data):
        if len(self.conn_pool):
            fd = self.conn_pool.pop()
        else:
            #TODO
            pass

        status = yield self.sending(fd, data)
        if status == False:
            yield creturn(False, None)

        recvdata = ''
 
        while 1:
            data, isclosed = yield self.recving(fd)
            recvdata += data
            
            if isclosed:
                self.logic.close(fd)
                yield creturn(False, None)

            loop = 1
            result, _, _ = self.protocol.parse(recvdata)
                    
            data = yield self.logic.dispatch(result, fd)
            if result:
                break
        
        
        self.conn_pool.append(fd)
        yield creturn(True, data)


    @logic_schedule()
    def recving(self, fd):
        data = yield self.server.event_read(fd)
        self.log.debug("[%s] fd :[%s] received :%s" % (self.name, fd, data[0]))
        yield creturn(data)
        

    @logic_schedule()
    def sending(self, fd, data):
        status = yield self.server.event_write(fd, self.protocol.packet(data))
        if status:
            self.log.debug("[%s] fd :[%s] send done :%s" % (self.name, fd, data))
        yield creturn(status)



__all__ = ['TcpServerAction', 'TcpClientAction']
