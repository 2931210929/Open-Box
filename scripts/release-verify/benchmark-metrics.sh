#!/bin/sh
# 采样不启动另一个 Node 进程，避免把采样器自身的堆误算成面板开销。
for name in panel core; do
 file=/tmp/openbox-$name.pid
 pid=$(cat "$file" 2>/dev/null) || continue
 [ -r "/proc/$pid/status" ] || continue
 printf '%s.pid %s\n' "$name" "$pid"
 awk -v name="$name" '/VmRSS:/{print name ".rssKiB",$2} /VmHWM:/{print name ".hwmKiB",$2}' "/proc/$pid/status"
 awk -v name="$name" '{print name ".cpuTicks",$14+$15}' "/proc/$pid/stat"
done
for metric in memory.current memory.peak cpu.stat; do
 [ -r "/sys/fs/cgroup/$metric" ] || continue
 if [ "$metric" = cpu.stat ]; then
  awk '/^usage_usec /{print "cgroup.cpuUsec",$2} /^nr_throttled /{print "cgroup.throttled",$2} /^throttled_usec /{print "cgroup.throttledUsec",$2}' /sys/fs/cgroup/cpu.stat
 else
  printf 'cgroup.%s %s\n' "$metric" "$(cat "/sys/fs/cgroup/$metric")"
 fi
done
[ ! -r /sys/fs/cgroup/memory.stat ] || awk '/^inactive_file /{print "cgroup.inactiveFile",$2}' /sys/fs/cgroup/memory.stat
