#coding=utf-8

from log import log
from schedule import *


class Connections(object):
    """
        connnetions manager, save uid, actions
        logic can use action's method through this class
    """

    def __init__(self):
        self.log = log
        self.name_actions = {}
        self.uid_actions = {}


    def save(self, action):
        """ save action by name """
        self.name_actions[action.name] = action


    def get(self, name):
        return self.name_actions.get(name)

    
    def save_uid(self, uid, action):
        """ uid, action map """
        self.uid_actions[uid] = action


    def clear(self, uid):
        if self.uid_actions.has_key(uid):
            action = self.uid_actions[uid]
            action.clear(uid)
            del self.uid_actions[uid]
            
        

    @logic_schedule()
    def sending(self, uid, data):
        """ try to use action's sending """
        action = self.uid_actions.get(uid)
        if action == None:
            yield creturn(False)
        
        status = yield action.sending(uid, data)
        yield creturn(status)
        
                
    @logic_schedule()
    def recving(self, uid):
        """ try to use action's recving """
        action = self.uid_actions.get(uid)
        if action == None:
            yield creturn('', True)
        
        result = yield action.recving(uid)
        yield creturn(result)


conn = Connections()


__all__ = ['conn']
