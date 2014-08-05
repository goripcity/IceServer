#coding=utf-8

from log import log
from schedule import *


class Protocol(object):
    def __init__(self):
        self.log = log


    @logic_schedule()
    def handshake(self, fd):
        yield creturn(True)


    @logic_schedule()
    def close(self, fd):
        yield creturn(True)


    def parse(self, data):
        result = data
        return result, '',  False


    def packet(self, *args):
        result = args[0]
        return result 



__all__ = ['Protocol']
