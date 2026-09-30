"""Publish approved installer only. No private source, business files, or history deletion."""
from pathlib import Path
import os,sys,json,hashlib,io,zipfile,urllib.request,urllib.parse,subprocess,shutil,struct
ROOT=Path.cwd();CH=ROOT/'updates/three-site-replenishment';OUT=ROOT/'release-verification-2019';OUT.mkdir(exist_ok=True)
DESC=ROOT/'.github/three-site-2019-transfer.json';IN=ROOT/'incoming-three-site-2019';IN.mkdir(exist_ok=True)
VER='2.0.19';TAG='three-site-v'+VER;REPO='yangxiaodegit/family-menu';EXE='Three_Site_Replenishment_Setup_'+VER+'.exe'
ALLOWED={EXE,'latest.json','PUBLIC_RELEASE_VERIFICATION.json','Three_Site_Replenishment_SHA256_'+VER+'.txt'}
OLD_SHA='faa51f91f9f8ccdf55df9db8a784cf66997593c87b516e1398f02079f09d23e3'
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT)
def gh(*a,allow_missing=False):
 r=subprocess.run(['gh',*a],cwd=ROOT,capture_output=True)
 if r.returncode and not allow_missing:raise RuntimeError(r.stderr.decode(errors='replace')[:1200])
 return r

def commit(message,paths):
 git('config','user.name','github-actions[bot]');git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
 git('add','-A','--',*paths)
 if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode:
  git('commit','-m',message+' [skip ci]');git('push','origin','HEAD:main')
 return git('rev-parse','HEAD').decode().strip()

def prepare():
 d=json.loads(DESC.read_text(encoding='utf-8'));u=urllib.parse.urlparse(d['url'])
 if d['version']!=VER or u.scheme!='https' or not u.hostname or not u.hostname.endswith('.oaiusercontent.com') or u.username or u.password:raise ValueError('Invalid approved public-only transfer')
 with urllib.request.urlopen(urllib.request.Request(d['url'],headers={'User-Agent':'ThreeSitePublication/2.0.19'}),timeout=60) as r:raw=r.read(30*1024*1024+1)
 if len(raw)>30*1024*1024 or sha(raw)!=d['artifact_sha256']:raise ValueError('Public archive integrity failed')
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  if len(z.namelist())!=4 or set(z.namelist())!=ALLOWED or any(x.file_size>30*1024*1024 for x in z.infolist()) or z.testzip():raise ValueError('Public allowlist failed')
  for n in ALLOWED:(IN/n).write_bytes(z.read(n))
 m=json.loads((IN/'latest.json').read_text(encoding='utf-8'));v=json.loads((IN/'PUBLIC_RELEASE_VERIFICATION.json').read_text(encoding='utf-8'));b=(IN/EXE).read_bytes()
 if (m['product'],m['version'],m['platform'],m['arch'],m['setup'])!=('ThreeSiteReplenishment',VER,'windows','amd64',EXE):raise ValueError('Manifest product mismatch')
 if sha(b)!=d['installer_sha256'] or m['sha256']!=d['installer_sha256'] or len(b)!=d['installer_size'] or m['size']!=len(b):raise ValueError('Wrong approved binary')
 if v['version']!=VER or not v['all_passed'] or v['source_commit']!=d['source_commit'] or v['installer_sha256']!=sha(b) or v['independent_rebuild']!='identical' or not v['native_edge_checks'] or not all(c['passed'] for c in v['native_edge_checks']):raise ValueError('Native verification incomplete')
 pe=struct.unpack_from('<I',b,0x3c)[0]
 if b[:2]!=b'MZ' or b[pe:pe+4]!=b'PE\0\0' or struct.unpack_from('<H',b,pe+4)[0]!=0x8664 or struct.unpack_from('<H',b,pe+24+68)[0]!=2:raise ValueError('Wrong Windows GUI format')
 old=json.loads((CH/'latest.json').read_text(encoding='utf-8'))
 if old['version']!='2.0.18' or old['sha256']!=OLD_SHA:raise ValueError('Stable channel changed; do not overwrite')
 old_exe=CH/old['setup']
 if sha(old_exe.read_bytes())!=OLD_SHA:raise ValueError('Stable installer mismatch')
 fixture=ROOT/'retired-fixtures';fixture.mkdir(exist_ok=True);shutil.copy2(old_exe,fixture/old_exe.name)
 (OUT/'previous-latest.json').write_bytes((CH/'latest.json').read_bytes())
 found=gh('release','view',TAG,'--repo',REPO,'--json','isDraft',allow_missing=True)
 if found.returncode:gh('release','create',TAG,'--repo',REPO,'--draft','--latest=false','--title','三站补货中心 2.0.19 · 零库存顶部指标','--notes',m['notes']+'\n\n安装包未签名，请保留安全防护。验证使用隔离合成资料，不是用户本机或真实平台验收。')
 elif not json.loads(found.stdout)['isDraft']:raise ValueError('Published version cannot be overwritten')
 gh('release','upload',TAG,'--repo',REPO,*[str(IN/n) for n in sorted(ALLOWED)],'--clobber')
 for n in ALLOWED:shutil.copy2(IN/n,CH/n)
 c=commit('Offer verified total-zero KPI 2.0.19 online',[str((CH/n).relative_to(ROOT)) for n in sorted(ALLOWED)])
 (OUT/'channel-commit.json').write_text(json.dumps({'commit':c,'version':VER,'sha256':sha(b),'source_commit':v['source_commit']}),encoding='utf-8')
 print('Channel prepared',c,flush=True)

