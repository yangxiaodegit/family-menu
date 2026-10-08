"""Publish the approved four-file installer archive; retain source/history and old installers."""
from pathlib import Path
import datetime
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
OUT = ROOT / 'release-verification-2024'
DESC = ROOT / '.github/three-site-2024-transfer.json'
IN = ROOT / 'incoming-three-site-2024'
VER = '2.0.24'
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
    '2.0.22': '7bb12da35354ab620da9dc014bbe70832d3ff18e9033f2c577fa564429ae6a28',
    '2.0.23': '2674bb444778d79915e5be844c3217f061c7ecbe2a9e8ad6930c035adcc7ed10',
}
LIMIT = 30 * 1024 * 1024
SOURCE = '8c51bafdf98d5d769a574d903dc0d3d1a68f9a45'
TREE = '687d6146e74f188c12f2ab5c2c85da05dd4d5122'
RUN = '37557744949'
EXPECTED_SHA = '1670c013f1aad4ae9686c9357694476d0ff6c1b517132dbbf7228027883addde'
EXPECTED_SIZE = 16343040
CANDIDATE_ALLOWED = {EXE, 'CANDIDATE_MANIFEST.json', 'CANDIDATE_VERIFICATION.json', CHECKSUM}
NOTES = '三站长期参数及商品级别、新品、库存规则可在程序维护；旧表首次兼容迁入，已保存参数和显式新品true/false保留。POP打开设置页即迁入商品目录。韩国货值与装箱配方内置，界面统一，检查框与批量选择优化。升级保留原配置和资料。'



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
    expected = {'version', 'transport', 'artifact_sha256', 'installer_sha256', 'installer_size', 'source_commit', 'source_tree', 'workflow_run', 'parts'}
    if set(desc) != expected or desc['transport'] != 'public-binary-chunks' or desc['version'] != VER:
        raise ValueError('Only credential-free public binary parts and a four-file stage are accepted')
    for key in ('artifact_sha256', 'installer_sha256'):
        if not re.fullmatch('[a-f0-9]{64}', desc[key]):
            raise ValueError('Invalid digest: ' + key)
    if desc['source_commit'] != SOURCE or desc['source_tree'] != TREE or str(desc['workflow_run']) != RUN:
        raise ValueError('Unexpected validated source identity')
    if type(desc['installer_size']) is not int or not 0 < desc['installer_size'] <= LIMIT:
        raise ValueError('Invalid approved installer size')
    parts = desc['parts']
    if (not isinstance(parts, list) or not 0 < len(parts) <= 512
            or any(set(p) != {'name', 'size', 'sha256'}
                   or p['name'] != 'part'+str(i).zfill(4)+'.bin'
                   or type(p['size']) is not int or not 0 < p['size'] <= 73728
                   or not re.fullmatch('[a-f0-9]{64}', p['sha256']) for i,p in enumerate(parts))
            or sum(p['size'] for p in parts) != desc['installer_size']):
        raise ValueError('Invalid approved public binary parts')

def collect_public_parts(folder, parts):
    if set(p.name for p in folder.iterdir()) != {p['name'] for p in parts}:
        raise ValueError('Unexpected or missing public binary part')
    data = bytearray()
    for p in parts:
        raw = (folder/p['name']).read_bytes()
        if len(raw) != p['size'] or sha(raw) != p['sha256']:
            raise ValueError('Public binary part integrity failed')
        data.extend(raw)
        if len(data) > LIMIT:
            raise ValueError('Public binary size limit exceeded')
    return bytes(data)


