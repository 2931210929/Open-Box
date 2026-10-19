路由器端 / Docker v0.1.341（x64、arm64）

- 直连 IP 段现在和直连域名一样在入口放行：站点集或前置自定义分流里的 `ipCidr`，以及直连 `geoip` 集合，命中的连接不再进入内核。
- 终端分流里被指定走代理 / 拒绝的终端仍然全部进内核，不会因为这条旁路被放走；其它终端继续享受直连旁路。
- 规则页「业务入口」补充直连 IP 的判断：IP 目标会提示入口已启用直连 IP 集合，是否命中以右栏实测为准；走代理的域名不再误显示为「直连应答放行」。
- 内核保持 1.14.1-openbox-tcp28；Geo 保持 2026-10-19（1,919 份 GeoSite、260 份 GeoIP）。
- 升级保留订阅、规则、面板密码和客户端配置；升级脚本会在内核运行时重新生成入口规则。

「直连不进内核」仍需开启 FakeIP；关闭 FakeIP 时，域名目标仍会进内核。直连 IP 集合按部署时的分流重建；如果找不到可安全旁路的地址，会按兼容路径进内核。

本次客户端未更新，最新正式版仍为 v0.1.330。

### 客户端下载

- [Android · 0.1.330](https://github.com/liandu2024/Open-Box/releases/download/v0.1.340/open-box-android-0.1.330.apk)
- [Linux amd64 · 0.1.330](https://github.com/liandu2024/Open-Box/releases/download/v0.1.340/open-box-desktop-linux-0.1.330-amd64.deb)
- [macOS arm64 · 0.1.330](https://github.com/liandu2024/Open-Box/releases/download/v0.1.340/open-box-macos-0.1.330-arm64.dmg)
- [Windows x64 · 0.1.330](https://github.com/liandu2024/Open-Box/releases/download/v0.1.340/open-box-windows-0.1.330-x64-setup.exe)
