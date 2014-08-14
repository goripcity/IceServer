import os,sys
sys.path.append('../')

from server import *
from http import *

class HttpProtocol(BaseProtocol):
    def __init__(self):
        super(HttpProtocol, self).__init__()
        self.parsers = {}


    @logic_schedule()
    def close(self, uid):
        if self.parsers.has_key(uid):
            del self.parsers[uid]
        yield creturn(True)


    @logic_schedule()
    def handle(self, data, uid):
        yield creturn(self.parse(data, uid))



    def parse(self, data, uid):
        if self.parsers.has_key(uid):
            parser = self.parsers[uid]
        else:
            parser = HttpParser()
            self.parsers[uid] = parser

        return parser.parse(data)



    def packet(self, httppacket):
        if isinstance(httppacket, HttpPacket):
            return httppacket.packet()
        else:
            return httppacket
        



__all__ = ["HttpProtocol"]
