from pathlib import Path
import subprocess,json,hashlib,shutil,os
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
manifest={str(p.relative_to(out)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in out.rglob('*') if p.is_file()}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2))
