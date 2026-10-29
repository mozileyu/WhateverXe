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
 # productbuild adds separate bundle-version references without package versions.
 packages=[x for x in refs if (x.text or '').strip().startswith('#')]
 assert len(packages)==7 and all(x.attrib.get('version')=='0.3.2.266' for x in packages)
 infos=list(expanded.glob('*.pkg/PackageInfo'))
 assert len(infos)==7 and all(ET.parse(p).getroot().attrib['version']=='0.3.2.266' for p in infos)
 (O/'Package-Version-Verification.json').write_text(json.dumps({'version':'0.3.2.266','distribution_packages':len(packages),'component_packageinfos':len(infos),'pkgutil_expand_exit':results['pkg-expand-for-version-check']['returncode'],'PASS':True},indent=2))
 shutil.rmtree(expanded)
 for p in (O/'RELEASE').glob('*.kext/Contents/Info.plist'):
  info=plistlib.loads(p.read_bytes());(O/(p.parent.parent.name+'.Info.json')).write_text(json.dumps(info,default=str,indent=2))
# Static native inspection only. No loading, installation or GPU calls.
for p in (O/'RELEASE').glob('*.kext/Contents/MacOS/*'):
 name=p.name
 run(name+'-file',['file',p])
 run(name+'-imports',['xcrun','nm','-u',p])
 run(name+'-signature',['codesign','-d','--verbose=4',p],gate=False)
system_providers={}
for p in pathlib.Path('/System/Library/Extensions').glob('*.kext/Contents/Info.plist'):
 try:
  d=plistlib.loads(p.read_bytes());system_providers[d['CFBundleIdentifier']]={'version':d.get('CFBundleVersion'),'compatible':d.get('OSBundleCompatibleVersion'),'path':str(p)}
 except (KeyError,ValueError,OSError):pass
(O/'Runner-System-Kexts.json').write_text(json.dumps(system_providers,indent=2))
clients={}
for osname in ['Common','Tahoe']:
 for p in (g/'payloads'/osname).rglob('Contents/Info.plist'):
  d=plistlib.loads(p.read_bytes())
  if d.get('OSBundleLibraries'):clients[d['CFBundleIdentifier']]={'requires':d['OSBundleLibraries'],'runner_system_providers':{k:system_providers.get(k) for k in d['OSBundleLibraries']},'scope':'Plist inventory only; missing kernel-collection providers and private symbol/structure compatibility remain unverified.'}
(O/'Native-Dependency-Inventory.json').write_text(json.dumps(clients,indent=2))
import tarfile
with tarfile.open(O/'Native-RELEASE-kexts.tar.gz','w:gz') as tar:
 for bundle in (O/'RELEASE').glob('*.kext'):
  tar.add(bundle,arcname=bundle.name)
(O/'results.json').write_text(json.dumps({'runner':os.environ['STAGE4C_RUNNER'],'results':results,'hardware':'NOT TESTED','GPU_runtime':'NOT TESTED','package_installation':'NOT PERFORMED'},indent=2))
manifest={p.relative_to(O).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in O.rglob('*') if p.is_file()}
(O/'SHA256SUMS.json').write_text(json.dumps(manifest,indent=2))
sys.exit(any(v['returncode'] for v in results.values() if v['gate']))
