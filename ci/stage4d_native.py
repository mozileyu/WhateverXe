import pathlib,subprocess,json,hashlib,os,sys,urllib.request,zipfile,shutil,tarfile,time
R=pathlib.Path(__file__).resolve().parents[1];O=R/'stage4d-output';O.mkdir();L=O/'logs';L.mkdir();D=O/'downloads';D.mkdir();results={}
assert sys.platform=='darwin' and os.uname().machine=='x86_64'
def run(n,a,cwd=R):
 t=time.time();p=subprocess.run(list(map(str,a)),cwd=cwd,capture_output=True,timeout=1200);(L/(n+'.stdout.txt')).write_bytes(p.stdout);(L/(n+'.stderr.txt')).write_bytes(p.stderr);results[n]={'argv':list(map(str,a)),'cwd':str(cwd),'returncode':p.returncode,'seconds':time.time()-t};print(n,p.returncode,flush=True);return p.returncode
downloads=[]
def fetch(url,name,expected=None):
 p=D/name
 with urllib.request.urlopen(url,timeout=90) as r:p.write_bytes(r.read())
 h=hashlib.sha256(p.read_bytes()).hexdigest()
 if expected:assert h==expected
 downloads.append({'url':url,'name':name,'sha256':h,'bytes':p.stat().st_size});return p
v=R/'voodoo'
try:
 run('OS',['sw_vers']);run('Xcode',['xcodebuild','-version']);run('clang',['xcrun','clang++','--version']);run('source',['git','rev-parse','HEAD'],v);run('submodules',['git','submodule','status','--recursive'],v)
 for conf in ['DEBUG','RELEASE']:
  p=fetch('https://github.com/acidanthera/VoodooInput/releases/download/1.1.6/VoodooInput-1.1.6-'+conf+'.zip','VoodooInput-1.1.6-'+conf+'.zip')
  d=v/'Dependencies/VoodooInput'/conf.title();d.mkdir(parents=True)
  with zipfile.ZipFile(p) as z:z.extractall(d)
 p=fetch('https://github.com/USBToolBox/kext/releases/download/1.2.0/USBToolBox-1.2.0-RELEASE.zip','USBToolBox-1.2.0-RELEASE.zip','c315a3a5acfd496dd97d0d19b4fbd1d487103d2fd541c5651583d4c9cebcfe07')
 fetch('https://codeload.github.com/USBToolBox/usbdump/zip/refs/heads/master','usbdump-source.zip')
 fetch('https://codeload.github.com/USBToolBox/kext/zip/refs/tags/1.2.0','USBToolBox-source-1.2.0.zip')
 assert run('patch-check',['git','apply','--check',R/'ci/fx506hm-i2c.patch'],v)==0
 assert run('patch-apply',['git','apply',R/'ci/fx506hm-i2c.patch'],v)==0
 rc=run('VoodooI2C-Release',['xcodebuild','-workspace','VoodooI2C.xcworkspace','-scheme','VoodooI2C','-derivedDataPath','build','-jobs','2','-configuration','Release','ARCHS=x86_64','ONLY_ACTIVE_ARCH=YES','CODE_SIGNING_ALLOWED=NO'],v)
 if rc==0:
  b=v/'build/Build/Products/Release';dest=O/'RELEASE';dest.mkdir()
  for n in ['VoodooI2C.kext','VoodooI2CHID.kext']:shutil.copytree(b/n,dest/n)
  with tarfile.open(O/'Native-input-kexts.tar.gz','w:gz') as t:
   for p in dest.iterdir():t.add(p,arcname=p.name)
  run('source-diff',['git','diff','--binary'],v)
  # Complete tracked corresponding source, including exact recursive submodules.
  files=subprocess.check_output(['git','ls-files','--cached','--recurse-submodules','-z'],cwd=v).decode().split('\0')
  with tarfile.open(O/'Corresponding-Source.tar.gz','w:gz') as t:
   for rel in files:
    if rel and (v/rel).is_file():t.add(v/rel,arcname=rel,recursive=False)
  (O/'Source-SHA256.json').write_text(json.dumps({rel:hashlib.sha256((v/rel).read_bytes()).hexdigest() for rel in files if rel and (v/rel).is_file()},indent=2))

except Exception as e:
 (L/'exception.txt').write_text(repr(e));results['exception']={'returncode':1,'message':repr(e)}
(O/'downloads.json').write_text(json.dumps(downloads,indent=2));(O/'results.json').write_text(json.dumps(results,indent=2))
(O/'SHA256SUMS.json').write_text(json.dumps({p.relative_to(O).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in O.rglob('*') if p.is_file()},indent=2));sys.exit(any(x['returncode'] for x in results.values()))
