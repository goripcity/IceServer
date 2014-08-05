#coding=utf-8

from log import log
from schedule import *


class Connections(object):
    """
        connnetions manager, save fd, actions
        logic can use action's method through this class
    """

    def __init__(self):
        self.log = log
        self.name_actions = {}
        self.fd_actions = {}


    def save(self, action):
        """ save action by name """
        self.name_actions[action.name] = action


    def get(self, name):
        return self.name_actions.get(name)

    
    def save_fd(self, fd, action):
        """ fd, action map """
        self.fd_actions[fd] = action


    def clear_fd(self, fd):
        del self.fd_actions[fd]
        

    @logic_schedule()
    def sending(self, fd, data):
        """ try to use action's sending """
        action = self.fd_actions.get(fd)
        if action == None:
            yield creturn(False)
        
        status = yield action.sending(fd, data)
        yield creturn(status)
        
                
    @logic_schedule()
    def recving(self, fd):
        """ try to use action's recving """
        action = self.fd_actions.get(fd)
        if action == None:
            yield creturn('', True)
        
        result = yield action.recving(fd)
        yield creturn(result)


conn = Connections()


__all__ = ['conn']
