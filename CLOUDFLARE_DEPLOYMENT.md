# Yifunlife Workplace · Cloudflare 共享测试部署

目标是现有 Cloudflare Worker `yifunlife-workplace`，GitHub 仓库 `MarkFang458/Yifunlife_Workplace` 的 `main`。

## 当前状态

完整代码已同步 main（0f432bf），Cloudflare 完整容器构建和发布成功。
四个空的私有 R2 桶已创建，业务数据库及应用容器绑定已部署。
Zero Trust Free 已由负责人启用，全站 Access 策略仅允许负责人及指定查看邮箱；当前提交补齐网关 issuer、audience 配置。
登录后首次账号自行设置、容器启动、全部页面和实际附件上传仍需完成线上验证，尚不能称为完整验收通过。

## 保留范围

Python 主服务和原报价、采购、售后模块全部保留。根目录源代码与 `workflow-source.tar.gz` 一起组成完整系统，`prepare_source.py` 校验后恢复全部模块。
三个中心挂载在同一个站点的 `/modules/quote/`、`/modules/procurement/`、`/modules/aftersales/`，静态资源、客户端请求、图片、下载和人员管理跳转都使用同域路径。紧凑行高和原有适配样式保留。
财务与工厂此前尚未开放的功能仍按原范围显示，不能把这解释为迁移后删去功能。

## 数据与文件分离

应用容器只运行服务。业务库由独立 `BusinessDatabase` SQLite Durable Object 持久保存；应用连接使用内存 SQLite，完整运行原来的查询、约束和触发器，然后以版本检查将结果状态原子保存。采购入库生成的编号、时间和关联不会在服务端重复生成。
测试库采用分块快照，单块小于 Cloudflare SQL 行限制。当前逻辑快照上限 8 MiB，面向小规模共享测试；正式版需要查询级数据服务、压力与恢复测试。正式资料不得直接导入这个模拟库，也不得将它误认为大规模正式数据库方案。

照片、报价图片及附件直接通过容器私有 outbound binding 写入四个私有 R2 桶，数据库只存对象 key 和归属。没有开放公开桶，没有把业务图片保存到应用容器或 GitHub。
任何本机客户数据库、登录会话、bridge 密钥和上传文件都未包含在源码包中。

## 登录与权限

站点支持直接账号密码登录（AUTH_MODE=password），网关向核心服务校验已有登录会话和邮箱名单；未登录无法访问任何业务模块，查看账号在网关及核心层均只读。原 Access 模式保留作可选配置。直接模式禁止匿名自助注册，新账号由管理员建立。
负责人邮箱 `markfang458@hotmail.com`，共享查看邮箱 `yifunlife@hotmail.com`。
已建立账号保留原密码与资料，不重建用户。没有预设或公布账号密码。原先邮件验证后的自行设置方式仅用于 Access 模式。
初始化管理员时才建立明确标注的模拟客户、项目、商品、设计、任务、线索、采购、库存、售后和平台运营资料。运营中心与 CEO 汇总读取同一份账号账本，使用上海统计日期。

## 发布步骤

1. 将当前部署源文件同步到 main，保留仓库私有状态。
2. 建立 `yifunlife-procurement-files`、`yifunlife-aftersales-files` 私有 R2 桶。
3. 为现有 Worker 配置 Access 邮箱策略，将其实际 issuer 与 audience 写入 `wrangler.jsonc` 的 `ACCESS_ISSUER`、`ACCESS_AUD`；不得关闭签名验证或绕过登录。
4. 现有 Git integration 使用 `npx wrangler deploy`。Wrangler 先恢复模块源码，Workers Builds 构建 Docker 镜像并部署原服务。主机无需安装 Docker。
5. 核对构建、镜像发布和容器启动日志，验证登录前拒绝访问、登录后所有页面、真实 R2 上传下载及只读写入拒绝。只有这些通过才能称为完整站点上线。

## 本地复查

- `python3 scripts/build_cloud_image.py`（需要 Node 在 PATH）：构建原报价与采购全部页面，售后使用保留的 Worker 和静态资源。
- `python3 scripts/test_cloud_auth.py`：临时 HTTP 服务器验证账号自行设置、会话身份和只读保护。
- 配置 `NODE` 和 `YIFUN_MINIFLARE_MODULE` 后运行 `python3 scripts/test_cloud_database.py`：原迁移、模拟数据、原子保存、失败回滚、并发保护、自增、触发器编号、Unicode 分块等。
- `wrangler deploy --dry-run --containers-rollout=none --outdir /tmp/yifun-cloud-worker-check`，然后 `node scripts/test_cloud_gateway.mjs`：编译部署网关，验证 Access 签名、邮箱名单、三个模块路由和私有 R2 文件读写。

Cloudflare 官方存储限制：https://developers.cloudflare.com/durable-objects/platform/limits/
