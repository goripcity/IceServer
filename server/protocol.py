#coding=utf-8

from log import log
from schedule import *
from conn import conn


class BaseProtocol(object):
    def __init__(self):
        self.log = log
        self.conn = conn


    @logic_schedule()
    def handshake(self, uid):
        """ connection handshake """
        yield creturn(True)


    @logic_schedule()
    def close(self, uid):
        yield creturn(True)


    @logic_schedule()
    def handle(self, data, uid):
        yield creturn(self.parse(data)) 
    


    def parse(self, data):
        """
            datastream parse
            return result, dataleft, True/False (continue parse?)
        """

        result = data
        return result, '',  False


    def packet(self, data):
        result = args
        return result 



__all__ = ['BaseProtocol']
