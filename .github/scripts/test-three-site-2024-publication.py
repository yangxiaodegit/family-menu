import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import unittest
import tempfile
import zipfile

spec=importlib.util.spec_from_file_location('publisher',Path(__file__).with_name('publish-three-site-2024.py'))
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
class PublicationGuardTests(unittest.TestCase):
 def fixture(self):
  exe=bytearray(256);exe[:2]=b'MZ';struct.pack_into('<I',exe,60,64);exe[64:68]=b'PE\0\0';struct.pack_into('<H',exe,68,0x8664);struct.pack_into('<H',exe,64+24+68,2);exe=bytes(exe)
  h=hashlib.sha256(exe).hexdigest()
  m={'product':'ThreeSiteReplenishment','version':p.VER,'platform':'windows','arch':'amd64','setup':p.EXE,'sha256':h,'size':len(exe)}
  proof={'version':p.VER,'all_passed':True,'source_commit':p.SOURCE,'source_tree':p.TREE,'installer_sha256':h,'installer_size':len(exe),'independent_rebuild':'identical','native_edge_checks':[{'name':'fixture','passed':True} for _ in range(27)],'workflow_run':p.RUN,'go_top_level':{'pass':641,'skip':126,'fail':0},'javascript':{'pass':120,'fail':0,'skipped':0},'browser_checks':40,'independent_rebuild_files':[{'file':p.EXE if i==0 else 'fixture'+str(i),'sha256':h,'independent_sha256':h} for i in range(7)]}
  files={p.EXE:exe,'latest.json':json.dumps(m).encode(),'PUBLIC_RELEASE_VERIFICATION.json':json.dumps(proof).encode(),p.CHECKSUM:(h+'  '+p.EXE+'\n').encode()}
  desc={'version':p.VER,'transport':'public-binary-chunks','parts':[{'name':'part0000.bin','size':len(exe),'sha256':h}],'source_commit':p.SOURCE,'source_tree':p.TREE,'installer_sha256':h,'installer_size':len(exe),'workflow_run':p.RUN}
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
 def test_missing_rebuild_or_source_tree_mismatch_rejected(self):
  for field in ('source_tree','independent_rebuild_files'):
   files,desc=self.fixture();proof=json.loads(files['PUBLIC_RELEASE_VERIFICATION.json']);proof[field]='b'*40 if field=='source_tree' else [];files['PUBLIC_RELEASE_VERIFICATION.json']=json.dumps(proof).encode();raw=self.archive(files,desc)
   with self.assertRaises(ValueError):p.validate_archive(raw,desc)
 def test_wrong_manifest_or_failed_browser_rejected(self):
  files,desc=self.fixture();proof=json.loads(files['PUBLIC_RELEASE_VERIFICATION.json']);proof['browser_checks']=39;files['PUBLIC_RELEASE_VERIFICATION.json']=json.dumps(proof).encode();raw=self.archive(files,desc)
  with self.assertRaises(ValueError):p.validate_archive(raw,desc)
 def test_tampered_or_extra_public_binary_parts_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   folder=Path(tmp);raw=b'approved synthetic bytes';part={'name':'part0000.bin','size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
   (folder/part['name']).write_bytes(raw)
   self.assertEqual(p.collect_public_parts(folder,[part]),raw)
   (folder/part['name']).write_bytes(b'tampered')
   with self.assertRaises(ValueError):p.collect_public_parts(folder,[part])
   (folder/part['name']).write_bytes(raw);(folder/'foreign.txt').write_text('unexpected')
   with self.assertRaises(ValueError):p.collect_public_parts(folder,[part])
 def test_public_part_names_and_total_size_checked(self):
  for field,value in [('name','../private.bin'),('size',1)]:
   files,desc=self.fixture();desc['parts'][0][field]=value;raw=self.archive(files,desc)
   with self.assertRaises(ValueError):p.validate_archive(raw,desc)
if __name__=='__main__':unittest.main()

