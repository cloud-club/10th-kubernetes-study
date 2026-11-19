#!/usr/bin/env python3
"""Check rendered resources and real value overrides before deployment."""
import subprocess
from pathlib import Path
import yaml
root=Path(__file__).resolve().parents[1]
def render(args):
 return list(yaml.safe_load_all(subprocess.check_output(args,cwd=root,text=True)))
def keyed(docs):return {d['kind']:d for d in docs if d}
plain=keyed([yaml.safe_load(p.read_text()) for p in sorted((root/'deploy/plain').glob('*.yaml'))])
dev=keyed(render(['kubectl','kustomize','deploy/kustomize/overlays/dev']))
prod=keyed(render(['kubectl','kustomize','deploy/kustomize/overlays/prod']))
helm=keyed(render(['helm','template','nginx','deploy/helm/nginx']))
custom=keyed(render(['helm','template','nginx','deploy/helm/nginx','--set','replicaCount=2','--set','image.tag=1.27-alpine']))
for label,docs in [('plain',plain),('kustomize-dev',dev),('helm',helm)]:
 assert set(docs)=={'Deployment','Service'}
 for kind in docs:
  assert docs[kind]['spec']==plain[kind]['spec'], (label,kind)
  assert 'namespace' not in docs[kind]['metadata']
 print(label, 'Deployment/Service specs match, namespace is injected at deploy time')
assert prod['Deployment']['spec']['replicas']==2
assert custom['Deployment']['spec']['replicas']==2
assert custom['Deployment']['spec']['template']['spec']['containers'][0]['image']=='nginx:1.27-alpine'
print('PASS: dev=1, prod=2, Helm replica/image overrides work')
