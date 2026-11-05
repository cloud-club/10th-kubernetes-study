# W1 Assaignment: 로컬 Kubernetes 설치와 nginx 실행

## 환경
- 클러스터: kind
- 컨테이너 런타임: Docker desktop

## 클러스터 확인

![노드 Ready 상태](assaignment/week1/week1_ybhan_img/week1-ybhan-nodes)

## nginx Pod 실행

![nginx Pod Running 상태](assaignment/week1/week1_ybhan_img/week1-ybhan-nginx)

## 막힌 부분

kubectl get nodes가 클러스터에 연결되어 별도 kubeconfig 파일을 가리키도록 KUBECONFIG 환경 변수 사용했습니다. 이외에는 1주차 과제 흐름 쭉 따라갔습니다.