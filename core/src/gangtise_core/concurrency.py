"""线程池：工作线程继承提交时的 contextvars（请求级 Authorization / AK·SK / uid 等）。

标准 ThreadPoolExecutor 不传递 contextvars，MCP 常驻进程里工作线程会拿不到请求鉴权，
域名也会按「非透传」解析成内网地址。脚本内并发请求统一用本模块的 ThreadPoolExecutor。
"""
from __future__ import annotations

import contextvars
from concurrent.futures import ThreadPoolExecutor as _ThreadPoolExecutor


class ThreadPoolExecutor(_ThreadPoolExecutor):
    def submit(self, fn, /, *args, **kwargs):
        # 每个任务单独 copy：同一 Context 不能被多个线程同时 run
        ctx = contextvars.copy_context()
        return super().submit(ctx.run, fn, *args, **kwargs)
