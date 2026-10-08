"""Public-channel native Windows verification with isolated synthetic data only."""
from pathlib import Path
import hashlib,http.cookiejar,json,os,sqlite3,subprocess,time,urllib.request,urllib.error,zipfile,uuid
ROOT=Path.cwd();CHANNEL=ROOT/'updates/three-site-replenishment';OUT=ROOT/'release-verification-2024';OUT.mkdir(exist_ok=True)
API='https://api.github.com/repos/yangxiaodegit/family-menu/contents/updates/three-site-replenishment/'
VERSION='2.0.24';SETUP='Three_Site_Replenishment_Setup_2.0.24.exe'
PRIOR={'2.0.18':'faa51f91f9f8ccdf55df9db8a784cf66997593c87b516e1398f02079f09d23e3','2.0.19':'9cbd7eaaecd67a7be3ef7c55a3700cb551beaa6cbfd7ef333e805615fefce1ba','2.0.20':'286e48519125db5b1ec54a429f59b24e44d7bc01549a43d28c84e793f288c3cc','2.0.21':'eba574be88e6a9f2f824de1e74235137ca06120b04abe3f0d82ccd7d31847204','2.0.22':'7bb12da35354ab620da9dc014bbe70832d3ff18e9033f2c577fa564429ae6a28','2.0.23':'2674bb444778d79915e5be844c3217f061c7ecbe2a9e8ad6930c035adcc7ed10'}
checks=[];procs=[];active=None;check_context=""

def check(name,ok):
 name=check_context+name
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
 args=[str(Path(os.environ['SystemRoot'])/'System32/curl.exe'),'-q','--ipv4','--http1.1','--fail','--silent','--show-error','--proto','=https','--max-redirs','0','--connect-timeout','15','--max-time','180','--max-filesize',str(max_size),'-H','Accept: application/vnd.github.raw+json','-H','User-Agent: ThreeSiteReleaseVerification/2.0.24','-o',str(p),url]
 r=subprocess.run(args,capture_output=True,timeout=190)
 if r.returncode:raise RuntimeError('Anonymous GitHub download failed: curl='+str(r.returncode))
 if expected and digest(p)!=expected:raise ValueError('Anonymous download hash mismatch')
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
 c.execute("INSERT OR REPLACE INTO objects(kind,id,site,updated,body) VALUES('publication-proof','persist','korea','2026-09-30','{\"label\":\"升级保留校验\",\"units\":19}')");c.commit();c.close()
 files=[]
 for root in [state,*[local/n for n in ['CoupangKoreaWorkbench','JDSelfOperatedWorkbench','JDPOPWorkbench']]]:
  root.mkdir(parents=True,exist_ok=True);p=root/'保留业务资料_测试.txt';p.write_text('仅CI合成校验，不是真实账本、库存或发票。',encoding='utf-8');files.append(p)
 return {str(p):digest(p) for p in files}
def proof(state):
 c=sqlite3.connect('file:'+str(state/'workspace.db')+'?mode=ro',uri=True)
 try:return c.execute("select id,body from objects where kind='publication-proof'").fetchall()
 finally:c.close()
def spawn(args,env,cwd=None):
 p=subprocess.Popen(list(map(str,args)),env=env,cwd=cwd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);procs.append(p);return p

def seed_configs(conn,local):
 configs={}
 for site,folder,name,id in [('jd','JDSelfOperatedWorkbench','settings.json','100317396031'),('pop','JDPOPWorkbench','workbench_settings.json','12345678'),('korea','CoupangKoreaWorkbench','workbench_settings.json','000101')]:
  cfg=request(conn,'sites/'+site)['settings']
  for key in list(cfg):
   if key.endswith('_dir'):
    isolated=local.parent/'synthetic-data'/site/key;isolated.mkdir(parents=True,exist_ok=True);cfg[key]=str(isolated)
  cfg.setdefault('new_product_overrides',{})[id]=True
  cfg['future_setting']={'integer':18446744073709551615,'nested':{'preserve':True}}
  p=local/folder/name;p.parent.mkdir(parents=True,exist_ok=True)
  p.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
  configs[site]={'path':p,'id':id,'original':cfg}
 return configs