def finish():
 report=OUT/'windows-official-update-2019.json';r=json.loads(report.read_text(encoding='utf-8'));m=json.loads((CH/'latest.json').read_text(encoding='utf-8'))
 if r['version']!=VER or not r['all_passed'] or r['sha256']!=m['sha256'] or not all(x['passed'] for x in r['checks']):raise ValueError('Official upgrade verification failed')
 gh('release','upload',TAG,'--repo',REPO,str(report),'--clobber');gh('release','edit',TAG,'--repo',REPO,'--draft=false','--latest=false')
 (CH/report.name).write_bytes(report.read_bytes())
 (CH/'README.md').write_text('# 三站补货中心在线更新\n\n当前正式版本：**2.0.19**。韩国零库存＝计算总库存为0且无在途，计算总库存沿用可售＋待入库＋有效已报送未下单。韩国补货计划和总控台顶部常驻明显指标，点击查看明细；未知库存不按0。\n\n原2.0.18可在程序内检查更新。保留稳定2.0.18发行文件，不删除源码历史或任何业务资料。其他程序更新频道不受影响。\n\n原生Windows/Edge及完整官方匿名下载、2.0.18原更新器在线升级验证使用隔离合成资料，不是用户本机验收。安装包未签名，请保留安全软件。\n',encoding='utf-8')
 paths=['updates/three-site-replenishment/'+report.name,'updates/three-site-replenishment/README.md']
 revoked=CH/'revoked-versions.json'
 if revoked.exists():
  v=json.loads(revoked.read_text(encoding='utf-8'));v['replacement']=VER;revoked.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8');paths.append(str(revoked.relative_to(ROOT)))
 if DESC.exists():DESC.unlink();paths.append(str(DESC.relative_to(ROOT)))
 c=commit('Finish 2.0.19 verified online update; retain prior stable release',paths)
 (OUT/'publication-result.json').write_text(json.dumps({'version':VER,'commit':c,'all_passed':True,'sha256':m['sha256'],'previous_stable_retained':True,'other_channels_unchanged':True},indent=2),encoding='utf-8')

def rollback():
 p=OUT/'previous-latest.json'
 if not p.exists():return
 current=json.loads((CH/'latest.json').read_text(encoding='utf-8'))
 if current.get('version')!=VER:return
 # Never roll back a successfully published and verified release.
 if (OUT/'publication-result.json').exists():return
 (CH/'latest.json').write_bytes(p.read_bytes());commit('Restore stable channel after incomplete 2.0.19 verification',['updates/three-site-replenishment/latest.json'])
 print('Stable channel restored; draft remains unpromoted',flush=True)
if __name__=='__main__':
 if len(sys.argv)!=2 or sys.argv[1] not in {'prepare','finish','rollback'}:raise ValueError('Expected phase')
 globals()[sys.argv[1]]()
