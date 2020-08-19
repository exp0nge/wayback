# wayback


a basic impl of wayback with [Skynet](https://siasky.net/) and [HNS](https://www.namebase.io/)

Demo: [https://youtu.be/5HzxJKa-E0M](https://youtu.be/5HzxJKa-E0M)

## storage

All static (CSS, JS, HTML) content is uploaded to Skynet via a middleware layer (`application.py`) which is hosted on a server. HNS is used to manage both the record keeping of the historical state of URLs visited before and to use a more friendly URL to reference the sites and the website.

## usage

Visit the URL linked in this repo description and visit a site! If it's the first time the backend sees it, it will cache it for later retrieval. 
