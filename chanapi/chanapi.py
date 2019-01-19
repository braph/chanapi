#!/usr/bin/python3

import json
import requests
import tempfile

from urllib.parse import urlparse, urlunparse
from os.path import dirname, basename

from lxml import html

class ChanUpload():
    __slots__ = (
        'base_url',
        'post_url',
        'captcha_url',
        'captcha_solve_url',

        'requests_obj'
    )
    
    def __init__(self, base_url, requests_obj):
        self.base_url = base_url
        self.post_url           = base_url + '/post.php'
        self.requests_obj       = requests_obj
        self.captcha_url        = base_url + '/inc/lib/captcha/captcha.php'
        self.captcha_solve_url  = base_url + '/ip_bypass.php'

    def getTree(self, url):
        result = self.requests_obj.get(url)
        return html.fromstring(result.content)

    def doPost(self, url, *args, **kwargs):
        tree = self.getTree(url)
        self.doPostTree(tree, *args, **kwargs)

    def doPostTree(self, tree, subject='', text='', files=None, email='', password=None):
        # email=sage
        form = tree.xpath('//form[@name = "post"]')[0]

        data = {}
        inputs = form.xpath('.//input')
        for inp in inputs:
            try:
                data[inp.name] = inp.attrib['value']
            except Exception as e:
                pass #print(e, inp.attrib)

        files_data = {}
        if files:
            for f, fkey in zip(files, ['file', 'file2', 'file3', 'file4']):
                files_data[fkey] = open(f, 'rb')

        data['json_response'] = 1
        data['subject'] = subject
        data['body']    = text
        data['email']   = email
        if password:
            data['password'] = password

        #print(data)
        #print(data.keys())
        #print(files_data)

        result = self.requests_obj.post(self.post_url, data=data, files=files_data)
        json_result = json.loads(result.text)
        if 'redirect' in json_result:
            return json_result

        try:
            json_result = json.loads(result.text)
            if 'ip_bypass' in json_result['error']:
                print('must solve a captcha ')
                if not solveCaptcha():
                    print('nope!')
                    return False
            elif 'redirect' in json_result:
                return json_result['redirect']
        except:
            pass

        result = self.requests_obj.post(self.post_url, data=data, files=files_data)
        print(result)
        print(result.text)


    def solveCaptcha(self, max_tries=3):
        result = self.requests_obj.get(self.captcha_url)

        with open(tempfile.NamedTemporaryFile('wb', prefix='captcha')) as f:
            f.file.write(result.content)
            os.system("feh '%s' &" % f.file.name)

        while True:
            code = input('Captcha: ')
            if code:
                break

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

    def __init__(self, base_url, requests_obj=requests):
        self.base_url       = base_url
        self.board_url      = base_url + '/%s/%d.json'
        self.thread_url     = base_url + '/%s/res/%d.json'
        self.catalog_url    = base_url + '/%s/catalog.json'
        self.requests_obj   = requests_obj
    
    def getJson(self, url):
        result = self.requests_obj.get(url)
        return json.loads(result.text)

    def getBoard(self, board):
        return self.getJson(self.board_url % board)

    def getThread(self, board, thread):
        return self.getJson(self.thread_url % (board, thread))

    def getCatalog(self, board):
        return self.getJson(self.catalog_url % board)

    def getAllThreadsOfBoard(board):
        catalog = getCatalog(board)
        for cata in catalog:
            for thread in cata['threads']:
                try:
                    yield getThread('b', thread['no'])
                except Exception as e:
                    print(e)

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

