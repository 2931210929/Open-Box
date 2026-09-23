<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/pic/logo-dark.png">
  <img src="docs/pic/logo.png" alt="Open-Box" height="72">
</picture>

OpenWrt 上的一体化透明代理：安装包内置 Open-Box、sing-box 内核、Node 运行时以及完整 GeoSite / GeoIP 数据，安装后通过浏览器完成订阅、节点、分流、DNS 和防火墙设置，不需要手写配置文件。

## 使用说明视频

[观看 Open-Box 使用说明视频（YouTube）](https://youtu.be/G_7AmjfSRQ8)

## 推荐服务

- 优惠购买 AI 接口、机场、VPS、住宅 IP：[**安格超市**](https://blog.angeworld.cc/market)
- AI 中转站：[**SUPERDOOR 订阅服务**](https://ai.superdoor.top/)
- 按需付费 AI 服务：[**OPENDOOR**](https://ai.opendoor.sbs/)

## 界面

**概览**：四个测试站点的延时和最近几次的走势、连接 / 内存 / 流量的实时曲线、域名过滤统计和按月的流量洞察都在一页上。

![面板概览](docs/pic/overview.webp)

**代理 · 策略**：每个站点集一张卡片，直接看到当前线路和节点健康状态。

![代理页策略页签](docs/pic/proxies-policies.webp)

**域名穿透**：展开策略后，可以看到站点集、节点组和具体节点的完整链路。

![域名穿透](docs/pic/proxies-penetration.webp)

**规则 · 真实路由**：输入域名后可预览规则匹配结果，并实际发起请求查看线路、DNS 和命中规则。
「模拟终端」会在 LAN 网桥上临时挂一个带独立 MAC 的虚拟网口,像一台真实设备那样从入口进入路由器。ESXi 等虚拟化平台要把端口组安全策略的「混杂模式」设为接受,否则虚拟终端建不起来(面板会提示,不会悄悄退回内核诊断)。

![规则调试](docs/pic/rules-route-test.webp)

**订阅管理**：支持 Clash YAML、base64 分享链接和常见 sing-box 分享链接；订阅分享区域可展开或收起，分享链接支持二维码、复制和启停。

![订阅管理](docs/pic/settings-subscriptions.webp)

**出站节点**：自动择优组和手动选择组可以混排，动态组会按关键词自动收编新节点。

![出站节点](docs/pic/settings-groups.webp)

**目标分流**：站点集支持域名、域名后缀、关键词、IP 段、规则集和规则集链接等匹配方式。

![目标分流](docs/pic/settings-policies.webp)

**链式代理**：住宅 / 静态 IP 这类出口指定一个前置节点或节点组，编辑时就能测速、看出口 IP 和归属。

![链式代理](docs/pic/settings-chain-proxy.webp)

**后端设置**：IPv6、测速地址、内核服务和统一组件升级都在这里管理。自动测速会遵守每个策略配置的检测间隔；同一节点在间隔内复用已有结果，超时按策略立即重试或切换。

![后端设置](docs/pic/settings-backend.webp)

**手机端**：同一个面板，窄屏自动改成单列 / 两列布局，底部导航。

<p>
  <img src="docs/pic/mobile-overview.webp" alt="手机端概览" width="45%">
  <img src="docs/pic/mobile-proxies.webp" alt="手机端代理" width="45%">
</p>

## 主要功能

- **订阅与节点**：支持 Clash 配置、base64 节点分享和 shadowsocks、vmess、vless（含 REALITY）、trojan、hysteria2（含端口跳跃）、tuic、anytls、wireguard 等协议。节点命名遵循 Open-Box 的重命名规则：有重命名时使用重命名，没有重命名时保留原名称。
- **节点组**：提供自动择优（url-test）、手动选择（select）和故障转移组；动态组按关键词跟随订阅更新，静态组可以手工选择节点。故障转移组按主备页签排优先级：主用不通才切到备用，主用恢复再切回。
- **链式代理**：给住宅 / 静态 IP 这类出口（socks5 / http / https，可粘链接或分字段填写）指定一个前置节点或节点组，流量先经前置再到出口；建好后作为普通节点用在节点组、站点集和终端分流里。
- **目标分流**：规则可以直接填写，也可以添加规则集链接。规则集链接和本地规则明细可以同时保留、同时生效，不会因为导入明细而删除原有链接。规则集链接每 24 小时随内核启动更新一次，链接旁的「立即更新」可以马上重拉，内核自动加载新内容。
- **切换不重启内核**：站点集在直连和代理之间切换时只改写一份很小的「开关规则集」，内核不重启——已建立的连接不断（下载、视频、SSH 不受影响），新连接和 DNS 在 1 秒内按新线路走。只有设备没有 nftables 重定向（纯 tun）、切换又牵动入口旁路，或者分流设置改过还没重启内核时，才会自动重新部署并重启一次。
- **屏蔽 QUIC**：后端设置里的开关（默认关）。打开后走代理线路的 QUIC（UDP 443）被拒绝，浏览器自动退回 TCP；直连的站点不受影响。
- **规则集导入**：在站点集编辑窗口点击“导入规则”，输入规则列表地址后可以先预览解析结果，再把域名、域名后缀、关键词、IP/CIDR 等明细导入站点集。导入后的明细保存在本地，启动时不再依赖该远程规则链接。
- **订阅分享**：可以选择要分享的节点，设置标题和域名/IP，协议前缀支持 HTTP 或 HTTPS；保存一次即可生成并关闭窗口。分享列表支持展开/收起，单条分享可以启用或停用，也可以复制链接、刷新和删除。
- **DNS 接管**：支持接管 dnsmasq 转发、防火墙劫持和禁用三种模式，国内域名与代理域名可以分别解析。DNS 页有两个上游可改地址和协议（UDP / TCP）：「兜底直连 DNS」给直连域名用，部署时优先用 WAN 下发的 DNS，读不到才用它填的地址；「代理 DNS 上游」给走代理的域名用，内核经站点集选中的节点向它查询。哪个域名用哪个上游由站点集此刻的出口决定，不用单独配置；要把某个域名固定成某个 IP 或另一个域名，用「DNS 重写」。
- **入口旁路**：两种模式自动选，不用配置。**默认放行**（FakeIP 开着、兜底走直连时）：走代理的域名拿到的是占位地址、一定进内核，其余目标只要解析到的地址不在「进内核」名单（走代理 / 拒绝的站点集的 IP 集合）里，就在系统入口（nftables）直接放行——兜底直连、按域名直连的目标都不再经过内核。**默认进内核**（其余情况）：只有此刻走直连的站点集里的 IP 集合（默认「国内」的 geoip-cn 等）在入口放行，和走代理的集合有重叠的段会扣掉再放。两种模式之间、直连 / 代理翻面，都只改写几份规则集文件，内核不重启。此刻是哪种模式、为什么，规则页「业务入口」那一步写着。默认放行模式的边界：把一个站点集从直连切到代理后，终端本地 DNS 缓存里还没过期的真实 IP 仍会按直连走；终端自带 DoH、开 FakeIP 之前缓存的真实 IP 同样不在保证内。
- **共享网络**：可以把内核入站开放给局域网中的其它设备作为代理使用。
- **导出与导入**：把分流、站点集、节点组、DNS、面板设置打成一个文件，可选带上订阅和节点、链式代理、终端分流、共享网络；新设备导入后重启内核即可。文件不含面板密码。
- **流量统计**：按终端设备、节点和访问目标查看每日流量。
- **内置规则数据库**：完整安装包自带 GeoSite / GeoIP 数据，首次安装和启动无需单独下载规则数据库。
- **组件升级**：Open-Box 程序、sing-box 内核和 GeoSite / GeoIP 数据统一从本仓库 Release 获取。升级前会校验本地版本和文件完整性，版本一致且文件正常时不会重复下载；完整安装包始终包含三类组件，新安装无需另行下载规则数据库。
- **LuCI 兜底页**：面板打不开时，可以从路由器的“服务 → Open-Box”页面启停服务、恢复直连或卸载。

## 下载

请从 [GitHub Releases](https://github.com/liandu2024/Open-Box/releases/latest) 下载对应架构的完整安装包：

- `x64`：x86_64 路由器
- `arm64`：aarch64 路由器

完整安装包包含 Open-Box、sing-box、Node 运行时和全部 GeoSite / GeoIP 数据。每个资产旁边都有 SHA256 校验文件。

## 安装

SSH 以 root 登录 OpenWrt 路由器后执行：

```sh
curl -fsSL https://raw.githubusercontent.com/liandu2024/Open-Box/main/scripts/install.sh | sh
```

GitHub 访问不畅时，需要先通过可访问的 raw 镜像获取安装脚本，再让脚本使用镜像下载发布包：

```sh
curl -fsSL https://gh-proxy.com/raw.githubusercontent.com/liandu2024/Open-Box/main/scripts/install.sh | sh -s -- --mirror
```

`--mirror` 只控制安装包下载；如果最外层的 `raw.githubusercontent.com` 本身无法访问，直接在原地址后追加 `--mirror` 仍然无法取得脚本。

安装过程中会问一次面板端口（默认 **3036**，直接回车即可）。端口会先检查是否可用——被别的程序占用、或与 Open-Box 自己和系统的端口冲突时，会说明原因并让你重填。也可以用 `--port` 直接指定，例如在上面的命令末尾加 ` --port 3080`。装完之后还能改，见[修改面板端口](#修改面板端口)。

安装要求：OpenWrt、x86_64 或 aarch64、至少 512MB 存储空间和 512MB 内存。安装 / 升级脚本会检查并尝试用 opkg 或 apk 补齐系统依赖（kmod-tun、kmod-nft-queue、kmod-nft-nat、kmod-veth、ip-full、ca-bundle）；软件源不通时只提示、不中断，可稍后按提示手动安装，设 `OPENBOX_SKIP_DEPS=1` 可跳过这一步。安装完成后，用浏览器打开脚本提示的 `http://<路由器局域网 IP>:<面板端口>` 地址，首次访问设置管理密码。

安装完成后，用浏览器打开 `http://<路由器 LAN 地址>:<面板端口>`（安装脚本结束时会打印这个地址），**首次打开时设置面板密码**。以后忘了密码不用重装，见下面的[忘记面板密码](#忘记面板密码)。

## 修改面板端口

新装的默认端口是 **3036**；**v0.1.216 及更早装的机器升级后端口不变**（还是 2026），不会被新默认值挪走。

两种改法，效果一样：

- **LuCI 页面**：路由器管理界面 → 服务 → Open-Box，「Open-Box 面板」那张卡片的按钮排末尾点「修改端口」。填新端口保存即可；有冲突不会保存并告诉你原因，面板正在运行的话会自动重启一次。
- **SSH**：`open-box port` 看当前端口，`open-box port 3080` 改成 3080。

改完记得用新地址访问面板。

## 忘记面板密码

面板密码保存在路由器上，能以 root 登上路由器就能查到，**不需要重装，也不会丢失订阅和规则**。两个地方可以看：

**1. LuCI 页面**：路由器管理界面 → 服务 → Open-Box，页面顶部「完整管理请到 Open-Box 面板：」那一行，面板地址后面直接显示 `密码: xxxx`。刚升级完看不到的话，退出 LuCI 重新登录一次。

**2. SSH 命令**：SSH 登上路由器后运行 `open-box`，选 `1`：

```text
root@OpenWrt:~# open-box

Open-Box v0.1.216
  1) 当前密码
  2) 重新启动
  3) 检查升级
  4) 卸载
  5) 退出
请选择 [1-5]: 1

  面板地址: http://192.168.1.1:3036
  当前密码: ********
```

只想要密码本身可以直接运行 `open-box password`；`open-box check` 检查有没有新版本，`open-box update` 直接升级，`open-box restart` 重启内核和面板，`open-box uninstall` 卸载。

以上两个入口从 **v0.1.210** 开始提供。更早的版本先通过 SSH 执行下面「升级」一节的命令升到最新版（升级会保留密码、订阅和规则），升级完成后 `open-box` 命令就可以用了。

查到密码后想换一个：登录面板，在「设置」页点「修改密码」。

## 升级

面板中可以从“设置 → 后端设置”检查更新，也可以通过 SSH 执行：

```sh
curl -fsSL https://raw.githubusercontent.com/liandu2024/Open-Box/main/scripts/update.sh | sh
```

升级会保留订阅、规则和面板密码，并校验 Open-Box、sing-box、GeoSite / GeoIP 组件。相同且完整的组件直接复用，只有变化、缺失或损坏的组件才会从本仓库 Release 下载。

### 回退到上一个版本

如果升级后面板或内核异常,可以用下面的命令回退:脚本会到 GitHub 查当前版本之前最近的正式 Release,重新下载那一版的完整安装包装回去。路由器本机不保留旧版备份,所以回退需要能访问 GitHub(或镜像);订阅、规则、面板密码等数据目录不会被动。

```sh
curl -fsSL https://raw.githubusercontent.com/liandu2024/Open-Box/main/scripts/update.sh | sh -s -- --rollback --direct
```

GitHub 访问不畅时，使用代理执行：

```sh
curl -fsSL https://gh-proxy.com/raw.githubusercontent.com/liandu2024/Open-Box/main/scripts/update.sh | sh -s -- --rollback --mirror https://gh-proxy.com
```

两条命令都会自动识别路由器架构,下载上一个版本的完整安装包,先校验 SHA256,再替换当前文件;校验或替换失败会保留现有安装。--mirror 只影响安装包下载,查询 Release 列表的 GitHub API 会先直连、直连不通再经镜像。

## 卸载

默认停止服务并保留订阅和配置数据：

```sh
curl -fsSL https://raw.githubusercontent.com/liandu2024/Open-Box/main/scripts/uninstall.sh | sh
```

连数据一起删除：

```sh
curl -fsSL https://raw.githubusercontent.com/liandu2024/Open-Box/main/scripts/uninstall.sh | sh -s -- --purge
```

## 许可证

本仓库公开安装、升级和卸载所需脚本、界面说明图片及发布资产。面板和内核的许可证与版权信息随安装包提供。

## Star 增长

<a href="https://www.star-history.com/#liandu2024/open-box&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=liandu2024/open-box&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=liandu2024/open-box&type=Date" />
    <img alt="Open-Box Star 增长图" src="https://api.star-history.com/svg?repos=liandu2024/open-box&type=Date" />
  </picture>
</a>
