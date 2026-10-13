#!/usr/bin/env python3
"""Run the common fixture in temporary network namespaces on a dev host.
Does not stop services, change the host routing/firewall, or install packages.
"""
import argparse
import json
import shlex
import subprocess
import threading
import time
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--host', required=True)
p.add_argument('--sudo', action='store_true')
p.add_argument('--platform', required=True, choices=['openwrt', 'linux'])
p.add_argument('--source', default='/tmp/openbox-performance-325')
p.add_argument('--output', required=True)
p.add_argument('--mbps', type=int, default=250)
a = p.parse_args()
stamp = str(int(time.time()))
root = '/tmp/obperf-' + stamp
g, f, c = ['obperf-' + stamp + '-' + s for s in ['g', 'f', 'c']]
prefix = ['sudo', '-n'] if a.sudo else []


def command(args, check=True):
    r = subprocess.run(['ssh', a.host, shlex.join(prefix + args)], capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(shlex.join(args) + ': ' + r.stderr[-1200:])
    return r.stdout.strip()


def shell(script, check=True):
    return command(['sh', '-c', script], check)


def ip(ns, *args):
    return command(['ip', '-n', ns, *args])


def execute(ns, *args):
    return command(['ip', 'netns', 'exec', ns, *args])


def launch(ns, name, executable, *args):
    line = shlex.join(['ip', 'netns', 'exec', ns, 'nice', '-n', '10', executable, *args])
    shell('OPENSSL_CONF=/dev/null OPENBOX_DIRECT_ANSWER_FLAG=' + shlex.quote(root + '/data/flip/direct-answer.on') + ' ' + line + ' </dev/null >' + shlex.quote(root + '/' + name + '.log') + ' 2>&1 & echo $! >' + shlex.quote(root + '/' + name + '.pid'))


def stop(name):
    # Only terminate processes whose command line references this fixture directory.
    shell('p=$(cat ' + shlex.quote(root + '/' + name + '.pid') + ' 2>/dev/null) || exit 0; '
          'tr "\\0" " " </proc/$p/cmdline 2>/dev/null | grep -F ' + shlex.quote(root) + ' >/dev/null || exit 0; '
          'kill "$p" 2>/dev/null || true; for n in 1 2 3; do kill -0 "$p" 2>/dev/null || exit 0; sleep 1; done; kill -9 "$p" 2>/dev/null || true', check=False)


def metrics(pid):
    value = shell('awk \'/VmRSS:/{print "rssKiB",$2}/VmHWM:/{print "hwmKiB",$2}\' /proc/' + str(pid) + '/status; awk \'{print "cpuTicks",$14+$15}\' /proc/' + str(pid) + '/stat')
    return {k: int(v) for k, v in (line.split() for line in value.splitlines())}


def service_pids():
    panel = shell('pgrep -f "/opt/open-box/panel/server/[i]ndex.mjs" | head -n1')
    core = shell('pgrep -f "^/opt/open-box/bin/[s]ing-box" | head -n1')
    return {'panel': int(panel), 'core': int(core)}


result = {'platform': a.platform, 'conditions': {'streams': 4, 'nodes': 1000, 'rateLimitMbps': a.mbps, 'proxy': 'local SOCKS5, no encryption', 'nice': 10}, 'throughput': [], 'samples': []}
before = service_pids()
result['liveServiceBefore'] = {name: {'pid': pid, **metrics(pid)} for name, pid in before.items()}
result['host'] = {'kernel': command(['uname', '-r']), 'arch': command(['uname', '-m']), 'cpuCount': shell('getconf _NPROCESSORS_ONLN 2>/dev/null || grep -c "^processor" /proc/cpuinfo'), 'version': json.loads(command(['cat', '/opt/open-box/meta.json']))['version']}
samples_stop = threading.Event()
thread = None
phase = 'setup'


def sample():
    while not samples_stop.is_set():
        try:
            pid = int(command(['cat', root + '/core.pid']))
            result['samples'].append({'time': time.time(), 'phase': phase, **metrics(pid)})
        except Exception:
            pass  # kernel is deliberately stopped between the two modes
        samples_stop.wait(1)


try:
    shell('mkdir -p ' + shlex.quote(root + '/data') + '; cp -R ' + shlex.quote(a.source + '/flip') + ' ' + shlex.quote(root + '/data/flip') + '; cp ' + shlex.quote(a.source + '/bench-net') + ' ' + shlex.quote(root + '/bench-net') + '; cp ' + shlex.quote(a.source + '/socks.json') + ' ' + shlex.quote(root + '/socks.json') + '; chmod +x ' + shlex.quote(root + '/bench-net'))
    for ns in [g, f, c]:
        command(['ip', 'netns', 'add', ns])
        ip(ns, 'link', 'set', 'lo', 'up')
    ip(g, 'link', 'add', 'eth0', 'type', 'veth', 'peer', 'name', 'eth0', 'netns', f)
    ip(g, 'link', 'add', 'eth1', 'type', 'veth', 'peer', 'name', 'eth0', 'netns', c)
    for ns, interface, address in [(g, 'eth0', '10.77.25.2/24'), (f, 'eth0', '10.77.25.3/24'), (g, 'eth1', '10.78.25.1/24'), (c, 'eth0', '10.78.25.2/24')]:
        ip(ns, 'addr', 'add', address, 'dev', interface)
        ip(ns, 'link', 'set', interface, 'up')
    for address in ['198.51.100.7/32', '198.51.100.8/32']:
        ip(f, 'addr', 'add', address, 'dev', 'lo')
    ip(g, 'route', 'add', 'default', 'via', '10.77.25.3')
    ip(g, 'route', 'add', '198.51.100.0/24', 'via', '10.77.25.3')
    ip(f, 'route', 'add', '10.78.25.0/24', 'via', '10.77.25.2')
    ip(c, 'route', 'add', 'default', 'via', '10.78.25.1')
    execute(g, 'sysctl', '-q', '-w', 'net.ipv4.ip_forward=1')
    execute(g, 'sysctl', '-q', '-w', 'net.ipv4.conf.all.send_redirects=0')
    execute(g, 'sysctl', '-q', '-w', 'net.ipv4.conf.eth1.send_redirects=0')
    ip(g, 'rule', 'add', 'pref', '8999', 'fwmark', '0x2024', 'lookup', 'main')
    ip(g, 'rule', 'add', 'pref', '8998', 'fwmark', '0x02000000/0x02000000', 'goto', '9010')
    command(['mkdir', '-p', '/etc/netns/' + c])
    shell('printf "nameserver 10.78.25.1\\n" >' + shlex.quote('/etc/netns/' + c + '/resolv.conf'))
    launch(f, 'fixture', root + '/bench-net', 'server')
    launch(f, 'proxy', '/opt/open-box/bin/sing-box', 'run', '-c', root + '/socks.json')
    for mode in ['auto', 'tun']:
        stop('core')
        original = command(['cat', a.source + '/' + mode + '.json'])
        config = json.loads(original.replace('/opt/open-box/data/', root + '/data/'))
        # Store only the common fixture configuration; no live configuration is read.
        data = json.dumps(config).encode()
        write = subprocess.run(['ssh', a.host, shlex.join(prefix + ['sh', '-c', 'cat >' + shlex.quote(root + '/config.json')])], input=data)
        write.check_returncode()
        launch(g, 'core', '/opt/open-box/bin/sing-box', 'run', '-D', root + '/data', '-c', root + '/config.json')
        phase = mode + '-idle'
        if thread is None:
            thread = threading.Thread(target=sample)
            thread.start()
        time.sleep(5)
        for kind in ['direct', 'proxy']:
            domain = kind + '.bench.test'
            peer = json.loads(execute(c, 'curl', '--max-time', '15', '--noproxy', '*', '-fsS', 'http://' + domain + ':8080/fixture'))
            if kind == 'proxy':
                assert peer['source'] == '198.51.100.8', peer
            else:
                assert peer['source'] in ['10.78.25.2', '10.77.25.2'], peer
            phase = mode + '-' + kind + '-warmup'
            execute(c, 'nice', '-n', '10', root + '/bench-net', 'load', '--seconds', '3', '--parallel', '4', '--mbps', str(a.mbps), 'http://' + domain + ':8080/bulk')
            phase = mode + '-' + kind
            value = json.loads(execute(c, 'nice', '-n', '10', root + '/bench-net', 'load', '--seconds', '10', '--parallel', '4', '--mbps', str(a.mbps), 'http://' + domain + ':8080/bulk'))
            value.update({'mode': mode, 'kind': kind, 'peerSource': peer['source']})
            assert value['errors'] == 0
            result['throughput'].append(value)
    result['result'] = 'passed'
finally:
    samples_stop.set()
    if thread:
        thread.join()
    for name in ['core', 'proxy', 'fixture']:
        stop(name)
    for ns in [c, g, f]:
        command(['ip', 'netns', 'del', ns], check=False)
    # Only the resolver file created for this unique namespace is removed.
    command(['rm', '-f', '/etc/netns/' + c + '/resolv.conf'], check=False)
    command(['rmdir', '/etc/netns/' + c], check=False)
    after = service_pids()
    result['liveServiceAfter'] = {name: {'pid': pid, **metrics(pid)} for name, pid in after.items()}
    assert before == after, 'live services must retain their PIDs'
    Path(a.output).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'platform': a.platform, 'result': result.get('result', 'failed'), 'liveServicePIDs': 'unchanged', 'throughputMbps': [round(v['mbps'], 1) for v in result['throughput']]}), flush=True)
