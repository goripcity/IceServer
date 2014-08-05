#coding=utf-8

import socket
import select, errno
import os, sys 


from util import set_linger, set_keepalive
from log import log
from action import *
from schedule import *
from conn import conn


BUFSIZ = 8092
MAXPACKET = 2 << 19
LISTEN_LIST = 1024



class IceServer(object):
    """
        IceServer
            event-driven with epoll

    """
    def __init__(self):
        self.epoll = select.epoll()             #epoll
        self.log = log                          #log
        self.polltime = -1                      #epoll wait time
        self.socks = {}                         #save sockets  {fd: (socket, addr)}
        self.actions = []                       #save actions 
        self.callbacks = {}                     #save callbacks {fd or uid: (callback, *args)}
        self.schedule = g_logic_schedule        #global schedule
        self.sendlist = {}                      #save uids {fd: [uids..]}



    def tcp_listen(self, addr):
        """ create a tcp listen socket """

        try:
            listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listen_sock.bind(addr)

            listen_sock.listen(LISTEN_LIST)
            listen_sock.setblocking(0)

            fd = listen_sock.fileno()
            self.socks[fd] = (listen_sock, addr)
            self.log.debug("TCP Listening %s:%d" % (addr[0], addr[1]))

        except select.error, msg:
            self.log.error(msg.strerror)
            sys.exit(-1)

        return fd

    
    def event_tcplisten(self, fd):
        """ event readable, tcp listen handler """
        try:
            conn, addr = self.socks[fd][0].accept()
        except socket.error, msg:
            self.info.debug('Accept connection error %s' % msg.strerror)
            return -1, None

        return self.register_newconnection(conn, addr)



    def register_newconnection(self, sock, addr):
        """
            register new accepted connection to epoll
            noblock, keepalive, saveinfo
        """
        
        fd = sock.fileno()
        sock.setblocking(0)
        set_keepalive(sock)
        self.socks[fd] = (sock, addr)
        self.sendlist[fd] = []
        self.epoll.register(fd, select.EPOLLIN | select.EPOLLET)

        self.log.debug("Accept connection from %s, %d, fd = %d" % (addr[0], addr[1], fd))
        return fd, addr

        
    def wait_read(self, fd, callback):
        """ register readable event, such as tcp listen ready"""
            
        self.callbacks[fd] = (callback, (fd,))
        self.epoll.register(fd, select.EPOLLIN)
    

    def run(self):
        while True:
            self.before_event()
            self.event_wait()
    

    def before_event(self):
        """ run before event wait """
        pass


    def event_wait(self):
        epoll_list = self.epoll.poll(self.polltime)

        for fd, events in epoll_list:
            if select.EPOLLIN & events:  # readable
                callback, args = self.callbacks.get(fd, \
                    (self.log.info, ("%s read callback miss" % fd, )))
                callback(*args)

            elif select.EPOLLOUT & events: # writeable
                callback, args = self.callbacks.get(fd, \
                    (self.log.info, ("%s write callback miss" % fd, )))
                callback(*args)


    
    def add_action(self, action):
        """
            action: TcpServerAction TcpClientAction instance
        """

        self.actions.append(action)
        action.server = self
        if hasattr(action, 'tcp_listen'):
            action.tcp_listen()
            
        elif hasattr(action, 'create_pool'):
            action.create_pool()


    def event_read(self, fd):
        """ modify tcp fd readable event """
        self.epoll.modify(fd, select.EPOLLIN | select.EPOLLET)
        self.callbacks[fd] = (self.event_tcprecv, (fd, self.schedule.current_uid))



    def event_tcprecv(self, fd, uid):
        """ tcp read callback """
        recvdata = ''
        loop = 1 
        while loop:
            loop, recvdata, isclosed = self.tcp_read(fd, recvdata)

        self.schedule.run(uid, (recvdata, isclosed))
        
    
   
    def tcp_read(self, fd, recvdata):
        """ 
            nonblocking tcp read 
            return True/False(need continue?), data, True/False(is fd closed?)
        """
        
        sock = self.socks[fd][0]
        try:
            data = sock.recv(BUFSIZ)
            if not data:
                if recvdata == '': 
                    self.tcpread_close(fd)
                    return False, recvdata, True
            else:
                recvdata += data
                return True, recvdata, False

        except socket.error, msg:
            if msg.errno == errno.EAGAIN:
                return False, recvdata, False
            else:
                self.tcpread_errclose(fd, msg)
                return False, recvdata, True



    def tcpread_close(self, fd):
        self.log.debug("Fd : [%s] tcp_read close " % fd)
        self.socks[fd][0].close()
        self.clear_fd(fd)


    def tcpread_errclose(self, fd, msg):
        self.log.info("Tcp_read error [%s] : %s" % (fd, msg.strerror))
        self.__kill_it(self.socks[fd][0])
        self.clear_fd(fd)


    def clear_fd(self, fd):
        self.epoll.unregister(fd)
        del self.sendlist[fd]
        del self.socks[fd]
        conn.clear_fd(fd)


    def __kill_it(self, conn):
        """ send rst """
        set_linger(conn, 1, 0)        
        conn.close()

        
    def event_write(self, fd, data):
        """ modify tcp fd writeable event """
        uid = self.schedule.current_uid
        self.epoll.modify(fd, select.EPOLLOUT | select.EPOLLET)
        self.callbacks[fd] = (self.event_tcpsend, (fd,))
        self.sendlist[fd].append((uid, data))

    
    def event_tcpsend(self, fd):
        """ nonblocking tcp send, stop if error occurs, go to schedule if done """
        sendlist = self.sendlist[fd]
        sock = self.socks[fd][0]

        while 1:
            if sendlist:
                uid, send_data = sendlist.pop(0)
            else:
                break

            lenth = len(send_data)
            if lenth == 0:
                self.schedule.run(uid, False)
                continue

            send_len = 0
            while 1:
                try:
                    send_len += sock.send(send_data)
                    if send_len == lenth:
                        self.schedule.run(uid, True)
                        break
                    else:
                        continue

                except socket.error, msg:
                    if msg.errno == errno.EAGAIN:        
                        if send_len == lenth:
                            self.schedule.run(uid, True)
                            return 
                        self.epoll.modify(fd, select.EPOLLOUT | select.EPOLLET)                
                        self.sendlist[fd].insert(0, (send_data[send_len:], uid))
                        self.log.debug("Send to [%s:] %s \nLet's have a break, and send \
                                        the left: %s" % (fd, send_data[:send_len], \
                                        send_data[send_len:]))
                        return 

                    else:
                        self.tcpsend_errclose(fd, msg)
                        for data, uid in sendlist:
                            self.schedule.run(uid, False)
                        return 


    def tcpsend_errclose(self, fd, msg):
        self.log.debug("Tcp_send error [%s] : %s" % (fd, msg.strerror))
        self.__kill_it(self.socks[fd]['conn'])
        self.clear_fd(fd)


    def reg_tcp_connect(self, addr):
        """ register nonblocking tcp connect """

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            fd = sock.fileno()
            sock.setblocking(0)
            sock.connect(addr)
        except socket.error, msg:
            if msg.errno != errno.EINPROGRESS:
                return -1

        self.sendlist[fd] = []
        self.socks[fd] = (sock, addr)
        self.wait_write(fd, self.event_tcpconnect) 
        
        return fd



    def wait_write(self, fd, callback):
        """ register writeable event, such as tcp connect ready"""
        self.callbacks[fd] = (callback, (fd, self.schedule.current_uid))
        self.epoll.register(fd, select.EPOLLOUT| select.EPOLLET)



    def event_tcpconnect(self, fd, suid):
        """ nonblocking tcp connect callback """
        sock = self.socks[fd][0]
        err_no = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        if err_no == 0:
            set_keepalive(sock)
        else:
            self.tcpconn_errclose(fd, err_no)

        self.schedule.run(suid, err_no)


    def tcpconn_errclose(self, fd, errno):
        self.log.debug("Tcp_connect error [%s] : %s" % (fd, os.strerror(errno)))
        self.__kill_it(self.socks[fd][0])
        self.clear_fd(fd)

      


__all__ = ['IceServer']



if __name__ == '__main__':
    srv = IceServer()
    srv.add_action(TcpServerAction(('localhost', 7777)))
    srv.run()
    
