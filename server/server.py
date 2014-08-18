#coding=utf-8

import socket
import select, errno
import os, sys
import time
from heapq import heappop, heappush


from util import set_linger, set_keepalive, Timer, get_uid, set_nodelay
from log import log
from action import *
from schedule import *
from conn import conn


BUFSIZ = 8092
MAXPACKET = 2 << 19
LISTEN_LIST = 1024
EVREAD = 1
EVWRITE = 2

    

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
        self.events = {}                        #save {fd: events}
        self.actions = []                       #save actions 
        self.callbacks = {}                     #save callbacks {fd or uid: (callback, *args)}
        self.schedule = g_logic_schedule        #global schedule
        self.recvbuf = {}                       #save recvdata {uid: data}
        self.sendlist = {}                      #save uids {fd: [uids..]}
        self.maps = {}                          #save {fd: uid, uid: fd}
        self.wait_readevent = {}                #save schedule uid which is 
                                                #waiting for read event {fd: uid} 
        self.read_timeout = {}                  #save {uid: timeout}
        
        self.timer_heap = []                    #timer minheap
        self.timer_info = {}                    #timer info  key = time
                                                #            value = [Timer() ...]


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
        
        uid = self.init_sock(sock, addr)
        self.log.debug("Accept connection from %s, %d, uid = %s" % (addr[0], addr[1], uid[:8]))
        fd = sock.fileno()

        self.epoll.register(fd, select.EPOLLIN | select.EPOLLET)
        self.callbacks[fd] = (self.event_tcprecv, (fd,))

        return uid, addr

        
    def wait_read(self, fd, callback, *args):
        """ add readable event"""

        if not self.events.has_key(fd):
            self.epoll.register(fd, select.EPOLLIN)
        elif self.events[fd] & EVREAD == 0:
            #for hiredis, write > read 
            return 
        else:
            self.epoll.modify(fd, select.EPOLLIN | select.EPOLLET)

        self.events[fd] = EVREAD
        self.callbacks[fd] = (callback, args)
    
    

    def wait_write(self, fd, callback, *args):
        """ add writeable event"""

        if self.events.has_key(fd):
            self.epoll.modify(fd, select.EPOLLOUT | select.EPOLLET)
        else:
            self.epoll.register(fd, select.EPOLLOUT | select.EPOLLET )
            
        self.events[fd] = EVWRITE
        self.callbacks[fd] = (callback, args)



    def del_write(self, fd):
        """ must del_write before wait_read """
        self.events[fd] = EVREAD


    def clean_up(self, fd):
        """ clean fd """
        del self.events[fd]
        self.epoll.unregister(fd)
        


    def run(self):
        while True:
            self.before_event()
            self.event_wait()
  

    def set_timer(self, timer):
        """ add a timer """
        hit = time.time() + timer.elapse
        heappush(self.timer_heap, hit)
        if self.timer_info.has_key(hit):
            self.timer_info[hit].append(timer)
        else:
            self.timer_info[hit] = [timer]
        

    def run_timer(self):
        if self.timer_heap == []:
            return -1

        while len(self.timer_heap) != 0:
            now = time.time()
            hit = self.timer_heap[0]
            if now < hit:
                return hit - now

            #run timer
            heappop(self.timer_heap)
            timers = self.timer_info[hit]
            for timer in timers:
                if timer.run():
                    self.set_timer(timer)
                
            del self.timer_info[hit]
            
        return -1

    def before_event(self):
        """ run before event wait """
        self.schedule.signal_handle()
        self.polltime = self.run_timer()


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



    def event_read(self, uid, timeout = -1):
        """ read form recvbuf or wait event"""
        fd = self.maps.get(uid, -1)
        if fd == -1:
            return -1, None

        buf = self.recvbuf[fd]
        if buf:
            self.recvbuf[fd] = ''
            return 0, buf
        else:
            if timeout != -1:
                self.read_timeout[uid] = timeout
                tm = Timer(timeout, self.timeout_read, uid)
                self.set_timer(tm)
            self.epoll.modify(fd, select.EPOLLIN | select.EPOLLET)
            self.callbacks[fd] = (self.event_tcprecv, (fd,))
            self.wait_readevent[fd] = self.schedule.current_uid
            return 1, None 


    def timeout_read(self, uid):
        if self.read_timeout.has_key(uid):
            fd = self.maps.get(uid, -1)
            if fd != -1:
                self.tcpread_errclose(fd, 'Timeout')



    def event_tcprecv(self, fd):
        """ tcp read callback """
        recvdata = ''
        loop = 1 
        while loop:
            loop, recvdata, isclosed = self.tcp_read(fd, recvdata)

        if not isclosed:
            self.recvbuf[fd] += recvdata
            if len(self.recvbuf[fd]) > MAXPACKET:
                self.tcpread_errclose(fd, "Packet too long")
                return 

        uid = self.wait_readevent.get(fd)

        if uid:
            buf = self.recvbuf[fd]
            self.recvbuf[fd] = ''
            del self.wait_readevent[fd]
            if self.read_timeout.has_key(uid):
                del self.read_timeout[uid]
            self.schedule.run(uid, (buf, isclosed))


   
    def tcp_read(self, fd, recvdata):
        """ 
            nonblocking tcp read 
            return True/False(need continue?), data, True/False(is fd closed?)
        """
        
        sock = self.socks[fd][0]
        try:
            data = sock.recv(BUFSIZ)
            if not data:
                self.tcpread_close(fd)
                return False, recvdata, True
            else:
                recvdata += data
                return True, recvdata, False

        except socket.error, msg:
            if msg.errno == errno.EAGAIN:
                return False, recvdata, False
            else:
                self.tcpread_errclose(fd, msg.strerror)
                return False, recvdata, True



    def tcpread_close(self, fd):
        self.log.debug("Fd : [%s] tcp_read close " % fd)
        self.socks[fd][0].close()
        self.clear_fd(fd)


    def tcpread_errclose(self, fd, msg):
        self.log.info("Tcp_read error [%s] : %s" % (fd, msg))
        self.__kill_it(self.socks[fd][0])
        self.clear_fd(fd)


    def init_sock(self, sock, addr):
        fd = sock.fileno()
        self.socks[fd] = (sock, addr)
        self.events[fd] = 0
        self.sendlist[fd] = []
        self.recvbuf[fd] = ''
        
        uid = self.maps_save(fd)

        sock.setblocking(0)
        set_keepalive(sock)
        set_nodelay(sock)
        
        return uid


    def close(self, uid):
        """ close by server """
        fd = self.maps.get(uid, -1)
        if fd == -1:
            return False

        self.log.debug("Close by server", fd)
        self.__kill_it(self.socks[fd][0])
        self.clear_fd(fd)



    def clear_fd(self, fd):
        self.epoll.unregister(fd)

        #clean event
        if self.wait_readevent.has_key(fd):
            self.schedule.run(self.wait_readevent[fd], ('', True))
            del self.wait_readevent[fd]

        for uid, _ in self.sendlist[fd]:
            self.schedule.run(uid, False)

        del self.sendlist[fd]
        del self.socks[fd]
        del self.recvbuf[fd]
        del self.events[fd]
        uid = self.maps.get(fd) 
        del self.maps[fd]
        del self.maps[uid]

        if self.callbacks.has_key(fd):
            del self.callbacks[fd]

        conn.clear(uid)


    def __kill_it(self, conn):
        """ send rst """
        set_linger(conn, 1, 0)        
        conn.close()

        
    def event_write(self, uid, data):
        """ modify tcp fd writeable event """

        fd = self.maps.get(uid, -1)
        if fd == -1:
            return False
       
        self.epoll.modify(fd, select.EPOLLOUT | select.EPOLLET)
        self.callbacks[fd] = (self.event_tcpsend, (fd,))
        self.sendlist[fd].append((self.schedule.current_uid, data))   

        return True

    
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
                        #change event to read
                        self.epoll.modify(fd, select.EPOLLIN | select.EPOLLET)
                        self.callbacks[fd] = (self.event_tcprecv, (fd,))
                        self.schedule.run(uid, True)
                        break
                    else:
                        continue

                except socket.error, msg:
                    if msg.errno == errno.EAGAIN:        
                        self.epoll.modify(fd, select.EPOLLOUT | select.EPOLLET)                
                        self.sendlist[fd].insert(0, (send_data[send_len:], uid))
                        self.log.debug("Send to [%s:] %s \nLet's have a break, and send \
                                        the left: %s" % (fd, send_data[:send_len], \
                                        send_data[send_len:]))
                        return 

                    else:
                        self.schedule.run(uid, False)
                        self.tcpsend_errclose(fd, msg)
                        return 


    def tcpsend_errclose(self, fd, msg):
        self.log.debug("Tcp_send error [%s] : %s" % (fd, msg.strerror))
        self.__kill_it(self.socks[fd][0])
        self.clear_fd(fd)


    def reg_tcp_connect(self, addr):
        """ register nonblocking tcp connect """

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            sock.setblocking(0)
            sock.connect(addr)
        except socket.error, msg:
            if msg.errno != errno.EINPROGRESS:
                sock.close()
                return -1

        uid = self.init_sock(sock, addr)
        fd = sock.fileno()
        self.callbacks[fd] = (self.event_tcpconnect, (fd, self.schedule.current_uid))
        self.epoll.register(fd, select.EPOLLOUT| select.EPOLLET)
        
        return uid



    def event_tcpconnect(self, fd, suid):
        """ nonblocking tcp connect callback """
        sock = self.socks[fd][0]
        err_no = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        if err_no != 0:
            self.tcpconn_errclose(fd, err_no)

        self.schedule.run(suid, err_no)


    def tcpconn_errclose(self, fd, errno):
        self.log.debug("Tcp_connect error [%s] : %s" % (fd, os.strerror(errno)))
        self.__kill_it(self.socks[fd][0])
        self.clear_fd(fd)


    def maps_save(self, fd):
        """ save fd:uid, uid:fd """
        uid = get_uid()
        self.maps[fd] = uid
        self.maps[uid] = fd
        return uid



__all__ = ['IceServer']



if __name__ == '__main__':
    srv = IceServer()
    srv.add_action(TcpServerAction(('localhost', 7777)))
    srv.run()
    
