import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import unittest
import zipfile

spec=importlib.util.spec_from_file_location('publisher',Path(__file__).with_name('publish-three-site-2023.py'))
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
class PublicationGuardTests(unittest.TestCase):
 def fixture(self):
  exe=bytearray(256);exe[:2]=b'MZ';struct.pack_into('<I',exe,60,64);exe[64:68]=b'PE\0\0';struct.pack_into('<H',exe,68,0x8664);struct.pack_into('<H',exe,64+24+68,2);exe=bytes(exe)
  h=hashlib.sha256(exe).hexdigest()
  m={'product':'ThreeSiteReplenishment','version':p.VER,'platform':'windows','arch':'amd64','setup':p.EXE,'sha256':h,'size':len(exe)}
  proof={'version':p.VER,'all_passed':True,'source_commit':'a'*40,'installer_sha256':h,'installer_size':len(exe),'independent_rebuild':'identical','native_edge_checks':[{'passed':True}],'workflow_run':'123'}
  files={p.EXE:exe,'latest.json':json.dumps(m).encode(),'PUBLIC_RELEASE_VERIFICATION.json':json.dumps(proof).encode(),p.CHECKSUM:(h+'  '+p.EXE+'\n').encode()}
  desc={'version':p.VER,'url':'https://example.oaiusercontent.com/synthetic.zip','source_commit':'a'*40,'installer_sha256':h,'installer_size':len(exe),'workflow_run':'123'}
  return files,desc
 def archive(self,files,desc):
  b=io.BytesIO()
  with zipfile.ZipFile(b,'w') as z:
   for name,data in files.items():z.writestr(name,data)
  raw=b.getvalue();desc['artifact_sha256']=hashlib.sha256(raw).hexdigest();return raw
 def test_exact_public_allowlist_and_binary_proof(self):
  files,desc=self.fixture();raw=self.archive(files,desc);self.assertEqual(set(p.validate_archive(raw,desc)[0]),p.ALLOWED)
 def test_private_or_extra_member_rejected(self):
  files,desc=self.fixture();files['review-source.zip']=b'private';raw=self.archive(files,desc)
  with self.assertRaises(ValueError):p.validate_archive(raw,desc)
 def test_failed_native_proof_rejected(self):
  files,desc=self.fixture();proof=json.loads(files['PUBLIC_RELEASE_VERIFICATION.json']);proof['native_edge_checks'][0]['passed']=False;files['PUBLIC_RELEASE_VERIFICATION.json']=json.dumps(proof).encode();raw=self.archive(files,desc)
  with self.assertRaises(ValueError):p.validate_archive(raw,desc)
 def test_manifest_hash_or_source_commit_mismatch_rejected(self):
  for field in ('installer_sha256','source_commit'):
   files,desc=self.fixture();raw=self.archive(files,desc);desc[field]='b'*(64 if field=='installer_sha256' else 40)
   with self.assertRaises(ValueError):p.validate_archive(raw,desc)
 def test_unsafe_transfer_url_rejected(self):
  for url in ('http://example.oaiusercontent.com/file','https://evil.com/file','https://x.oaiusercontent.com@evil.com/file','https://x.oaiusercontent.com:80/file'):
   files,desc=self.fixture();raw=self.archive(files,desc);desc['url']=url
   with self.assertRaises(ValueError):p.validate_archive(raw,desc)
if __name__=='__main__':unittest.main()
