# v0.1.344 发布前验收

本次更新路由器端与 Docker，修复升级下载依赖 FakeIP / 内核代理状态的问题。源码构建提交为 `3afcc44be31fb02e71955e1316c56db46a46cfde`，内核保持 `1.14.1-openbox-tcp28`。未构建或发布新客户端。

## 修复范围

升级在第一个网络请求之前统一暂停原本运行的内核，等待服务及 TUN 退出，清理系统 DNS 中可能遗留的 FakeIP 应答，再通过系统网络获取脚本、版本、组件或完整包。旧脚本接力、手动执行、组件升级及回退共用该准备过程，不修改用户的 FakeIP、DNS、终端分流或 IPv6 设置。

脚本刷新、预检及主流程接管异常退出的恢复责任。取消、下载/校验失败、无需升级时恢复原来运行的内核；原来停止的内核保持停止。无法停止内核或清理 DNS 缓存时在下载前明确失败，不进入文件替换。

独立的 `install.sh`、`update.sh`、`uninstall.sh` 及 SHA256 已进入固定打包和 Release 入口检查。新版 `update.sh` 在两个架构的完整包和独立资产内字节一致，SHA256 为 `8548b0b02e613405dc209ca4fca43b5487807d657a4832d7fb493eca1aa1b165`。

## 三套环境

| 环境 | 最终版本 | 安装 / 升级 / 启动 / 核心功能 | 结果 |
| --- | --- | --- | --- |
| OpenWrt 开发路由器 `192.168.3.35` | v0.1.344 | 完整包全新安装、v0.1.343 升级、LuCI/CLI、面板及内核、DNS/HTTPS、原数据恢复 | 通过 |
| Ubuntu 虚拟机 `192.168.3.23` | v0.1.344 | 完整包全新安装、v0.1.343 升级、glibc Node、systemd/CLI、面板及内核、DNS/HTTPS、原端口及数据恢复 | 通过 |
| Docker `192.168.3.210`，SSH 宿主 `.21` | v0.1.344 | 实际 LAN IP 离线全新安装、v0.1.343 镜像升级、卷/密码/规则保留、DNS/HTTPS/SOCKS、重启及内核自启 | 通过 |

最终元数据的源码、Geo、内核和绑定程序摘要一致；完整性清单全部通过。Docker 无 OOM 或自动重启，保留原端口 `2026`；OpenWrt 保留 `3036`，Ubuntu 保留 `2026`。正式路由器 `192.168.3.1` 本轮未连接、未写文件或配置、未停止服务、未执行升级。

## FakeIP 及恢复专项

- 开发路由器实际部署 `dnsmasq` / `hijack` 两种 DNS 模式，分别测试 FakeIP 开/关，共四个组合。开启用例先确认 GitHub 域名真实命中 `198.19.0.2`，再验证暂停内核、TUN 消失、系统 DNS 返回真实地址、公开脚本下载 HTTP 200 / TLS 校验正常、恢复内核及 profile 字节不变。四组通过。
- 组件清单故意设置错误 SHA256：运行中的内核在失败后恢复；原来停止的内核仍保持停止；没有替换安装文件，profile 不变。
- 后台获取最新脚本时请求取消：worker 退出，状态为 `cancelled`，取消标志清理，内核恢复、profile 不变。
- 在开发路由器安装 v0.1.343，恢复原数据，再放入正式机同款旧升级入口（SHA256 `2e5ed2495a914861155a4f0230c7f95701cb211f364718b1cce9bdbf6c0c17e6`）。强制 GitHub 命中 FakeIP 后，从已安装入口以 `--detach` 发起完整升级，成功接力至 v0.1.344，状态 `done`，新版脚本摘要正确，内核自动恢复。专项临时 profile 及下载通道已还原。

## Docker TLS 对照及边界

首轮百度 SOCKS 请求出现 TLS EOF，测试立即失败并恢复旧服务，原始失败记录保留。旧版 v0.1.343 同样出现该现象。进一步在测试容器完全停止 Open-Box 内核后，绕过 SOCKS、固定百度两个 IP 直接访问：每个 IP 三次请求均有一次相同 EOF；Example 三次直连正常。这证明该 EOF 可发生在 Open-Box 内核之外，未作为已修复或通过项。

旧版百度与 Example 的直连/SOCKS 对照共 12 次请求完成正常 TLS。最终新版对 Example、淘宝、必应分别连续三次 SOCKS 请求均返回 200，升级后及冷启动健康、内核自启、实际 LAN 地址、数据保留全部通过。v0.1.343 与 v0.1.344 的内核、原生核心及六个绑定服务入口逐字节一致；本次没有宣称修复外部百度链路的间歇断开。

## 构建、Geo 及教程

