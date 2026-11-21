#!/usr/bin/env bash
# Deploy to an explicitly selected disposable teaching cluster.
set -euo pipefail
image=${1:?Usage: deploy_k8s.sh IMAGE SOURCE_COMMIT}
source_commit=${2:?Full source commit required}
: "${KUBE_CONTEXT:?Set KUBE_CONTEXT to the teaching cluster context}"
namespace=${KUBE_NAMESPACE:-mlops-team3}
if [[ ! "$source_commit" =~ ^[0-9a-f]{40}$ ]]; then
  echo "SOURCE_COMMIT must be a full Git SHA" >&2
  exit 2
fi
if [[ "$namespace" != mlops-team3* ]]; then
  echo "This teaching script only manages mlops-team3 namespaces" >&2
  exit 2
fi
k=(kubectl --context "$KUBE_CONTEXT" --namespace "$namespace")
kubectl --context "$KUBE_CONTEXT" create namespace "$namespace" --dry-run=client -o yaml \
  | kubectl --context "$KUBE_CONTEXT" apply -f -
kubectl set image --local -f k8s/deployment.yaml "api=$image" -o yaml \
  | kubectl set env --local -f - "SOURCE_COMMIT=$source_commit" "MODEL_VERSION=0.2.0" -o yaml \
  | "${k[@]}" apply -f -
"${k[@]}" apply -f k8s/service.yaml -f k8s/hpa.yaml -f k8s/pdb.yaml
# Production baseline remains 500m in deployment.yaml. The 2-CPU teaching node
# needs smaller requests so a manual scale to three and an HPA drill can fit.
"${k[@]}" set resources deployment/flight-delay-api \
  --requests=cpu=100m,memory=128Mi --limits=cpu=750m,memory=384Mi
"${k[@]}" rollout status deployment/flight-delay-api --timeout=240s
"${k[@]}" get deployment,pods,service,hpa,pdb