def job(conn,path,body):
 started=request(conn,path,{'key':str(uuid.uuid4()),**body})
 if not started.get('id'):return started
 def done():
  v=request(conn,'jobs/'+started['id'])
  if v['state'] in ('queued','running'):return None
  if v['state']!='done':raise AssertionError('Settings task failed: '+v.get('error',''))
  return v
 return wait(done,90)['result']

def upgrade(manifest,OLD):
 global active,check_context
 check_context=OLD+' -> '+VERSION+': '
 home=Path(os.environ['RUNNER_TEMP'])/('three-site-forward-2024-from-'+OLD);home.mkdir(exist_ok=True)
 local=home/'Local';roaming=home/'Roaming'
 state=Path(os.environ['USERPROFILE'])/('three-site-2024-qa-'+os.environ['GITHUB_RUN_ID']+'-from-'+OLD)/'自定义工作区 保留资料'
 for p in [local,roaming,state]:p.mkdir(parents=True,exist_ok=True)
 env=dict(os.environ,LOCALAPPDATA=str(local),APPDATA=str(roaming))
 target=local/'Programs/ThreeSiteReplenishment'
 check('program and state use different Windows drives',target.drive.lower()!=state.drive.lower())
 old_setup=ROOT/'retired-fixtures'/('Three_Site_Replenishment_Setup_'+OLD+'.exe')
 check('prior stable installer SHA256 verified',old_setup.is_file() and digest(old_setup)==PRIOR[OLD])
 p=spawn([old_setup,'--online-update','--state-dir',state,'--no-launch'],env);p.wait(90)
 check(OLD+' initial isolated installation completed',p.returncode==0)
 p=spawn([target/'ReplenishmentSuite.exe','--no-browser'],env,cwd=target)
 active=wait(lambda:connect(state,OLD));check('actual '+OLD+' host started',active[0]['version']==OLD)
 configs=seed_configs(active,local)
 stop(active);p.wait(30);active=None
 hashes=seed(state,local);before=proof(state)
 p=spawn([target/'ReplenishmentSuite.exe','--no-browser'],env,cwd=target);active=wait(lambda:connect(state,OLD))
 request(active,'update/check',{})
 def checked():
  s=request(active,'update/status')
  if s.get('stage')=='error':raise AssertionError('Updater check failed: '+s.get('error',''))
  return s if not s['running'] else None
 s=wait(checked,100)
 check('real old updater offers 2.0.24 and exact verified hash',s.get('available') and s['manifest']['version']==VERSION and s['manifest']['sha256']==manifest['sha256'])
 body={'version':VERSION,'confirm':True}
 if OLD in ('2.0.22','2.0.23'):body['manifest']=dict(s['manifest'])
 request(active,'update/install',body)
 oldconn=active;stages=[];end=time.monotonic()+200
 while time.monotonic()<end:
  conn=connect(state,VERSION)
  if conn:active=conn;break
  try:
   s=request(oldconn,'update/status');stage=s.get('stage')
   if stage not in stages:stages.append(stage)
   if stage=='error':raise AssertionError('Actual updater failed: '+s.get('error',''))
  except (urllib.error.URLError,OSError,ValueError):pass
  time.sleep(.3)
 else:raise TimeoutError('New host did not start')
 check('real updater downloaded and installed 2.0.24',active[0]['version']==VERSION)
 check('installed manifest matches 2.0.24',json.loads((target/'manifest.json').read_text())['version']==VERSION)
 check('downloaded installer hash is identical',digest(state/'updates'/SETUP)==manifest['sha256'])
 for site,data in configs.items():
  current=json.loads(data['path'].read_text(encoding='utf-8'))
  check(site+' original configuration fields and exact unknown 64-bit value preserved',all(current.get(k)==v for k,v in data['original'].items() if k!='confirmed_blank_stock_as_zero'))
  view=request(active,'sites/'+site)
  check(site+' saved new-product flag preserved',view['settings']['new_product_overrides'][data['id']] is True)
  cfg=view['settings'];cfg['new_product_overrides'][data['id']]=False
  job(active,'sites/'+site+'/settings',{'value':cfg,'base_hash':view['settings_hash'],'confirm':True})
  reread=request(active,'sites/'+site)
  check(site+' explicit saved false survives reread',reread['settings']['new_product_overrides'][data['id']] is False)
  written=json.loads(data['path'].read_text(encoding='utf-8'))
  check(site+' unknown 64-bit field survives new version save',written['future_setting']==data['original']['future_setting'])
 check('custom database records preserved',proof(state)==before)
 check('all station synthetic data bytes preserved',all(digest(Path(n))==h for n,h in hashes.items()))
 check('custom workspace registration preserved',Path(json.loads((target/'online-install.json').read_text())['state_dir'])==state)
 # The existing old updater creates a full transfer ZIP before replacement.
 backups=list(state.rglob('*.zip'))
 check('pre-upgrade ZIP backup exists and has valid CRC',bool(backups) and all(zipfile.ZipFile(z).testzip() is None for z in backups))
 check('new program retains online updater',request(active,'update/status')['current']==VERSION)
 request(active,'update/check',{});s=wait(checked,100)
 check('updated program reports current without downgrade',s.get('stage')=='current' and s['manifest']['version']==VERSION and not s['available'])
 for path,marker in [('korea-operations.js',b'korea_merge_commit'),('korea-operations.js',b'korea_zero_stock_export'),('ui.css',b'zero-stock-card'),('korea-operations-model.js',b'zero-available-metric'),('korea-operations-model.js','可售库存为0'.encode()),('online-update.js',b'checkedRelease'),('online-update.js',b'sameRelease'),('online-update.js',b'manifest:m'),('features.js',b'jdCatalogRows'),('jd-catalog-model.js',b'pageJDCatalog'),('program-products.js',b'programProductsPage'),('program-business.js',b'businessSettingsPanel'),('program-packing.js',b'packingDialog')]:
  with active[1].open(active[0]['url']+path,timeout=10) as r:b=r.read()
  check('new host includes '+marker.decode(),marker in b)
 stop(active);active=None;wait(lambda:not (state/'runtime.json').exists());p.wait(10)
 check('old updater process cleanly exits and new runtime registration is removed',p.returncode==0)
 check_context=''
 return stages

