#! /usr/bin/env python
#coding=utf-8

import os,sys
sys.path.append('../')

import unittest
from unittest import TestCase
from protocol import HttpParser, HttpPacket

REQUEST_GET = """GET /scripts/S?name=value&nam&=& HTTP/1.1
Host: static.blog.csdn.net
User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:19.0) Gecko/20100101 Firefox/19.0
Accept: text/css,*/*;q=0.1
Accept-Language: zh-cn,zh;q=0.8,en-us;q=0.5,en;q=0.3
Accept-Encoding: gzip, deflate
Referer: http://blog.csdn.net/jiyucn/article/details/2111387
Cookie: __utma=17226283.1927683933.1365479519.1407823920.1407824256.250; __utmz=17226283.1407824256.250.250.utmcsr=baidu|utmccn=(organic)|utmcmd=organic|utmctr=python%20testcase; __gads=ID=b1c77addf9ae004c:T=1369639903:S=ALNI_MZn1t0eybwuocaDQUzxm7ryzs3eXg; pgv_pvi=381343744; lzstat_uv=10605078472595754958|2717980@2955225@3429585; uuid_tt_dd=-6479680046218917419_20131128; __message_sys_msg_id=2568; __message_gu_msg_id=0; __message_cnel_msg_id=0; _JQCMT_ifcookie=1; _JQCMT_browser=4513b27c4c49c58c54c5ed0c1fb27ef1; __message_in_school=0; __message_district_code=110000; __utmb=17226283.1.10.1407824256; __utmc=17226283; dc_tos=na6k5c; dc_session_id=1407824256330
Connection: keep-alive
    test
If-Modified-Since: Thu, 31 Jan 2013 05:25:14 GMT
Cache-Control: max-age=0

"""

REQUEST_POST = """POST /safebrowsing/gethash?client=navclient-auto-ffox&appver=19.0.2&pver=2.2&wrkey=AKEgNit9_Iuq8M1nl77pvXl6Ku0Q94xqqe8svgtbkafU2tdgC0xc_3t8gZfuzt5jABlvmp6659y_EinB0oIZi8Ys== HTTP/1.1
Host: safebrowsing.clients.google.com
User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:19.0) Gecko/20100101 Firefox/19.0
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
Accept-Language: zh-cn,zh;q=0.8,en-us;q=0.5,en;q=0.3
Accept-Encoding: gzip, deflate
Content-Length: 4
Content-Type: text/plain
Cookie: PREF=ID=27ad9b0345804aae:U=8b0d61389b745dde:LD=zh-CN:TM=1365413067:LM=1401176716:S=QVZaP4iBjL3cizCa; NID=67=g1OnPNXcnrSIHLngWNRowz58rIUKSS31wExxccpXsiQ_o1YX5NxE_H31ClGCMFcbjSW0nG7qZBJKG5pzGxzouYnFP6fpYXwS_VbDvh_1ZdIK_D0Ugvsl-Q-_iZ4OnTjg-LMDFOO1KwT8KqvpVYKwSg; SID=DQAAAIoAAADFy2EZv3J_SvtyQBKo1R8rjHBqULOFIp6LT9D8ckhJzKDLIeIWVpCI73x-WBkDBr7byAA0vmz4VxPuCFWHQjhXevdrCsqte2UbJUaaAvM6VaYJ3GCVUC6FL-tNDc5hkyDakCNW5QNjkb4vRl6ktJua-NM3pOSU_zszoqQm_O-5OPIbJ9-fgSjUGpf_oej9BCQ; HSID=AcKfjBAMsDdXnKhFD; APISID=ynxrpFkvOZsQNklT/AILddsRNC243ktiNz
Connection: keep-alive
Pragma: no-cache
Cache-Control: no-cache

TEST"""

RESPONSE = """HTTP/1.1 200 OK
Server: nginx
Date: Tue, 12 Aug 2014 06:22:10 GMT
Content-Type: text/css
Content-Length: 10
Connection: keep-alive
Keep-Alive: timeout=20
Last-Modified: Mon, 14 Oct 2013 03:29:45 GMT
Accept-Ranges: bytes
Set-Cookie: _session_id="2|1:0|10:1406601993|11:_session_id|76:NTJhMmM1NTg5Njk0OGE0OGRjNDVjZjFmXzUyZDdhMTVlOTY5NDhhNmYzYmU3NmQyMl9zZXNzaW9u|394cfedbf64ec007838f72248cac4a80fb334f1c620bb79eb10a45224c4bdca8"; expires=Thu, 28 Aug 2014 02:46:33 GMT; Path=/
ETag: "274b4a08dc8ce1:1718"
X-Powered-By: ASP.NET

1234567890"""


WRONG = """HTTP/1.1 200 OK
Server%s nginx
Date: Tue, 12 Aug 2014 06:22:10 GMT
Content-Type: text/css %s
Connection: keep-alive
Keep-Alive: timeout=20
Last-Modified: Mon, 14 Oct 2013 03:29:45 GMT
Accept-Ranges: bytes
Set-Cookie: _session_id="2|1:0|10:1406601993|11:_session_id|76:NTJhMmM1NTg5Njk0OGE0OGRjNDVjZjFmXzUyZDdhMTVlOTY5NDhhNmYzYmU3NmQyMl9zZXNzaW9u|394cfedbf64ec007838f72248cac4a80fb334f1c620bb79eb10a45224c4bdca8"; expires=Thu, 28 Aug 2014 02:46:33 GMT; Path=/
ETag: "274b4a08dc8ce1:1718"
X-Powered-By: ASP.NET

1234567890"""

