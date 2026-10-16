- 降低 TCP 长连接空闲时的内存占用，及时释放闲置读取缓冲；默认 GC、读取批量和转发设置保持不变（#413，本次仅覆盖 TCP 缓冲占用，其他持续增长情况仍需分别排查）。

本次更新 OpenWrt / Linux 路由器端 x64、arm64，内核更新至 tcp28。Geo 已核对 2026-10-16 最新快照：1,917 份 GeoSite、260 份 GeoIP。

客户端沿用 v0.1.330：

### 客户端下载

- [Android · 0.1.330](https://github.com/liandu2024/Open-Box/releases/download/v0.1.330/open-box-android-0.1.330.apk)
- [Linux amd64 · 0.1.330](https://github.com/liandu2024/Open-Box/releases/download/v0.1.330/open-box-desktop-linux-0.1.330-amd64.deb)
- [macOS arm64 · 0.1.330](https://github.com/liandu2024/Open-Box/releases/download/v0.1.330/open-box-macos-0.1.330-arm64.dmg)
- [Windows x64 · 0.1.330](https://github.com/liandu2024/Open-Box/releases/download/v0.1.330/open-box-windows-0.1.330-x64-setup.exe)