def main():
 m=json.loads((CHANNEL/'latest.json').read_text(encoding='utf-8'))
 check('channel identity is correct',(m['product'],m['version'],m['platform'],m['arch'],m['setup'])==('ThreeSiteReplenishment',VERSION,'windows','amd64',SETUP))
 check('channel installer matches size and SHA256',(CHANNEL/SETUP).stat().st_size==m['size'] and digest(CHANNEL/SETUP)==m['sha256'])
 latest=OUT/'anonymous-latest.json'
 def visible():
  download(API+'latest.json?ref=main',latest,131072)
  return json.loads(latest.read_text(encoding='utf-8')).get('version')==VERSION
 wait(visible,120)
 check('anonymous official manifest matches',json.loads(latest.read_text(encoding='utf-8'))==m)
 exe=OUT/SETUP;download(API+SETUP+'?ref=main',exe,m['size'],m['sha256']);check('complete official executable downloaded without authentication',exe.stat().st_size==m['size'])
 stages={version:upgrade(m,version) for version in PRIOR}
 report={'version':VERSION,'all_passed':True,'size':m['size'],'sha256':m['sha256'],'workflow_run':os.environ.get('GITHUB_RUN_ID'),'native_os':'Windows Server 2022','anonymous_download':True,'cross_volume':True,'upgrade_paths':[version+' -> '+VERSION for version in PRIOR],'observed_stages':stages,'checks':checks,'scope':'Actual Windows programs and original online updater; isolated synthetic data. Not user PC or platform final upload.'}
 print('OFFICIAL_UPDATE_VERIFICATION_JSON '+json.dumps(report,ensure_ascii=False),flush=True)
 (OUT/'windows-official-update-2024.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');exe.unlink()
if __name__=='__main__':
 try:main()
 finally:
  if active:
   try:stop(active)
   except Exception:pass
  for p in procs:
   if p.poll() is None:p.terminate()
  (OUT/'checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')



