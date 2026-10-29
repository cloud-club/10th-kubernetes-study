# 1주차 과제: 로컬 Kubernetes 설치와 nginx 실행

## 과제 목표

로컬 환경에 Kubernetes 클러스터를 준비하고, 클러스터에서 nginx Pod를 실행해 봅니다.

## 할 일

1. [kind](https://kind.sigs.k8s.io/) 또는 Docker Desktop Kubernetes 중 하나로 로컬 클러스터를 설치합니다.
2. 클러스터가 준비됐는지 확인합니다.

   ```bash
   kubectl cluster-info
   kubectl get nodes
   ```

3. 이 저장소의 [`nginx-pod.yaml`](./nginx-pod.yaml)을 적용합니다.

   ```bash
   kubectl apply -f nginx-pod.yaml
   kubectl get pods -w
   ```

4. Pod 상태와 설정을 확인합니다.

   ```bash
   kubectl get pods
   kubectl describe pod nginx
   ```

## 제출물

- 클러스터가 준비된 것을 확인할 수 있는 터미널 화면 캡처 (`kubectl get nodes` 결과 포함)
- nginx가 실행 중인 화면 캡처 (`kubectl get pods` 결과 포함)
- 사용한 클러스터 종류(kind 또는 Docker Desktop)와 실행 중 막혔던 점이 있다면 간단한 설명

이번 과제에서는 nginx Pod가 클러스터 안에서 실행되는 것까지 확인합니다. 브라우저 접속이나 외부 공개는 다루지 않으며, Service와 Ingress 등 네트워크 주제에서 이어서 실습합니다.
