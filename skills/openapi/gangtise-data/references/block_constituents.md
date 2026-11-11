# 板块成分股（已并入 constituents）

本能力已整合到 **`scripts/constituents.py`**（`-m sector`）。

旧入口 `scripts/block_constituents.py` 仍可用，会转发到同一实现。

完整说明见 [成分股调用指导](./constituents.md)。

```bash
python3 scripts/constituents.py -k 机器人
python3 scripts/constituents.py -s 121000130
```

指数成分股权重请使用：

```bash
python3 scripts/constituents.py -m index --indexes 000300.SH -td 2026-06-30
```
