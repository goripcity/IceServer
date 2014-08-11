IceServer
=========

Ice = LIghtweight, with Coroutine, use Epoll for event-driven server framework for Linux,  write in Python

I'm just tired of writing logic with async operate and lots of callbacks, and want to write async operate like writing  sync operate, step by step. Twisted is cool and can do what I want, but it's too large and complex. 
    
This server is designed to be simple, nonblocking and running in single thread only, but scalable and can do lots of tcpserver works.


Build a server
---------


This is a simplest echo server

    from server import *
    SERVER = ('localhost', 9999)

    srv = IceServer()
    srv_action = TcpServerAction(SERVER)
    srv.add_action(srv_action)
    srv.run()

Then I want to do something more: recv string ‘gettime’, and return current time
   
    from datetime import datetime
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



But when I used telnet to test this server, the result was not as I excepted,  because telent sends line with '\r\n'.
So let's add the telnet protocol 

    from datetime import datetime
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

But in general, servers can't work by their own, they must use something like memcache or database to finish 
their work. So let's continue.

    from datetime import datetime
    from server import *
    SERVER = ('localhost', 9999)
    TIMESERVER = ('localhost', 10000)
    
    srv = IceServer()
    srv_action = TcpServerAction(SERVER)
    srv_logic = Logic()
    srv_action.reg_logic(srv_logic)

    srv_protocol = TelnetProtocol()
    srv_action.reg_protocol(srv_protocol)
    
    #--->new code begin :add mc client
    # we need to add logic and protocol as we built server before, but we assume it's done here
    
    tm_client = TcpClientAction(TIMESERVER, 'timeserver', 3)  #address, name, connection pool's num 
    # TODO add protocol
    # TODO add logic 
    srv.add_action(tm_client)
    #--->new code end
    
    srv.add_action(srv_action)
    srv.run()

Now we build a connections pool and use it in logic.dispatch


    class Logic(BaseLogic):
        def __init__(self):
            super(Logic, self).__init__()
    
        @logic_schedule()
        def dispatch(self, result, uid):
            if result == 'gettime':
            #--->new code begin : get time from timeserver
                tm_client = conn.get('timeserver')    #conn is global connetion manager
                status, result = yield tm_client.request(result)
                if status:
                    yield creturn(result)
            
            #--->new code end
                yield creturn(str(datetime.now()))
        
            yield creturn('command wrong')
            
         
      
Write Protocol
---------
As is mentioned above， a new protocol class must rewrite "parse" and "packet"，maybe need to rewrite “handshake” and “handle”. Read actions.py and protocol.py for more details


Write Logic
---------

Just rewrite "dispatch" and add your own logic funcitions

    
Noitce
---------

Each function with async operate must use Decorator "@logic_schedule()" and use "yield" to wait for return
Each function with logic_schedule() must use "yield creturn(*args)" to return, or it will raise an error.

    
    
### Thanks for reading
