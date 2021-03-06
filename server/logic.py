#coding=utf-8

from log import log
from schedule import *
from conn import conn

class BaseLogic(object):
    def __init__(self):
        self.log = log
        self.conn = conn


    @logic_schedule()
    def dispatch(self, result, uid):
        yield creturn(result)


    @logic_schedule()
    def close(self, uid):
        yield creturn()



__all__ = ['BaseLogic']
