#!/usr/bin/env python3
import pathlib,subprocess,sys,os,json,time,hashlib,shutil,tarfile,plistlib
R=pathlib.Path(__file__).resolve().parents[1];O=R/'stage4h-output';O.mkdir();L=O/'logs';L.mkdir();results={}
assert sys.platform=='darwin' and os.uname().machine=='x86_64'
def run(n,a,gate=True,timeout=1500):
 t=time.time()
 try:p=subprocess.run(list(map(str,a)),cwd=R,capture_output=True,timeout=timeout,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'));rc=p.returncode;out=p.stdout;err=p.stderr
 except Exception as e:rc=127;out=b'';err=str(e).encode()
 (L/(n+'.stdout.txt')).write_bytes(out);(L/(n+'.stderr.txt')).write_bytes(err);(L/(n+'.command.json')).write_text(json.dumps({'argv':list(map(str,a)),'returncode':rc,'gate':gate,'seconds':time.time()-t},indent=2));results[n]={'returncode':rc,'gate':gate};print(n,rc,flush=True);return rc
for n,a in [('OS',['sw_vers']),('kernel',['uname','-r']),('Xcode',['xcodebuild','-version']),('clang',['xcrun','clang++','--version']),('source-commit',['git','rev-parse','HEAD'])]:run(n,a)
run('CPU159',['python3','tools/test.py'])
for p in (R/'build/tests').glob('*'):
 if p.suffix in ['.log','.json']:(O/'cpu-tests').mkdir(exist_ok=True);shutil.copyfile(p,O/'cpu-tests'/p.name)
success=[]
for mode,extra,gate in [('RELEASE',['--release'],True),('DEBUG',[],False)]:
 rc=run(mode+'-build',['python3','tools/build.py',*extra,'--output',O/mode],gate)
 if rc:continue
 success.append(mode);run(mode+'-Compat-ABI',['python3','tools/check_compat_version.py',O/mode])
 for k in ['WhateverXe','AppleIntelTGLCompat']:
  exe=O/mode/(k+'.kext/Contents/MacOS')/k
  run(mode+'-'+k+'-file',['file',exe]);run(mode+'-'+k+'-undefined',['xcrun','nm','-u',exe]);run(mode+'-'+k+'-signature',['codesign','-d','--verbose=4',exe],False)
  info=plistlib.loads((exe.parent.parent/'Info.plist').read_bytes());assert info['CFBundleVersion']==('0.6.2d1' if k=='WhateverXe' else '0.6.1')
with tarfile.open(O/'New-Native-Kexts.tar.gz','w:gz') as t:
 for mode in success:
  for p in (O/mode).iterdir():
   if p.name.endswith(('.kext','.dSYM')) or p.name in ['build-manifest.json','boot-stack.json']:t.add(p,arcname=mode+'/'+p.name)
manifest={}
for d in ['WhateverXe','AppleIntelTGLCompat','tools','tests']:
 for p in sorted((R/d).glob('*')):
  if p.is_file() and p.suffix in ['.cpp','.hpp','.py','.plist']:manifest[p.relative_to(R).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
(O/'Corresponding-Source-SHA256.json').write_text(json.dumps(manifest,indent=2))
(O/'results.json').write_text(json.dumps({'results':results,'successful_builds':success,'source_base':'68a24273ea9ba668e7bb029ed60fd775c45b16d1 + exact Stage4C patch + minimal 25G83 patch','driver_version':'0.6.2d1','provider_version':'0.6.1 unchanged ABI','graphics_pkg':'UNCHANGED existing 0.3.2.266; not rebuilt/downloaded','runtime':'NOT TESTED','hardware':'NOT TESTED','installed_or_loaded':False},indent=2))
(O/'SHA256SUMS.json').write_text(json.dumps({p.relative_to(O).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in O.rglob('*') if p.is_file()},indent=2))
sys.exit(any(v['returncode'] for v in results.values() if v['gate']))
