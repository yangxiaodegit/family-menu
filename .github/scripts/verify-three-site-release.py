"""Verify public installer bytes and a real isolated 2.0.14 -> 2.0.15 upgrade.
Only synthetic runner data is used. No private source or user data is required.
"""
import hashlib
import http.cookiejar
import json
import os
from pathlib import Path
import sqlite3
import struct
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

VERSION = '2.0.15'
SHA = os.environ['EXPECTED_SHA256']
SIZE = int(os.environ['EXPECTED_SIZE'])
SETUP = 'Three_Site_Replenishment_Setup_2.0.15.exe'
API = 'https://api.github.com/repos/yangxiaodegit/family-menu/contents/updates/three-site-replenishment/'
CURL = str(Path(os.environ['SystemRoot']) / 'System32/curl.exe')
ROOT = Path(os.environ['RUNNER_TEMP']) / ('three-site-public-qa-' + uuid.uuid4().hex)
ROOT.mkdir(parents=True)
RESULT = Path('release-verification')
RESULT.mkdir(exist_ok=True)
checks = []
connections = []
processes = []


def check(name, ok):
    checks.append({'check': name, 'pass': bool(ok)})
    print(('PASS ' if ok else 'FAIL ') + name, flush=True)
    if not ok:
        raise AssertionError(name)


def wait(fn, seconds=75):
    deadline = time.monotonic() + seconds
    last = None
    while time.monotonic() < deadline:
        try:
            value = fn()
            if value:
                return value
        except Exception as exc:
            last = exc
        time.sleep(0.2)
    raise TimeoutError('Native app readiness timed out: ' + repr(last))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download(url, path, maximum, redirects=False):
    args = [CURL, '-q', '--ipv4', '--http1.1', '--fail', '--silent', '--show-error',
            '--proto', '=https', '--proto-redir', '=https', '--retry', '3',
            '--retry-delay', '2', '--connect-timeout', '10', '--max-time', '180',
            '--max-filesize', str(maximum), '--max-redirs', '5' if redirects else '0',
            '-H', 'Accept: application/vnd.github.raw+json',
            '-H', 'X-GitHub-Api-Version: 2022-11-28',
            '-H', 'User-Agent: ThreeSite-Release-Verification',
            '--write-out', '%{http_code}\n%{url_effective}', '-o', str(path)]
    if redirects:
        args.append('--location')
    result = subprocess.run(args + [url], capture_output=True, text=True, timeout=240)
    if result.returncode:
        raise RuntimeError('Official GitHub download failed: ' + result.stderr[-1200:])
    code, effective = result.stdout.strip().split('\n', 1)
    host = urllib.parse.urlsplit(effective).hostname
    if code != '200' or host not in ('api.github.com', 'github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com'):
        raise RuntimeError('Unexpected official download response: ' + code + ' ' + str(host))
    return path


def pe_gui(path):
    raw = path.read_bytes()
    off = struct.unpack_from('<I', raw, 0x3c)[0]
    return (raw[:2] == b'MZ' and raw[off:off+4] == b'PE\0\0'
            and struct.unpack_from('<H', raw, off+4)[0] == 0x8664
            and struct.unpack_from('<H', raw, off+24+68)[0] == 2)


def request(url, headers=None, body=None, opener=None):
    req = urllib.request.Request(url, headers=headers or {},
            data=None if body is None else json.dumps(body).encode('utf-8'))
    with opener.open(req, timeout=8) as response:
        return json.load(response)


def connect(state, expected_version):
    runtime = json.loads((state / 'runtime.json').read_text(encoding='utf-8'))
    if runtime['version'] != expected_version:
        return None
    url = runtime['url']
    if urllib.parse.urlsplit(url).hostname not in ('127.0.0.1', 'localhost', '::1'):
        raise RuntimeError('Unexpected non-loopback native service URL')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    headers = {'Origin': url.rstrip('/'), 'Content-Type': 'application/json',
               'X-Replen-CSRF': runtime['secret'], 'X-Replen-Version': runtime['version'],
               'X-Replen-Protocol': '2'}
    request(url + 'api/bootstrap', headers, {'secret': runtime['secret']}, opener)
    connection = (url, headers, runtime['pid'], opener)
    connections.append(connection)
    return connection


def db_snapshot(state):
    db = sqlite3.connect((state / 'workspace.db').as_uri() + '?mode=ro', uri=True)
    try:
        return db.execute('select kind,id,site,body from objects order by kind,id').fetchall()
    finally:
        db.close()


