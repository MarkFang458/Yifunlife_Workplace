# 完整源码说明

主系统源码位于仓库根目录。三个原生业务模块、数据库迁移及 Cloudflare 准备配置完整保存在 workflow-source.tar.gz；没有减少任何页面或功能。

克隆仓库后运行：

```sh
python3 prepare_source.py
```

脚本验证 SHA-256 后恢复原目录。然后按 README 启动本地版。业务数据库、历史附件、密钥和预设密码未上传。Cloudflare 主服务数据库事务迁移仍未完成，不能把当前源码称为已经上线的完整云端版本。

Cloudflare 完整入口及当前状态见 `CLOUDFLARE_DEPLOYMENT.md`。运行 `scripts/package_cloud_source.py` 会重新打包全部模块和校验值，排除依赖、运行资料与密钥。
