#!/usr/bin/env bash
# 현재 구독·리소스 그룹의 전체 인벤토리 스냅샷 — Bicep 역공학 + cutover 후 회귀 비교용.
# 출력: backups/azure-snapshot/<timestamp>/
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RG="${RESOURCE_GROUP:-rg-ejp-9638}"
SUB="$(az account show --query id -o tsv)"
TS="$(date +%Y%m%d-%H%M%S)"
OUT_DIR="$REPO_ROOT/backups/azure-snapshot/$TS"
mkdir -p "$OUT_DIR"

echo "subscription: $SUB"
echo "resource group: $RG"
echo "output: $OUT_DIR"

echo "[1/6] 리소스 목록"
az resource list -g "$RG" -o json > "$OUT_DIR/resources.json"
az resource list -g "$RG" --query "[].{name:name,type:type,location:location,sku:sku.name}" -o table > "$OUT_DIR/resources.txt"

echo "[2/6] role assignments (RBAC)"
az role assignment list --resource-group "$RG" --include-inherited -o json > "$OUT_DIR/role_assignments.json"

echo "[3/6] Container App 상세"
if az containerapp list -g "$RG" --query "[0].name" -o tsv 2>/dev/null | grep -q .; then
  for app in $(az containerapp list -g "$RG" --query "[].name" -o tsv); do
    az containerapp show -g "$RG" --name "$app" -o json > "$OUT_DIR/containerapp_${app}.json"
    # env vars (이름만, 값은 secret 마스킹)
    az containerapp show -g "$RG" --name "$app" \
      --query "properties.template.containers[0].env[].{name:name, hasValue:value!=null, secretRef:secretRef}" \
      -o table > "$OUT_DIR/containerapp_${app}_envvars.txt"
  done
fi

echo "[4/6] Cosmos 계정·컨테이너"
for acct in $(az cosmosdb list -g "$RG" --query "[].name" -o tsv 2>/dev/null); do
  az cosmosdb show -g "$RG" --name "$acct" -o json > "$OUT_DIR/cosmos_${acct}.json"
  for db in $(az cosmosdb sql database list -g "$RG" --account-name "$acct" --query "[].name" -o tsv); do
    az cosmosdb sql container list -g "$RG" --account-name "$acct" --database-name "$db" -o json \
      > "$OUT_DIR/cosmos_${acct}_${db}_containers.json"
  done
done

echo "[5/6] AI Search service"
for svc in $(az search service list -g "$RG" --query "[].name" -o tsv 2>/dev/null); do
  az search service show -g "$RG" --name "$svc" -o json > "$OUT_DIR/search_${svc}.json"
done

echo "[6/6] Storage account"
for sa in $(az storage account list -g "$RG" --query "[].name" -o tsv 2>/dev/null); do
  az storage account show -g "$RG" --name "$sa" -o json > "$OUT_DIR/storage_${sa}.json"
done

echo
echo "✓ 스냅샷 완료: $OUT_DIR"
ls -la "$OUT_DIR"
