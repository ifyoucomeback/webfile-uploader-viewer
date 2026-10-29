# webfile-uploader-viewer

用于上传指定文件并在多客户端查看。客户端监控目录并分片上传文件；服务端负责文件存储、管理后台、播放和下载。支持最多五文件并发，以及按客户端浏览实际保存目录。

## 模块职责

| 位置 | 职责 |
| --- | --- |
| `server/server.py` | 服务端启动入口 |
| `server/application.py` | 应用创建、路由注册、静态资源和生命周期 |
| `server/routes/` | 按认证、用户、文件、上传、下载、播放等功能组织 HTTP 接口 |
| `server/routes/file_browser.py` | 按客户端浏览实际保存目录、查询文件导航入口 |
| `server/routes/file_preview.py`、`file_downloads.py`、`file_actions.py` | 实际存储路径对应的预览、下载、删除和审计接口 |
| `server/dependencies.py` | Web 会话、Root 权限、上传 PSK 校验 |
| `server/security/passwords.py` | 密码生成和验证 |
| `server/security/users.py` | 用户认证、增删改及配置持久化 |
| `server/security/sessions.py` | 会话创建、过期和失效 |
| `server/services/upload_coordinator.py` | 每客户端最多五个文件任务、独立续传及同目标替换 |
| `server/services/upload_runtime.py` | 异步协调锁、客户端任务映射、重启恢复和运行时清理 |
| `server/services/maintenance.py` | 后台维护任务的启动和停止 |
| `server/services/audit.py` | 操作审计日志 |
| `server/services/client_resolver.py` | 客户端反向 DNS 查询 |
| `server/services/storage_summary.py` | 客户端活动和磁盘统计 |
| `server/services/file_browser.py` | 客户端存储根目录隔离、实际目录浏览、关联原始路径及文件删除 |
| `server/storage/paths.py` | 路径校验及文件、元数据路径构造 |
| `server/storage/locks.py` | 文件删除与上传提交共用的目标锁，以及上传任务锁 |
| `server/storage/file_repository.py` | 已完成文件的索引、元数据和删除 |
| `server/storage/upload_store.py` | 上传任务、分片持久化和过期清理 |
| `server/storage/upload_commit.py` | 分片合并、完整性验证、文件替换及失败回滚 |
| `server/storage/checksums.py` | SHA-256 校验 |
| `server/upload_manager.py`、`server/auth.py` | 组合上述组件，保留主要管理方法作为兼容入口 |
| `client/app.py`、`client/web.py` | 客户端启动及 Web 应用装配 |
| `client/application.py` | 客户端组件、共享状态和配置重载 |
| `client/upload_settings.py` | 上传并发默认值、1～5 范围校验 |
| `client/runtime.py`、`client/single_instance.py` | 后台任务和进程锁的生命周期 |
| `client/routes/` | 配置、文件、任务和状态接口 |
| `client/routes/file_browser.py`、`file_preview.py`、`file_downloads.py`、`file_actions.py` | 本地目录浏览、预览、下载和删除的独立接口 |
| `client/dependencies.py` | 文件接口获取当前客户端运行实例 |
| `client/services/local_files.py` | 监控目录范围内的文件管理、上传中删除保护和队列清理 |
| `client/services/queue.py` | 入队、去重、优先级调整及队列快照 |
| `client/services/sync.py` | 文件索引比较、摘要缓存和同步判断 |
| `client/services/recovery.py` | 查找和优先恢复断点任务 |
| `client/services/workers.py` | 目录监控、动态并发调度及不占上传名额的延迟重试 |
| `client/monitor.py`、`client/directory_events.py` | 目录扫描、过滤、缓存及文件系统事件适配 |
| `client/uploader.py` | 共享 HTTP 会话、总带宽限制及多个文件上传协调 |
| `client/transfer/progress.py` | 每个文件独立的进度、速度及阶段 |
| `client/transfer/connection.py` | HTTP 会话、健康检查和远端文件查询 |
| `client/transfer/protocol.py` | 上传初始化、分片传输及完成确认 |
| `client/static/` | 客户端样式及按配置、状态、队列、文件、任务拆分的脚本 |
| `shared/file_access.py` | 两端共用的根目录边界、相对路径及符号链接检查 |
| `shared/directory_listing.py` | 当前目录枚举、文件夹优先排序、搜索和分页 |
| `shared/file_preview.py` | 文本编码识别与限量预览 |
| `shared/file_streaming.py` | 视频单段 Range 响应 |
| `shared/file_http.py` | 文件操作错误到 HTTP 状态的转换 |
| `shared/static/file-browser.js`、`file-preview.js` | 两端共用的目录浏览组件和预览窗口 |
| `shared/static/pagination.js` | 通用页码输入、范围校验及 Enter 跳转，供目录列表和等待上传队列共用 |
| `shared/static/file-browser.css`、`shared/assets.py` | 公共样式与资源挂载位置 |

