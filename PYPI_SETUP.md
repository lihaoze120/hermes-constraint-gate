# PyPI 发布 — 一次性设置指南

## 1. PyPI 账号（如果还没有）

去 https://pypi.org 注册账号，启用 2FA。

## 2. 创建 API Token（或配置 Trusted Publishing）

### 方式 A：Trusted Publishing（推荐，不需要 token）

在 PyPI 项目设置里：
1. 进入 https://pypi.org/manage/projects/ 创建 `hermes-constraint-gate` 项目
2. 进入项目的 Settings → Publishing
3. 添加 Trusted Publisher：
   - Owner: `lihaoze120`
   - Repository: `hermes-constraint-gate`
   - Workflow: `publish.yml`
   - Environment: `pypi`

### 方式 B：API Token（备用）

1. PyPI → Account Settings → API Tokens → Add token
2. Scope 选 "hermes-constraint-gate"
3. 复制 token
4. GitHub → repo Settings → Secrets and variables → Actions → New secret
   - Name: `PYPI_API_TOKEN`
   - Value: 粘贴刚才的 token

如果用方式 B，需要把 publish.yml 里的最后一步改为：
```yaml
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          password: ${{ secrets.PYPI_API_TOKEN }}
```

## 3. GitHub 设置

在 GitHub repo → Settings → Environments → New environment:
- Name: `pypi`
- 可选：设置 review 规则（比如需要手动 approve 才能发布）

## 4. 首次发布

```bash
# 确保版本号在 pyproject.toml 里更新了
git tag v0.12.0
git push origin v0.12.0
```

推送 tag 后 GitHub Actions 自动构建并发布到 PyPI。

## 5. 验证

```bash
pip install hermes-constraint-gate
cg --version
```

---

## 文件清单

| 文件 | 说明 |
|------|------|
| `.github/workflows/publish.yml` | 发布工作流（tag push 触发） |
| `pyproject.toml` | 更新：urls、ruff 配置、pytest-cov、版本 0.12.0 |
| `MANIFEST.in` | sdist 包含的非 Python 文件 |
| `.gitignore` | 新增 build/dist 相关条目 |

## 可选：更新 CI 加 lint + coverage

把 `.github/workflows/ci.yml` 的 test job 改成：

```yaml
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pytest pyyaml ruff pytest-cov

      - name: Lint
        run: ruff check .

      - name: Run tests with coverage
        run: pytest tests/ -v --cov=plugin --cov-report=term-missing
```
