#!/usr/bin/env python3
"""将本仓库 skills 同步到 Hermes shared/skills。

默认：同步目标目录里已有、且本仓库能解析到源的 skill，并始终带上 system 系列
（即使目标里还没有）。可用 --skills 显式指定名称，或用分类名批量同步。

注意：Hermes 容器内 /shared/skills 不是宿主机目录的实时挂载，
docker_start.sh / docker_install.sh 通过 docker cp 灌入。
仅同步宿主机 shared/skills 不会更新正在运行的容器；
需要 --docker-cp（或重新执行 docker_start）才会进容器。

示例：
  python3 scripts/sync_hermes_skills.py
  python3 scripts/sync_hermes_skills.py --skills gangtise-data,gangtise-file
  python3 scripts/sync_hermes_skills.py --skills research
  python3 scripts/sync_hermes_skills.py --skills openapi,system --dry-run
  python3 scripts/sync_hermes_skills.py --skills openapi --docker-cp
  python3 scripts/sync_hermes_skills.py --dest /path/to/skills
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set

ROOT = Path(__file__).resolve().parent.parent
SKILLS_ROOT = ROOT / "skills"
DEFAULT_DEST = Path.home() / ".hermes/docker-utils/shared/skills"

# 解析同名 skill 时的优先级（一般不会撞名）
CATEGORIES: Sequence[str] = ("openapi", "system", "tools", "research", "others")

# 未指定 --skills 时，除目标已有目录外，始终同步这些分类（即使目标里还没有）
ALWAYS_SYNC_CATEGORIES: Sequence[str] = ("system",)

IGNORE_NAMES = {
    "__pycache__",
    ".venv",
    "node_modules",
    ".git",
    "_core",
    ".DS_Store",
}
IGNORE_SUFFIXES = (".pyc", ".authorization")
IGNORE_FILES = {".env", "infos.json"}


def _ignore(dirpath: str, names: List[str]) -> Set[str]:
    skipped: Set[str] = set()
    for name in names:
        if name in IGNORE_NAMES or name in IGNORE_FILES:
            skipped.add(name)
            continue
        if name.endswith(IGNORE_SUFFIXES):
            skipped.add(name)
    return skipped


def list_category_skills(category: str) -> List[str]:
    base = SKILLS_ROOT / category
    if not base.is_dir():
        return []
    return sorted(p.name for p in base.iterdir() if p.is_dir() and not p.name.startswith("."))


def build_source_index() -> Dict[str, Path]:
    """skill 名 → 源目录（按 CATEGORIES 优先）。"""
    index: Dict[str, Path] = {}
    for cat in CATEGORIES:
        for name in list_category_skills(cat):
            index.setdefault(name, SKILLS_ROOT / cat / name)
    return index


def list_dest_skills(dest: Path) -> List[str]:
    if not dest.is_dir():
        return []
    return sorted(p.name for p in dest.iterdir() if p.is_dir() and not p.name.startswith("."))


def parse_skills_arg(raw: Optional[str]) -> List[str]:
    if not raw or not raw.strip():
        return []
    parts: List[str] = []
    for chunk in raw.replace(",", " ").split():
        name = chunk.strip()
        if name:
            parts.append(name)
    return parts


def expand_skill_selectors(selectors: Iterable[str], index: Dict[str, Path]) -> List[str]:
    """名称或分类 → 去重后的 skill 名列表（保持选择顺序）。"""
    out: List[str] = []
    seen: Set[str] = set()
    for sel in selectors:
        if sel in CATEGORIES:
            for name in list_category_skills(sel):
                if name not in seen:
                    seen.add(name)
                    out.append(name)
            continue
        if sel not in index:
            raise SystemExit(
                f"未知 skill「{sel}」：不在本仓库 skills/{{{','.join(CATEGORIES)}}} 下，"
                f"也不是分类名。"
            )
        if sel not in seen:
            seen.add(sel)
            out.append(sel)
    return out


def sync_one(src: Path, dest_skill: Path, *, dry_run: bool) -> None:
    if dry_run:
        print(f"  DRY  {src.relative_to(ROOT)}  →  {dest_skill}")
        return
    if dest_skill.exists():
        shutil.rmtree(dest_skill)
    shutil.copytree(src, dest_skill, ignore=_ignore)
    print(f"  OK   {src.relative_to(ROOT)}  →  {dest_skill}")


def docker_cp_skills(
    dest: Path,
    names: Sequence[str],
    *,
    container: str,
    dry_run: bool,
) -> None:
    """把宿主机 dest 下的 skill 灌进容器 /shared/skills（与 docker_start.sh 一致）。"""
    if dry_run:
        for name in names:
            print(f"  DRY  docker cp {dest / name}/.  {container}:/shared/skills/{name}/")
        return
    # 确认容器在跑
    probe = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", container],
        capture_output=True,
        text=True,
    )
    if probe.returncode != 0 or probe.stdout.strip() != "true":
        raise SystemExit(f"容器「{container}」未运行，无法 --docker-cp")

    for name in names:
        src = dest / name
        if not src.is_dir():
            print(f"  SKIP docker cp：宿主机无目录 {src}")
            continue
        subprocess.run(
            ["docker", "exec", "-u", "root", container, "mkdir", "-p", f"/shared/skills/{name}"],
            check=True,
        )
        subprocess.run(
            ["docker", "cp", f"{src}/.", f"{container}:/shared/skills/{name}/"],
            check=True,
        )
        print(f"  OK   docker cp → {container}:/shared/skills/{name}/")
    subprocess.run(
        ["docker", "exec", "-u", "root", container, "chmod", "-R", "a+rX", "/shared/skills"],
        check=True,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="同步本仓库 skills 到 Hermes shared/skills",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=DEFAULT_DEST,
        help=f"目标 skills 目录（默认 {DEFAULT_DEST}）",
    )
    parser.add_argument(
        "--skills",
        default="",
        help=(
            "要同步的 skill 名或分类名，逗号/空格分隔。"
            f"分类：{', '.join(CATEGORIES)}。"
            "省略则同步目标目录已有且仓库有源的 skill，"
            f"并始终带上 {', '.join(ALWAYS_SYNC_CATEGORIES)}。"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印将要同步的映射，不写盘",
    )
    parser.add_argument(
        "--docker-cp",
        action="store_true",
        help="同步宿主机后，再 docker cp 进运行中的 Hermes 容器 /shared/skills",
    )
    parser.add_argument(
        "--container",
        default="hermes",
        help="--docker-cp 目标容器名（默认 hermes）",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    dest: Path = args.dest.expanduser().resolve()
    index = build_source_index()
    selectors = parse_skills_arg(args.skills)

    if selectors:
        names = expand_skill_selectors(selectors, index)
    else:
        if not dest.is_dir():
            raise SystemExit(f"目标目录不存在：{dest}（默认模式需要已有 skills 目录）")
        names = [n for n in list_dest_skills(dest) if n in index]
        missing = [n for n in list_dest_skills(dest) if n not in index]
        if missing:
            print(f"跳过目标中无仓库源的目录：{', '.join(missing)}")
        # system 等 ALWAYS_SYNC_CATEGORIES：目标里没有也要同步进去
        seen = set(names)
        for cat in ALWAYS_SYNC_CATEGORIES:
            for name in list_category_skills(cat):
                if name in index and name not in seen:
                    seen.add(name)
                    names.append(name)

    if not names:
        print("没有需要同步的 skill。")
        return 0

    if not args.dry_run:
        dest.mkdir(parents=True, exist_ok=True)

    print(f"同步 {len(names)} 个 skill → {dest}" + (" (dry-run)" if args.dry_run else ""))
    for name in names:
        sync_one(index[name], dest / name, dry_run=args.dry_run)

    if args.docker_cp:
        print(f"docker cp → 容器 {args.container}:/shared/skills" + (" (dry-run)" if args.dry_run else ""))
        docker_cp_skills(dest, names, container=args.container, dry_run=args.dry_run)

    print("完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
