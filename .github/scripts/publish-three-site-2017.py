"""Scoped public publication. No private source or business file is copied.
The temporary transfer contains exactly the installer and three public reports.
Git history and all unrelated programs are preserved. No force push.
"""
from pathlib import Path
import hashlib,io,json,os,shutil,struct,subprocess,sys,time,urllib.request,urllib.parse,zipfile
ROOT=Path.cwd();CHANNEL=ROOT/'updates/three-site-replenishment'
DESCRIPTOR=ROOT/'.github/three-site-2017-transfer.json'
INCOMING=ROOT/'incoming-three-site-2017';INCOMING.mkdir(exist_ok=True)
FIXTURES=ROOT/'retired-fixtures';FIXTURES.mkdir(exist_ok=True)
VER='2.0.17';TAG='three-site-v2.0.17';REPO='yangxiaodegit/family-menu'
EXE='Three_Site_Replenishment_Setup_2.0.17.exe'
EXPECTED='4d9e87cb205f76b62cbda0e982bf36d14480a671258adec128f7ac0235f8844a'
SIZE=16243712
ALLOWED={EXE,'latest.json','PUBLIC_RELEASE_VERIFICATION.json','Three_Site_Replenishment_SHA256_2.0.17.txt'}

def gh(*args,ok=True):
 r=subprocess.run(['gh',*args],cwd=ROOT,capture_output=True)
 if ok and r.returncode:raise RuntimeError('GitHub publication command failed: '+r.stderr.decode('utf-8',errors='replace')[:1000])
 return r

def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def sha(b):return hashlib.sha256(b).hexdigest()
def identity():
 m=json.loads((INCOMING/'latest.json').read_text(encoding='utf-8'))
 b=(INCOMING/EXE).read_bytes()
 if (m['product'],m['version'],m['platform'],m['arch'],m['setup'],m['size'],m['sha256'])!=('ThreeSiteReplenishment',VER,'windows','amd64',EXE,SIZE,EXPECTED):raise ValueError('Manifest identity mismatch')
 if len(b)!=SIZE or sha(b)!=EXPECTED:raise ValueError('Installer identity mismatch')
 pe=struct.unpack_from('<I',b,0x3c)[0]
 if b[:2]!=b'MZ' or b[pe:pe+4]!=b'PE\0\0' or struct.unpack_from('<H',b,pe+4)[0]!=0x8664 or struct.unpack_from('<H',b,pe+24+68)[0]!=2:raise ValueError('Not Windows amd64 GUI PE')
 r=json.loads((INCOMING/'PUBLIC_RELEASE_VERIFICATION.json').read_text(encoding='utf-8'))
 if r['version']!=VER or r['native_verification']!='passed' or r['installer_sha256']!=EXPECTED or r['independent_rebuild']!='identical' or not all(x['pass'] for x in r['native_install_checks']):raise ValueError('Missing native verification')
 return m,r

def commit_push(message,paths):
 git('config','user.name','github-actions[bot]');git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
 git('add','-A','--',*paths)
 if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode:
  git('commit','-m',message+' [skip ci]');git('push','origin','HEAD:main')
 return git('rev-parse','HEAD').decode().strip()

def prepare():
 d=json.loads(DESCRIPTOR.read_text(encoding='utf-8'));u=urllib.parse.urlparse(d['url'])
 if d['version']!=VER or d['artifact_sha256']!='4dcfd7c7109dcba27765a7e511634be8419d005de5d52bfac0c4dfae5315a6a5':raise ValueError('Unexpected public-ready artifact')
 if u.scheme!='https' or not u.hostname or not u.hostname.endswith('.oaiusercontent.com') or u.username or u.password:raise ValueError('Invalid binary-only transfer URL')
 # This is a one-off download of approved public assets, never an executable
 # script from an external service. Size/hash and exact ZIP member list enforced.
 req=urllib.request.Request(d['url'],headers={'User-Agent':'ThreeSitePublication/2.0.17'})
 with urllib.request.urlopen(req,timeout=60) as r:raw=r.read(30*1024*1024+1)
 if len(raw)>30*1024*1024 or sha(raw)!=d['artifact_sha256']:raise ValueError('Transfer integrity failed')
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  names=z.namelist()
  if len(names)!=len(ALLOWED) or set(names)!=ALLOWED or any(i.file_size>30*1024*1024 for i in z.infolist()) or z.testzip():raise ValueError('Unexpected public file set')
  for n in names:(INCOMING/n).write_bytes(z.read(n))
 m,r=identity()
 for ver in ['2.0.14','2.0.15']:
  n='Three_Site_Replenishment_Setup_'+ver+'.exe';p=CHANNEL/n
  if p.exists():shutil.copy2(p,FIXTURES/n)
  else:raise ValueError('Expected controlled old-version fixture absent: '+n)
 # Create a draft release first; the updater channel is the atomic commit.
 found=gh('release','view',TAG,'--repo',REPO,'--json','isDraft',ok=False)
 if found.returncode:
  gh('release','create',TAG,'--repo',REPO,'--draft','--latest=false','--title','三站补货中心 2.0.17 · 稳定业务在线发行','--notes','以已验证2.0.16业务为基线，保留韩国批次合并和运营SKU零库存检测。仅补齐在线更新、校验、备份与保留资料的安装流程。未签名，请保持安全软件开启。2.0.14和2.0.15已撤回。')
 elif not json.loads(found.stdout)['isDraft']:raise ValueError('Existing published version must not be overwritten')
 gh('release','upload',TAG,'--repo',REPO,*[str(INCOMING/n) for n in sorted(ALLOWED)],'--clobber')
 CHANNEL.mkdir(parents=True,exist_ok=True)
 for n in ALLOWED:shutil.copy2(INCOMING/n,CHANNEL/n)
 rev={'product':'ThreeSiteReplenishment','revoked':['2.0.14','2.0.15'],'replacement':VER,'reason':'用户反馈旧版运行异常；采用稳定2.0.16业务及独立校验的在线安装适配。','history_policy':'保留源码历史与业务记录，不删除任何用户数据。'}
 (CHANNEL/'revoked-versions.json').write_text(json.dumps(rev,ensure_ascii=False,indent=2),encoding='utf-8')
 commit=commit_push('Set online channel to verified stable 2.0.17',[str(CHANNEL.relative_to(ROOT))])
 (ROOT/'release-verification-2017').mkdir(exist_ok=True)
 (ROOT/'release-verification-2017/channel-commit.json').write_text(json.dumps({'commit':commit,'source_commit':r['source_commit'],'sha256':EXPECTED,'version':VER}),encoding='utf-8')
 print('Published updater channel:',VER,EXPECTED,flush=True)

