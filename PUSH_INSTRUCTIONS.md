# 推送到 GitHub（huanongfish）的步骤

本文件夹已是一个初始化好的 git 仓库（含一次提交）。在你自己电脑上执行：

## 方式 A：用 gh CLI（最省事）
```bash
cd group-meeting-paper-reading
gh auth login          # 首次需登录，按提示浏览器授权
gh repo create huanongfish/group-meeting-paper-reading --public --source=. --push
```

## 方式 B：先在网页建空仓库，再 git 推
1. 打开 https://github.com/new ，Owner 选 huanongfish，仓库名填 group-meeting-paper-reading，
   **不要**勾选 Add README/.gitignore/License（本地已有），点 Create。
2. 然后：
```bash
cd group-meeting-paper-reading
git remote add origin https://github.com/huanongfish/group-meeting-paper-reading.git
git branch -M main
git push -u origin main
```

完成后仓库地址即 https://github.com/huanongfish/group-meeting-paper-reading
