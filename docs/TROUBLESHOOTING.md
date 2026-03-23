# PYTA Research — 排查手册

> 记录真实踩过的坑，避免下次重复排查。每次新增问题请补充到对应章节。
> 最后更新：2026-03-24

---

## 目录

1. [前端页面无法访问 / 空白](#1-前端页面无法访问--空白)
2. [CI 失败：FastAPI status_code=204 断言错误](#2-ci-失败fastapi-status_code204-断言错误)
3. [Git 冲突：branch has conflicts that must be resolved](#3-git-冲突branch-has-conflicts-that-must-be-resolved)
4. [TypeScript build 失败：imports unused / declared but never read](#4-typescript-build-失败imports-unused--declared-but-never-read)
5. [推演结果全部 DEGRADED / data_quality: degraded](#5-推演结果全部-degraded--data_quality-degraded)
6. [CI 不触发 / 一直显示旧结果](#6-ci-不触发--一直显示旧结果)

---

## 1. 前端页面无法访问 / 空白

**症状**：浏览器访问 `http://127.0.0.1:4174/` 显示无法访问、ERR_CONNECTION_REFUSED，或页面空白。

### 第一步：确认端口实际状态

```bash
lsof -i :4174
```

- **没有输出** → 进程根本没跑，见"重新启动"。
- **有输出但 curl 返回 000** → 进程僵死，占着端口但不响应，见"杀进程"。

### 第二步：杀掉僵死进程

```bash
pkill -f "vite preview"
lsof -ti :4173 :4174 :4175 | xargs kill -9 2>/dev/null
sleep 1
```

### 第三步：确认 dist 是最新版本

> ⚠️ 常见陷阱：build 报错之后 dist 还是旧的，重启 preview 也没用。

```bash
cd frontend
npm run build        # 必须零错误才有效
```

如果 build 报错，先修代码再 build，不要跳过这步直接 preview。

### 第四步：重新启动 preview

```bash
npm run preview -- --port 4174 --host 127.0.0.1 &
sleep 3 && curl -s -o /dev/null -w "HTTP %{http_code}" http://127.0.0.1:4174/
# 期望：HTTP 200
```

### 快速诊断命令（一条）

```bash
npm run build 2>&1 | tail -5 && \
pkill -f "vite preview"; sleep 1 && \
npm run preview -- --port 4174 --host 127.0.0.1 &
sleep 3 && curl -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:4174/
```

---

## 2. CI 失败：FastAPI status_code=204 断言错误

**症状**：CI 日志出现：
```
AssertionError: Status code 204 must not have a response body
```

**根因**：FastAPI `0.115+` 在路由注册时断言 204 不能有 response body，即使函数返回 `None` 也会触发。

**错误写法**：
```python
@router.post("/settings/llm", status_code=status.HTTP_204_NO_CONTENT)
def save(...) -> None:
    ...
```

**正确写法**：
```python
from fastapi import Response

@router.post("/settings/llm")
def save(...) -> Response:
    ...
    return Response(status_code=204)
```

**排查命令**（搜索所有违规路由）：
```bash
grep -rn "HTTP_204_NO_CONTENT\|status_code=204" src/ --include="*.py"
```

> ⚠️ 注意：错误在 **模块加载时** 就抛出，不是请求时，所以 `create_app()` 直接爆。
> 本地验证：`python3 -c "from src.api.app import create_app; create_app(); print('OK')"`

---

## 3. Git 冲突：branch has conflicts that must be resolved

**症状**：GitHub PR 页面显示 "This branch has conflicts that must be resolved"。

**背景**：我们的长期分支 `PYTA/secondary-market-mvp` 在 main 合并了其他 PR 之后，历史 commit 与 main 产生分叉，直接 rebase 会逐条重放十几个旧 commit 全部冲突。

### 正确解法（跳过历史，只保留差异）

```bash
# 1. 如果 rebase 已经在进行中，先中止
git rebase --abort

# 2. 找出我们相对 main 的全部文件差异
git diff origin/main..HEAD --name-only

# 3. 从 main 新建干净分支
git checkout -b feat/inv-XX-description origin/main

# 4. 把我们的版本逐文件 checkout 过来
git checkout <旧分支名> -- <文件1> <文件2> ...

# 5. build 验证 + commit + push
npm run build
git add -A && git commit -m "feat: ..."
git push -u origin feat/inv-XX-description
```

**关键原则**：不要试图 rebase 一个有十几个旧 commit 的长期分支，直接取文件差异比逐 commit 解冲突快 10 倍。

---

## 4. TypeScript build 失败：imports unused / declared but never read

**症状**：`npm run build` 报错：
```
error TS6192: All imports in import declaration are unused.
error TS6133: 'xxx' is declared but its value is never read.
```

**根因**：常见于 agent 生成代码时，在文件顶部添加了 import 和 state，但忘记在 JSX 中实际使用。

**排查**：

```bash
npm run build 2>&1 | grep "TS6192\|TS6133\|TS6196"
```

**修法**：

1. 找到报错文件，确认 import 的组件/类型是否在 JSX 里有 `<Component />` 渲染
2. 确认 `useState` 的变量是否有对应的 `onClick={() => setXxx(true)}` 和 `{xxx && <Modal />}`
3. 如果确实不需要，删掉对应的 import 和 state

**预防**：agent 写完组件后立即跑 `npm run build`，不要等到"测试发现问题"再排查。

---

## 5. 推演结果全部 DEGRADED / data_quality: degraded

**症状**：5 个 agent 状态全部是 `degraded`，`data_quality: degraded`，`stop_reason: timeout`。

**根因**：LLM timeout 设置过短，MiniMax 等推理模型实际需要 28-40 秒，但 timeout 设置为 20 秒。

**检查**：
```bash
# 查看当前 timeout 设置
grep -n "timeout" src/sandbox/llm/client.py
grep -n "timeout" src/config/settings.py
```

**正确值**：
```python
# src/sandbox/llm/client.py
timeout = httpx.Timeout(60.0, connect=10.0)  # 不是 20.0

# src/config/settings.py
llm_timeout_seconds: float = 60.0
```

**快速验证**：
```bash
python3 -c "
import asyncio, httpx, datetime

async def test():
    payload = {
        'ticker': 'NVDA', 'market': 'US',
        'events': [{'event_id': 'test', 'event_type': 'manual_input',
                    'content': '测试推演', 'source': 'cli',
                    'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    'symbol': 'NVDA', 'metadata': {}}],
        'round_timeout_ms': 90000,
        'narrative_guide': 'NVDA 测试'
    }
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post('http://localhost:8000/api/v1/sandbox/run', json=payload)
        d = r.json()
        rc = d.get('round_complete', {})
        print(f'quality={rc.get(\"data_quality\")} | reason={rc.get(\"stop_reason\")}')
        for a in rc.get('per_agent_status', []):
            print(f'  {a[\"agent_type\"]:30s} {a[\"perspective_status\"]}')

asyncio.run(test())
"
```

期望输出：`quality=complete | reason=all_perspectives_received`，5 个 agent 全部 `live`。

---

## 6. CI 不触发 / 一直显示旧结果

**症状**：push 之后 `gh run list` 看不到新的 CI run，或 `gh pr checks` 显示旧的失败结果。

**原因 A：concurrency cancel-in-progress**

workflow 配置了 `cancel-in-progress: true`，如果两次 push 太快，第二次 push 触发的 run 会取消第一次，但有时新 run 没能正常排队。

**解法**：推一个空 commit 重新触发：
```bash
git commit --allow-empty -m "ci: retrigger" && git push
```

**原因 B：`gh pr checks` 缓存了旧结果**

等 30-60 秒后再查，或直接看 Actions 页面：
```bash
gh run list --branch <分支名> --limit 5
# 找到最新 run_id 后
gh run view <run_id> --log-failed
```

**原因 C：PR 的 head 和本地不一致**

确认 PR 指向的是正确分支：
```bash
gh pr view <PR号> --json headRefName,headRefOid
```

---

## 通用排查顺序

遇到"跑不起来"类问题，按以下顺序排查，不要跳步：

```
1. npm run build         → 确认代码本身没有编译错误
2. lsof -i :端口号       → 确认进程状态（没跑 / 僵死 / 正常）
3. kill 旧进程            → 确保端口干净
4. 重新启动 + curl 验证   → HTTP 200 才算真正成功
5. 看后端日志             → python3 -c "from src.api.app import create_app; create_app()"
```

**不要做**：
- ❌ 不 build 直接重启 preview（dist 是旧的）
- ❌ 端口占用了直接换端口（根因没解决）
- ❌ CI 失败直接 retry 不看日志（症状不会消失）
- ❌ 看到 rebase 冲突就硬解（用新建分支+checkout文件更快）
