#!/usr/bin/env python3
"""Native macOS-only upstream builds; never installs payloads or touches EFI."""
import json,os,pathlib,subprocess,sys,time,shutil,hashlib,plistlib
R=pathlib.Path(__file__).resolve().parents[1];O=R/'stage4c-output';O.mkdir();L=O/'logs';L.mkdir();results={}
def run(name,args,cwd=R,gate=True):
 t=time.time()
 try:
  p=subprocess.run(list(map(str,args)),cwd=cwd,capture_output=True,timeout=1500,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
  rc=p.returncode;stdout=p.stdout;stderr=p.stderr
 except Exception as e:rc=127;stdout=b'';stderr=str(e).encode()
 (L/(name+'.stdout.txt')).write_bytes(stdout);(L/(name+'.stderr.txt')).write_bytes(stderr)
 (L/(name+'.command.json')).write_text(json.dumps({'argv':list(map(str,args)),'cwd':str(cwd),'returncode':rc,'gate':gate,'seconds':time.time()-t},indent=2))
 results[name]={'returncode':rc,'gate':gate};print(name,rc,flush=True);return rc
assert sys.platform=='darwin' and os.uname().machine=='x86_64'
for name,args in [('OS',['sw_vers']),('kernel',['uname','-a']),('Xcode',['xcodebuild','-version']),('compiler',['xcrun','clang++','--version']),('pkgbuild',['pkgbuild','--version']),('productbuild',['productbuild','--version']),('python',['python3','--version']),('node',['node','--version']),('rcodesign',['rcodesign','--version'])]:run(name,args,gate=False)
ref=R/'reference'
run('upstream-cpu',['python3','tools/test.py'],ref,gate=False)
for p in (ref/'build/tests').glob('*'):
 if p.suffix in ['.json','.log']:(O/'upstream-tests').mkdir(exist_ok=True);shutil.copyfile(p,O/'upstream-tests'/p.name)
run('apply-stage4b',['git','apply',R/'ci/stage4b-wex.patch'],ref)
run('stage4b-cpu',['python3','tools/test.py'],ref,gate=False)
for p in (ref/'build/tests').glob('*'):
 if p.suffix in ['.json','.log']:(O/'stage4b-tests').mkdir(exist_ok=True);shutil.copyfile(p,O/'stage4b-tests'/p.name)
run('stage4c-cpu',['python3','tools/test.py'])
for p in (R/'build/tests').glob('*'):
 if p.suffix in ['.json','.log']:(O/'stage4c-tests').mkdir(exist_ok=True);shutil.copyfile(p,O/'stage4c-tests'/p.name)
run('WEX-RELEASE',['python3','tools/build.py','--release','--output',O/'RELEASE'])
run('Compat-ABI-floor',['python3','tools/check_compat_version.py',O/'RELEASE'])
g=R/'graphics';run('Graphics-build',['python3','tools/build.py','--output',O/'Graphics'],g)
package=O/'Graphics/WhateverXe-Graphics-0.3.2.266.pkg'
if package.exists():
 run('Graphics-full-test',['python3','tools/test.py',package],g)
 run('pkg-container-signature',['pkgutil','--check-signature',package],gate=False)
 expanded=O/'expanded-for-version-check'
 run('pkg-expand-for-version-check',['pkgutil','--expand-full',package,expanded])
 import xml.etree.ElementTree as ET
 refs=ET.parse(expanded/'Distribution').getroot().findall('pkg-ref')
 assert all(x.attrib['version']=='0.3.2.266' for x in refs)
 for p in expanded.glob('*.pkg/PackageInfo'):assert ET.parse(p).getroot().attrib['version']=='0.3.2.266'
 shutil.rmtree(expanded)
 for p in (O/'RELEASE').glob('*.kext/Contents/Info.plist'):
  info=plistlib.loads(p.read_bytes());(O/(p.parent.parent.name+'.Info.json')).write_text(json.dumps(info,default=str,indent=2))
import tarfile
with tarfile.open(O/'Native-RELEASE-kexts.tar.gz','w:gz') as tar:
 for bundle in (O/'RELEASE').glob('*.kext'):
  tar.add(bundle,arcname=bundle.name)
(O/'results.json').write_text(json.dumps({'runner':os.environ['STAGE4C_RUNNER'],'results':results,'hardware':'NOT TESTED','GPU_runtime':'NOT TESTED','package_installation':'NOT PERFORMED'},indent=2))
manifest={p.relative_to(O).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in O.rglob('*') if p.is_file()}
(O/'SHA256SUMS.json').write_text(json.dumps(manifest,indent=2))
sys.exit(any(v['returncode'] for v in results.values() if v['gate']))
