#!/usr/bin/python3

import os
import json
import time
import base64
import requests
import tempfile

from os.path import dirname
from urllib.parse import urlparse, urlunparse

from lxml import html

import deadsimplethreading

class PostError(Exception):
    pass

class FloodDetected(PostError):
    pass

class CaptchaError(PostError):
    pass

class BannedError(PostError):
    pass

class ChanUpload():
    __slots__ = (
        'base_url',
        'post_url',
        'captcha_url',
        'captcha_solve_url',

        'fortune_captcha_url', # TOR

        'requests_obj'
    )
    
    def __init__(self, base_url, requests_obj=None):
        if not requests_obj:
            requests_obj = requests.Session()

        self.base_url = base_url
        self.post_url           = base_url + '/post.php'
        self.requests_obj       = requests_obj
        self.captcha_url        = base_url + '/inc/lib/captcha/captcha.php'
        self.captcha_solve_url  = base_url + '/ip_bypass.php'
        self.fortune_captcha_url = base_url + '/fortune_captcha.php'

    def loadCookies(self, storage_file):
        ''' Load cookies into session '''
        try:
            with open(storage_file, 'r') as fh:
                self.requests_obj.cookies.update(json.load(fh))
        except FileNotFoundError:
            pass #print('warning:', )
        except Exception as e:
            print(e)

    def storeCookies(self, storage_file):
        ''' Store cookies '''
        with open(storage_file, 'w') as fh:
            json.dump(dict(self.requests_obj.cookies), fh)

    def getTree(self, url):
        result = self.requests_obj.get(url)
        return html.fromstring(result.content)

    def post(self, url, *args, **kwargs):
        ''' See _postTree for args '''
        tree = self.getTree(url)
        return self.postTree(tree, *args, **kwargs)

    def postTree(self, *args, sleep=10, tries=15, **kwargs):
        ''' See _postTree for args '''

        ex = None
        for _ in range(tries):
            try:
                return self._postTree(*args, **kwargs)
            except BannedError:
                raise
            except PostError as e:
                time.sleep(sleep)
                ex = e
        raise ex

    def _postTree(self, tree, text='', name='', subject='', email='', files=None, password=None):
        # email=sage
        form = tree.xpath('//form[@name = "post"]')[0]

        data = {}
        inputs = form.xpath('.//input')
        for inp in inputs:
            try:
                data[inp.name] = inp.attrib['value']
            except Exception as e:
                pass #print(e, inp.attrib)

        print(list(data.keys()))

        files_data = {}
        if files:
            for f, fkey in zip(files, ['file', 'file2', 'file3', 'file4']):
                files_data[fkey] = open(f, 'rb')

        data['json_response'] = 1
        data['subject'] = subject
        data['body']    = text
        data['email']   = email
        if name:
            data['user'] = name
        if password:
            data['password'] = password

        #print(data)
        print(list(data.keys()))
        #print(files_data)

        result = self.requests_obj.post(self.post_url, data=data, files=files_data)
        json_result = json.loads(result.text)
        print(json_result)

        try:
            if 'redirect' in json_result:
                return json_result

            elif 'error' in json_result:
                if 'banned' in json_result:
                    raise BannedError(json_result)

                elif 'Flood' in json_result['error']:
                    raise FloodDetected(json_result)

                elif 'ip_bypass' in json_result['error']:
                    print('must solve a captcha ')
                    if not self.solveCaptcha():
                        print('captcha solving failed nope!')
                    raise CaptchaError(json_result)

                elif 'fortune_captcha' in json_result['error']:
                    print('must solve a fortune captcha ')
                    if not self.solveFortuneCaptcha():
                        print('captcha solving failed nope!')
                    raise CaptchaError(json_result)
                else:
                    raise PostError(json_result)
        except PostError:
            raise
        except Exception as e:
            raise Exception(json_result)

        #result = self.requests_obj.post(self.post_url, data=data, files=files_data)
        #print(result.text)
        #return result

    def _inputForCaptcha(self, f):
        os.system("feh '%s' &" % f)

        while True:
            code = input('Captcha: ')
            if code:
                return code

    def solveFortuneCaptcha(self, max_tries=30):
        # http-equiv="refresh" content="15">
        result = self.requests_obj.get(self.fortune_captcha_url)
        print(result.text)
        tree = html.fromstring(result.content)

        data = {}
        inputs = tree.xpath('.//input')
        for inp in inputs:
            data[inp.name] = inp.attrib.get('value', '')

        img_base64 = tree.xpath('//img/@src')[0]
        img_base64 = img_base64.split('base64,')[1]
        img_data   = base64.standard_b64decode(img_base64)
        with tempfile.NamedTemporaryFile('wb', prefix='captcha') as f:
            f.file.write(img_data)
            f.file.flush()
            data['captcha_code'] = self._inputForCaptcha(f.name)

        result = self.requests_obj.post(self.fortune_captcha_url, data=data)
        print(result)
        print(result.text)

        if 'Try again' in result.text:
            if max_tries > 1:
                return self.solveCaptcha(max_tries - 1)
            else:
                return False

        return True

    def solveCaptcha(self, max_tries=5):
        result = self.requests_obj.get(self.captcha_url)

        with tempfile.NamedTemporaryFile('wb', prefix='captcha') as f:
            f.file.write(result.content)
            f.file.flush()
            code = self._inputForCaptcha(f.name)

        data = dict(captcha_code=code)
        result = self.requests_obj.post(self.captcha_solve_url, data=data)
        print(result)
        print(result.text)

        if 'Try again' in result.text:
            if max_tries > 1:
                return self.solveCaptcha(max_tries - 1)
            else:
                return False

        return True


