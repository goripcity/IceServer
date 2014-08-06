#coding=utf-8

import socket
import struct

class Timer(object):
    """ timer object """
    def __init__(self, elapse, func, *args):
        self.func = func
        self.args = args
        self.times = 1
        self.elapse = elapse

    def set_times(self, times):
        self.times = times

    def run(self):
        if self.times == 0:
            return 0
        elif self.times != -1:
            self.times -= 1
        self.func(*self.args)
        return self.times

    def remove(self):
        self.times = 0


def tcp_connect(addr):
    """tcp connect，return socket or None"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        sock.connect(addr)    
    except:
        return None

    return sock


def udp_connect():
    """udp connect，return socket"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
    except:
        return None

    return sock


def set_linger(sock, onoff = 1, wait_time = 0):
    """tcp linger, onoff 0/1 off/on"""
    linger = struct.pack("ii", onoff, wait_time)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, linger)
    

def set_keepalive(sock, alive = 1):
    """tcp keepalive alive 0/1 off/on"""
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, alive)



