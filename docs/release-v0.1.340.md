路由器端 / Docker v0.1.340（x64、arm64）

- 修复「直连不进内核」在终端分流里有一台设备指定走代理后、其它设备的直连域名也全部进内核的问题（#553）。现在只有被指定走代理 / 拒绝的终端仍全部进内核，其它终端继续按直连应答放行。
- 修复「不进内核」终端在部署时被误判为走代理终端、从而单独关掉入口旁路的问题。
- 规则页「业务入口」在直连应答放行可用时显示「直连应答放行」，不再一律显示「进入内核」。
- 内置 Geo 数据更新至 2026-10-19（1,919 份 GeoSite、260 份 GeoIP），支持简体中文、繁体中文和英文说明搜索。
- 内核保持 1.14.1-openbox-tcp28；升级保留订阅、规则、面板密码和客户端配置。升级后请在面板重启一次内核，让入口规则按新代码重建。

「直连不进内核」仍需开启 FakeIP；关闭 FakeIP 时，按域名直连的目标仍会进内核。

本次客户端未更新，最新正式版仍为 v0.1.330。

### 客户端下载

- [Android · 0.1.330](https://github.com/liandu2024/Open-Box/releases/download/v0.1.340/open-box-android-0.1.330.apk)
- [Linux amd64 · 0.1.330](https://github.com/liandu2024/Open-Box/releases/download/v0.1.340/open-box-desktop-linux-0.1.330-amd64.deb)
- [macOS arm64 · 0.1.330](https://github.com/liandu2024/Open-Box/releases/download/v0.1.340/open-box-macos-0.1.330-arm64.dmg)
- [Windows x64 · 0.1.330](https://github.com/liandu2024/Open-Box/releases/download/v0.1.340/open-box-windows-0.1.330-x64-setup.exe)