def finish():
 report=ROOT/'release-verification-2017/windows-official-update-2017.json'
 r=json.loads(report.read_text(encoding='utf-8'))
 if r['version']!=VER or not r['all_passed'] or r['sha256']!=EXPECTED or not all(x['passed'] for x in r['checks']):raise ValueError('Official forward-upgrade tests incomplete')
 if sha((CHANNEL/EXE).read_bytes())!=EXPECTED:raise ValueError('Channel was modified during verification')
 gh('release','upload',TAG,'--repo',REPO,str(report),'--clobber')
 gh('release','edit',TAG,'--repo',REPO,'--draft=false','--latest=false')
 removed=[]
 for ver in ['2.0.14','2.0.15']:
  p=CHANNEL/('Three_Site_Replenishment_Setup_'+ver+'.exe')
  if p.exists():p.unlink();removed.append(p.name)
  oldtag='three-site-v'+ver
  found=gh('release','view',oldtag,'--repo',REPO,'--json','tagName',ok=False)
  if not found.returncode:
   if json.loads(found.stdout)['tagName']!=oldtag:raise ValueError('Unexpected release identity')
   gh('release','delete',oldtag,'--repo',REPO,'--yes')
  found=gh('api','repos/'+REPO+'/git/ref/tags/'+oldtag,ok=False)
  if not found.returncode:gh('api','--method','DELETE','repos/'+REPO+'/git/refs/tags/'+oldtag)
 oldwf=ROOT/'.github/workflows/publish-three-site-2.0.15.yml'
 if oldwf.exists():oldwf.unlink()
 # The old verify script only accepted .15; retire it with its workflow.
 oldscript=ROOT/'.github/scripts/verify-three-site-release.py'
 if oldscript.exists():oldscript.unlink()
 (CHANNEL/'windows-official-update-2017.json').write_bytes(report.read_bytes())
 (CHANNEL/'README.md').write_text('''# 三站补货中心在线更新\n\n当前正式在线版本：**2.0.17**。这是已验证2.0.16业务的在线兼容发行版，不重新引入已撤回的2.0.14/2.0.15批次代码。\n\n[官方安装包](https://github.com/yangxiaodegit/family-menu/releases/download/three-site-v2.0.17/Three_Site_Replenishment_Setup_2.0.17.exe) · [发行页](https://github.com/yangxiaodegit/family-menu/releases/tag/three-site-v2.0.17)\n\n2.0.14和2.0.15公开安装包、发行页及旧专用发布任务已撤回；Git历史没有清空。其他程序的更新目录未更改。旧在线版本使用程序内“检查更新”；原2.0.16离线版请先安装一次2.0.17，之后即可使用在线更新。\n\n已验证真实Windows安装程序、2.0.16覆盖安装、2.0.14/2.0.15原在线流程下载升级、匿名GitHub完整下载与SHA256一致。验证使用隔离合成数据，不是用户本机或平台后台验收。安装包未签名，请保留安全防护。\n\n本目录只有发行文件与公开验证信息，不包含店铺源码、账号密钥、账本、库存或发票。\n''',encoding='utf-8')
 if DESCRIPTOR.exists():DESCRIPTOR.unlink()
 paths=['updates/three-site-replenishment','.github/workflows/publish-three-site-2.0.15.yml','.github/scripts/verify-three-site-release.py','.github/three-site-2017-transfer.json']
 commit=commit_push('Withdraw broken .14/.15 installers and keep verified .17 channel',paths)
 audit={'version':VER,'channel_commit':commit,'withdrawn_installers':removed,'withdrawn_release_tags':['three-site-v2.0.14','three-site-v2.0.15'],'old_publication_workflow_removed':True,'source_history_preserved':True,'other_products_untouched':True,'sha256':EXPECTED}
 (ROOT/'release-verification-2017/publication-result.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
 print('Public publication and retirement completed:',commit,flush=True)

if __name__=='__main__':
 if len(sys.argv)!=2 or sys.argv[1] not in {'prepare','finish'}:raise ValueError('Expected publication phase')
 globals()[sys.argv[1]]()
