# 3주차 과제: Kubernetes CI/CD — 이지석

> 3주차 기본 과제 1~3을 수행했습니다. 공개 GHCR에서 인증 Secret 없이 새 SHA 이미지를 받아 v1·v2 직접 CI와 v3 자동 GitOps 배포 및 실제 응답까지 확인했습니다.

- GitHub: **dev-jiseok**
- 개인 실습 저장소: [dev-jiseok/kubernetes-study-lab](https://github.com/dev-jiseok/kubernetes-study-lab) (비공개)
- 이미지: `ghcr.io/dev-jiseok/nginx-api:<전체 소스 commit SHA>`
- 기준 과제: [Issue #14](https://github.com/cloud-club/10th-kubernetes-study/issues/14)
- 실습일: 2026-11-19, macOS ARM64

## 수행 결과

| 항목 | 확인 결과 |
|---|---|
| 일반 YAML·Kustomize·Helm | 세 namespace의 Nginx 기본 페이지 HTTP 200, 기본 spec 동등성, dev=1/prod=2 및 Helm values 변경 확인 |
| GitHub Actions 직접 배포 | 공개 GHCR의 새 전체 SHA 이미지로 v1 → v2 자동 배포, build/deploy 성공, 새 Pod와 실제 응답 확인 |
| Argo CD GitOps | 비공개 Git 읽기 전용 인증, 첫 v2 Sync, v3 이미지 게시·Git 갱신·자동 동기화·응답 확인 |
| Public GHCR | 개인 자격 증명 없는 manifest 요청 HTTP 200, linux/amd64·linux/arm64 포함, Pod imagePullSecrets 없음 |
| 선택 심화 1 | replicas 변경과 Pod template 변경의 ReplicaSet 차이 관찰 후 원복 |
| 추가 관찰 | selfHeal 꺼짐/켜짐에 따른 live replicas 복원 비교 |

소스 저장소는 **Private**, GHCR 이미지 패키지는 **Public**입니다. 공개 전환 후 v1·v2·v3를 새 소스 SHA로 다시 빌드해 검증했습니다. `cicd-ci`와 `cicd-gitops`의 default ServiceAccount에 imagePullSecrets가 없고, 두 namespace에 Docker registry Secret도 없는 상태에서 수행했습니다. 아래 값은 이 최종 검증 결과입니다.

## 실습 환경

| 구성 | 실제 사용 버전/설정 |
|---|---|
| 클러스터 | kind `jiseok-netlab`, control-plane 1 + worker 2, 전용 kubeconfig |
| kind / node image | v0.33.0 / `kindest/node:v1.35.0` |
| Kubernetes 서버 / kubectl | v1.35.0 / v1.34.1 |
| 내장 Kustomize / Helm | v5.7.1 / v4.3.2 |
| Docker | Desktop 4.55.0, Engine 29.1.3, ARM64 |
| Argo CD | v3.6.2, 공식 버전 고정 설치 매니페스트 |
| Actions runner | hosted `ubuntu-latest` / 로컬 macOS ARM64 runner v2.338.2, `jiseok-k8s` 라벨 |
| Nginx | 과제 1·API 베이스 `nginx:alpine`, 심화 이미지 변경 `nginx:1.27-alpine` |

`nginx:alpine`은 가변 태그입니다. 본문은 실행 시점의 관찰이며, API 컨테이너의 실제 내용은 아래 imageID도 함께 기록했습니다. 이미지는 `linux/amd64,linux/arm64`로 빌드했고 이 클러스터에서는 ARM64 이미지를 실행했습니다.

## 과제 1. 세 가지 배포 도구

### 구성과 실행

공통 Deployment·Service에는 namespace를 고정하지 않았습니다. 세 방식 모두 `nginx:alpine`, Deployment 이름 `nginx`, 컨테이너 포트 80, Service 이름 `nginx`, ClusterIP, port/targetPort 80을 사용합니다.

```bash
kubectl -n cicd-plain apply -f deploy/plain/
kubectl -n cicd-kustomize apply -k deploy/kustomize/overlays/dev/
helm upgrade --install nginx deploy/helm/nginx -n cicd-helm
kubectl kustomize deploy/kustomize/overlays/dev/
kubectl kustomize deploy/kustomize/overlays/prod/
helm template nginx deploy/helm/nginx
helm template nginx deploy/helm/nginx --set replicaCount=2 --set image.tag=1.27-alpine
# namespace를 바꾸며 동일하게 확인
kubectl -n cicd-plain port-forward svc/nginx 18080:80
curl http://localhost:18080/
```

아래 결과는 실제 수집한 리소스와 HTTP 응답입니다. Argo CD 이미지 두 장은 수집한 JSON/응답을 렌더링한 기록이며 웹 UI 화면 캡처는 아닙니다.

- dev replicas=1, prod replicas=2. prod overlay를 실제 적용해 2개 Pod Ready까지 확인한 뒤 dev로 복구했습니다.
- Helm values의 `replicaCount`, `image.repository`, `image.tag`가 렌더링에 반영됩니다.
- 렌더링 결과를 비교해 기본 세 방식의 Deployment·Service spec이 동일함을 확인했습니다.


| namespace | HTTP | 응답 페이지 |
|---|---|---|
| `cicd-plain` | 200 | Welcome to nginx! |
| `cicd-kustomize` | 200 | Welcome to nginx! |
| `cicd-helm` | 200 | Welcome to nginx! |

### 비교

| 항목 | 일반 YAML | Kustomize | Helm |
|---|---|---|---|
| 공통 설정 재사용 | 같은 파일을 공용으로 적용. 차이가 많아지면 중복 발생 | base를 참조하고 변경분만 overlay에 선언 | templates에 values를 넣어 리소스 생성 |
| dev/prod 분리 | 별도 파일을 관리하거나 생성 도구 필요 | overlays/dev, overlays/prod | 환경별 values 파일 또는 --set |
| 이미지·replicas 위치 | Deployment spec | replicas/images 또는 patch | values.yaml |
| 장점 | 작은 구성의 최종 상태를 직접 읽기 쉽다 | 일반 YAML을 유지하며 환경 차이를 관리 | 배포 패키지와 릴리스 단위의 변경 관리 |
| 불편한 점 | 환경이 늘면 같은 변경을 반복 | 복잡한 patch 대상이나 overlay 구조를 추적해야 한다 | 템플릿과 values를 함께 읽고 렌더링 결과를 확인해야 한다 |
| 선택할 상황 | 단일 환경·작은 실습 | 팀 내부 앱의 환경별 설정 차이 | 여러 사용자에게 배포할 패키지·외부 앱 설치 |

이 Chart는 비교를 위해 이름/label을 최소화했습니다. Kustomize나 Helm이 모든 경우에 자동으로 특정 label을 추가한다고 가정하지 않았습니다. Helm 설치 시 릴리스 소유권 metadata는 추가될 수 있지만, 원하는 동작은 리소스의 spec이 결정합니다. YAML을 만들고 관리하는 도구와 Deployment controller의 역할을 구분해야 합니다.

## 과제 2. GitHub Actions·GHCR·Kubernetes 직접 배포

```mermaid
flowchart LR
  Source[개발자 main push] --> Build[GitHub hosted runner: multi-platform build]
  Build --> Registry[GHCR: 전체 소스 SHA 태그]
  Build -->|image job output| Runner[개인 macOS self-hosted runner]
  Runner -->|kubectl / 전용 kubeconfig| API[kind API / cicd-ci]
  Registry -->|노드가 pull| Pod[Nginx API Pod]
  API --> Pod
```

GitHub-hosted runner에서 로컬 kind API로 바로 접근할 수 없어 build/deploy job을 분리했습니다. 배포 job은 `kind-jiseok-netlab` context를 명시합니다. 개인 비공개 저장소의 main push에만 연결했으며 외부 PR 실행은 구성하지 않았습니다. 클러스터 API를 인터넷에 노출하지 않았습니다.

`build.outputs.image`를 deploy job에 전달합니다. `kubectl set image --local`로 이번 SHA를 manifest에 반영한 다음 apply합니다. `rollout status` 뒤에는 실제 `/api/hello`도 확인합니다. Service는 `80 → 8080`, readinessProbe는 `/healthz:8080`입니다.

### v1과 v2 실측

v2는 `app/nginx.conf`의 응답 버전을 바꾼 source push로 진행했습니다. CI 배포 리소스를 수동으로 수정하거나 수동 배포 명령을 실행하지 않았습니다. 앱의 동작 변경은 version 값뿐입니다.

- **v1**: 소스 `e0ec1aa1422384646872a3888622d20f16535be8` / [Actions build·deploy 성공](https://github.com/dev-jiseok/kubernetes-study-lab/actions/runs/44512969147)
- **v2**: 소스 `5720d8bf031ab767cc7c38024209ea122debbd3a` / [Actions build·deploy 성공](https://github.com/dev-jiseok/kubernetes-study-lab/actions/runs/44513140814)

전체 이미지 참조와 Pod imageID는 아래 표에서 별도로 확인할 수 있습니다. SHA 태그는 소스 추적에 유용하지만 덮어쓸 수 있습니다. 내용 자체를 고정하려면 digest 참조를 사용합니다. 멀티 플랫폼 이미지의 상위 index digest와 ARM64 개별 manifest digest는 서로 다른 객체를 가리킬 수 있어 imageID와 무조건 같다고 단정하면 안 됩니다.

## 과제 3. Argo CD와 GitOps

Argo CD v3.6.2를 설치하고, 개인 비공개 Git 저장소에 한정된 **읽기 전용 deploy key**를 등록했습니다. 개인키는 저장소 밖에서 관리하고 Argo CD repository Secret으로만 전달했습니다. Git 읽기 인증과 GHCR 이미지 pull 인증은 별개입니다.

Application은 `main`의 `deploy/gitops`를 읽고 `cicd-gitops`에 적용합니다. 공개 이미지 재검증의 첫 단계에서 v2 응답과 Synced/Healthy를 확인한 뒤 CI를 GitOps 방식으로 전환했습니다. 아래 첫 동기화 기록은 공개 이미지 기준으로 다시 진행한 결과입니다.

![Argo CD 첫 동기화 기록](../../img/week3/이지석/argocd-initial.png)

```mermaid
flowchart LR
  A[소스 commit A] --> Build[Actions: build / GHCR push]
  Build --> Image[nginx-api:A SHA]
  Build --> Update[update-manifest / contents: write]
  Update --> B[설정 commit B / image = A SHA]
  B -->|Argo CD가 Git을 읽음| Argo[자동 Sync / 상태 조정]
  Argo --> Cluster[kind / cicd-gitops]
  Image -->|노드가 pull| Cluster
```

최종 CI는 클러스터 명령 대신 Git의 image 한 줄을 바꿔 commit·push합니다. `app/**`와 `.github/workflows/ci.yml`만 push 트리거에 포함해 설정 commit이 다시 빌드되지 않게 했습니다. job 간 image output으로 전체 SHA를 전달하며, 새 소스가 이미 들어왔다면 오래된 실행이 최신 앱 변경을 덮어쓰지 않도록 source diff를 검사합니다.

### v3 자동 배포

- 소스 commit A: `5a3f260e5b7945c7290bfef48d7f4ad40f657d9b`
- 설정 commit B: `17d19c122ea737e454aba043119dfce329fbfee9`
- [Actions build/update-manifest](https://github.com/dev-jiseok/kubernetes-study-lab/actions/runs/44513783761)
- Argo CD: `Synced / Healthy`
- 실제 `/api/hello`: `{"message":"hello from nginx","version":"v3"}`

v3 push 이후 수동 Sync나 kubectl 이미지 변경 없이 자동 동기화 타임라인을 수집했습니다. Argo CD의 revision은 설정 commit B이고, Pod 이미지 태그는 소스 commit A입니다.

![Argo CD v3 자동 배포 기록](../../img/week3/이지석/argocd-v3.png)

### GitOps 질문 7개

1. **선언적 상태:** Git에 이미지 주소, replicas=1, Service 80/8080 같은 원하는 결과 상태를 저장합니다. controller가 실제 리소스를 그 값에 맞춥니다.
2. **버전과 변경 이력:** 소스 commit과 봇의 manifest commit을 연결해 어느 이미지가 배포됐는지 추적합니다. 이번 개인 실습은 main 직접 갱신이며 리뷰 승인 절차는 구성하지 않았습니다. 운영 환경에서 보호 브랜치·PR 리뷰를 추가하면 승인 이력을 남길 수 있습니다.
3. **Pull 방식:** Direct CI에서는 runner가 클러스터로 apply합니다. GitOps에서는 클러스터의 Argo CD가 Git을 읽습니다. 최종 build/update-manifest job에는 kubeconfig가 필요하지 않습니다. 공개 이미지이므로 별도의 이미지 인증 보조 job도 실행하지 않았습니다.
4. **상태 조정:** desired state는 Git, live state는 Kubernetes API에서 관찰한 리소스입니다. 차이를 비교해 OutOfSync를 표시하고 허용된 자동 동기화 정책으로 맞춥니다. polling이 있으므로 commit 직후 화면이 즉시 바뀌지 않을 수 있습니다.
5. **드리프트:** Git replicas=1에서 `kubectl scale`로 live replicas=3을 만들면 차이가 생깁니다. 자동 Sync는 새 Git 변경을 반영하고, selfHeal은 같은 Git revision 상태에서 발생한 live 변경도 복구하도록 합니다. 아래 실제 비교 실험에서는 Git commit을 추가하지 않았습니다.
6. **삭제와 복구:** prune은 Git에서 제거된 관리 대상 리소스를 클러스터에서도 삭제합니다. 잘못된 이미지 변경은 이전 참조로 Git을 revert하고 동기화해 복구합니다. 클러스터만 직접 되돌리면 다음 조정에서 Git 값으로 다시 바뀔 수 있습니다. prune 삭제 실험은 수행하지 않았습니다.
7. **CI와 CD:** CI는 이미지 빌드·게시와 Git의 이미지 참조 갱신, CD는 Argo CD의 동기화입니다. GHCR에 새 태그만 올려도 이 구성의 Argo CD가 자동으로 그 태그를 선택하지는 않습니다. image 참조 변경이 필요합니다.

### Synced와 Healthy는 별개

초기 인증 준비 순서 때문에 첫 GitOps Pod가 `ImagePullBackOff`가 됐을 때도 Application은 **Synced / Progressing**이었습니다. Git 선언을 적용했다는 것과 프로세스가 정상적으로 실행된다는 것은 다릅니다. 이 실패는 공개 전환 전 준비 과정에서 발생했습니다. 이후 GHCR을 Public으로 바꾸고 임시 인증을 제거한 뒤 새 v1·v2·v3 이미지를 검증했습니다. 본문에 제출한 최종 v3 결과는 수동 Sync 없이 자동 배포된 결과입니다.

## 선택 심화: Deployment controller가 보는 변경

예상: replicas만 바꾸면 기존 ReplicaSet의 Pod 수가 달라지고, Pod template의 image를 바꾸면 새 ReplicaSet이 생길 것으로 예상했습니다. 아래 명령으로 변경 전후를 관찰했고, 결과가 예상과 일치했습니다.

```bash
kubectl -n cicd-plain get deployment,rs,pods -o wide
kubectl -n cicd-plain scale deployment/nginx --replicas=2
kubectl -n cicd-plain get deployment,rs,pods -o wide
kubectl -n cicd-plain set image deployment/nginx nginx=nginx:1.27-alpine
kubectl -n cicd-plain rollout status deployment/nginx
kubectl -n cicd-plain get deployment,rs,pods -o wide
kubectl -n cicd-plain describe deployment nginx
kubectl -n cicd-plain rollout history deployment/nginx
kubectl -n cicd-plain apply -f deploy/plain/
```

| 관찰 | replicas=1에서 2 | image=nginx:alpine에서 nginx:1.27-alpine |
|---|---|---|
| 기존 ReplicaSet | `nginx-5878ccc46b`의 desired가 2로 증가 | 기존 desired가 0으로 감소 |
| 새 ReplicaSet | 생성되지 않음 | `nginx-b94d8cf4f` 생성 |
| 이유 | spec.replicas 변경 | spec.template 변경 |
| 복구 | 원본 plain YAML 재적용, replicas=1 | 원본 image=nginx:alpine으로 복구 |

배포 도구는 원하는 리소스를 만들고, 실제 ReplicaSet과 Pod의 조정은 Kubernetes controller가 수행합니다.

### selfHeal 추가 관찰

공개 이미지 재검증 이전에 수행한 별도 실험입니다. 자동 동기화는 유지하고 selfHeal만 끈 상태와 켠 상태를 비교했습니다. 이 실험 동안 Git revision은 동일하게 유지했습니다.

| 관찰 시각(UTC) | selfHeal | 실제 replicas | Sync / Health |
|---|---|---|---|
| 09:44:28 | false | 3 | OutOfSync / Healthy |
| 09:44:31 | true | 1 | Synced / Healthy |
| 09:44:33, 다시 3으로 변경 | true | 3 | OutOfSync / Healthy |
| 09:44:36 | true | 1 | Synced / Healthy |

## 문제와 해결

| 상황 | 원인과 해결 |
|---|---|
| 최초 Direct CI namespace 오류 | namespace를 배포보다 늦게 생성. 사전 생성 후 v1/v2 실행 성공 |
| GHCR 익명 pull 401 | 패키지가 Private. Public 변경 후 익명 manifest HTTP 200과 인증 Secret 없는 새 Pod 배포까지 재검증 |
| 초기 GitOps ImagePullBackOff | Git 인증과 이미지 pull 권한은 별개. Public 전환 후 두 namespace의 임시 registry Secret/참조를 제거하고 다시 검증 |
| GitOps 동기화 대기 | CI 완료와 Argo CD polling 시점이 다름. 수동 Sync 없이 Synced/Healthy 및 실제 응답까지 관찰 |

기본 과제의 미해결 항목은 없습니다. 실습 저장소와 Actions 로그는 비공개이므로 아래에 핵심 설정과 실제 결과를 함께 첨부합니다. 캡처 두 장은 **수집한 Kubernetes/Argo CD JSON과 HTTP 응답을 렌더링한 증빙**이며 Argo CD 웹 UI 화면은 아닙니다. 자격 증명은 포함하지 않았습니다. 선택 심화 2·3의 잘못된 이미지 태그 지정·Git revert 실험과 prune 삭제 실험은 수행 범위에 포함하지 않았습니다.

## 전체 버전 추적표

모든 이미지 태그는 전체 소스 SHA입니다. 각 행의 Deployment image와 Pod image는 동일하며, 아래 펼침 영역에 전체 값과 digest를 기록했습니다.

| 단계 | 소스 SHA (앞 12자리) | 실행 Pod | HTTP 응답 | GHCR 익명 요청 |
|---|---|---|---|---|
| Direct CI v1 | `e0ec1aa14223` | `nginx-api-9f59ff989-cqfpr` | 200 / v1 | 200 |
| Direct CI v2 | `5720d8bf031a` | `nginx-api-6db5cc5b94-l44r2` | 200 / v2 | 200 |
| GitOps 첫 동기화 v2 | `5720d8bf031a` | `nginx-api-6db5cc5b94-msqs2` | 200 / v2 | 200 |
| GitOps 자동 배포 v3 | `5a3f260e5b79` | `nginx-api-79674b5f94-9xcbg` | 200 / v3 | 200 |

<details>
<summary>Direct CI v1: 전체 이미지와 실행 증거</summary>

```text
Source SHA: e0ec1aa1422384646872a3888622d20f16535be8
Deployment image: ghcr.io/dev-jiseok/nginx-api:e0ec1aa1422384646872a3888622d20f16535be8
Pod: nginx-api-9f59ff989-cqfpr
Pod image: ghcr.io/dev-jiseok/nginx-api:e0ec1aa1422384646872a3888622d20f16535be8
Pod imageID: ghcr.io/dev-jiseok/nginx-api@sha256:cc9548e6c025a85a79b925e81869aba8a341541064d8980913a124c3b39c34a2
GHCR index digest: sha256:cc9548e6c025a85a79b925e81869aba8a341541064d8980913a124c3b39c34a2
GHCR anonymous manifest HTTP: 200
Pod imagePullSecrets: []
HTTP 200: {"message":"hello from nginx","version":"v1"}
```

</details>

<details>
<summary>Direct CI v2: 전체 이미지와 실행 증거</summary>

```text
Source SHA: 5720d8bf031ab767cc7c38024209ea122debbd3a
Deployment image: ghcr.io/dev-jiseok/nginx-api:5720d8bf031ab767cc7c38024209ea122debbd3a
Pod: nginx-api-6db5cc5b94-l44r2
Pod image: ghcr.io/dev-jiseok/nginx-api:5720d8bf031ab767cc7c38024209ea122debbd3a
Pod imageID: ghcr.io/dev-jiseok/nginx-api@sha256:c926bdbf669b6629fe54f99b96106ada5fca2112dde5a804613343964bf31cb0
GHCR index digest: sha256:c926bdbf669b6629fe54f99b96106ada5fca2112dde5a804613343964bf31cb0
GHCR anonymous manifest HTTP: 200
Pod imagePullSecrets: []
HTTP 200: {"message":"hello from nginx","version":"v2"}
```

</details>

<details>
<summary>GitOps 첫 동기화 v2: 전체 이미지와 실행 증거</summary>

```text
Source SHA: 5720d8bf031ab767cc7c38024209ea122debbd3a
Deployment image: ghcr.io/dev-jiseok/nginx-api:5720d8bf031ab767cc7c38024209ea122debbd3a
Pod: nginx-api-6db5cc5b94-msqs2
Pod image: ghcr.io/dev-jiseok/nginx-api:5720d8bf031ab767cc7c38024209ea122debbd3a
Pod imageID: ghcr.io/dev-jiseok/nginx-api@sha256:c926bdbf669b6629fe54f99b96106ada5fca2112dde5a804613343964bf31cb0
GHCR index digest: sha256:c926bdbf669b6629fe54f99b96106ada5fca2112dde5a804613343964bf31cb0
GHCR anonymous manifest HTTP: 200
Pod imagePullSecrets: []
HTTP 200: {"message":"hello from nginx","version":"v2"}
Argo CD revision: 8fda02ca582bac8882aa78466f7025eafc101e62
Argo CD: Synced / Healthy
관찰 시각 (UTC): 2026-11-19T11:19:25Z
```

</details>

<details>
<summary>GitOps 자동 배포 v3: 전체 이미지와 실행 증거</summary>

```text
Source SHA: 5a3f260e5b7945c7290bfef48d7f4ad40f657d9b
Deployment image: ghcr.io/dev-jiseok/nginx-api:5a3f260e5b7945c7290bfef48d7f4ad40f657d9b
Pod: nginx-api-79674b5f94-9xcbg
Pod image: ghcr.io/dev-jiseok/nginx-api:5a3f260e5b7945c7290bfef48d7f4ad40f657d9b
Pod imageID: ghcr.io/dev-jiseok/nginx-api@sha256:8778b897081cb9a8fd2232601652cffa69103345ffb0358b6db8d4dbe56ebf56
GHCR index digest: sha256:8778b897081cb9a8fd2232601652cffa69103345ffb0358b6db8d4dbe56ebf56
GHCR anonymous manifest HTTP: 200
Pod imagePullSecrets: []
HTTP 200: {"message":"hello from nginx","version":"v3"}
Argo CD revision: 17d19c122ea737e454aba043119dfce329fbfee9
Argo CD: Synced / Healthy
관찰 시각 (UTC): 2026-11-19T11:23:55Z
```

</details>

## 워크플로와 배포 설정

비공개 실습 저장소의 핵심 설정을 이 문서에 첨부했습니다. 자격 증명은 제외했습니다. 발표 자료와 전체 로그는 제출 PR에서 분리해 보관합니다.

<details>
<summary>과제 2: 공개 GHCR 직접 배포 워크플로</summary>

```yaml
name: Build and deploy Nginx API
on:
  push:
    branches: [main]
    paths: ['app/**', '.github/workflows/ci.yml']
  workflow_dispatch:
permissions:
  contents: read
concurrency:
  group: nginx-api-main
  cancel-in-progress: false
jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    outputs:
      image: ${{ steps.image.outputs.image }}
    steps:
      - uses: actions/checkout@v4
      - id: image
        shell: bash
        run: echo "image=ghcr.io/${GITHUB_REPOSITORY_OWNER,,}/nginx-api:${GITHUB_SHA}" >> "$GITHUB_OUTPUT"
      - uses: docker/setup-qemu-action@v3
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v6
        with:
          context: app
          push: true
          platforms: linux/amd64,linux/arm64
          tags: ${{ steps.image.outputs.image }}
          labels: org.opencontainers.image.source=https://github.com/${{ github.repository }}
  deploy:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: [self-hosted, macOS, ARM64, jiseok-k8s]
    env:
      IMAGE: ${{ needs.build.outputs.image }}
      KUBE_CONTEXT: kind-jiseok-netlab
    steps:
      - uses: actions/checkout@v4
      - name: Deploy exact source SHA
        shell: bash
        run: |
          set -euo pipefail
          kubectl set image --local -f deploy/ci/deployment.yaml nginx="$IMAGE" -o yaml \
            | kubectl --context "$KUBE_CONTEXT" -n cicd-ci apply -f -
          kubectl --context "$KUBE_CONTEXT" -n cicd-ci apply -f deploy/ci/service.yaml
          kubectl --context "$KUBE_CONTEXT" -n cicd-ci rollout status deployment/nginx-api --timeout=180s
          kubectl --context "$KUBE_CONTEXT" -n cicd-ci get deployment nginx-api -o jsonpath='{.spec.template.spec.containers[0].image}'
          kubectl --context "$KUBE_CONTEXT" -n cicd-ci get pods -o wide
      - name: Verify live API response
        shell: bash
        run: |
          set -euo pipefail
          kubectl --context "$KUBE_CONTEXT" -n cicd-ci port-forward svc/nginx-api 19080:80 > "$RUNNER_TEMP/port-forward.log" 2>&1 &
          PF_PID=$!
          trap 'kill "$PF_PID"' EXIT
          curl --fail --retry 20 --retry-connrefused --retry-delay 1 http://127.0.0.1:19080/api/hello
```

</details>

<details>
<summary>과제 3: 최종 GitOps 워크플로</summary>

```yaml
name: Build and deploy Nginx API
on:
  push:
    branches: [main]
    paths: ['app/**', '.github/workflows/ci.yml']
  workflow_dispatch:
permissions:
  contents: read
concurrency:
  group: nginx-api-main
  cancel-in-progress: false
jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    outputs:
      image: ${{ steps.image.outputs.image }}
    steps:
      - uses: actions/checkout@v4
      - id: image
        shell: bash
        run: echo "image=ghcr.io/${GITHUB_REPOSITORY_OWNER,,}/nginx-api:${GITHUB_SHA}" >> "$GITHUB_OUTPUT"
      - uses: docker/setup-qemu-action@v3
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v6
        with:
          context: app
          push: true
          platforms: linux/amd64,linux/arm64
          tags: ${{ steps.image.outputs.image }}
          labels: org.opencontainers.image.source=https://github.com/${{ github.repository }}
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
          fetch-depth: 0
      - name: Update desired state in Git
        shell: bash
        run: |
          set -euo pipefail
          # Refuse to publish an older application over a newer source push.
          git diff --quiet "$SOURCE_SHA" HEAD -- app/ .github/workflows/ci.yml
          python3 - <<'PYTHON'
          import os, re
          from pathlib import Path
          p = Path('deploy/gitops/deployment.yaml')
          text, count = re.subn(r'(?m)^(\s*image:) .+$', lambda m: m[1] + ' ' + os.environ['IMAGE'], p.read_text())
          assert count == 1, 'Expected one API image reference'
          p.write_text(text)
          PYTHON
          git config user.name 'github-actions[bot]'
          git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
          git add deploy/gitops/deployment.yaml
          if git diff --cached --quiet; then exit 0; fi
          git commit -m "deploy: nginx-api ${SOURCE_SHA}"
          git push origin HEAD:main
```

</details>

<details>
<summary>Argo CD Application</summary>

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: nginx-api
  namespace: argocd
spec:
  project: default
  source:
    repoURL: git@github.com:dev-jiseok/kubernetes-study-lab.git
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

</details>

<details>
<summary>GitOps Deployment</summary>

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-api
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nginx-api
  template:
    metadata:
      labels:
        app: nginx-api
    spec:
      containers:
        - name: nginx
          image: ghcr.io/dev-jiseok/nginx-api:5a3f260e5b7945c7290bfef48d7f4ad40f657d9b
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: 10m
              memory: 16Mi
            limits:
              memory: 64Mi
          readinessProbe:
            httpGet:
              path: /healthz
              port: 8080
            initialDelaySeconds: 2
            periodSeconds: 2
```

</details>

<details>
<summary>API Service</summary>

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-api
spec:
  type: ClusterIP
  selector:
    app: nginx-api
  ports:
    - port: 80
      targetPort: 8080
```

</details>

<details>
<summary>과제 1: 일반 YAML·Kustomize·Helm 설정</summary>

일반 YAML은 아래 두 리소스이며 Kustomize base에서도 같은 파일을 참조합니다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
        - name: nginx
          image: nginx:alpine
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: 10m
              memory: 16Mi
            limits:
              memory: 64Mi
---
apiVersion: v1
kind: Service
metadata:
  name: nginx
spec:
  type: ClusterIP
  selector:
    app: nginx
  ports:
    - port: 80
      targetPort: 80
```

```yaml
# deploy/kustomize/base/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - deployment.yaml
  - service.yaml

# deploy/kustomize/overlays/dev/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
replicas:
  - name: nginx
    count: 1

# deploy/kustomize/overlays/prod/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
replicas:
  - name: nginx
    count: 2

```

Helm `values.yaml`:

```yaml
replicaCount: 1
image:
  repository: nginx
  tag: alpine
```

Helm Deployment는 일반 YAML의 replicas를 `{{ .Values.replicaCount }}`, image를 `"{{ .Values.image.repository }}:{{ .Values.image.tag }}"`로 렌더링합니다. Service의 spec은 일반 YAML과 같습니다.

</details>

<details>
<summary>API 소스와 직접 배포 manifest의 관계</summary>

`deploy/ci/deployment.yaml`은 위 GitOps Deployment와 같은 spec이며 image의 초기값만 `ghcr.io/dev-jiseok/nginx-api:bootstrap`입니다. workflow가 apply 전에 `kubectl set image --local`로 전체 SHA를 넣으므로 bootstrap 태그는 배포하지 않습니다. Service는 두 namespace에서 동일합니다.

`app/Dockerfile` (최종 v3):

```dockerfile
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
```

`app/nginx.conf` (최종 v3):

```nginx
server {
    listen 8080;
    server_name _;
    default_type application/json;
    location = /healthz { return 200 '{"status":"ok"}\n'; }
    location = /api/hello { return 200 '{"message":"hello from nginx","version":"v3"}\n'; }
    location / { return 404 '{"error":"not found"}\n'; }
}
```

</details>

## 공식 참고 자료

- [Kustomize](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/)
- [Helm Chart](https://helm.sh/docs/chart_template_guide/getting_started/)
- [GitHub Actions 이미지 게시](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images)
- [GHCR](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [GITHUB_TOKEN 수명](https://docs.github.com/en/actions/concepts/security/github_token)
- [Argo CD 비공개 저장소](https://argo-cd.readthedocs.io/en/stable/user-guide/private-repositories/)
- [Argo CD 자동 동기화·selfHeal·prune](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)
- [Deployment rollout](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#updating-a-deployment)
- [컨테이너 이미지와 digest](https://kubernetes.io/docs/concepts/containers/images/)
