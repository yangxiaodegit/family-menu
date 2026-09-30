"""Public-channel verification on an isolated Windows Actions account.
Only synthetic sentinels are used. No local user's business files are accessed.
The old installers remain in runner TEMP only, never republished.
"""
from pathlib import Path
import hashlib,http.cookiejar,json,os,sqlite3,subprocess,time,urllib.request,urllib.error
ROOT=Path.cwd();CHANNEL=ROOT/'updates/three-site-replenishment'
OUT=ROOT/'release-verification-2017';OUT.mkdir(exist_ok=True)
API='https://api.github.com/repos/yangxiaodegit/family-menu/contents/updates/three-site-replenishment/'
VERSION='2.0.17';SETUP='Three_Site_Replenishment_Setup_2.0.17.exe'
checks=[];procs=[];active=None

def check(name,ok):
 checks.append({'name':name,'passed':bool(ok)});print(('PASS ' if ok else 'FAIL ')+name,flush=True)
 if not ok:raise AssertionError(name)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def wait(fn,seconds=60):
 end=time.monotonic()+seconds;last=None
 while time.monotonic()<end:
  try:
   x=fn()
   if x:return x
  except (OSError,ValueError,urllib.error.URLError) as e:last=type(e).__name__
  time.sleep(.3)
 raise TimeoutError(last or 'condition timeout')
def download(url,p,max_size,expected=None):
 r=subprocess.run([str(Path(os.environ['SystemRoot'])/'System32/curl.exe'),'-q','--ipv4','--http1.1','--fail','--silent','--show-error','--proto','=https','--max-redirs','0','--connect-timeout','15','--max-time','180','--max-filesize',str(max_size),'-H','Accept: application/vnd.github.raw+json','-H','User-Agent: ThreeSiteReleaseVerification/2.0.17','-o',str(p),url],capture_output=True,timeout=190)
 if r.returncode:raise RuntimeError('anonymous official download failed, curl='+str(r.returncode))
 if expected and digest(p)!=expected:raise ValueError('anonymous official download hash mismatch')
 return p

def request(conn,path,body=None):
 rt,op=conn;u=rt['url'];h={'Origin':u.rstrip('/'),'Content-Type':'application/json','X-Replen-CSRF':rt['secret'],'X-Replen-Version':rt['version'],'X-Replen-Protocol':'2'}
 q=urllib.request.Request(u+'api/'+path,data=None if body is None else json.dumps(body).encode(),headers=h)
 with op.open(q,timeout=10) as r:return json.load(r)
def connect(state,version):
 try:
  rt=json.loads((state/'runtime.json').read_text(encoding='utf-8'))
  if rt.get('version')!=version:return None
  op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
  conn=(rt,op);request(conn,'bootstrap',{'secret':rt['secret']});return conn
 except (OSError,ValueError,urllib.error.URLError):return None

def stop(conn):request(conn,'shutdown',{'confirm':True})
def seed(state,local):
 c=sqlite3.connect(state/'workspace.db')
 c.execute("INSERT OR REPLACE INTO objects(kind,id,site,updated,body) VALUES('publication-proof','persist','korea','2026-09-30','{\"label\":\"升级保留校验\",\"units\":17}')");c.commit();c.close()
 files=[]
 for root in [state,*[local/n for n in ['CoupangKoreaWorkbench','JDSelfOperatedWorkbench','JDPOPWorkbench']]]:
  root.mkdir(parents=True,exist_ok=True);p=root/'保留业务资料_测试.txt';p.write_text('仅CI合成保留校验，不是真实账本或库存',encoding='utf-8');files.append(p)
 return {str(p):digest(p) for p in files}
def proof(state):
 c=sqlite3.connect('file:'+str(state/'workspace.db')+'?mode=ro',uri=True)
 try:return c.execute("select id,body from objects where kind='publication-proof'").fetchall()
 finally:c.close()
def spawn(args,env):
 p=subprocess.Popen(list(map(str,args)),env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);procs.append(p);return p

