#!/usr/bin/env bash
# 推送到多 remote：
#   github → main；gitee → master（本地通常仍叫 main）
#   公开仓不含 ali_mcp_credential.py
#   gitlab → 额外 force-add 该私有文件后再推（供内网构建）
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
GITEE_BRANCH="master"
GITHUB_BRANCH="main"
GITLAB_BRANCH="main"
MODE="all"

for arg in "$@"; do
  case "${arg}" in
    --public) MODE="public" ;;
    --gitlab) MODE="gitlab" ;;
    -h|--help)
      sed -n '2,14p' "$0"
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
  echo "==> git push gitee ${BRANCH}:${GITEE_BRANCH}"
  git push gitee "${BRANCH}:${GITEE_BRANCH}"
  echo "==> git push github ${BRANCH}:${GITHUB_BRANCH}"
  git push github "${BRANCH}:${GITHUB_BRANCH}"
}

push_gitlab_with_private() {
  if [[ ! -f "${PRIVATE_FILE}" ]]; then
    echo "==> 缺少 ${PRIVATE_FILE}，gitlab 仅推当前提交" >&2
    git push gitlab "${BRANCH}:${GITLAB_BRANCH}"
    return 0
  fi

  echo "==> gitlab：临时纳入 ${PRIVATE_FILE} 后推送 ${BRANCH}:${GITLAB_BRANCH}"
  local before private_bak
  before="$(git rev-parse HEAD)"
  private_bak="$(mktemp)"
  cp "${PRIVATE_FILE}" "${private_bak}"

  git add -f "${PRIVATE_FILE}"
  if git diff --cached --quiet; then
    echo "（工作树与 index 无新私有改动，仍确保 tip 含该文件后推送）"
  else
    git commit -m "$(cat <<'EOF'
internal: include ali_mcp_credential.py for GitLab builds

EOF
)"
  fi

  # main 受保护时禁止 force；先 fetch+merge 再普通推送
  git fetch gitlab "${GITLAB_BRANCH}"
  git merge -m "merge gitlab/${GITLAB_BRANCH} before publishing private credential module" \
    "FETCH_HEAD" || {
    echo "gitlab merge 冲突，请手动处理后再推" >&2
    git merge --abort 2>/dev/null || true
    git reset --hard "${before}"
    cp "${private_bak}" "${PRIVATE_FILE}"
    rm -f "${private_bak}"
    return 1
  }
  git push gitlab "HEAD:${GITLAB_BRANCH}"

  git reset --hard "${before}"
  cp "${private_bak}" "${PRIVATE_FILE}"
  rm -f "${private_bak}"
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
