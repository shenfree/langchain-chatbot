# Git 提交流程说明

本项目按课程实施步骤逐步开发。每完成一个 Step 后，建议立即提交并打 tag，方便答辩时展示项目演进过程。

## 基本原则

- 每个 Step 单独提交。
- commit message 使用清晰格式：`step X: 简短说明`。
- tag 使用格式：`step-X-简短名称`。
- 提交前先运行本 Step 对应验证命令。
- 不提交 `.env`、日志文件、数据库文件和运行数据。

## 常用命令

```powershell
git add .
git commit -m "step X: short description"
git tag step-X-name
git push
git push origin step-X-name
```

## Step 14 示例

```powershell
git add .
git commit -m "step 14: organize configuration and docs"
git tag step-14-config-docs
git push
git push origin step-14-config-docs
```

## 查看历史

```powershell
git log --oneline --decorate
```

## 查看 tag

```powershell
git tag
```

## 注意事项

- `.env` 保存真实 API Key 和密码，不要提交。
- `logs/*.log` 是运行日志，不要提交。
- `data/` 是运行数据，不要提交。
- 如果误生成了缓存目录，可以删除 `__pycache__` 后再提交。

## 前后端分离 WebUI 扩展示例

```powershell
git add .
git commit -m "feat: add fastapi streamlit webui"
git tag step-16-fastapi-webui
git push
git push origin step-16-fastapi-webui
```
## Step 15 多环境配置示例

```powershell
git add .
git commit -m "step 15: add multi environment config"
git tag step-15-envs
git push
git push origin step-15-envs
```