def public_archive(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, raw in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw, compresslevel=6)
    return buffer.getvalue()


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
    rebuild = proof.get('independent_rebuild_files')
    if (proof.get('source_tree') != TREE or proof.get('go_top_level') != {'pass': 641, 'skip': 126, 'fail': 0}
            or proof.get('javascript') != {'pass': 120, 'fail': 0, 'skipped': 0}
            or proof.get('browser_checks') != 40 or len(checks) != 27
            or not isinstance(rebuild, list) or len(rebuild) != 7
            or len({c.get('file') for c in rebuild}) != 7
            or not all(isinstance(c.get('sha256'), str) and re.fullmatch('[a-f0-9]{64}', c['sha256'])
                       and c['sha256'] == c.get('independent_sha256') for c in rebuild)
            or next((c['sha256'] for c in rebuild if c.get('file') == EXE), None) != sha(binary)):
        raise ValueError('Exact native proof incomplete')
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
    if desc['installer_sha256'] != EXPECTED_SHA or desc['installer_size'] != EXPECTED_SIZE:
        raise ValueError('Unexpected approved installer')
    binary = collect_public_parts(IN/'installer-chunks', desc['parts'])
    if len(binary) != EXPECTED_SIZE or sha(binary) != EXPECTED_SHA:
        raise ValueError('Public reassembled installer differs from exact validated CI')
    (IN/EXE).write_bytes(binary)
    if set(p.name for p in IN.iterdir()) != ALLOWED | {'installer-chunks'}:
        raise ValueError('Unexpected public staged file')
    raw = public_archive({name: (IN/name).read_bytes() for name in ALLOWED})
    files, manifest, proof = validate_archive(raw, desc)
    old = json.loads((CH / 'latest.json').read_text(encoding='utf-8'))
    if old['version'] != '2.0.23' or old['sha256'] != PRIOR['2.0.23']:
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
           '--title', '三站补货中心 2.0.24 · 三站参数内置与新品保留', '--notes', manifest['notes'] +
           '\n\n安装包未签名，请保留安全防护。验证使用隔离合成资料，不是用户本机或真实平台验收。')
    elif not json.loads(found.stdout)['isDraft']:
        raise ValueError('Published version cannot be overwritten')
    gh('release', 'upload', TAG, '--repo', REPO, *[str(IN/n) for n in sorted(ALLOWED)], '--clobber')
    for name in ALLOWED:
        shutil.copy2(IN/name, CH/name)
    revision = commit('Offer exact verified three-site program settings 2.0.24 online',
                      [str((CH/n).relative_to(ROOT)) for n in sorted(ALLOWED)])
    (OUT/'channel-commit.json').write_text(json.dumps({
        'commit': revision, 'version': VER, 'sha256': manifest['sha256'],
        'source_commit': proof['source_commit']}), encoding='utf-8')
    print('Channel prepared', revision, flush=True)


def finish():
    report = OUT / 'windows-official-update-2024.json'
    result = json.loads(report.read_text(encoding='utf-8'))
    manifest = json.loads((CH/'latest.json').read_text(encoding='utf-8'))
    if (result['version'] != VER or result['all_passed'] is not True
            or result['sha256'] != manifest['sha256'] or result['size'] != manifest['size']
            or result.get('anonymous_download') is not True or result.get('cross_volume') is not True
            or not result['checks']
            or not all(x['passed'] is True for x in result['checks'])
            or result['upgrade_paths'] != [version+' -> '+VER for version in PRIOR]):
        raise ValueError('Official upgrade verification failed')
    gh('release', 'upload', TAG, '--repo', REPO, str(report), '--clobber')
    gh('release', 'edit', TAG, '--repo', REPO, '--draft=false', '--latest=false')
    (CH/report.name).write_bytes(report.read_bytes())
    (CH/'README.md').write_text(
        '# 三站补货中心在线更新\n\n当前正式版本：**2.0.24**。'+NOTES+
        '\n\n2.0.18至2.0.23原更新器匿名下载、安装和资料保留验证，及23到24真实原生窗口迁移验收均使用隔离Windows合成资料。历史安装包、源码与其他应用频道保留。另一台电脑原新品状态的历史原因未实机判定。\n', encoding='utf-8')
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
    revision = commit('Finish 2.0.24 verified online update; retain prior release history', paths)
    (OUT/'publication-result.json').write_text(json.dumps({
        'version': VER, 'commit': revision, 'all_passed': True, 'sha256': manifest['sha256'],
        'previous_stable_retained': list(PRIOR), 'other_channels_unchanged': True}, indent=2), encoding='utf-8')


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
        commit('Restore stable channel after incomplete 2.0.24 verification; remove transfer descriptor', paths)
    print('Incomplete publication rolled back; old installers and all history retained', flush=True)


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in {'prepare', 'finish', 'rollback'}:
        raise ValueError('Expected prepare, finish, or rollback')
    globals()[sys.argv[1]]()


