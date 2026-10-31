from pathlib import Path
import subprocess,json,hashlib,shutil,os,plistlib,urllib.request,zipfile
root=Path.cwd();repo=root/'voodoo';out=root/'out';out.mkdir(exist_ok=True)
def run(args,cwd=None):
 q=subprocess.run(args,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);print(q.stdout,flush=True)
 if q.returncode:raise SystemExit(q.returncode)
def clone(url,sha,path):
 run(['git','clone','--no-checkout',url,str(path)]);run(['git','checkout','--detach',sha],path)
clone('https://github.com/VoodooI2C/VoodooI2C.git','e3ac3ed207170c39db88d6a67a76cc9fd3a1895a',repo)
run(['git','submodule','update','--init','--recursive'],repo)
clone('https://github.com/acidanthera/MacKernelSDK.git','3f750085caa17ec3a7880f11c11bf4f48cd6a164',repo/'MacKernelSDK')
clone('https://github.com/acidanthera/ocbuild.git','020b14fa68a9825642e0c0fb643c2963bd679ae3',root/'ocbuild')
clone('https://github.com/acidanthera/VoodooInput.git','d897813718c2ef9ad143b6a86240fe52dcb1693e',root/'input-source')
run(['git','apply','--check',str(root/'ci/stage5b-publish.patch')],repo);run(['git','apply',str(root/'ci/stage5b-publish.patch')],repo)
run(['/bin/bash','-c','source "'+str(root/'ocbuild/ci-bootstrap.sh')+'"'],repo)
run(['/bin/bash','-c','source "'+str(root/'input-source/VoodooInput/Scripts/bootstrap.sh')+'" && mkdir -p Dependencies && mv VoodooInput Dependencies/'],repo)
for config in ['Debug','Release']:
 run(['xcodebuild','-workspace','VoodooI2C.xcworkspace','-scheme','VoodooI2C','-derivedDataPath','build','-jobs','1','-configuration',config,'ARCHS=x86_64','ONLY_ACTIVE_ARCH=YES','CURRENT_PROJECT_VERSION=2.9.1d5','MODULE_VERSION=2.9.1d5'],repo)
 products=repo/'build/Build/Products'/config
 shutil.copytree(products,out/config,dirs_exist_ok=True)
# Pinned official stock plugins: preserve existing published interfaces/bytes.
archive=root/'stock-2.9.1.zip'
urllib.request.urlretrieve('https://github.com/VoodooI2C/VoodooI2C/releases/download/v2.9.1/VoodooI2C-2.9.1-RELEASE.zip',archive)
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='368e5eb60794583c340764813bd7e8244e94d3d3c06ea5b67034addd539487f4'
stock=root/'stock'
with zipfile.ZipFile(archive) as z:z.extractall(stock)
diagnostics=[]
for config in ['Debug','Release']:
 dest=out/'diagnostic'/config/'VoodooI2C.kext';shutil.copytree(stock/'VoodooI2C.kext',dest)
 plugins={str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (dest/'Contents/PlugIns').rglob('*') if p.is_file()}
 shutil.copyfile(out/config/'VoodooI2C.kext/Contents/MacOS/VoodooI2C',dest/'Contents/MacOS/VoodooI2C')
 info=dest/'Contents/Info.plist';data=plistlib.loads(info.read_bytes());data['CFBundleVersion']='2.9.1d5'
 key='VoodooI2CPCILakeController';match=data['IOKitPersonalities'][key]['IOPCIMatch']
 assert '0x43e88086' not in match.lower();data['IOKitPersonalities'][key]['IOPCIMatch']=match+' 0x43e88086'
 info.write_bytes(plistlib.dumps(data,sort_keys=False))
 checks=[]
 for cmd in [['/usr/bin/codesign','--force','--sign','-',str(dest)],['/usr/bin/codesign','--verify','--deep','--strict','--verbose=2',str(dest)],['/usr/bin/codesign','-dvv',str(dest)],['/usr/bin/lipo','-archs',str(dest/'Contents/MacOS/VoodooI2C')]]:
  q=subprocess.run(cmd,text=True,capture_output=True);print(q.stdout+q.stderr,flush=True);checks.append({'argv':cmd,'rc':q.returncode,'stdout':q.stdout,'stderr':q.stderr})
 assert all(hashlib.sha256((dest/k).read_bytes()).hexdigest()==v for k,v in plugins.items()),'Stock plugin bytes changed'
 diagnostics.append({'config':config,'version':data['CFBundleVersion'],'matching':data['IOKitPersonalities'][key]['IOPCIMatch'],'stock_plugins_unchanged':True,'codesign_checks':checks,'hardware':'NOT TESTED'})
(out/'diagnostic-validation.json').write_text(json.dumps(diagnostics,indent=2))
manifest={str(p.relative_to(out)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in out.rglob('*') if p.is_file()}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2))
