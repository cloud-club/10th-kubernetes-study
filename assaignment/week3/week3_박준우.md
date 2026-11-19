# 1. 일반 YAML, Kustomize, Helm으로 이미지 배포하고 비교하기

## 1-1. 일반 YAML로 배포하기

다음과 같이 YAML 파일을 정의하여 NGINX Deployment와 ClusterIP Service를 생성했습니다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
  labels:
    app.kubernetes.io/name: nginx
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: nginx
  template:
    metadata:
      labels:
        app.kubernetes.io/name: nginx
    spec:
      containers:
        - name: nginx
          image: nginx:alpine
          ports:
            - name: http
              containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: nginx
  labels:
    app.kubernetes.io/name: nginx
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: nginx
  ports:
    - name: http
      protocol: TCP
      port: 80
      targetPort: 80
```

위 Deployment, Service를 `cicd-plain` Namespace에 배포하였습니다.
이후 Port Forward를 사용해 `curl` 로 요청을 보내 정상적으로 Nginx에 접근할 수 있는 것을 확인하였습니다.

![](../../../img/junwoo-park/week03/plain-result.png)

## 1-2. Kustomize로 배포하기

Kustomize는 Base에 공통으로 사용되는 리소스를 정의하고, Overlay에서 각 환경별로 설정을 다르게 하여 배포할 수 있습니다.

우선 공통적으로 Nginx Deployment와 Service가 필요하므로 `base/`에는 다음과 같이 정의할 수 있습니다.

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
  labels:
    app.kubernetes.io/name: nginx
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: nginx
  template:
    metadata:
      labels:
        app.kubernetes.io/name: nginx
    spec:
      containers:
        - name: nginx
          image: nginx:alpine
          ports:
            - name: http
              containerPort: 80
```

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx
  labels:
    app.kubernetes.io/name: nginx
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: nginx
  ports:
    - name: http
      protocol: TCP
      port: 80
      targetPort: 80
```

```yaml
# kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - deployment.yaml
  - service.yaml
```

그리고 Overlay는 dev, prod 환경별로 replicas를 다르게  설정합니다.
Deployment의 Replicas의 경우, `kustomization.yaml` 에서 바로 설정할 수 있습니다. ([참조](https://github.com/kubernetes-sigs/kustomize/blob/master/examples/replicas.md))

```yaml
# dev/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
replicas:
  - name: nginx
    count: 1
```

```yaml
# prod/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
replicas:
  - name: nginx
    count: 2
```

Dev Overlay를 배포하고 테스트해보면 다음과 같이 Nginx Deploy의 Replica가 1개 생성되며, 정상적으로 접근되는 것을 확인하였습니다.

![](../../../img/junwoo-park/week03/kustomize-dev-result.png)

Prod Overlay를 배포하면 Nginx Deploy의 Replica가 2개 생성되며, 정상적으로 접근되는 것을 확인하였습니다.

![](../../../img/junwoo-park/week03/kustomize-prod-result.png)

# 3. Helm으로 배포하기

Helm으로 배포하기 위해서는 우선 `templates/` 에 리소스를 정의해야 합니다.
그리고 `values.yaml` 에 정의된 값을 사용하기 위해서는 `{{ .Values.{값} }}` 과 같이 정의하면 사용할 수 있습니다.
Helm Chart를 생성할 때는 `helm create` 를 사용하였습니다.
그리고 replicas를 포함해 labels, image 등 최대한 values.yaml 파일로 변경할 수 있도록 구성했습니다.

```yaml
# templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
  labels:
    {{- include "nginx.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      {{- include "nginx.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "nginx.selectorLabels" . | nindent 8 }}
    spec:
      containers:
        - name: nginx
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: {{ .Values.service.targetPort }}
```

```yaml
# templates/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx
  labels:
    {{- include "nginx.labels" . | nindent 4 }}
spec:
  type: {{ .Values.service.type }}
  selector:
    {{- include "nginx.selectorLabels" . | nindent 4 }}
  ports:
    - name: http
      protocol: TCP
      port: {{ .Values.service.port }}
      targetPort: {{ .Values.service.targetPort }}
