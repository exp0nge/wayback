from logging.config import dictConfig
from flask import Flask, request, jsonify
import requests
from user_agent import generate_user_agent
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import datetime
import base64
from flask_cors import CORS
import asyncio
import aiohttp
from aiohttp import ClientSession, ClientConnectorError
from aiohttp.client_exceptions import ContentTypeError

app = Flask(__name__)
CORS(app)

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


async def _fetch(u, file_type, session, sem):
    try:
        app.logger.debug(
            'requesting {}, filename: {}'.format(u, u.split("/")[-1]))
        async with sem:
            def req():
                return session.request(method='POST',
                                       url="https://siasky.net/skynet/skyfile",
                                       data=requests.get(u).content,
                                       headers={
                                           'Content-Type': file_type,
                                           'Accept': 'application/json'
                                       },
                                       params={
                                           'filename': u.split("/")[-1]
                                       })

            async def handle_rate_limit(iter=1):
                sky_response = await req()
                if sky_response.status == 200:
                    return await sky_response.json()
                elif sky_response.status == 429:
                    app.logger.debug('got 429, sleeping for 1')
                    await asyncio.sleep(1 * iter)
                    return await handle_rate_limit(iter ** 2)
                else:
                    err = 'skynet didnt return 200, got {}'.format(await sky_response.text())
                    app.logger.error(err)
                    raise ValueError(err)
            sky_response = await handle_rate_limit()
    except ClientConnectorError:
        return None
    return (u, sky_response['skylink'])


async def get_skylinks(base_url, tags, file_type):
    sem = asyncio.Semaphore(5)
    async with ClientSession() as session:
        app.logger.info(
            "base_url {}, file_type {}".format(base_url, file_type))
        skylinks = {}
        tasks = []
        for c in tags:
            if c:
                if c.startswith('http'):
                    u = c
                else:
                    u = urljoin(base_url, c)
                tasks.append(_fetch(u=u, file_type=file_type,
                                    session=session, sem=sem))
        results = await asyncio.gather(*tasks)
        for u, lnk in results:
            skylinks[u] = lnk
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
            soup = BeautifulSoup(html, features='html.parser')
            css = set(x.get('href') for x in soup.find_all(
                "link", attrs={'rel': 'stylesheet'}) if x.get('href'))
            css_sky = asyncio.run(get_skylinks(url, css, 'text/css'))
            js = set(x.get('src')
                     for x in soup.find_all("script"))
            js_sky = asyncio.run(get_skylinks(url, js, 'text/javascript'))
            img = set(x.get('src') for x in soup.find_all("img"))
            img_sky = asyncio.run(get_skylinks(
                url, img, 'application/octet-stream'))
            sky_html = replace_with_skylinks(
                html, {**css_sky, **js_sky, **img_sky})
            sky_html_response = requests.post(
                "https://siasky.net/skynet/skyfile", data=sky_html.encode(), headers={'Content-Type': 'text/html'}, params={
                    'filename': '{}.{}'.format(base64.b64encode(url.encode()), datetime.datetime.now().timestamp())
                })
            sky_html_response.raise_for_status()

            extract = {
                'content': html,
                'img': list(img),
                'img_sky': list(img_sky),
                'css': list(css),
                'css_sky': list(css_sky),
                'js': list(js),
                'js_sky': list(js_sky),
                'sky_html': sky_html,
                'sky_html_link': sky_html_response.json()['skylink']
            }

            return jsonify(extract)
        except Exception as e:
            app.logger.error("error on url: {}, error: {}".format(url, e))
            return 'unprocessable', 400
    else:
        return 'missing r', 400


if __name__ == "__main__":
    app.run(debug=True)
