import requests
import json
import os.path as osp
from os import mkdir
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from browsermobproxy import Server
import aiohttp
import asyncio

DOWNLODAD_URL = "/media/alexhowe/mydisk/Douyin"
SUBDIR = ""
headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 '
                  'Safari/537.36'}


class Video(object):
    __slots__ = ['name', 'url', 'id']

    def __str__(self):
        return "The Video Name is: {}\n, Url is: {}".format(self.name, "\n".join(self.url))


def url_transfer(url):
    server = Server("/home/alexhowe/workspace/browsermob-proxy-2.1.4/bin/browsermob-proxy")
    server.start()
    proxy = server.create_proxy()
    chrome_options = Options()
    chrome_options.add_argument('--proxy-server={0}'.format(proxy.proxy))
    # chrome_options.add_argument('--headless')
    # chrome_options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(chrome_options=chrome_options)
    proxy.new_har("douyin", options={'captureHeaders': True, 'captureContent': True})
    driver.get(url)
    nick = driver.find_element_by_class_name('nickname').text
    print(nick)
    global SUBDIR
    SUBDIR = nick
    if not osp.exists(osp.join(DOWNLODAD_URL, nick)):
        mkdir(osp.join(DOWNLODAD_URL, nick))
    result = proxy.har
    for entry in result['log']['entries']:
        _url = entry['request']['url']
        if "web/api" in _url:
            # print(_url)
            cookies = driver.get_cookies()
            return get_json(cookies, _url), _url, cookies


def get_json(cookies, _url):
    with requests.Session() as sess:
        sess.headers.clear()
        sess.headers[
            "User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) " \
                            "Chrome/73.0.3683.86 Safari/537.36 "
        for cookie in cookies:
            sess.cookies.set(cookie['name'], cookie['value'])
        text = sess.get(_url).text
        # print(text)
        return text


def extract_from_result(url):
    res, url, cookies = url_transfer(url)
    rjson = json.loads(res)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(extract_videos(res))
    while rjson['has_more']:
        max_cursor = rjson['max_cursor']
        # print(max_cursor)
        surl = str(url).split("&")
        for i in surl:
            if "max_cursor" in i:
                rp = "max_cursor={}".format(max_cursor)
                surl[surl.index(i)] = rp
                next_url = "&".join(surl)
                print(next_url)
                text = get_json(cookies, next_url)
                loop = asyncio.get_event_loop()
                loop.run_until_complete(extract_videos(text))
                rjson = json.loads(text)


async def extract_videos(text: str):
    aweme_list = json.loads(text)["aweme_list"]
    for aweme in aweme_list:
        video = Video()
        video.name = aweme['desc'].split("#")[0].strip()
        video.url = aweme['video']['download_addr']['url_list']
        video.id = aweme['aweme_id']
        if aweme['desc'].startswith('#'):
            video.name = video.id
        # videos.append(video)
        async with aiohttp.ClientSession(headers=headers) as session:
            await download_video(session, video)


async def download_video(session, video: Video):
    # res = requests.get(video.url[0])
    try:
        video_path = osp.join(DOWNLODAD_URL, SUBDIR, video.name + ".mp4")
        if not osp.exists(video_path):
            await download(session, video, video_path)
        elif osp.getsize(video_path) == 0:
            await download(session, video, video_path)
        else:
            print("Video: {} is already exists".format(video.name))
    except Exception as e:
        print("Video: {} downloads failed".format(video.name), e)


async def download(session, video, video_path):
    async with session.get(video.url[0]) as res:
        print("Downloading {} >>>>>>>>>>>>>>>>>".format(video.name), res.status)
        content = await res.content.read()
        if res.status == 200:
            with open(video_path, "wb")as fw:
                fw.write(content)


if __name__ == '__main__':
    extract_from_result("http://v.douyin.com/xE6BD3/")
