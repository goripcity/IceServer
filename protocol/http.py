#coding=utf-8

from urllib import quote, unquote

MAXLINE = 65535
MAXHEADER = 100
MAXBODY = 1024*1024

METHOD = ['POST', 'GET', 'OPTIONS', 'DELETE', 'HEAD', 'PUT', 'TRACE', 'CONNECT']


REQUEST_START = "%s %s HTTP/%s"
RESPONSE_START = "HTTP/%s %s %s"

RESPONSE_CODES = {
    # Informational.
    100: ('continue',),
    101: ('switching_protocols',),
    102: ('processing',),
    103: ('checkpoint',),
    122: ('uri_too_long', 'request_uri_too_long'),
    200: ('ok', 'okay', 'all_ok', 'all_okay', 'all_good', '\\o/', '✓'),
    201: ('created',),
    202: ('accepted',),
    203: ('non_authoritative_info', 'non_authoritative_information'),
    204: ('no_content',),
    205: ('reset_content', 'reset'),
    206: ('partial_content', 'partial'),
    207: ('multi_status', 'multiple_status', 'multi_stati', 'multiple_stati'),
    208: ('im_used',),

    # Redirection.
    300: ('multiple_choices',),
    301: ('moved_permanently', 'moved', '\\o-'),
    302: ('found',),
    303: ('see_other', 'other'),
    304: ('not_modified',),
    305: ('use_proxy',),
    306: ('switch_proxy',),
    307: ('temporary_redirect', 'temporary_moved', 'temporary'),
    308: ('resume_incomplete', 'resume'),

    # Client Error.
    400: ('bad_request', 'bad'),
    401: ('unauthorized',),
    402: ('payment_required', 'payment'),
    403: ('forbidden',),
    404: ('not_found', '-o-'),
    405: ('method_not_allowed', 'not_allowed'),
    406: ('not_acceptable',),
    407: ('proxy_authentication_required', 'proxy_auth', 'proxy_authentication'),
    408: ('request_timeout', 'timeout'),
    409: ('conflict',),
    410: ('gone',),
    411: ('length_required',),
    412: ('precondition_failed', 'precondition'),
    413: ('request_entity_too_large',),
    414: ('request_uri_too_large',),
    415: ('unsupported_media_type', 'unsupported_media', 'media_type'),
    416: ('requested_range_not_satisfiable', 'requested_range', 'range_not_satisfiable'),
    417: ('expectation_failed',),
    418: ('im_a_teapot', 'teapot', 'i_am_a_teapot'),
    422: ('unprocessable_entity', 'unprocessable'),
    423: ('locked',),
    424: ('failed_dependency', 'dependency'),
    425: ('unordered_collection', 'unordered'),
    426: ('upgrade_required', 'upgrade'),
    428: ('precondition_required', 'precondition'),
    429: ('too_many_requests', 'too_many'),
    431: ('header_fields_too_large', 'fields_too_large'),
    444: ('no_response', 'none'),
    449: ('retry_with', 'retry'),
    450: ('blocked_by_windows_parental_controls', 'parental_controls'),
    451: ('unavailable_for_legal_reasons', 'legal_reasons'),
    499: ('client_closed_request',),

    # Server Error.
    500: ('internal_server_error', 'server_error', '/o\\', '✗'),
    501: ('not_implemented',),
    502: ('bad_gateway',),
    503: ('service_unavailable', 'unavailable'),
    504: ('gateway_timeout',),
    505: ('http_version_not_supported', 'http_version'),
    506: ('variant_also_negotiates',),
    507: ('insufficient_storage',),
    509: ('bandwidth_limit_exceeded', 'bandwidth'),
    510: ('not_extended',),
}



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
        

class HttpPacket(object):
    """ simple http protocol packet """
    def __init__(self):
        self.headers = {}
        self.packets = ['']


    def packet(self):
        pos = -1
        lenth = len(self.packets[pos])
        if lenth:
            self.headers['Content-Length'] = str(lenth)
            pos = -2
        
        for k,v in self.headers.items():
            self.packets.insert(pos, "%s: %s" % (k, v))

        return '\r\n'.join(self.packets)



    def update_url(self, url, args):
        arglist = []
        for k,v in args.items():
            arglist.append("%s=%s" % (quote(k), quote(v)))

        return '%s?%s' % (url, '&'.join(arglist))
  


    def update_cookie(self, cookie):
        clist = []
        for k,v in cookie.items():
            clist.append("%s=%s" % (k, v))

        return "; ".join(clist)
        

    def request(self, method, url, 
        args = None, 
        headers = None,
        cookie = None,
        body = None,
        version = "1.1"):

        if args:
            url = self.update_url(url, args)

        self.packets.insert(0, REQUEST_START % (method, url, version))        

        if headers:
            self.headers.update(headers)
        
        if cookie:
            self.headers['Cookie'] = self.update_cookie(cookie)

        if body:
            self.packets.append(body)
        
        

    def response(self, status, reason = None,
        headers = None,
        cookie = None,
        body = None,
        version = "1.1"):

        if reason == None:
            reason = RESPONSE_CODES.get(status, ('unknown',))[0]

        self.packets.insert(0, RESPONSE_START % (version, status, reason))        

        if headers:
            self.headers.update(headers)

        if cookie:
            self.headers['Set-Cookie'] = self.update_cookie(cookie)

        if body:
            self.packets.append(body)



__all__ = ['HttpParser', 'HttpPacket']
