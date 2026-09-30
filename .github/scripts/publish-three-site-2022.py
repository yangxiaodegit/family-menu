"""Publish the approved four-file installer archive; retain source/history and old installers."""
from pathlib import Path
import hashlib
import io
import json
import re
import shutil
import struct
import subprocess
import sys
import urllib.parse
import urllib.request
import zipfile

ROOT = Path.cwd()
CH = ROOT / 'updates/three-site-replenishment'
OUT = ROOT / 'release-verification-2022'
DESC = ROOT / '.github/three-site-2022-transfer.json'
IN = ROOT / 'incoming-three-site-2022'
VER = '2.0.22'
TAG = 'three-site-v' + VER
REPO = 'yangxiaodegit/family-menu'
EXE = 'Three_Site_Replenishment_Setup_' + VER + '.exe'
CHECKSUM = 'Three_Site_Replenishment_SHA256_' + VER + '.txt'
ALLOWED = {EXE, 'latest.json', 'PUBLIC_RELEASE_VERIFICATION.json', CHECKSUM}
PRIOR = {
    '2.0.18': 'faa51f91f9f8ccdf55df9db8a784cf66997593c87b516e1398f02079f09d23e3',
    '2.0.19': '9cbd7eaaecd67a7be3ef7c55a3700cb551beaa6cbfd7ef333e805615fefce1ba',
    '2.0.20': '286e48519125db5b1ec54a429f59b24e44d7bc01549a43d28c84e793f288c3cc',
    '2.0.21': 'eba574be88e6a9f2f824de1e74235137ca06120b04abe3f0d82ccd7d31847204',
}
LIMIT = 30 * 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def gh(*args, allow_missing=False):
    result = subprocess.run(['gh', *args], cwd=ROOT, capture_output=True)
    if result.returncode and not allow_missing:
        raise RuntimeError(result.stderr.decode(errors='replace')[:1200])
    return result


def commit(message, paths):
    git('config', 'user.name', 'github-actions[bot]')
    git('config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
    git('add', '-A', '--', *paths)
    if subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=ROOT).returncode:
        git('commit', '-m', message + ' [skip ci]')
        git('push', 'origin', 'HEAD:main')
    return git('rev-parse', 'HEAD').decode().strip()


def check_descriptor(desc):
    url = urllib.parse.urlparse(desc['url'])
    if (desc['version'] != VER or url.scheme != 'https' or not url.hostname
            or not url.hostname.endswith('.oaiusercontent.com') or url.username or url.password
            or url.port not in (None, 443) or url.fragment):
        raise ValueError('Invalid approved public-only transfer')
    for key in ('artifact_sha256', 'installer_sha256'):
        if not re.fullmatch('[a-f0-9]{64}', desc[key]):
            raise ValueError('Invalid digest: ' + key)
    if not re.fullmatch('[a-f0-9]{40}', desc['source_commit']):
        raise ValueError('Expected exact verified source commit')
    if type(desc['installer_size']) is not int or not 0 < desc['installer_size'] <= LIMIT:
        raise ValueError('Invalid approved installer size')