def upgrade(old,manifest):
 global active
 home=Path(os.environ['RUNNER_TEMP'])/('three-site-forward-'+old);home.mkdir(exist_ok=True)
 local=home/'Local';roaming=home/'Roaming';state=home/'自定义工作区 保留资料'
 for p in [local,roaming,state]:p.mkdir(exist_ok=True)
 env=dict(os.environ,LOCALAPPDATA=str(local),APPDATA=str(roaming))
 old_setup=ROOT/'retired-fixtures'/('Three_Site_Replenishment_Setup_'+old+'.exe')
 check(old+' old fixture is available for controlled upgrade',old_setup.is_file())
 p=spawn([old_setup,'--online-update','--state-dir',state,'--no-launch'],env);p.wait(90)
 check(old+' initial isolated installation completed',p.returncode==0)
 target=local/'Programs/ThreeSiteReplenishment'
 p=spawn([target/'ReplenishmentSuite.exe','--no-browser'],env)
 active=wait(lambda:connect(state,old));check(old+' actual old host started',active[0]['version']==old)
 request(active,'shutdown',{'confirm':True});p.wait(30);active=None
 hashes=seed(state,local);before=proof(state)
 p=spawn([target/'ReplenishmentSuite.exe','--no-browser'],env)
 active=wait(lambda:connect(state,old))
 request(active,'update/check',{})
 def checked():
  s=request(active,'update/status')
  if s.get('stage')=='error':raise AssertionError(old+' updater check failed: '+s.get('error',''))
  return s if not s['running'] else None
 s=wait(checked,100)
 check(old+' real updater offers only 2.0.17',s.get('available') and s['manifest']['version']==VERSION and s['manifest']['sha256']==manifest['sha256'])
 request(active,'update/install',{'version':VERSION,'confirm':True})
 oldconn=active;stages=[];end=time.monotonic()+200
 while time.monotonic()<end:
  conn=connect(state,VERSION)
  if conn:active=conn;break
  try:
   s=request(oldconn,'update/status');stage=s.get('stage')
   if stage not in stages:stages.append(stage)
   if stage=='error':raise AssertionError(old+' actual update failed: '+s.get('error',''))
  except (urllib.error.URLError,OSError,ValueError):pass
  time.sleep(.3)
 else:raise TimeoutError(old+' new host did not open')
 check(old+' real updater downloaded and installed new version',active[0]['version']==VERSION)
 check(old+' target manifest matches 2.0.17',json.loads((target/'manifest.json').read_text())['version']==VERSION)
 check(old+' downloaded installer hash is identical',digest(state/'updates'/SETUP)==manifest['sha256'])
 check(old+' custom database records preserved',proof(state)==before)
 check(old+' all station data sentinel bytes preserved',all(digest(Path(n))==h for n,h in hashes.items()))
 check(old+' custom workspace launch registration preserved',Path(json.loads((target/'online-install.json').read_text())['state_dir'])==state)
 st=request(active,'update/status');check(old+' new program retains online updater',st['current']==VERSION)
 request(active,'update/check',{});s=wait(checked,100)
 check(old+' upgraded program reports current with no broken downgrade',s.get('stage')=='current' and s['manifest']['version']==VERSION and not s['available'])
 for path,marker in [('korea-operations.js',b'korea_merge_commit'),('korea-operations.js',b'korea_zero_stock_export')]:
  with active[1].open(active[0]['url']+path,timeout=10) as r:b=r.read()
  check(old+' new host serves '+marker.decode(),marker in b)
 stop(active);active=None;wait(lambda:not (state/'runtime.json').exists());p.wait(10)
 check(old+' safe exit after successful forward upgrade',p.returncode==0)
 return stages

def main():
 m=json.loads((CHANNEL/'latest.json').read_text(encoding='utf-8'))
 check('channel has exact approved identity',(m['product'],m['version'],m['platform'],m['arch'],m['setup'])==('ThreeSiteReplenishment',VERSION,'windows','amd64',SETUP))
 check('channel installer has exact size and SHA256',(CHANNEL/SETUP).stat().st_size==m['size'] and digest(CHANNEL/SETUP)==m['sha256'])
 latest=OUT/'anonymous-latest.json'
 def visible():
  download(API+'latest.json?ref=main',latest,131072)
  return json.loads(latest.read_text(encoding='utf-8')).get('version')==VERSION
 wait(visible,120)
 remote=json.loads(latest.read_text(encoding='utf-8'));check('anonymous official manifest matches',remote==m)
 exe=OUT/SETUP;download(API+SETUP+'?ref=main',exe,m['size'],m['sha256']);check('anonymous official full executable downloaded',exe.stat().st_size==m['size'])
 stages={}
 for old in ['2.0.14','2.0.15']:stages[old]=upgrade(old,m)
 r={'version':VERSION,'all_passed':True,'size':m['size'],'sha256':m['sha256'],'workflow_run':os.environ.get('GITHUB_RUN_ID'),'native_os':'Windows Server 2022','anonymous_download':True,'upgrade_paths':['2.0.14 -> 2.0.17','2.0.15 -> 2.0.17'],'observed_stages':stages,'checks':checks,'scope':'Real installed Windows programs and original updater download/install flow; synthetic data only. No user computer or platform final upload tested.'}
 (OUT/'windows-official-update-2017.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');exe.unlink()
try:main()
finally:
 if active:
  try:stop(active)
  except Exception:pass
 for p in procs:
  if p.poll() is None:p.terminate()
 (OUT/'checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