文件管理、上传、下载和播放具有独立的代码入口，通过统一的路径规则、文件仓库和目标锁保持关联。`ServerServices` 在一个应用内装配组件，路由通过 `request.app.state.services` 获取服务；客户端采用相同的应用实例隔离方式。业务组件不从启动入口反向导入全局状态，也不使用混入类拼装行为。

前端继续使用普通脚本。客户端先加载公共组件和各功能脚本，最后由 `app.js` 启动刷新。两端的 `files.js` 分别适配各自接口，目录交互和预览窗口由 `shared/static/` 统一实现；旧的 `video-player.js`、`downloads.js` 已被公共组件替代。后端的浏览、预览、下载和删除仍按职责分在独立文件。

## 安装与启动

在项目根目录执行：

```sh
python -m pip install -r requirements.txt
cp server/config.example.json server/config.json
cp client/config.example.json client/config.json
```

首次部署先编辑这两个配置文件，再启动程序。已有配置的机器直接沿用原文件，不执行上述复制命令。实际 `config.json` 不提交到 Git，配置示例中的 PSK 和密码摘要均为空。

- 服务端 `auth.upload_psk` 与客户端 `upload.psk` 填写相同的预共享密钥。
- 服务端 `auth.root.password_hash` 填写 Root 密码摘要；客户端配置实际的服务器地址和监控目录，服务端配置存储目录和内部 DNS。
- Root 密码摘要可在本机交互生成，输入的密码不会显示在终端：

```sh
python -c "from getpass import getpass; from server.auth import AuthManager; print(AuthManager.hash_password(getpass('Root password: ')))"
```

配置完成后：

```sh
python -m server.server
python -m client.app
```

部署新版本时，需要将 `shared/` 作为公共目录一起更新，放在 `server/` 和 `client/` 的同级位置。仅部署客户端时复制 `client/` 与 `shared/`；仅部署服务端时复制 `server/` 与 `shared/`。既有运行依赖不变。

两个进程应分别在各自的终端或服务中运行。也支持原有脚本启动方式：

```sh
python server/server.py
python client/app.py
```

通过 Uvicorn 启动时，从项目根目录使用完整模块路径：

```sh
python -m uvicorn server.server:app --host 0.0.0.0 --port 5211
python -m uvicorn client.app:app --host 0.0.0.0 --port 5210
```

也兼容在 `server` 目录执行 `uvicorn server:app`，以及在 `client` 目录执行 `uvicorn app:app`。

配置仍位于 `server/config.json` 和 `client/config.json`。部署时配置服务端 Root 密码摘要、上传 PSK、存储目录以及客户端监控目录。密码摘要可通过 `server.auth.AuthManager.hash_password()` 生成。

现有上传协议继续使用 Linux 绝对文件路径，客户端 WWAN 地址发现仍依赖 `ifconfig`。Windows 上的测试使用临时目录，并在完整 HTTP 上传测试中适配路径；测试通过不表示 Linux 部署环境和实际 WWAN/DNS 已验证。

## 网页设置并发上传

客户端使用独立页面导航：`/` 查看正在上传的文件、进度和总速度；`/queue` 查看等待队列、跳转页码、暂停/开始自动扫描或立即扫描上传；`/files` 浏览本地目录并预览、下载和删除文件；`/settings` 配置服务端、监控目录、并发数和带宽。公共导航位于 `client/templates/base.html`，四个页面的内容分别位于 `index.html`、`queue.html`、`files.html` 和 `settings.html`。更新客户端时需完整复制 `client/`，并保留同级 `shared/` 和原有实际配置。