def validate_archive(raw, desc):
    """Pure validation, before channel mutations or extraction; return approved bytes."""
    check_descriptor(desc)
    if len(raw) > LIMIT or sha(raw) != desc['artifact_sha256']:
        raise ValueError('Public archive integrity failed')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        if (len(entries) != 4 or set(archive.namelist()) != ALLOWED
                or any(x.is_dir() or x.file_size > LIMIT for x in entries)
                or sum(x.file_size for x in entries) > LIMIT or archive.testzip()):
            raise ValueError('Public allowlist failed')
        files = {name: archive.read(name) for name in ALLOWED}
    manifest = json.loads(files['latest.json'])
    proof = json.loads(files['PUBLIC_RELEASE_VERIFICATION.json'])
    binary = files[EXE]
    if tuple(manifest[k] for k in ('product', 'version', 'platform', 'arch', 'setup')) != (
            'ThreeSiteReplenishment', VER, 'windows', 'amd64', EXE):
        raise ValueError('Manifest product mismatch')
    if (sha(binary) != desc['installer_sha256'] or manifest['sha256'] != desc['installer_sha256']
            or len(binary) != desc['installer_size'] or manifest['size'] != len(binary)):
        raise ValueError('Wrong approved binary')
    checksum_lines = files[CHECKSUM].decode('utf-8-sig').splitlines()
    matching_lines = [line.split() for line in checksum_lines if line.strip()]
    if not any(len(parts) == 2 and parts[0].lower() == sha(binary)
               and parts[1].lstrip('*') == EXE for parts in matching_lines):
        raise ValueError('Installer checksum file mismatch')
    checks = proof.get('native_edge_checks')
    if (proof['version'] != VER or proof['all_passed'] is not True
            or proof['source_commit'] != desc['source_commit']
            or proof['installer_sha256'] != sha(binary) or proof['installer_size'] != len(binary)
            or proof['independent_rebuild'] != 'identical' or not isinstance(checks, list)
            or not checks or not all(c.get('passed') is True for c in checks)):
        raise ValueError('Native verification incomplete')
    if desc.get('workflow_run') is not None and str(proof.get('workflow_run')) != str(desc['workflow_run']):
        raise ValueError('Unexpected verification workflow run')
    if len(binary) < 64 or binary[:2] != b'MZ':
        raise ValueError('Wrong Windows GUI format')
    pe = struct.unpack_from('<I', binary, 0x3c)[0]
    if (pe + 94 > len(binary) or binary[pe:pe+4] != b'PE\0\0'
            or struct.unpack_from('<H', binary, pe+4)[0] != 0x8664
            or struct.unpack_from('<H', binary, pe+24+68)[0] != 2):
        raise ValueError('Wrong Windows GUI format')
    return files, manifest, proof


def prepare():
    OUT.mkdir(exist_ok=True)
    desc = json.loads(DESC.read_text(encoding='utf-8'))
    check_descriptor(desc)
    with urllib.request.urlopen(urllib.request.Request(desc['url'], headers={
            'User-Agent': 'ThreeSitePublication/2.0.22'}), timeout=60) as response:
        raw = response.read(LIMIT + 1)
    files, manifest, proof = validate_archive(raw, desc)
    old = json.loads((CH / 'latest.json').read_text(encoding='utf-8'))
    if old['version'] != '2.0.21' or old['sha256'] != PRIOR['2.0.21']:
        raise ValueError('Stable channel changed; do not overwrite')
    fixture = ROOT / 'retired-fixtures'
    fixture.mkdir(exist_ok=True)
    for version, expected in PRIOR.items():
        path = CH / ('Three_Site_Replenishment_Setup_' + version + '.exe')
        if sha(path.read_bytes()) != expected:
            raise ValueError('Retained stable installer mismatch: ' + version)
        shutil.copy2(path, fixture / path.name)
    (OUT / 'previous-latest.json').write_bytes((CH / 'latest.json').read_bytes())
    IN.mkdir(exist_ok=True)
    for name, data in files.items():
        (IN / name).write_bytes(data)
    found = gh('release', 'view', TAG, '--repo', REPO, '--json', 'isDraft', allow_missing=True)
    if found.returncode:
        gh('release', 'create', TAG, '--repo', REPO, '--draft', '--latest=false',
           '--title', '三站补货中心 2.0.22 · 韩国可售库存为0款数', '--notes', manifest['notes'] +
           '\n\n安装包未签名，请保留安全防护。验证使用隔离合成资料，不是用户本机或真实平台验收。')
    elif not json.loads(found.stdout)['isDraft']:
        raise ValueError('Published version cannot be overwritten')
    gh('release', 'upload', TAG, '--repo', REPO, *[str(IN/n) for n in sorted(ALLOWED)], '--clobber')
    for name in ALLOWED:
        shutil.copy2(IN/name, CH/name)
    revision = commit('Offer verified Korea available-zero stock count 2.0.22 online',
                      [str((CH/n).relative_to(ROOT)) for n in sorted(ALLOWED)])
    (OUT/'channel-commit.json').write_text(json.dumps({
        'commit': revision, 'version': VER, 'sha256': manifest['sha256'],
        'source_commit': proof['source_commit']}), encoding='utf-8')
    print('Channel prepared', revision, flush=True)


