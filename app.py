#!/usr/bin/python3
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qsl, quote, unquote
import requests
import gzip
from io import BytesIO


def debug_get(*args, **kwargs):
    import requests
    import socket
    import ssl
    import subprocess
    import time

    print("\n=== REQUEST STARTED ===")
    print(f"TIME: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Capture timeout settings
    connect_timeout = kwargs.get('timeout', 5)
    if isinstance(connect_timeout, tuple):
        print(f"CONNECT TIMEOUT: {connect_timeout[0]}s")
        print(f"READ TIMEOUT: {connect_timeout[1]}s")
    else:
        print(f"TIMEOUT (both connect and read): {connect_timeout}s")

    print("\n-- REQUEST DETAILS --")
    print(f"URL: {args[0]}")
    print(f"METHOD: {kwargs.get('method', 'GET')}")
    url_parts = requests.utils.urlparse(args[0])
    print(f"SCHEME: {url_parts.scheme}")
    print(f"HOST: {url_parts.netloc}")
    print(f"PATH: {url_parts.path}")
    print(f"QUERY: {url_parts.query}")
    print(f"REQUEST HEADERS: {kwargs.get('headers', {})}")

    # DNS Resolution check
    try:
        print("\n-- DNS INFO --")
        start_dns = time.time()
        ip = socket.gethostbyname(url_parts.netloc)
        dns_time = time.time() - start_dns
        print(f"RESOLVED IP: {ip}")
        print(f"DNS RESOLUTION TIME: {dns_time:.3f}s")
    except socket.gaierror as e:
        print(f"DNS RESOLUTION FAILED: {str(e)}")

    start = time.time()
    try:
        # Create a session to get more control
        session = requests.Session()

        # Set up event hooks to track timing
        timing = {}

        def time_hook(r, *args, **kwargs):
            timing['connection_time'] = time.time() - start
            return r

        session.hooks['response'] = [time_hook]

        # Make the request
        response = session.get(
            args[0],
            timeout=kwargs.get('timeout', 5),
            **{k:v for k,v in kwargs.items() if k != 'timeout'}
        )

        print("\n-- CONNECTION SUCCESS --")
        print(f"INITIAL CONNECTION TIME: {timing.get('connection_time', 'N/A')}s")
        print(f"TOTAL TIME: {time.time() - start:.3f}s")
        print(f"ELAPSED TIME: {response.elapsed.total_seconds()}s")

        print(f"STATUS CODE: {response.status_code}")
        print(f"RESPONSE HEADERS: {dict(response.headers)}")
        print(f"RESPONSE SIZE: {len(response.content)} bytes")

        return response

    except requests.exceptions.SSLError as e:
        print("\n-- SSL ERROR --")
        print(f"ERROR TYPE: SSLError")
        print(f"FAILED AFTER: {time.time() - start:.3f}s")
        print(f"ERROR MESSAGE: {str(e)}")
        print(f"HOST: {url_parts.netloc}")
        if 'ip' in locals():
            print(f"RESOLVED IP: {ip}")
            print(f"DNS TIME: {dns_time}s")
        # Try getting SSL certificate info
        try:
            cert_info = ssl.get_server_certificate((url_parts.netloc, 443))
            print(f"\nCERTIFICATE INFO:\n{cert_info}")
        except:
            print("Failed to retrieve certificate info")
        raise

    except requests.exceptions.TooManyRedirects as e:
        print("\n-- TOO MANY REDIRECTS ERROR --")
        print(f"ERROR TYPE: TooManyRedirects")
        print(f"FAILED AFTER: {time.time() - start:.3f}s")
        print(f"ERROR MESSAGE: {str(e)}")
        if hasattr(e, 'response'):
            print(f"LAST REDIRECT URL: {e.response.url}")
            print(f"REDIRECT HISTORY:")
            for resp in e.response.history:
                print(f"  {resp.url} -> {resp.status_code}")
        raise

    except requests.exceptions.ConnectTimeout as e:
        print("\n-- CONNECTION TIMEOUT ERROR --")
        print(f"ERROR TYPE: ConnectTimeout")
        print(f"FAILED AFTER: {time.time() - start:.3f}s")
        print(f"ERROR MESSAGE: {str(e)}")
        print(f"UNABLE TO CONNECT TO: {url_parts.netloc}")
        print(f"RESOLVED IP: {ip if 'ip' in locals() else 'DNS resolution failed'}")
        print(f"DNS TIME: {dns_time if 'dns_time' in locals() else 'N/A'}s")
        print(f"TIMEOUT SETTING: {connect_timeout}s")

        # Try a quick ping to check basic connectivity
        try:
            ping = subprocess.run(['ping', '-c', '1', '-W', '2', url_parts.netloc],
                                capture_output=True, text=True)
            print("\n-- PING TEST --")
            print(f"PING RESPONSE:\n{ping.stdout}")
        except:
            print("PING TEST: Failed to execute")

        raise

    except requests.exceptions.ReadTimeout as e:
        print("\n-- READ TIMEOUT ERROR --")
        print(f"ERROR TYPE: ReadTimeout")
        print(f"FAILED AFTER: {time.time() - start:.3f}s")
        print(f"ERROR MESSAGE: {str(e)}")
        print(f"PARTIAL CONNECTION TIME: {timing.get('connection_time', 'N/A')}s")
        print(f"TIMEOUT SETTING: {connect_timeout}s")
        if 'response' in locals():
            print(f"PARTIAL RESPONSE CODE: {getattr(response, 'status_code', 'N/A')}")
            print(f"PARTIAL HEADERS: {dict(getattr(response, 'headers', {}))}")
            print(f"PARTIAL CONTENT LENGTH: {len(getattr(response, 'content', b''))} bytes")
        raise

    except requests.exceptions.ConnectionError as e:
        print("\n-- CONNECTION ERROR --")
        print(f"ERROR TYPE: ConnectionError")
        print(f"FAILED AFTER: {time.time() - start:.3f}s")
        print(f"ERROR MESSAGE: {str(e)}")
        print(f"RESOLVED IP: {ip if 'ip' in locals() else 'DNS resolution failed'}")
        print(f"DNS TIME: {dns_time if 'dns_time' in locals() else 'N/A'}s")

        # Try traceroute to see where connection fails
        try:
            traceroute = subprocess.run(['traceroute', url_parts.netloc],
                                      capture_output=True, text=True, timeout=10)
            print("\n-- TRACEROUTE --")
            print(f"ROUTE:\n{traceroute.stdout}")
        except:
            print("TRACEROUTE: Failed to execute")

        raise

    except requests.exceptions.HTTPError as e:
        print("\n-- HTTP ERROR --")
        print(f"ERROR TYPE: HTTPError")
        print(f"FAILED AFTER: {time.time() - start:.3f}s")
        print(f"ERROR MESSAGE: {str(e)}")
        if hasattr(e, 'response'):
            print(f"STATUS CODE: {e.response.status_code}")
            print(f"RESPONSE HEADERS: {dict(e.response.headers)}")
            print(f"RESPONSE CONTENT: {e.response.content[:500]}...")  # First 500 bytes
            print(f"REQUEST URL: {e.response.url}")
            print(f"REQUEST METHOD: {e.response.request.method}")
            print(f"REQUEST HEADERS: {dict(e.response.request.headers)}")
        raise

    except Exception as e:
        print("\n-- UNEXPECTED ERROR --")
        print(f"ERROR TYPE: {type(e).__name__}")
        print(f"ERROR MESSAGE: {str(e)}")
        print(f"FAILED AFTER: {time.time() - start:.3f}s")
        if 'ip' in locals():
            print(f"RESOLVED IP: {ip}")
            print(f"DNS TIME: {dns_time}s")
        if 'timing' in locals():
            print(f"PARTIAL CONNECTION TIME: {timing.get('connection_time', 'N/A')}s")
        raise

    finally:
        print("\n=== REQUEST ENDED ===\n")

if os.getenv('DEBUG'):
    original_get = requests.get
    requests.get = debug_get

PORT = 80
REGION_ALL = 'all'

PLAYLIST_PATH = 'playlist.m3u8'
EPG_PATH = 'epg.xml'
STATUS_PATH = ''
APP_URL = 'https://i.mjh.nz/SamsungTVPlus/.channels.json'
EPG_URL = f'https://i.mjh.nz/SamsungTVPlus/{REGION_ALL}.xml.gz'
PLAYBACK_URL = 'https://jmp2.uk/sam-{id}.m3u8'


class Handler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self._params = {}
        super().__init__(*args, **kwargs)

    def _error(self, message):
        self.send_response(500)
        self.end_headers()
        self.wfile.write(f'Error: {message}'.encode('utf8'))
        raise

    def do_GET(self):
        # Serve the favicon.ico file
        if self.path == '/favicon.ico':
            self._serve_favicon()
            return

        routes = {
            PLAYLIST_PATH: self._playlist,
            EPG_PATH: self._epg,
            STATUS_PATH: self._status,
        }

        parsed = urlparse(self.path)
        func = parsed.path.split('/')[1]
        self._params = dict(parse_qsl(parsed.query, keep_blank_values=True))

        if func not in routes:
            self.send_response(404)
            self.end_headers()
            return

        try:
            routes[func]()
        except Exception as e:
            self._error(e)

    def _serve_favicon(self):
        # Serve the favicon file as an ICO file
        try:
            with open('favicon.ico', 'rb') as f:
                self.send_response(200)
                self.send_header('Content-Type', 'image/x-icon')
                self.end_headers()
                self.wfile.write(f.read())
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()

    def _playlist(self):
        all_channels = requests.get(APP_URL).json()['regions']

        # Retrieve filters from URL or fallback to environment variables
        regions = [region.strip().lower() for region in (self._params.get('regions') or os.getenv('REGIONS', REGION_ALL)).split(',')]
        regions = [region for region in all_channels.keys() if region.lower() in regions or REGION_ALL in regions]
        groups = [unquote(group).lower() for group in (self._params.get('groups') or os.getenv('GROUPS', '')).split(',')]
        groups = [group for group in groups if group]

        start_chno = int(self._params['start_chno']) if 'start_chno' in self._params else None
        sort = self._params.get('sort', 'chno')
        include = [x for x in self._params.get('include', '').split(',') if x]
        exclude = [x for x in self._params.get('exclude', '').split(',') if x]

        self.send_response(200)
        self.send_header('content-type', 'vnd.apple.mpegurl')
        self.end_headers()

        channels = {}
        print(f"Including channels from regions: {regions}")
        for region in regions:
            channels.update(all_channels[region].get('channels', {}))

        self.wfile.write(b'#EXTM3U\n')
        for key in sorted(channels.keys(), key=lambda x: channels[x]['chno'] if sort == 'chno' else channels[x]['name'].strip().lower()):
            channel = channels[key]
            logo = channel['logo']
            group = channel['group']
            name = channel['name']
            url = PLAYBACK_URL.format(id=key)
            channel_id = f'samsung-{key}'

            # Skip channels that require a license
            if channel.get('license_url'):
                continue

            # Apply include/exclude filters
            if (include and channel_id not in include) or (exclude and channel_id in exclude):
                print(f"Skipping {channel_id} due to include / exclude")
                continue

            # Apply group filter
            if groups and group.lower() not in groups:
                print(f"Skipping {channel_id} due to group filter")
                continue

            chno = ''
            if start_chno is not None:
                if start_chno > 0:
                    chno = f' tvg-chno="{start_chno}"'
                    start_chno += 1
            elif channel.get('chno') is not None:
                chno = ' tvg-chno="{}"'.format(channel['chno'])

            # Write channel information
            self.wfile.write(f'#EXTINF:-1 channel-id="{channel_id}" tvg-id="{key}" tvg-logo="{logo}" group-title="{group}"{chno},{name}\n{url}\n'.encode('utf8'))

    def _epg(self):
        # Download the .gz EPG file
        with requests.get(EPG_URL, stream=True) as resp:
            resp.raise_for_status()

            self.send_response(200)
            self.send_header('Content-Type', 'application/xml')
            self.end_headers()

            # Decompress the .gz content
            with gzip.GzipFile(fileobj=BytesIO(resp.content)) as gz:
                chunk = gz.read(1024)
                while chunk:
                    self.wfile.write(chunk)
                    chunk = gz.read(1024)

    def _status(self):
        all_channels = requests.get(APP_URL).json()['regions']

        # Generate HTML content with the favicon link
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()

        host = self.headers.get('Host')
        self.wfile.write(f'''
            <html>
            <head>
                <title>Samsung TV Plus for Channels</title>
                <link rel="icon" href="/favicon.ico" type="image/x-icon">
            </head>
            <body>
                <h1>Samsung TV Plus for Channels</h1>
                <p>Playlist URL: <b><a href="http://{host}/{PLAYLIST_PATH}">http://{host}/{PLAYLIST_PATH}</a></b></p>
                <p>EPG URL (Set to refresh every 1 hour): <b><a href="http://{host}/{EPG_PATH}">http://{host}/{EPG_PATH}</a></b></p>
                <h2>Available regions &amp; groups</h2>
        '''.encode('utf8'))

        # Display regions and their group titles with links
        for region, region_data in all_channels.items():
            encoded_region = quote(region)
            self.wfile.write(f'<h3><a href="http://{host}/{PLAYLIST_PATH}?regions={encoded_region}">{region_data["name"]}</a> ({region})</h3><ul>'.encode('utf8'))

            group_names = set(channel.get('group', None) for channel in region_data.get('channels', {}).values())
            for group in sorted(name for name in group_names if name):
                encoded_group = quote(group)
                self.wfile.write(f'<li><a href="http://{host}/{PLAYLIST_PATH}?regions={encoded_region}&groups={encoded_group}">{group}</a></li>'.encode('utf8'))
            self.wfile.write(b'</ul>')

        self.wfile.write(b'</body></html>')


class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass


def run():
    server = ThreadingSimpleServer(('0.0.0.0', PORT), Handler)
    server.serve_forever()


if __name__ == '__main__':
    run()