```

그리고 `Chart.yaml` 에 간단한 Chart 정보를 작성하였습니다.

```yaml
# Chart.yaml
apiVersion: v2
name: nginx
description: Nginx (nginx:alpine) for week3 CI/CD assignment
type: application
version: 0.1.0
appVersion: "alpine"
```

마지막으로 dev 환경에 사용할 `values.yaml`, prod 환경에 사용할 `values-prod.yaml` 을 정의한 후 배포하였습니다.

```yaml
# values.yaml
replicaCount: 1

image:
  repository: nginx
  tag: alpine
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80
  targetPort: 80
```

```yaml
# values-prod.yaml
replicaCount: 2
```

그리고 Dev환경을 배포하면 다음과 같습니다.

![](../../../img/junwoo-park/week03/helm-dev-result.png)

Prod환경을 배포하면 다음과 같습니다.

![](../../../img/junwoo-park/week03/helm-prod-result.png)

# 1-4. 비교

| 비교 항목 | 일반 YAML | Kustomize | Helm |
|---|---|---|---|
| 공통 설정을 재사용하는 방식 | 재사용 수단 없음. 파일 복사 | `base/` 를 overlay가 `resources: ../../base` 로 참조 | `templates/` 하나를 두고 values 로 값을 주입 |
| dev/prod 설정을 나누는 방식 | 환경별 디렉터리/파일을 통째로 복제 | `overlays/dev`, `overlays/prod` 에 차이만 패치(`replicas`, `images`, `labels`, patches) | `values-dev.yaml` / `values-prod.yaml` 파일 또는 `--set` |
| 이미지·replicas를 바꾸는 위치 | `deployment.yaml` 직접 수정 | overlay `kustomization.yaml` 의 `images:` / `replicas:` (또는 `kustomize edit set image`) | `values.yaml` 의 `image.*`, `replicaCount` (또는 `-f`, `--set`) |
| 장점 | 가장 단순하고 결과가 눈에 그대로 보임. 도구 추가 필요 없음 | 템플릿 문법 없이 순수 YAML 유지. `kubectl` 에 내장. 차이(diff)만 관리 | 패키지·버전 관리, `helm history`/`rollback`, 설치/삭제 라이프사이클, 외부 차트 재사용 |
| 불편했던 점 | 환경이 늘면 중복이 늘고 수정 누락 위험? (사실 간단한 Nginx 배포에서는 가장 편했음) | 패치 방식이 여러 가지(builtin 필드, strategic merge, JSON6902)라 처음엔 헷갈림. 조건문·반복 같은 로직은 불가 | Go 템플릿 들여쓰기(`nindent`)와 헬퍼 작성 부담, 렌더링 전엔 결과가 안 보임. `upgrade` 시 이전 값이 남는 동작(`--reset-values`) 주의 |
| 어떤 상황에서 선택할지 | 일회성 테스트, 환경이 하나인 작은 서비스 | 자체 서비스의 환경별(dev/stg/prod) 차이 관리, 순수 YAML 선호 시? | 여러 팀/고객에게 배포하는 패키지, 설정 옵션이 많은 앱 |

# 2. 개인 GitHub Actions/GHCR/Kubernetes 연동하기

우선 주어진 `Dockerfile` 과 `nginx.conf` 를 `app/` 디렉토리에 생성했습니다.

그리고 `deploy/ci/` 디렉토리에 Nginx Deployment와 Service를 생성했습니다.

```yaml
# deploy/ci/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-api
  labels:
    app.kubernetes.io/name: nginx-api
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: nginx-api
  template:
    metadata:
      labels:
        app.kubernetes.io/name: nginx-api
    spec:
      containers:
        - name: nginx
          image: ghcr.io/<github-id>/nginx-api:placeholder
          ports:
            - name: http
              containerPort: 8080
          readinessProbe:
            httpGet:
              path: /healthz
              port: http
```

```yaml
# deploy/ci/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-api
  labels:
    app.kubernetes.io/name: nginx-api
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: nginx-api
  ports:
    - name: http
      port: 80
      targetPort: 8080