启用自动上传（`upload.enabled: true`）时，客户端启动后自动重新扫描磁盘、比较服务端索引，并将需要上传的文件入队。首次全量同步失败后每 5 秒重试，成功后停止这项重试；恢复自动上传、修改配置时会再次全量检查，补上已有文件。暂停状态启动时不自动上传，待恢复后再同步。手动“立即上传全部扫描文件”也会重新读取磁盘，不再只使用内存中的目录缓存。

同时更新客户端和服务端代码并重启后，在客户端页面的“上传配置 → 同时上传文件数”选择 **1～5**，点击“保存配置”。默认是 **1**，选择 2～5 即启用多个文件同时上传，保存后无需再次重启。

- 增加并发数：有等待文件时立即补充上传任务。
- 减少并发数：已经启动的文件继续完成；在活动任务数低于新配置后，才启动下一项。因此调整后可能短暂显示“5 / 1”，表示五个旧任务仍在完成。
- 正常按等待队列的 FIFO 顺序启动，完成顺序由文件大小、速度及校验耗时决定；断点恢复仍可优先排队。
- “暂停任务”停止启动新文件，正在上传的文件继续完成；恢复后继续处理等待队列。
- 失败文件单独等待配置的重试间隔，不占用上传名额，也不阻塞其他文件。页面会显示等待重试的数量。
- “总上传带宽”由所有并发任务共享，0 或负数表示不限速，不会因并发数量增加而成倍提高限速。

带宽单位为 Bytes/s，例如 `300000` 约为 293 KiB/s、2.4 Mbps。文件分片通过小块流式发送来限速；该设置只限制文件上传数据，不限制网页响应、预览下载或其他进程流量。nethogs 显示的是整个进程的网络流量。客户端网页状态轮询使用 `/api/status?include_queue=false`，只返回队列及重试数量；等待队列改为 `/api/queue?page=1&page_size=50` 服务端分页，避免每秒发送完整队列。隐藏网页时停止状态轮询。静态资源 URL 带内容版本号，防止更新后混用旧脚本。

排查设备限速时，可执行 `curl -s 'http://127.0.0.1:5210/api/status?include_queue=false' | python3 -m json.tool`。响应的 `bandwidth` 包含运行进程 PID、限速值、模式 `shared-stream-v1`、累计提交的上传数据字节数及最近一秒提交量。这些计数发生在向 HTTP 客户端交付数据时，不等同于网卡实际发送量，不包含 HTTP 开销、重传和网页响应。启动和调整限速时也会输出 `[BANDWIDTH]` 日志。旧版默认 `/api/status` 仍保留完整队列，供已有调用方兼容；新版网页不再使用它。

配置保存在 `client/config.json` 的 `upload.max_concurrent_uploads`。旧配置缺少该字段时自动补为 1；配置接口对范围外、非整数和布尔值返回 400，不保存无效设置。只调整并发数也会保留其他已配置的上传参数。

服务端保留同一客户端最多五个未完成文件任务，分别校验上传归属、分片和完成请求。重启时恢复所有未完成目标；同一目标的重复旧任务仅采用最新的一份。客户端避免重复入队，服务端针对同一目标复用断点或替换旧任务。

状态接口 `/api/status` 新增 `currents`（每文件进度）、`active_count`、`max_concurrent_uploads`、`retrying`。原有 `current` 保留，表示活动列表中的第一个文件；`speed` 表示总速度。网页展示全部正在上传的文件和各自的进度、速度及“计算摘要 / 上传中 / 服务端合并校验”阶段。

## 文件目录浏览与操作

**服务端**：从左侧导航进入“客户端”，点击客户端文件导航卡片，或进入“文件浏览”后从左侧选择客户端。进入后展示服务器实际保存的文件夹层级，支持点击进入、面包屑返回和上一级。当前完整服务器路径显示在列表上方，每个已记录元数据的文件下方显示原始路径；未记录的文件明确显示“未记录”。

例如原始文件 `/home/user/data/day/clip.mp4` 沿用现有保存规则，可能位于 `<上传根目录>/<客户端>./home.user.data/day/clip.mp4`。浏览器展示 `home.user.data → day → clip.mp4` 这一实际结构。本功能不迁移已有文件。没有上传索引的普通实际文件也可查看、下载和删除；系统的元数据、审计、暂存目录及替换备份不显示。

