from logging.config import dictConfig
from flask import Flask, request, jsonify
import requests
from user_agent import generate_user_agent
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import datetime
import base64

app = Flask(__name__)


dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

SIASKY_BASE_URL = 'https://siasky.net/'


def get_skylinks(base_url, tags, file_type):
    app.logger.info("base_url {}, file_type {}".format(base_url, file_type))
    skylinks = {}
    for c in tags:
        if c:
            if c.startswith('http'):
                u = c
            else:
                u = urljoin(base_url, c)
            sky_response = requests.post(
                "https://siasky.net/skynet/skyfile", data=requests.get(u), headers={'Content-Type': file_type}, params={'filename': u.split("/")[-1]})
            sky_response.raise_for_status()
            skylinks[c] = sky_response.json()['skylink']
    return skylinks


def replace_with_skylinks(html, sky_links):
    for orig, lnk in sky_links.items():
        html = html.replace(orig, '{}{}'.format(SIASKY_BASE_URL, lnk))
    return html


@app.route("/")
def cors():
    url = request.args.get("r")
    if url:
        headers = {
            'User-Agent': generate_user_agent()
        }
        try:
            html = requests.get(url, headers=headers).text
            soup = BeautifulSoup(html)
            css = [x.get('href') for x in soup.find_all(
                "link", attrs={'rel': 'stylesheet'}) if x.get('href')]
            css_sky = get_skylinks(url, css, 'text/css')
            js = [x.get('src')
                  for x in soup.find_all("script")]
            js_sky = get_skylinks(url, js, 'text/javascript')
            img = [x.get('src') for x in soup.find_all("img")]
            img_sky = get_skylinks(url, img, 'application/octet-stream')
            sky_html = replace_with_skylinks(
                html, {**css_sky, **js_sky, **img_sky})
            sky_html_response = requests.post(
                "https://siasky.net/skynet/skyfile", data=sky_html.encode(), headers={'Content-Type': 'text/html'}, params={
                    'filename': '{}.{}'.format(base64.b64encode(url.encode()), datetime.datetime.now().timestamp())
                })
            sky_html_response.raise_for_status()

            extract = {
                'content': html,
                'img': img,
                'img_sky': img_sky,
                'css': css,
                'css_sky': css_sky,
                'js': js,
                'js_sky': js_sky,
                'sky_html': sky_html,
                'sky_html_link': sky_html_response.json()['skylink']
            }

            return jsonify(extract)
        except Exception as e:
            app.logger.error("error on url: {}, error: {}".format(url, e))
            return 'unprocessable', 400
    else:
        return 'missing r', 400
