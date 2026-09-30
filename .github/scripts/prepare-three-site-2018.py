"""Explicitly parameterize the reviewed .17 publication harness for final .18.
Only version/hash/old-release scope changes; source templates are blob-pinned.
"""
from pathlib import Path
import hashlib,subprocess
ROOT=Path.cwd()
def source(name,expected):
 raw=subprocess.check_output(['git','show','HEAD:.github/scripts/'+name])
 if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=expected:raise ValueError('Publication harness changed: '+name)
 return raw.decode('utf-8')
def one(s,a,b):
 if s.count(a)!=1:raise ValueError('Ambiguous release substitution: '+a[:70])
 return s.replace(a,b)

pub=source('publish-three-site-2017.py','1346b8cc6c40b38716053eff9f26c34b32543260')
qa=source('verify-three-site-2017.py','88ea914b4c66719b456c6bd9cdd1bc7298b6b4ed')
pub=pub.replace('2.0.17','2.0.18').replace('2017','2018')
pub=one(pub,'4d9e87cb205f76b62cbda0e982bf36d14480a671258adec128f7ac0235f8844a','faa51f91f9f8ccdf55df9db8a784cf66997593c87b516e1398f02079f09d23e3')
pub=one(pub,'SIZE=16243712','SIZE=16245248')
pub=one(pub,'4dcfd7c7109dcba27765a7e511634be8419d005de5d52bfac0c4dfae5315a6a5','ba2b06135f117da345d3027d17012e04be36071ec8d2df826576a9647ce32150')
pub=pub.replace("['2.0.14','2.0.15']","['2.0.14','2.0.15','2.0.17']")
pub=one(pub,"  else:raise ValueError('Expected controlled old-version fixture absent: '+n)","  else:\n   if ver not in ['2.0.14','2.0.15']:raise ValueError('Expected old fixture absent')\n   raw=git('show','391b31c23fe5da19141e4ad8bb551fe6012166a7:updates/three-site-replenishment/'+n)\n   (FIXTURES/n).write_bytes(raw)")
pub=one(pub," oldwf=ROOT/'.github/workflows/publish-three-site-2.0.15.yml'"," oldwf=ROOT/'.github/workflows/publish-three-site-2.0.17.yml'")
pub=one(pub," paths=['updates/three-site-replenishment','.github/workflows/publish-three-site-2.0.15.yml','.github/scripts/verify-three-site-release.py','.github/three-site-2018-transfer.json']"," paths=['updates/three-site-replenishment','.github/workflows/publish-three-site-2.0.17.yml','.github/three-site-2018-transfer.json']")
pub=pub.replace("['three-site-v2.0.14','three-site-v2.0.15']","['three-site-v2.0.14','three-site-v2.0.15','three-site-v2.0.17']")
pub=pub.replace('2.0.14和2.0.15公开安装包','2.0.14、2.0.15及过渡2.0.17公开安装包')
pub=pub.replace('仅补齐在线更新、校验、备份与保留资料的安装流程。','补齐在线更新、校验、备份与保留资料的安装流程，并修复程序与资料位于不同盘符时的路径兼容。')
qa=qa.replace('2.0.17','2.0.18').replace('2017','2018')
qa=qa.replace("for old in ['2.0.14','2.0.15']:","for old in ['2.0.14','2.0.15','2.0.17']:")
qa=qa.replace("'2.0.15 -> 2.0.18']","'2.0.15 -> 2.0.18','2.0.17 -> 2.0.18']")
# The .17 updater performs a full backup before starting the .18 installer.
qa=one(qa," check(old+' custom database records preserved',proof(state)==before)"," check(old+' custom database records preserved',proof(state)==before)\n if old=='2.0.17':check('2.0.17 creates complete backup before online installation',bool(list((state/'backups').glob('*.zip'))))")
for n,s in [('publish-three-site-2018.generated.py',pub),('verify-three-site-2018.generated.py',qa)]:
 compile(s,n,'exec')
 (ROOT/'.github/scripts'/n).write_bytes(s.encode('utf-8'))
print('Prepared final .18 publication, withdrawal scope and real .14/.15/.17 forward-upgrade checks')
