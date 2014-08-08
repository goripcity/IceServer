IceServer
=========

Ice = LIghtweight, with Coroutine, use Epoll for event-driven server framework for Linux,  write in Python

I'm just tired of write logic with async operate and callbacks, and want to write async operate as sync operate, step by step. Twisted is cool and can do what I want, but it's too large and complex. 
    
This server is design to be simple, nonblocking and run single thread only, but scalable and can do lots of tcpserver works.



Usage
---------

This is a simplest server, default echo server

    from server import *
    SERVER = ('localhost', 9999)

    srv = IceServer()
    srv_action = TcpServerAction(SERVER)
    srv.add_action(srv_action)
    srv.run()

Then I want do something more, recv string ‘gettime’, and return current time
    
    from server import *
    SERVER = ('localhost', 9999)
    
    srv = IceServer()
    srv_action = TcpServerAction(SERVER)
    
    #--->new code begin :add logic
    srv_logic = Logic()
    srv_action.reg_logic(srv_logic)
    #--->new code end
    
    srv.add_action(srv_action)
    srv.run()

This is the Logic class, inherit from class BaseLogic, we'll discuss logic_schedule() and creturn later

    class Logic(BaseLogic):
        def __init__(self):
            super(Logic, self).__init__()
    
        @logic_schedule()
        def dispatch(self, result, uid):
            if result == 'gettime':
                yield creturn(str(datetime.now()))
        
            yield creturn('command wrong')



But when I use telnet to test this server, the result is not I want because telent send line with '\r\n'.
So let's add the telnet protocol 

    from server import *
    SERVER = ('localhost', 9999)
    
    srv = IceServer()
    srv_action = TcpServerAction(SERVER)
    srv_logic = Logic()
    srv_action.reg_logic(srv_logic)
    
    #--->new code begin :add protocol
    srv_protocol = TelnetProtocol()
    srv_action.reg_protocol(srv_protocol)
    #--->new code end
    
    srv.add_action(srv_action)
    srv.run()
        
The TelnetProtocol class, inherit from class BaseProtocol, need to treat data as stream beacuse the data
from socket is stream

    class TelnetProtocol(BaseProtocol):
        def __init__(self):
            super(TelnetProtocol, self).__init__()

        def parse(self, data):
            """
                datastream parse
                return result, dataleft, True/False (continue parse?)
            """
            index = data.find("\r\n")
            if index == -1: 
                return None, data, False

            end = index + 2 
            if index == end:
                return data[:index], '', False
            else:
                return data[:index], data[end:], True

        def packet(self, data):
            return data + '\r\n'

        
Now, the server is done, and I can use protocol and logic to deal something complex.

But in general， servers can't work by their own, they must use something like memcache or database to finish their work.So let's continue






        