#class ChanURLs():
#    def getThread

#    https://kohlchan.net/m/res/21058.html
#                        /m/res/20202.html
#                        /m/1.html
#                        /m/
#
#    def getJSON(self, url):
#        pass
#
#
#    chanUrls = ChanURLs('http://kohlchan.net')
#    chanUrls.json.



    #def mkJson(url):
    #    ''' Return JSON url '''
    #    # https://kohlchan.net/m/res/21058.html
    #    parts = urlparse(url)
    #    path = parts.path
    #    path = dirname(path)
    #    path = path.replace('res', 'src')
    #    path += '/%s%s' % (post['tim'], post['ext'])
    #    parts = parts._replace(path=path)
    #    return urlunparse(parts)

class ChanJson():
    '''
        Basic access to chans json API
    '''

    __slots__ = (
        'base_url',
        'board_url',
        'thread_url',
        'catalog_url',

        'requests_obj'
    )

    def __init__(self, base_url, requests_obj=None):
        if not requests_obj:
            requests_obj = requests

        self.base_url       = base_url
        self.board_url      = base_url + '/%s/%d.json'
        self.thread_url     = base_url + '/%s/res/%d.json'
        self.catalog_url    = base_url + '/%s/catalog.json'
        self.requests_obj   = requests_obj
    
    def getJson(self, url):
        result = self.requests_obj.get(url)
        return json.loads(result.text)

    def getBoard(self, board, page=1):
        return self.getJson(self.board_url % (board, page))

    def getThread(self, board, thread):
        return self.getJson(self.thread_url % (board, thread))

    #def getBoardUrl(self, board, page=1):
    #    return self.board_url % (board, page)

    #def getThreadUrl(self, board, thread):
    #    return self.thread_url % (board, thread)

    def getCatalog(self, board):
        return self.getJson(self.catalog_url % board)

    @deadsimplethreading.threaded_func
    def getAllThreadsOfBoard(self, board):
        catalog = self.getCatalog(board)
        for cata in catalog:
            for thread in cata['threads']:
                try:
                    yield deadsimplethreading.threaded(
                        ChanJson.getThread, self, board, thread['no']
                    )
                except Exception as e:
                    print(e)

    #def mkJson(url):
    #    ''' Return JSON url '''
    #    # https://kohlchan.net/m/res/21058.html
    #    parts = urlparse(url)
    #    path = parts.path
    #    path = dirname(path)
    #    path = path.replace('res', 'src')
    #    path += '/%s%s' % (post['tim'], post['ext'])
    #    parts = parts._replace(path=path)
    #    return urlunparse(parts)


class FileInfo():
    __slots__ = (
        'filename',
        'basename',
        'ext',
        'tim',
        'url',
        'md5'
    )

    def __init__(self, filename, basename, ext, tim, url, md5):
        self.filename = filename
        self.basename = basename
        self.ext = ext
        self.tim = tim
        self.url = url
        self.md5 = md5

    def __repr__(self):
        return "['%s' %s %s]" % (self.filename, self.tim, self.url)

    def getFileUrl(post, url):
        ''' Return URL of posted file by ['tim', 'ext'] fields and base url '''
        # https://kohlchan.net/m/res/21058.html
        parts = urlparse(url)
        path = parts.path
        path = dirname(path)
        path = path.replace('res', 'src')
        path += '/%s%s' % (post['tim'], post['ext'])
        parts = parts._replace(path=path)
        return urlunparse(parts)

    def fromJson(post, url):
        return FileInfo(
            '%s%s' % (post['filename'], post['ext']),
            post['filename'],
            post['ext'][1:],
            post['tim'],
            FileInfo.getFileUrl(post, url),
            post['md5']
        )

    def getFiles(post, url):
        if 'tim' in post:
            yield FileInfo.fromJson(post, url)

            if 'extra_files' in post:
                for extra in post['extra_files']:
                    yield getFileInfo(extra, url)