def main():
    manifest_path = download(API + 'latest.json?ref=main', ROOT / 'latest.json', 65536)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    check('Public latest manifest is the expected 2.0.15 Windows amd64 release',
          (manifest['product'], manifest['version'], manifest['platform'], manifest['arch'], manifest['setup'])
          == ('ThreeSiteReplenishment', VERSION, 'windows', 'amd64', SETUP))
    check('Manifest size and SHA256 match the approved CI artifact',
          manifest['size'] == SIZE and manifest['sha256'] == SHA)
    setup = download(API + SETUP + '?ref=main', ROOT / SETUP, SIZE)
    check('Official IPv4 Contents API downloads the entire installer', setup.stat().st_size == SIZE)
    check('Official Contents API installer SHA256 matches', digest(setup) == SHA)
    check('Published installer is Windows x64 GUI, not a console application', pe_gui(setup))
    release_url = 'https://github.com/yangxiaodegit/family-menu/releases/download/three-site-v2.0.15/' + SETUP
    release_copy = download(release_url, ROOT / 'release-copy.exe', SIZE, redirects=True)
    check('GitHub Release direct download matches the same installer',
          release_copy.stat().st_size == SIZE and digest(release_copy) == SHA)
    old = download(API + 'Three_Site_Replenishment_Setup_2.0.14.exe?ref=main', ROOT / 'old-2.0.14.exe', 16203776)
    check('Previous official 2.0.14 installer remains unchanged',
          old.stat().st_size == 16203776 and digest(old) == 'ec4d3a7a69757b59a87eaed68c108c9041ee0ca7e8bfd376d0627a6dcc007cb0')
    env = dict(os.environ, LOCALAPPDATA=str(ROOT / 'Local'), APPDATA=str(ROOT / 'Roaming'))
    Path(env['LOCALAPPDATA']).mkdir(parents=True)
    Path(env['APPDATA']).mkdir(parents=True)
    state = Path(os.environ['USERPROFILE']) / ('three-site-release-qa-' + uuid.uuid4().hex)
    state.mkdir()
    subprocess.run([str(old), '--online-update', '--state-dir', str(state), '--no-launch'],
                   env=env, timeout=100, check=True)
    target = Path(env['LOCALAPPDATA']) / 'Programs/ThreeSiteReplenishment'
    app = target / 'ReplenishmentSuite.exe'
    check('Previous installer installs successfully into isolated runner directories', app.is_file())
    check('Program and custom data reside on different Windows volumes',
          target.drive.lower() != state.drive.lower())
    process = subprocess.Popen([str(app), '--no-browser'], env=env)
    processes.append(process)
    url, headers, oldpid, opener = wait(lambda: connect(state, '2.0.14'))
    check('Previous installed app starts as 2.0.14',
          request(url + 'api/update/status', headers, opener=opener)['current'] == '2.0.14')
    retained = {}
    for name in ('JDPOPWorkbench', 'CoupangKoreaWorkbench', 'JDSelfOperatedWorkbench'):
        folder = Path(env['LOCALAPPDATA']) / name
        folder.mkdir(exist_ok=True)
        sentinel = folder / 'release-preservation-test.txt'
        sentinel.write_bytes(('SYNTHETIC ONLY ' + name).encode('utf-8'))
        retained[sentinel] = digest(sentinel)
    sentinel = state / 'release-preservation-test.txt'
    sentinel.write_bytes(b'SYNTHETIC CUSTOM STATE - KEEP EXACT BYTES')
    retained[sentinel] = digest(sentinel)
    before = db_snapshot(state)
    subprocess.run([str(setup), '--online-update', '--state-dir', str(state)],
                   env=env, timeout=100, check=True)
    url, headers, newpid, opener = wait(lambda: connect(state, VERSION))
    check('Downloaded 2.0.15 installer upgrades and restarts the native app', newpid != oldpid)
    check('Installed host reports the actual 2.0.15 version',
          request(url + 'api/update/status', headers, opener=opener)['current'] == VERSION)
    check('Installed payload manifest is 2.0.15',
          json.loads((target / 'manifest.json').read_text(encoding='utf-8'))['version'] == VERSION)
    check('Custom state path is retained across the upgrade',
          os.path.samefile(json.loads((target / 'online-install.json').read_text(encoding='utf-8'))['state_dir'], state))
    check('Workspace database objects are preserved', db_snapshot(state) == before)
    check('All station and custom-state sentinel bytes are preserved',
          all(digest(path) == value for path, value in retained.items()))
    request(url + 'api/shutdown', headers, {}, opener)
    wait(lambda: not (state / 'runtime.json').exists(), seconds=30)
    check('Upgraded native service shuts down cleanly', True)


try:
    main()
except Exception as exc:
    checks.append({'check': 'verification exception', 'pass': False, 'error': str(exc)})
    raise
finally:
    for url, headers, pid, opener in reversed(connections):
        try:
            request(url + 'api/shutdown', headers, {}, opener)
        except Exception:
            pass
    for process in processes:
        if process.poll() is None:
            process.terminate()
    report = {'version': VERSION, 'sha256': SHA, 'size': SIZE,
              'runner_os': os.environ.get('RUNNER_OS'),
              'all_passed': bool(checks) and all(item['pass'] for item in checks), 'checks': checks}
    (RESULT / 'windows-official-download.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