```

`cicd-ci` 라는 Namespace를 생성한 후, Self Hosted Runners를 설치했습니다.

![](../../../img/junwoo-park/week03/action-install.png)

그리고 `./run.sh` 를 실행해 터미널에 Self Hosted Runners를 Foreground로 실행했습니다.

main 브랜치에 commit이 발생할 때마다 이미지를 빌드하도록 Workflow를 작성하였습니다.

```yaml
name: ci

on:
  push:
    branches: [main]

# 연속 push 시 순서대로 실행
concurrency:
  group: deploy-cicd-ci
  cancel-in-progress: false

jobs:
build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    outputs:
      image: ${{ steps.vars.outputs.image }}
      digest: ${{ steps.build.outputs.digest }}
    steps:
      - uses: actions/checkout@v4

      - name: Compute image name
        id: vars
        shell: bash
        run: |
          set -euo pipefail
          owner="${GITHUB_REPOSITORY_OWNER,,}"
          image="ghcr.io/${owner}/nginx-api:${GITHUB_SHA}"
          echo "image=${image}" >> "$GITHUB_OUTPUT"
          echo "IMAGE=${image}"

      - uses: docker/setup-qemu-action@v3
      - uses: docker/setup-buildx-action@v3

      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        id: build
        uses: docker/build-push-action@v6
        with:
          context: app
          platforms: linux/amd64,linux/arm64
          push: true
          tags: ${{ steps.vars.outputs.image }}
          labels: |
            org.opencontainers.image.source=${{ github.server_url }}/${{ github.repository }}
            org.opencontainers.image.revision=${{ github.sha }}

  deploy:
    needs: build
    runs-on: [self-hosted, kind-local]
    permissions:
      contents: read
    env:
      IMAGE: ${{ needs.build.outputs.image }}
      DIGEST: ${{ needs.build.outputs.digest }}
      KUBE_CONTEXT: kind-kind
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to cicd-ci
        shell: bash
        run: |
          set -euo pipefail
          echo "IMAGE=$IMAGE"
          kubectl set image --local -f deploy/ci/deployment.yaml nginx="$IMAGE" -o yaml \
            | kubectl --context "$KUBE_CONTEXT" -n cicd-ci apply -f -
          kubectl --context "$KUBE_CONTEXT" -n cicd-ci apply -f deploy/ci/service.yaml
          kubectl --context "$KUBE_CONTEXT" -n cicd-ci rollout status deployment/nginx-api --timeout=180s
          kubectl --context "$KUBE_CONTEXT" -n cicd-ci get deployment nginx-api \
            -o jsonpath='{.spec.template.spec.containers[0].image}'; echo

      - name: Record result
        shell: bash
        run: |
          {
            echo "### Deploy result"
            echo "- commit: \`$GITHUB_SHA\`"
            echo "- image: \`$IMAGE\`"
            echo "- digest: \`$DIGEST\`"
            echo "- pods:"
            kubectl --context "$KUBE_CONTEXT" -n cicd-ci get pods -l app.kubernetes.io/name=nginx-api \
              -o jsonpath='{range .items[*]}  - {.metadata.name} {.spec.containers[0].image} {.status.containerStatuses[0].imageID}{"\n"}{end}'
          } >> "$GITHUB_STEP_SUMMARY"
