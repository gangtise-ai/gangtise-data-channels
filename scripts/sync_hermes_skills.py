#!/usr/bin/env python3
"""将本仓库 skills 同步到 Hermes shared/skills。

默认：只同步目标目录里已有、且本仓库能解析到源的 skill。
可用 --skills 显式指定名称，或用分类名批量同步（含 research）。

示例：
  python3 scripts/sync_hermes_skills.py
  python3 scripts/sync_hermes_skills.py --skills gangtise-data,gangtise-file
  python3 scripts/sync_hermes_skills.py --skills research
  python3 scripts/sync_hermes_skills.py --skills openapi,system --dry-run
  python3 scripts/sync_hermes_skills.py --dest /path/to/skills
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set

ROOT = Path(__file__).resolve().parent.parent
SKILLS_ROOT = ROOT / "skills"
DEFAULT_DEST = Path.home() / ".hermes/docker-utils/shared/skills"

# 解析同名 skill 时的优先级（一般不会撞名）
CATEGORIES: Sequence[str] = ("openapi", "system", "tools", "research", "others")

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
            "省略则只同步目标目录已有、且仓库有源的 skill。"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印将要同步的映射，不写盘",
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

    if not names:
        print("没有需要同步的 skill。")
        return 0

    if not args.dry_run:
        dest.mkdir(parents=True, exist_ok=True)

    print(f"同步 {len(names)} 个 skill → {dest}" + (" (dry-run)" if args.dry_run else ""))
    for name in names:
        sync_one(index[name], dest / name, dry_run=args.dry_run)
    print("完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