class HttpTest(TestCase):
    def setUp(self):
        self.parser = HttpParser()
        self.packet = HttpPacket()


    def compare_get(self):
        self.assertEqual(self.parser.method, 'GET')

        header = self.parser.header
        args = self.parser.args
        cookies = header['Cookie']

        self.assertEqual(header['Connection'], "keep-alivetest")
        self.assertEqual(cookies['__utmc'], "17226283")
        self.assertEqual(args['name'], "value")


    def compare_post(self):
        self.assertEqual(self.parser.method, 'POST')
        header = self.parser.header
        cookies = header['Cookie']
        #print header

        self.assertEqual(header['Connection'], "keep-alive")
        self.assertEqual(cookies['HSID'], "AcKfjBAMsDdXnKhFD")
        self.assertEqual(self.parser.body, "TEST")


    def compare_response(self):
        self.assertEqual(self.parser.status, '200')

        header = self.parser.header
        cookies = header['Set-Cookie']

        self.assertEqual(header['Connection'], "keep-alive")
        self.assertEqual(cookies['Path'], "/")
        self.assertEqual(self.parser.body, "1234567890")


    def test_request(self):
        #get
        request = '\r\n'.join(REQUEST_GET.split('\n'))
        result, _, status = self.parser.parse(request)
        self.compare_get()
        
        self.assertNotEqual(result, None)

        #get one by one
        for x in request:
            result, _, status = self.parser.parse(x)

        self.assertNotEqual(result, None)
            
        self.compare_get()

        #post one by one
        request = '\r\n'.join(REQUEST_POST.split('\n'))
        for x in request:
            result, _, status = self.parser.parse(x)

        self.assertNotEqual(result, None)

        self.compare_post()

        #post+get+post
        request += '\r\n'.join(REQUEST_GET.split('\n'))
        request += '\r\n'.join(REQUEST_POST.split('\n'))

        result, _, status = self.parser.parse(request)
        self.assertNotEqual(result, None)
        self.assertEqual(status, True)
        self.compare_post()

        result, _, status = self.parser.parse()
        self.assertNotEqual(result, None)
        self.assertEqual(status, True)
        self.compare_get()
        
        result, _, status = self.parser.parse()
        self.assertNotEqual(result, None)
        self.assertEqual(status, False)
        self.compare_post()
        

    def test_response(self):
        #response 
        request = '\r\n'.join(RESPONSE.split('\n'))
        result, _, status = self.parser.parse(request)
        
        self.assertNotEqual(result, None)
        self.compare_response()

        #response one bye one
        for x in request:
            result, _, status = self.parser.parse(x)
        
        self.assertNotEqual(result, None)
        self.compare_response()

        #response *2
        request += '\r\n'.join(RESPONSE.split('\n'))
        result, _, status = self.parser.parse(request)
        self.assertNotEqual(result, None)
        self.assertEqual(status, True)
        self.compare_response()

        result, _, status = self.parser.parse()
        self.assertNotEqual(result, None)
        self.assertEqual(status, False)
        self.compare_response()
        

    def test_wrongstream(self):
        request = '1'*100000
        request += '\r\n'.join(REQUEST_GET.split('\n'))
        request += '\r\n'.join(REQUEST_GET.split('\n'))

        result, _, status = self.parser.parse(request[:80000])
        result, _, status = self.parser.parse(request[80000:])
        self.assertNotEqual(result, None)
        self.compare_get()

        wrong1 = WRONG % ('xx', '\r\nContent-Length: 10')
        wrong2 = WRONG % (':', '')
        wrong3 = WRONG % (':', '\r\nContent-Length: 10000000')
        wrong4 = WRONG % (':', '\r\nContent-Length: xxxx')
        

        for string in [wrong1, wrong2, wrong3, wrong4]:
            request = '\r\n'.join(string.split('\n'))
            result, _, status = self.parser.parse(request)
            self.assertEqual(result, None)


        request = '\r\n'.join(REQUEST_GET.split('\n'))
        result, _, status = self.parser.parse(request)
        self.assertNotEqual(result, None)
        self.compare_get()

        
    def test_req_packet(self):
        args = {'urlname':'urlvalue', 'urlname1':'urlvalue1'}
        cookie = {'cookie1':'cv1', 'cookie2':'cv2'}
        headers = {'header1': 'hv1', 'header2': 'hv2'}
        body = 'This is a test packet'
        self.packet.request('POST', '/testurl', args=args, 
                            headers=headers, cookie=cookie, body=body)
        
        result, _, status = self.parser.parse(self.packet.packet())
        self.assertNotEqual(result, None)



    def test_res_packet(self):
        cookie = {'cookie1':'cv1', 'cookie2':'cv2'}
        headers = {'header1': 'hv1', 'header2': 'hv2'}
        body = 'This is a test packet'

        self.packet.response(200, headers=headers, cookie=cookie, body=body)
        result, _, status = self.parser.parse(self.packet.packet())
        self.assertNotEqual(result, None)
        self.assertEqual(self.parser.reason, 'ok')




if __name__ == '__main__':
    unittest.main()
