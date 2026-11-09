#!/usr/bin/env bash
# 推送到多 remote：
#   gitee / github — 正常推送（不含 ali_mcp_credential.py）
#   gitlab         — 额外 force-add 该私有文件后再推（供内网构建）
#
# 用法：
#   ./scripts/push_remotes.sh              # 推当前分支到 gitee、github、gitlab
#   ./scripts/push_remotes.sh --public     # 仅 gitee + github
#   ./scripts/push_remotes.sh --gitlab     # 仅 gitlab（带私有文件）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

BRANCH="$(git branch --show-current)"
PRIVATE_FILE="mcp/src/ali_mcp_credential.py"
MODE="all"

for arg in "$@"; do
  case "${arg}" in
    --public) MODE="public" ;;
    --gitlab) MODE="gitlab" ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
    *)
      echo "未知参数: ${arg}" >&2
      exit 1
      ;;
  esac
done

if [[ -z "${BRANCH}" ]]; then
  echo "无法解析当前分支" >&2
  exit 1
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "工作区有未提交改动，请先 commit 再推送。" >&2
  exit 1
fi

push_public() {
  echo "==> git push gitee ${BRANCH}"
  git push gitee "${BRANCH}"
  echo "==> git push github ${BRANCH}"
  git push github "${BRANCH}"
}

push_gitlab_with_private() {
  if [[ ! -f "${PRIVATE_FILE}" ]]; then
    echo "==> 缺少 ${PRIVATE_FILE}，gitlab 仅推当前提交" >&2
    git push gitlab "${BRANCH}"
    return 0
  fi

  echo "==> gitlab：临时纳入 ${PRIVATE_FILE} 后推送"
  local before
  before="$(git rev-parse HEAD)"
  git add -f "${PRIVATE_FILE}"
  if git diff --cached --quiet; then
    echo "（私有文件相对 HEAD 无变化，直接推送）"
    git push gitlab "${BRANCH}"
    return 0
  fi

  git commit -m "$(cat <<'EOF'
internal: include ali_mcp_credential.py for GitLab builds

EOF
)"
  # 内网仓允许 --force-with-lease：gitlab tip 常比公开仓多这一笔私有提交
  git push --force-with-lease gitlab "${BRANCH}"

  git reset --soft "${before}"
  git restore --staged "${PRIVATE_FILE}"
  echo "==> 本地已恢复为公开 tip（${before:0:7}），工作区保留 ${PRIVATE_FILE}"
}

case "${MODE}" in
  public)
    push_public
    ;;
  gitlab)
    push_gitlab_with_private
    ;;
  all)
    push_public
    push_gitlab_with_private
    ;;
esac

echo "完成（branch=${BRANCH}, mode=${MODE}）"
