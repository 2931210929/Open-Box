# Open-Box v0.1.370

- 路由器：加强本机 DNS 上游防循环保护，纠正缺少可选 queue 能力时的提示（#736）；修复旧版 Lua LuCI 入口和软链安装后的面板启动问题。
- 测速：区分域名解析失败、系统连接资源不足和普通连接超时，保留原始错误，减少误判节点故障。
- Windows / macOS：未连接时托盘／菜单栏图标为黑白，连接成功后显示彩色；暂停或连接失败时恢复黑白。
- 更新 Geo 规则库及简体中文、繁体中文、英文分类检索说明。

### 客户端下载

- [macOS arm64 · 0.1.370](https://github.com/liandu2024/Open-Box/releases/download/v0.1.370/open-box-macos-0.1.370-arm64.dmg)
- [Windows x64 · 0.1.370](https://github.com/liandu2024/Open-Box/releases/download/v0.1.370/open-box-windows-0.1.370-x64-setup.exe)
- [Android · 0.1.367](https://github.com/liandu2024/Open-Box/releases/download/v0.1.367/open-box-android-0.1.367.apk)
- [Linux amd64 · 0.1.367](https://github.com/liandu2024/Open-Box/releases/download/v0.1.367/open-box-desktop-linux-0.1.367-amd64.deb)
