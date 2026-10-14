# 发布前验收

## 每次发版前：检查 YouTube 教程

路由器端或客户端每次发版前，都检查[安格视界频道的最新视频](https://www.youtube.com/@Ange-Digital-Life/videos?hl=zh-CN)，不能只依赖面板的动态教程列表。

1. 查看频道最新上传的视频，筛选标题含 `Open-Box` 或 `openbox` 的条目（不区分大小写），核对视频链接、原标题和发布顺序。
2. 更新源码工作区及公开发布工作区 `README.md` 的「使用说明视频」，按发布先后排列、按视频 ID 去重，保留旧教程。没有新视频时不重复添加。
3. 同步源码工作区的 `panel/server/defaults/tutorial-videos.json`，使新安装及离线首次打开也有相同的教程列表；在提交和打包前完成。
4. 发布后读回 GitHub 公开分支的 README，确认新增链接已公开。若本次无法访问频道，记录「未完成检查」及原因，不将网络失败当成没有新视频。

## 内存与吞吐基准

基准脚本仅用于测试，不进入面板运行流程。`bench-net/main.go` 是标准库实现的本地 HTTP/DNS 数据源和计数客户端，需用 Go 编译为目标 Linux 架构；它不访问外网。

```sh
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -trimpath -ldflags='-s -w' -o <测试目录>/verify/bench-net scripts/release-verify/bench-net/main.go
# arm64 使用 GOARCH=arm64
```

将 `benchmark-api.mjs`、`benchmark-metrics.sh` 和目标架构的 `bench-net` 放入 Docker 宿主的测试目录 `verify/`，在该宿主运行：

```sh
python3 scripts/release-verify/docker-benchmark.py --arch x64 --root <测试目录> --baseline open-box:0.1.324 --candidate open-box:0.1.325
```

脚本使用独立的容器、网络和数据目录，固定 1000 个合成节点、四条 HTTP 流，本地 SOCKS5 代理不带加密。默认按 1 Gbit/s 的目标速率运行；`--mbps 0 --label uncapped --cases baseline,default` 可测不设速率上限的结果。后者仍受虚拟接口、数据源和测试 CPU 配额限制，不代表物理网卡或真实加密代理的最大吞吐，不同宿主的结果不能直接比较。

面板/内核 RSS 和进程历史峰值分别记录；容器同时记录 cgroup 内存、去除 inactive_file 后的工作集近似值、CPU 时间和节流计数。各进程的历史峰值不一定同时发生，不要将两列相加作为容器峰值。每个 JSON 保留逐秒样本和原始吞吐计数；导入和生成配置阶段包含在采样中。

`native-benchmark.py` 可通过 SSH 在 OpenWrt/Linux 开发机的临时网络命名空间运行同一组配置和数据源。先将 Docker 基准生成的 `auto-config.json`、`tun-config.json`、数据目录 `flip/`、`socks.json` 和 x64 `bench-net` 复制到该机器的独立测试目录，并将两份配置分别命名为 `auto.json`、`tun.json`。脚本以较低优先级运行，默认目标 250 Mbit/s，可通过 `--mbps` 调整。它不停止现有服务、不修改宿主路由或防火墙、不安装软件包，结束后检查原服务 PID 并清理自己的命名空间。

```sh
python3 scripts/release-verify/native-benchmark.py --host <OpenWrt开发机别名> --platform openwrt --source <测试目录> --output <结果.json>
python3 scripts/release-verify/native-benchmark.py --host <Linux开发机别名> --sudo --platform linux --source <测试目录> --output <结果.json>
```

`docker-log-rotation.test.mjs` 必须在覆盖 entrypoint 的临时容器运行，不能对现有网关执行。它验证持续打开的写入句柄、定时轮转、两份归档、近期 FATAL 和输出边界。

```sh
docker run --rm --network none -v <测试目录>/verify:/verify:ro --entrypoint /opt/open-box/node/bin/node open-box:0.1.325 --test /verify/docker-log-rotation.test.mjs
```

发版在本机打包(`scripts/build-release.sh`),源码不推 GitHub,所以没有 CI。以前是先发布、再用公开命令在两台 x86_64
机器上装一遍——验收之前用户已经能下载到,arm64 的包从来没跑过(审查第十七项)。现在按下面的顺序:**验收全过才发布**。

## 1. 打包

在干净的 `git worktree` 里打(打包脚本会拒绝有未提交改动的工作区、拒绝不是 `vX.Y.Z` 的版本号,见 build-release.sh 开头):

```sh
OPENBOX_VERSION=v0.1.266 ... sh scripts/build-release.sh x64 <产物目录>
OPENBOX_VERSION=v0.1.266 ... sh scripts/build-release.sh arm64 <产物目录>
```

## 2. 发布前验收(Release 还没建)

1. 本机起假镜像,把产物目录当 GitHub Release 的镜像前缀提供出去:

   ```sh
   python3 scripts/release-verify/fake-mirror.py --dir <产物目录> --tag v0.1.266 --port 8765
   ```

2. 两台 x86_64 机器上全新安装(OpenWrt 开发路由器会先备份、验完还原 data / etc):

   ```sh
   sh scripts/release-verify/run-host.sh openbox-dev install MIRROR=http://192.168.3.9:8765 TAG=v0.1.266
   sh scripts/release-verify/run-host.sh ubuntu23 install MIRROR=http://192.168.3.9:8765 TAG=v0.1.266
   ```

   验:版本号、meta.json 里的源码提交、面板 `/api/health`、命令行、LuCI 视图 / glibc Node、没有残留 `.old`、内核起得来、本机上网。

3. 升级路径(从当前公开版本升到新版本,用新的 update.sh):

   ```sh
   sh scripts/release-verify/run-host.sh ubuntu23 upgrade MIRROR=http://192.168.3.9:8765 TAG=v0.1.266
   ```

   当前公开版本默认经 ghfast.top 装;镜像慢的时候加 `OLD_MIRROR=direct` 直连 GitHub(2026-09-30 ghfast.top 给
   ubuntu23 只有 6 KB/s,直连约 1 MB/s)。direct 只在机器自己就能直连 GitHub 时能用(ubuntu23 可以);开发路由器卸掉
   内核之后直连 GitHub 不通(拿到真实地址、连接超时),用默认的 ghfast.top。取脚本之前会先停本机内核(内核开着时直连
   GitHub 会被它重置),要用的脚本都先取到才动机器,取不到就把内核拉回来、原样退出;数据备份在 `/root/ob-verify-backup`,
   半路断了下次会沿用、不覆盖。

   OpenWrt 也跑一遍:`sh scripts/release-verify/run-host.sh openbox-dev upgrade MIRROR=http://192.168.3.9:8765 TAG=v0.1.266`。

4. arm64:`sh scripts/release-verify/arm64-vm.sh <产物目录>/open-box-v0.1.266-linux-arm64.tar.gz`(虚拟机准备见 `vz/README.md`)。

5. 改过升级脚本的回退逻辑时,再验一次「新版本面板起不来 → 整体回退」:另打一个故意起不来的包(比如在临时 worktree 里给
   `panel/server/index.mjs` 开头加一行 `throw new Error('verify rollback')`,`OPENBOX_VERSION=v0.1.267 OPENBOX_ALLOW_DIRTY=1` 打 x64),
   另起一个假镜像(`--port 8766 --tag v0.1.267`),在已经装着新版本的机器上:

   ```sh
   sh scripts/release-verify/run-host.sh openbox-dev rollback MIRROR=http://192.168.3.9:8766 TAG=v0.1.266 BAD_TAG=v0.1.267
   ```

## 3. 发布,再用公开命令验一遍

`gh release create` 上传产物,附件里再带一份 `release-notes.md`(和发布说明同一份:面板「发现新版本」弹窗取更新日志时
先直连 GitHub API,不通才从镜像取这个附件,见 panel/server/system/updater.mjs 的 fetchReleaseNotes);同步公开分支(README 一键安装拉的是它);
等镜像缓存跟上之后:

```sh
sh scripts/release-verify/run-host.sh openbox-dev install MIRROR=https://ghfast.top TAG=v0.1.266
sh scripts/release-verify/run-host.sh ubuntu23 install MIRROR=https://ghfast.top TAG=v0.1.266
```
