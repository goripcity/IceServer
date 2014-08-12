#coding=utf-8

from urllib import quote, unquote

MAXLINE = 65535
MAXHEADER = 100
MAXBODY = 1024*1024

METHOD = ['POST', 'GET', 'OPTIONS', 'DELETE', 'HEAD', 'PUT', 'TRACE', 'CONNECT']

class HttpParser(object):
    """ simple http protocol parser """
    def __init__(self):
        self.response = True  
        self.header = {}
        self.stream = ''
        self.cursor = 0
        self.stage = 0    # 0 new package  1 parsing header 2 parsing body
        self.headerlen = 0
        self.last_pairs = []
                        

    def get_line(self):
        index = self.stream[self.cursor:].find('\r\n')
        if index == -1:
            if len(self.stream[self.cursor:]) > MAXLINE:  #drop line
                self.stream = self.stream[:self.cursor]
                return False, ''
            return False, ''

        line = self.stream[self.cursor: self.cursor + index]
        self.cursor += (index + 2)
        return True, line


    def update_stream(self):
        self.stream = self.stream[self.cursor:]
        self.cursor = 0

 
    def start_line(self):        
        """
            request:    <method> <request-url> <version>
            response :  <version> <status> <reason-phrase>
        """

        start = 0
        status = True
        while status:
            status, line = self.get_line()
            words = line.split(' ')
            if len(words) != 3:
                continue

            if words[0].startswith('HTTP'): #response
                self.response = True
                self.version = words[0]
                self.status = words[1]
                self.reason = words[2]
            elif words[0] in METHOD: #request
                self.response = False
                self.method = words[0]
                self.url = words[1]          
                self.parse_url()
                self.version = words[2]
            else:
                continue

            self.stage = 1
            self.headers = {}
            return True
 
        return False
        

    def parse_url(self):
        """ url?name=value&name1=value1..  """
        
        self.args = {}
        index = self.url.find('?')
        if index == -1:
            return 

        args = self.url[index+1:].split('&')
        for arg in args:
            kv = arg.split('=')
            if len(kv) > 1:
                self.args[unquote(kv[0])] = unquote(kv[1])


    def header_lines(self):
        if self.headerlen > MAXHEADER:
            self.drop()
            return False
            
        status = True
        while status:
            status, line = self.get_line()
            if status and line == '': #header end
                if self.response == False and self.method not in ['POST', 'PUT']:
                    self.stage = 0  #one packet without body
                    return True
                
                self.stage = 2 #packet need body
                return False 

            if status == False:        
                return False
    
            index = line.find(':')
            if index == -1: 
                if line[0] not in [' ', '\t'] or self.last_pairs == []:
                    self.drop()
                    return False
                pairs = [self.last_pairs[0], self.last_pairs[1] + line.lstrip()]
            else:
                self.headerlen += 1 
                pairs = line.split(':', 1)
                    
            if 'Cookie' in pairs[0]: 
                self.header[pairs[0]] = self.parse_cookies(pairs[1].lstrip())
            else:
                self.header[pairs[0]] = pairs[1].lstrip()
    
            self.last_pairs = pairs

        return False
                

    def drop(self):
        self.stream = ''
        self.cursor = 0
        self.stage = 0
        self.header = {}

    
    def get_body(self, lenth):
        if len(self.stream[self.cursor:]) < lenth:
            return False
        else:
            self.body = self.stream[self.cursor:self.cursor+lenth]
            self.cursor += lenth
            return True
        


    def parse_cookies(self, data):
        cookies = {}
        for pairs in data.split(';'):
            kv = pairs.split('=')
            if len(kv) > 1:
                cookies[kv[0].lstrip()] = kv[1].lstrip()

        return cookies


    def parse(self, stream = ''):
        parse_failed = (None, '', False)
        parse_done = (self, '', False)
        parse_continue = (self, '', True)

        self.stream += stream
            
        #parse start line
        if self.stage == 0:
            if self.start_line() == False:
                self.update_stream()
                return parse_failed

        #parse header
        if self.stage == 1:
            if self.header_lines():
                self.update_stream()
                self.stage = 0
                if '\r\n\r\n' in self.stream:
                    return parse_continue
                else:
                    return parse_done

        #parse body
        if self.stage == 2:
            if not self.header.has_key('Content-Length'):   # not support chunk now
                self.drop()
                return parse_failed
            try:
                lenth = int(self.header['Content-Length'])
                if lenth > MAXBODY:
                    self.drop()
                    return parse_failed
                    
                if self.get_body(lenth):
                    self.stage = 0
                    self.update_stream()
                    if '\r\n\r\n' in self.stream:
                        return parse_continue
                    else:
                        return parse_done
            except ValueError:
                self.drop()
                return parse_failed

        self.update_stream()
        return parse_failed
        


__all__ = ['HttpParser']
