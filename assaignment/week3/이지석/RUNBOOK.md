# Week 3 재현 및 발표 시연

작성자: 이지석 / dev-jiseok. 공용 레포에는 3주차만 제출합니다.

## 현재 제한

GHCR 패키지가 Private입니다. 실제 배포 검증은 `GITHUB_TOKEN`으로 만든 임시 imagePullSecret을 사용했습니다. 이 토큰은 해당 job 종료 시 만료되므로 상시 인증 구성이 아닙니다. **과제의 Public GHCR 요건은 아직 미완료**입니다. Git 읽기용 Argo CD deploy key와 이미지 pull 인증은 별개입니다.

1. dev-jiseok으로 https://github.com/users/dev-jiseok/packages/container/nginx-api/settings 에서 Public으로 변경합니다.
2. 익명 `docker buildx imagetools inspect ghcr.io/dev-jiseok/nginx-api:<전체 소스 SHA>` 성공을 확인합니다.
3. `kubectl --context kind-jiseok-netlab -n cicd-gitops patch serviceaccount default -p '{"imagePullSecrets":[]}'`로 임시 참조를 정리합니다. 검증 종료 시 이미 정리했으면 생략합니다.
4. `app/nginx.conf` 응답을 다음 버전으로 바꿔 main에 push합니다.
5. Actions 완료뿐 아니라 Application Synced/Healthy, 새 Pod image/imageID, 실제 API 응답을 확인합니다.

## 클러스터와 도구

kind 0.33.0, node image `kindest/node:v1.35.0`, Kubernetes 1.35.0, kubectl 1.34.1, Helm 4.3.2, Docker Desktop 4.55.0 / Engine 29.1.3, Argo CD 3.6.2.

```bash
kind create cluster --name jiseok-netlab --image kindest/node:v1.35.0 --config infra/kind.yaml
kubectl --context kind-jiseok-netlab get nodes
for ns in cicd-plain cicd-kustomize cicd-helm cicd-ci; do
  kubectl --context kind-jiseok-netlab create namespace "$ns" --dry-run=client -o yaml | kubectl --context kind-jiseok-netlab apply -f -
done
kubectl --context kind-jiseok-netlab -n cicd-plain apply -f deploy/plain
kubectl --context kind-jiseok-netlab -n cicd-kustomize apply -k deploy/kustomize/overlays/dev
helm --kube-context kind-jiseok-netlab upgrade --install nginx deploy/helm/nginx -n cicd-helm
kubectl kustomize deploy/kustomize/overlays/prod
helm template nginx deploy/helm/nginx --set replicaCount=2
```

이 작업 환경은 기본 kubeconfig를 바꾸지 않고 별도 `.runtime/kubeconfig`를 사용했습니다. 이 파일은 저장소 밖의 로컬 자격 증명입니다. 이 환경에서 아래 명령을 실행하려면 먼저 해당 kubeconfig 경로를 `KUBECONFIG`로 지정합니다.

## Direct CI

과제 2 시점 워크플로는 `examples/ci-direct.yml`에 보존했습니다. Public 전환 후에는 임시 인증 단계를 제거한 `examples/ci-direct-public.yml`을 참고합니다. self-hosted runner는 개인 비공개 레포에 등록하고 `jiseok-k8s` 라벨과 이 실습 클러스터 kubeconfig를 갖도록 실행합니다. main push만 배포하고 외부 PR은 실행하지 않습니다.

## GitOps

```bash
kubectl --context kind-jiseok-netlab create namespace argocd
kubectl --context kind-jiseok-netlab apply -n argocd --server-side -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.6.2/manifests/install.yaml
# 비공개 저장소 전용 read-only deploy key를 등록하고 Argo CD repository Secret에 연결합니다.
# 개인키, 토큰, kubeconfig를 Git에 넣지 않습니다.
kubectl --context kind-jiseok-netlab apply -f infra/argocd-application.yaml
kubectl --context kind-jiseok-netlab -n argocd get application nginx-api
```

현재 `.github/workflows/ci.yml`은 GitHub-hosted runner에서 이미지 빌드와 Git 갱신만 합니다. Argo CD가 `main:deploy/gitops`를 읽고 자동 적용합니다. `registry-session.yml`은 Public 전환 전의 한시적 인증 검증 도구이며 앱 배포 명령은 없습니다. 새로 실행하면 과거 종료 표시 ConfigMap을 지우고 최대 40분 동안 임시 토큰을 유지합니다. `kubectl -n cicd-gitops create configmap verification-complete`를 실행하면 종료합니다.

## 발표 시연 (3분)

터미널 1:
```bash
kubectl --context kind-jiseok-netlab -n cicd-gitops port-forward svc/nginx-api 18090:80
```
터미널 2:
```bash
curl http://localhost:18090/api/hello
kubectl --context kind-jiseok-netlab -n argocd get application nginx-api
kubectl --context kind-jiseok-netlab -n cicd-gitops get deploy,rs,pods
```

Argo CD UI를 직접 확인하려면 별도 터미널에서 `kubectl -n argocd port-forward svc/argocd-server 18443:443`를 실행하고 `https://localhost:18443`를 엽니다. 관리자 초기 비밀번호는 로컬 Secret으로만 확인하고 캡처하거나 보고서에 넣지 않습니다.

라이브 시연 전에는 GHCR Public 전환과 익명 pull을 먼저 확인합니다. 불가능하면 저장된 검증 결과를 보여 주고, 현재 제약을 설명합니다. 문서의 실측 성공을 현재 시점의 지속적인 재배포 가능성으로 설명하지 않습니다.
