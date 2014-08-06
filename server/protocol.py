#coding=utf-8

from log import log
from schedule import *
from conn import conn


class Protocol(object):
    def __init__(self):
        self.log = log
        self.conn = conn


    @logic_schedule()
    def handshake(self, uid):
        """ connection handshake, close fd here if necessary """
        yield creturn(True)


    @logic_schedule()
    def close(self, uid):
        yield creturn(True)


    def parse(self, data):
        """
            datastream parse
            return result, dataleft, True/False (continue parse?)
        """

        result = data
        return result, '',  False


    def packet(self, *args):
        result = args[0]
        return result 



__all__ = ['Protocol']
