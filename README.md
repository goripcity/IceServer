IceServer
=========

Ice = LIghtweight, with Coroutine, use Epoll for event-driven server framework for Linux,  write in Python


Usage
---------

This is a simplest server, default echo server

    from server import *
    SERVER = ('localhost', 9999)

    srv = IceServer()
    srv_action = TcpServerAction(SERVER)
    srv.add_action(srv_action)
    srv.run()

tobecontinued ...
    

        
    
        
        
