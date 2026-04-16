#!/bin/bash
set -e

# ArgoCD Installation Script
# Version: 6.7.3 (ArgoCD v2.10.3)
# Date: 2026-04-06

ARGOCD_VERSION="6.7.3"
NAMESPACE="argocd"
RELEASE_NAME="argocd"

echo "=== Installing ArgoCD ${ARGOCD_VERSION} ==="

# Add Helm repo
echo "Adding ArgoCD Helm repository..."
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update

# Create namespace
echo "Creating namespace ${NAMESPACE}..."
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# Install ArgoCD
echo "Installing ArgoCD with Helm..."
helm upgrade --install ${RELEASE_NAME} argo/argo-cd \
  --namespace ${NAMESPACE} \
  --version ${ARGOCD_VERSION} \
  --values values.yaml \
  --wait

# Wait for pods to be ready
echo "Waiting for ArgoCD pods to be ready..."
kubectl wait --for=condition=Ready pod \
  -l app.kubernetes.io/name=argocd-server \
  -n ${NAMESPACE} \
  --timeout=300s

# Get initial admin password
echo ""
echo "=== ArgoCD Installation Complete ==="
echo ""
echo "Access Information:"
echo "  Namespace: ${NAMESPACE}"
echo "  Release: ${RELEASE_NAME}"
echo "  Version: ${ARGOCD_VERSION}"
echo ""
echo "NodePort Access:"
kubectl get svc -n ${NAMESPACE} ${RELEASE_NAME}-server -o jsonpath='{.spec.type}{"\n"}'
echo "  HTTP:  http://<node-ip>:$(kubectl get svc -n ${NAMESPACE} ${RELEASE_NAME}-server -o jsonpath='{.spec.ports[?(@.name=="http")].nodePort}')"
echo "  HTTPS: https://<node-ip>:$(kubectl get svc -n ${NAMESPACE} ${RELEASE_NAME}-server -o jsonpath='{.spec.ports[?(@.name=="https")].nodePort}')"
echo ""
echo "Initial Admin Password:"
kubectl -n ${NAMESPACE} get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
echo ""
echo ""
echo "Login:"
echo "  Username: admin"
echo "  Password: (see above)"
echo ""
echo "To change password:"
echo "  argocd account update-password"
echo ""