def finish():
    report = OUT / 'windows-official-update-2022.json'
    result = json.loads(report.read_text(encoding='utf-8'))
    manifest = json.loads((CH/'latest.json').read_text(encoding='utf-8'))
    if (result['version'] != VER or result['all_passed'] is not True
            or result['sha256'] != manifest['sha256'] or result['size'] != manifest['size']
            or result.get('anonymous_download') is not True or result.get('cross_volume') is not True
            or not result['checks']
            or not all(x['passed'] is True for x in result['checks'])
            or result['upgrade_paths'] != ['2.0.18 -> 2.0.22', '2.0.19 -> 2.0.22', '2.0.20 -> 2.0.22', '2.0.21 -> 2.0.22']):
        raise ValueError('Official upgrade verification failed')
    gh('release', 'upload', TAG, '--repo', REPO, str(report), '--clobber')
    gh('release', 'edit', TAG, '--repo', REPO, '--draft=false', '--latest=false')
    (CH/report.name).write_bytes(report.read_bytes())
    (CH/'README.md').write_text(
        '# 三站补货中心在线更新\n\n当前正式版本：**2.0.22**。'
        '韩国站新增“可售库存为0”款数，包含可售为0但仍有在途的商品；总控台同步显示。'
        '原总库存零库存的明细、导出和补货计算保持原口径。旧草稿未提供新指标时显示“—”，重新计算后显示核验数量。'
        '保留安装目录占用修复、更新确认复查和批次合并。\n\n'
        '2.0.18、2.0.19、2.0.20或2.0.21升级前保存工作并等待任务完成。若旧版升级按钮提示先检查更新，'
        '从托盘“安全退出”后由原快捷方式重新启动并检查更新。安装报错窗口需先关闭；只关闭工作台窗口可能继续驻留。'
        '保留历史安装包和源码历史，升级保留三站业务资料。\n\n'
        '原生Windows/Edge及四条原更新器官方匿名下载升级验证使用隔离合成资料，不是用户本机验收。'
        '安装包未签名，请保留安全软件。\n', encoding='utf-8')
    paths = [str((CH/report.name).relative_to(ROOT)), str((CH/'README.md').relative_to(ROOT))]
    revoked = CH/'revoked-versions.json'
    if revoked.exists():
        record = json.loads(revoked.read_text(encoding='utf-8'))
        record['replacement'] = VER
        revoked.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        paths.append(str(revoked.relative_to(ROOT)))
    if DESC.exists():
        DESC.unlink()
        paths.append(str(DESC.relative_to(ROOT)))
    revision = commit('Finish 2.0.22 verified online update; retain prior release history', paths)
    (OUT/'publication-result.json').write_text(json.dumps({
        'version': VER, 'commit': revision, 'all_passed': True, 'sha256': manifest['sha256'],
        'previous_stable_retained': ['2.0.18', '2.0.19', '2.0.20', '2.0.21'], 'other_channels_unchanged': True}, indent=2), encoding='utf-8')


def rollback():
    previous = OUT/'previous-latest.json'
    paths = []
    if not (OUT/'publication-result.json').exists() and previous.exists():
        current = json.loads((CH/'latest.json').read_text(encoding='utf-8'))
        if current.get('version') == VER:
            (CH/'latest.json').write_bytes(previous.read_bytes())
            paths.append(str((CH/'latest.json').relative_to(ROOT)))
    if DESC.exists():
        DESC.unlink()
        paths.append(str(DESC.relative_to(ROOT)))
    if paths:
        commit('Restore stable channel after incomplete 2.0.22 verification; remove transfer descriptor', paths)
    print('Incomplete publication rolled back; old installers and all history retained', flush=True)


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in {'prepare', 'finish', 'rollback'}:
        raise ValueError('Expected prepare, finish, or rollback')
    globals()[sys.argv[1]]()
