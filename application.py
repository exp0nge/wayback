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
import os
import sys
from requests.auth import HTTPBasicAuth
from urllib.parse import urlparse
import json

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
SKYFILE_HOST = 'https://siasky.net/skynet/skyfile'
NB_API_KEY = os.environ['NB_API_KEY'].strip()
NB_SECRET_KEY = os.environ['NB_SECRET_KEY'].strip()
RECORD_KEEPER_TLD = 'https://www.namebase.io/api/v0/dns/domains/knowest/nameserver'
RECORD_KEEPER_BASIC_AUTH = HTTPBasicAuth(NB_API_KEY, NB_SECRET_KEY)
NB_HEADERS = {
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}


async def _fetch(u, file_type, session, sem):
    try:
        app.logger.debug(
            'requesting {}, filename: {}'.format(u, u.split("/")[-1]))
        async with sem:
            def req():
                return session.request(method='POST',
                                       url=SKYFILE_HOST,
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


def _find_redirect_skylink(records, host):
    for record in records:
        print(record)
        if record['host'] == host:
            lnk = record['value'].split('v=txtv0;type=host;to=')[-1]
            return '{}{}'.format(
                SIASKY_BASE_URL,
                lnk[:-1]
            )


def find_existing_records(url):
    existing_nameserver_settings = requests.get(
        RECORD_KEEPER_TLD,
        auth=HTTPBasicAuth(NB_API_KEY, NB_SECRET_KEY),
        headers=NB_HEADERS
    )
    app.logger.debug(existing_nameserver_settings.json())
    existing_nameserver_settings.raise_for_status()
    records = existing_nameserver_settings.json()['records']
    domain = urlparse(url).netloc
    app.logger.debug('check for existing domain {}'.format(domain))
    existing_record = _find_redirect_skylink(records, domain)
    if existing_record:
        records_req = requests.get(existing_record)
        records_req.raise_for_status()
        records = records_req.json()
    else:
        records = {}
    return records


def _update_nb(url, new_skylink_to_append):
    domain = urlparse(url).netloc
    records = find_existing_records(url)
    epoch = datetime.datetime.now().timestamp()
    records[str(epoch)] = new_skylink_to_append
    update_req = requests.post(
        url=SKYFILE_HOST,
        data=json.dumps(records),
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        params={
            'filename': '{}_{}'.format(domain, epoch)
        })
    update_req.raise_for_status()
    skylink = update_req.json()['skylink']
    update_ns_req = requests.put(
        RECORD_KEEPER_TLD,
        auth=HTTPBasicAuth(NB_API_KEY, NB_SECRET_KEY),
        json={
            'records': [
                {
                    "type": 'CNAME',
                    "host": domain,
                    "value": skylink,
                    "ttl": 5 * 60,
                }
            ],
            'deleteRecords': []
        }
    )
    app.logger.debug(update_ns_req.text)
    update_ns_req.raise_for_status()


@app.route("/")
def scrap():
    url = request.args.get("r")
    if urlparse(url).netloc:
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
            new_skylink = '{}{}'.format(
                SIASKY_BASE_URL,
                sky_html_response.json()['skylink']
            )
            extract = {
                'content': html,
                'img': list(img),
                'img_sky': list(img_sky),
                'css': list(css),
                'css_sky': list(css_sky),
                'js': list(js),
                'js_sky': list(js_sky),
                'sky_html': sky_html,
                'sky_html_link': new_skylink
            }
            _update_nb(url, sky_html_response.json()['skylink'])
            return jsonify(extract)
        except Exception as e:
            raise e
            app.logger.error("error on url: {}, error: {}".format(url, e))
            return 'unprocessable', 400
    else:
        return 'missing r', 400


@app.route('/history')
def history():
    url = request.args.get("r")
    if urlparse(url).netloc:
        records = []
        for k, v in find_existing_records(url).items():
            records.append({
                'epoch': k,
                'skylink': v
            })
        return jsonify(records)
    else:
        return 'missing r', 400


if __name__ == "__main__":
    app.run(debug=True)