**客户端**：点击页面顶部“本地文件浏览”，先选择已配置的监控根目录，再逐层进入文件夹。这里显示目录内全部普通文件，文本文件也可以查看；自动上传继续遵循包含/排除扩展名规则。浏览、预览、下载、删除都限定在这些监控目录内。

两端均支持：

- 当前目录内按名称搜索、文件夹优先排序、分页、刷新和面包屑导航。多页时可手动输入页码并点击“跳转”或按 Enter；超出范围或非整数会提示错误。
- 文本预览：UTF-8、UTF-16、GB18030，最多显示前 256 KB。内容作为纯文本显示；完整大文件可下载。
- 视频预览：浏览器原生支持的格式与编码可播放和拖动进度；不支持的编码需要下载后查看，服务端不做转码。
- 任意普通文件下载、单文件删除、当前页选择多个文件后批量删除。文件夹用于导航，删除操作针对文件。

删除前会显示确认提示。客户端删除只影响本地文件，会同步移除排队和重试记录；正在上传的文件返回 409，待上传完成后才能删除。删除和上传任务启动共用操作锁，避免检查后又开始上传的竞争问题。服务端删除只影响服务器副本及对应索引，保留审计记录；有未完成上传任务的目标暂不能删除。客户端原文件仍在时，后续同步可能再次上传。

客户端等待上传队列同样支持输入页码跳转。自动刷新会保留正在输入的页码，队列缩短时会回到有效页；翻页仅切换显示，不改变实际上传顺序。空列表或只有一页时跳页控件禁用。本功能无需新增或修改 `config.json` 配置。

本地接口位于 `/api/files/browse`、`preview`、`stream`、`download`、`file`，以 `root` 和根目录内的 `path` 定位。服务端新接口位于 `/api/admin/file-browser` 及其 `clients`、`preview`、`stream`、`download`、`file` 子路径，以 `client_name` 与实际存储相对路径定位，均要求 Web 登录。原有文件列表及播放/下载接口继续保留。

## 本机测试清理

本次重构已完成 24 项回归测试，验证了上传、续传、覆盖回滚、权限、下载、播放和客户端关闭等流程。

并发功能另通过 28 项检查，覆盖 1～5 并发、动态增减、FIFO 分派、暂停恢复、独立延迟重试、共享带宽、配置校验与持久化、五任务重启续传，以及五文件真实 HTTP 并行上传。测试使用独立临时目录，结束后自动清理。

目录浏览功能通过 43 项接口与逻辑检查，包括实际目录/原始路径关联、文本编码和截断、视频 Range、下载、索引和审计清理、越界及内部目录拦截、Windows 路径别名保护、上传与删除竞争、五任务并发回归。另有一项真实符号链接创建测试因本机权限限制跳过，链接拦截逻辑单独测试通过。前端完成目录进入/返回、文本安全显示、视频关闭、删除取消、批量删除及异步切换范围的 DOM 交互检查；当前环境无法连接浏览器控制组件，未完成真实浏览器视觉与点击验证。

按用户要求，验证结束后已移除测试脚本、测试专用依赖清单、测试数据、测试缓存和一次性辅助脚本。源码目录及交付压缩包保留程序、运行依赖和说明；后续测试也应在隔离目录中进行，并在完成后清理本次生成的临时产物。

`pyproject.toml` 仅保留 Python 代码格式与静态检查规则，不参与程序运行。工作区上层的 `AGENTS.md` 记录自动清理约定，供后续协作遵循。

## 审查中修复的问题

1. 上传初始化先判断“同一目标”会取消同一文件的未完成任务，导致断点丢失；现在先识别完整文件身份，再决定续传或替换。
2. 重启恢复不能因为正式文件存在就跳过上传任务，因为该文件可能是尚待替换的旧版本。
3. 恢复任务直接向 `asyncio.Queue` 内部容器追加条目会遗漏未完成任务计数；新条目现在通过标准入队方法加入，内部重排集中在队列组件。
4. 客户端关闭先取消并等待工作循环，再关闭监控和 HTTP 会话，最后释放进程锁；初始化失败也会释放锁。
5. 认证接口拒绝非对象 JSON，避免访问 `.get()` 时产生未处理异常。

依赖仍延续原项目不固定版本的方式；生产环境应使用已验证的部署依赖锁定文件。本次没有修改业务配置、上线服务或替换原始压缩包。