```

현재까지 작성한 내용을 "feat: nginx-api CI/CD (v1)" 라는 이름으로 커밋했습니다.

근데 `Deploy to cicd-ci` 단계에서 "Waiting for deployment "nginx-api" rollout to finish: 0 of 1 updated replicas are available..." 라는 메시지를 마지막으로 Timeout이 발생하더라고요. 그래서 우선 Pod 상태를 Describe로 확인해봤습니다.

![](../../../img/junwoo-park/week03/action-errimagepull.png)

이미지를 Pull하는데 에러가 발생하고 있었습니다. 이미지가 성공적으로 빌드되었는지를 확인해보았습니다.

![](../../../img/junwoo-park/week03/action-image-exists.png)

이미지는 정상적으로 빌드되었습니다. 그럼 원인은 권한 문제일 확률이 높다고 생각했습니다. GHCR Package가 Private으로 되어 있어서, Package만 Public으로 바꾼 후 실패한 deploy 스텝을 다시 실행했습니다.

![](../../../img/junwoo-park/week03/action-success.png)

Action이 정상적으로 완료되었습니다. 현재 HEAD의 Commit SHA와 Deployment의 Template 이미지 태그가 일치하는 것을 확인했습니다.

![](../../../img/junwoo-park/week03/action-sha-match.png)

현재 Nginx version은 `v1` 입니다.

![](../../../img/junwoo-park/week03/action-confirm-v1.png)
이제 `nginx.conf` 의 `version` 을 바꿔서 다시 커밋해보겠습니다. Action은 정상적으로 완료되었고, Commit SHA와 Deployment의 Template Image를 다시 확인해보았습니다.

![](../../../img/junwoo-park/week03/action-confirm-v2.png)

API 요청을 보내 version이 `v2` 로 바꼈는지 확인했습니다.

![](../../../img/junwoo-park/week03/action-confirm-v2-2.png)

# 3. Argo CD 연동과 GitOps 이해하기

우선 ArgoCD를 제 Kubernetes Cluster에 설치했습니다. Namepsace는 `argocd` 에 했습니다.

```sh
kubectl --context kind-kind create namespace argocd

kubectl --context kind-kind apply -n argocd --server-side --force-conflicts \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

```

그리고 ArgoCD에 로그인해주었습니다.

![](../../../img/junwoo-park/week03/argocd-login.png)

이제 읽기 전용 deploy key를 등록해보겠습니다.
아래 명령어를 통해 key를 생성하였습니다.

```sh
ssh-keygen -t ed25519 -N "" -C "argocd-readonly" -f ~/.ssh/argocd-nginx-api
```

그리고 ArgoCD에 레포지토리를 추가했습니다.

![](../../../img/junwoo-park/week03/argocd-add-repo.png)

이제 Deployment와 Service를 작성합니다. 2번에서 했던 것을 가져오되, GitOps의 철학(?)에 맞게 이미지 태그를 직접 지정합니다. Git에 적힌 값이 곧 원하는 상태이다?

```yaml
# deploy/gitops/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-api
  labels:
    app.kubernetes.io/name: nginx-api
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: nginx-api
  template:
    metadata:
      labels:
        app.kubernetes.io/name: nginx-api
    spec:
      containers:
        - name: nginx
          image: ghcr.io/boksam/nginx-api:5c642572ae24ad117c061e70b6ed1372dab4d42d
          ports:
            - name: http
              containerPort: 8080
          readinessProbe:
            httpGet:
              path: /healthz
              port: http
```

```yaml
# deploy/gitops/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-api
  labels:
    app.kubernetes.io/name: nginx-api
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: nginx-api
  ports:
    - name: http
      port: 80
      targetPort: 8080
```

이제 Application 정의를 작성해보겠습니다. `deploy/gitops/` 에 넣지 않고 밖으로 빼서 `argocd/` 디렉토리에 작성하였습니다.
아마도 `deploy/gitops/` 디렉토리에 Application 정의를 두면 ArgoCD가 자기 자신을 관리하는 구조가 되는 걸까요?

```yaml
# argocd/application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: nginx-api-gitops
  namespace: argocd
spec:
  project: default
  source:
    repoURL: git@github.com:boksam/nginx-api-cicd.git
    targetRevision: main
    path: deploy/gitops
  destination:
    server: https://kubernetes.default.svc
    namespace: cicd-gitops
  syncPolicy:
    syncOptions:
      - CreateNamespace=true