完整 preflight：1,729 项通过、7 项默认跳过、0 失败，类型检查与 Go 测试通过；其中五项原生客户端引擎对照另行构建后补跑，5/5 通过。剩余两项为需显式开启的 315 秒时间间隔测试和额外内核专项，不计入通过项。57 项升级脚本相关测试通过。

首次干净工作区测试缺少 Geo / 二进制准备，完成准备后重跑。并发 SQLite 测试夹具的锁持有子进程遇到 busy，修正夹具自身超时及退出码检查后完整回归通过；未修改生产 SQLite 行为。

本地开发板已重新部署，`http://127.0.0.1:2048` 提供预期入口 `index-DD1VcB0M.js`。arm64 最终包在 OpenWrt 虚拟机完成 Node、兼容库、内核 version/check 与面板健康冒烟；不替代物理 ARM 设备转发验收。

Geo 上游实时检查为 `24a931c326f2a4765eb8320fae1255b2baa0d53a`（2026-10-21T00:45:15Z），1,921 GeoSite / 260 GeoIP。两架构及 Docker 使用同一快照，三语分类说明和属性子集检索检查通过。

2026-10-21T06:22Z 已实时检查安格视界频道最新 30 条视频，6 条 Open-Box 教程的原标题、链接及发布顺序与源码 README、随包列表一致，没有新增相关视频，不重复添加。发布后再读回公开 README。

## 公开产物

[v0.1.344 已正式发布](https://github.com/liandu2024/Open-Box/releases/tag/v0.1.344)，46 个资产的服务端 SHA256、大小、上传状态与本地产物逐项一致。实际从公开地址下载 x64/arm64 完整包、两架构 Docker 镜像、组件清单、独立脚本、说明及校验文件，共 33 个文件，摘要全部一致；两个架构公开安装包中的升级脚本也与独立资产相同。

GitHub 直连和 ghfast 镜像的 `releases/latest/download/update.sh` 均为 HTTP 200 / TLS 校验 0，取得新版 `8548b0b0…` 脚本。公开 README 的 6 条教程及随包列表、三个安装/升级/卸载脚本已读回核对。

OpenWrt 与 Ubuntu 重新通过公开安装命令完成安装、启动、上网及原数据恢复，最终读回源码提交与绑定程序摘要正确。开发路由器再次从 v0.1.343 和正式机同款旧入口出发，GitHub 强制命中 FakeIP，脚本及升级内容取自公开 ghfast 通道，完整升级到 v0.1.344；状态 done、内核自动恢复，原 profile 和下载通道还原。

Ubuntu 运行中的 `/api/openbox/update/notes?latest=v0.1.344` 从公开镜像取得说明，与最终发布正文一致。升级弹窗实际使用的前端解析器检查通过：6 个列表项、4 个客户端实际下载链接，无维护注释残留。

发布维护后，GitHub 正文、release-notes.md 附件及 SHA256 再次核对一致，全部 46 个资产的服务端摘要再次通过。保留最近 10 个已发布 Release（v0.1.344 至 v0.1.335），仅删除 v0.1.334 的 Release，已读回确认其 Git 标签仍在。Android、macOS、Windows、Linux 最近正式版均为 0.1.330，原安装包和校验文件仍位于保留的 v0.1.340，无需搬迁，客户端下载链接继续指向这些实际文件。

## Issue 巡检与跟进

发送前重新获取完整讨论，与已审阅的正文、评论及附件核对，避免忽略新信息或重复评论。本轮跟进 7 条近期未回复故障和 4 条新增补充讨论，回复后读回正文与状态；以下 11 条均保持打开，没有把本次升级修复当成其它问题已解决：

- [#686 回复](https://github.com/liandu2024/Open-Box/issues/686#issuecomment-6310138783)
- [#681 回复](https://github.com/liandu2024/Open-Box/issues/681#issuecomment-6310140098)
- [#680 回复](https://github.com/liandu2024/Open-Box/issues/680#issuecomment-6310141548)
- [#679 回复](https://github.com/liandu2024/Open-Box/issues/679#issuecomment-6310142833)
- [#678 回复](https://github.com/liandu2024/Open-Box/issues/678#issuecomment-6310143921)
- [#669 回复](https://github.com/liandu2024/Open-Box/issues/669#issuecomment-6310145060)
- [#668 回复](https://github.com/liandu2024/Open-Box/issues/668#issuecomment-6310146137)
- [#659 回复](https://github.com/liandu2024/Open-Box/issues/659#issuecomment-6310147228)
- [#663 回复](https://github.com/liandu2024/Open-Box/issues/663#issuecomment-6310148306)
- [#661 回复](https://github.com/liandu2024/Open-Box/issues/661#issuecomment-6310149399)
- [#658 回复](https://github.com/liandu2024/Open-Box/issues/658#issuecomment-6310150503)