```

그리고 `deploy/gitops`와 `argocd/` 먼저 커밋 & 푸시한 후 ArgoCD Application을 확인해보았습니다.

![](../../../img/junwoo-park/week03/argocd-first-push.png)
ArgoCD Application은 `OutOfSync` 상태이더군요. Sync를 한 번 해보겠습니다.

![](../../../img/junwoo-park/week03/argocd-first-sync.png)

좋습니다. 이제 `Synced` 상태로 바꼈습니다.

ArgoCD UI에서도 확인해보면 정상적으로 Sync된 것이 보이더군요.

![](../../../img/junwoo-park/week03/argocd-first-sync-ui.png)

이제 GitHub Workflow를 수정해서 배포하면 Manifest가 갱신되도록 수정해보겠습니다.
2번의 Workflow를 거의 이용하되, 아래 3가지를 변경했습니다.

1. `on.push.paths` 필터를 추가했습니다.
2. `deploy` job(self-hosted, kubectl)을 지웠습니다.
3. `update-manifest` job(GitHub-hosted, `contents: write`)을 추가했습니다.

```yaml
name: ci

on:
  push:
    branches: [main]
    paths:
      - 'app/**'
      - '.github/workflows/ci.yml'

concurrency:
  group: ci-main
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    outputs:
      image: ${{ steps.vars.outputs.image }}
      digest: ${{ steps.build.outputs.digest }}
    steps:
      - uses: actions/checkout@v4

      - name: Compute image name
        id: vars
        shell: bash
        run: |
          set -euo pipefail
          owner="${GITHUB_REPOSITORY_OWNER,,}"
          echo "image=ghcr.io/${owner}/nginx-api:${GITHUB_SHA}" >> "$GITHUB_OUTPUT"

      - uses: docker/setup-qemu-action@v3
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        id: build
        uses: docker/build-push-action@v6
        with:
          context: app
          platforms: linux/amd64,linux/arm64
          push: true
          tags: ${{ steps.vars.outputs.image }}
          labels: |
            org.opencontainers.image.source=${{ github.server_url }}/${{ github.repository }}
            org.opencontainers.image.revision=${{ github.sha }}

  update-manifest:
    needs: build
    runs-on: ubuntu-latest
    permissions:
      contents: write
    env:
      IMAGE: ${{ needs.build.outputs.image }}
      SOURCE_SHA: ${{ github.sha }}
    steps:
      - uses: actions/checkout@v4
        with:
          ref: main

      - name: Update image in deploy/gitops
        shell: bash
        run: |
          set -euo pipefail
          yq -i '(.spec.template.spec.containers[] | select(.name == "nginx") | .image) = strenv(IMAGE)' \
            deploy/gitops/deployment.yaml
          git diff -- deploy/gitops/

      - name: Commit and push
        shell: bash
        run: |
          set -euo pipefail
          if git diff --quiet -- deploy/gitops/; then
            echo "no change"; exit 0
          fi
          git config user.name  "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add deploy/gitops/deployment.yaml
          git commit -m "chore(gitops): nginx-api image -> ${SOURCE_SHA:0:7}" \
                     -m "image: ${IMAGE}" -m "source-commit: ${SOURCE_SHA}"
          # 그 사이 main 이 움직였으면 rebase 후 재시도
          for i in 1 2 3; do
            git pull --rebase origin main && git push origin HEAD:main && break
            sleep 5
          done
          echo "### manifest commit: $(git rev-parse HEAD)" >> "$GITHUB_STEP_SUMMARY"
          echo "- source commit: \`${SOURCE_SHA}\`" >> "$GITHUB_STEP_SUMMARY"
          echo "- image: \`${IMAGE}\`" >> "$GITHUB_STEP_SUMMARY"
```

그리고 ArgoCD Application의 SyncPolicy를 automated로 변경합니다.

```yaml
# argocd/application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: nginx-api-gitops
  namespace: argocd
spec:
  project: default
  source:
    repoURL: git@github.com:boksam/nginx-api-cicd.git
    targetRevision: main
    path: deploy/gitops
  destination:
    server: https://kubernetes.default.svc
    namespace: cicd-gitops
  syncPolicy:
    automated:
      prune: true
    selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

그리고 커밋했습니다. 음 오류가 발생했는데, selfHeal 인덴트를 틀렸네요. 수정해서 커밋했습니다.
