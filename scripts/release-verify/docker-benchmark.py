#!/usr/bin/env python3
"""Isolated, offline Docker performance check. Run on the Docker host.

The verify directory must contain benchmark-api.mjs, benchmark-metrics.sh,
and the native bench-net binary. All created containers/network are removed.
"""
import argparse
import json
import os
import subprocess
import threading
import time
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--arch', required=True, choices=['x64', 'arm64'])
p.add_argument('--root', required=True)
p.add_argument('--baseline', default='open-box:0.1.324')
p.add_argument('--candidate', default='open-box:logrotate-test')
p.add_argument('--seconds', type=int, default=15)
p.add_argument('--mbps', type=int, default=1000)
p.add_argument('--cases', default='baseline,default,heap128,gc60')
p.add_argument('--subnet', default='10.77.25')
p.add_argument('--label', default='target1000')
a = p.parse_args()
assert 5 <= a.seconds <= 60 and 0 <= a.mbps <= 10000
root = Path(a.root).resolve()
verify = root / 'verify'
results = root / 'results'
results.mkdir(exist_ok=True)
stamp = str(int(time.time()))
prefix = 'obperf-' + a.arch + '-' + stamp
network, fixture, client, gateway = [prefix + s for s in ['-net', '-fixture', '-client', '-gateway']]
F, G, C = [a.subnet + s for s in ['.3', '.2', '.4']]


def docker(*args, check=True):
    r = subprocess.run(['docker', *map(str, args)], capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError('docker ' + ' '.join(map(str, args)) + ': ' + r.stderr[-1500:])
    return r.stdout.strip()


def api(stage):
    return json.loads(docker('exec', gateway, '/opt/open-box/node/bin/node', '/verify/benchmark-api.mjs', stage, F))


def wait_panel():
    for _ in range(45):
        r = subprocess.run(['docker', 'exec', gateway, 'curl', '-fsS', 'http://127.0.0.1:2026/api/health'], capture_output=True)
        if r.returncode == 0:
            return
        time.sleep(1)
    raise RuntimeError('benchmark panel did not start')


class Samples:
    def __init__(self):
        self.rows = []
        self.phase = 'setup'
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.loop)
        self.thread.start()

    def loop(self):
        while not self.stop.is_set():
            started = time.monotonic()
            try:
                row = {'time': time.time(), 'phase': self.phase}
                for line in docker('exec', gateway, 'sh', '/verify/benchmark-metrics.sh').splitlines():
                    key, value = line.split()
                    row[key] = int(value)
                self.rows.append(row)
            except Exception as e:
                self.rows.append({'time': time.time(), 'phase': self.phase, 'error': str(e)})
            self.stop.wait(max(0, 1 - (time.monotonic() - started)))

    def close(self):
        self.stop.set()
        self.thread.join()


def pause(samples, phase, seconds):
    samples.phase = phase
    time.sleep(seconds)


def peer(domain):
    value = json.loads(docker('exec', client, 'curl', '--max-time', '10', '--noproxy', '*', '-fsS', 'http://' + domain + ':8080/fixture'))
    assert value['source'] == (G if domain.startswith('direct.') else '198.51.100.8'), value


def load(domain, seconds):
    return json.loads(docker('exec', client, '/verify/bench-net', 'load', '--seconds', seconds, '--parallel', '4', '--mbps', a.mbps, 'http://' + domain + ':8080/bulk'))


def case(name):
    image = a.baseline if name == 'baseline' else a.candidate
    directory = root / (stamp + '-' + name)
    directory.mkdir()
    (directory / 'etc').mkdir()
    (directory / 'data').mkdir()
    env = ['OPENBOX_PANEL_HEAP_MB=160']
    if name == 'heap128':
        env = ['OPENBOX_PANEL_HEAP_MB=128']
    elif name == 'gc60':
        env = ['OPENBOX_PANEL_HEAP_MB=64', 'GOMEMLIMIT=60MiB', 'GOGC=30']
    elif name not in ['baseline', 'default']:
        raise ValueError(name)
    args = ['run', '-d', '--name', gateway, '--network', network, '--ip', G, '--cpus', '1', '--memory', '512m',
            '--cap-add', 'NET_ADMIN', '--cap-add', 'NET_RAW', '--device', '/dev/net/tun',
            '--sysctl', 'net.ipv4.ip_forward=1', '--sysctl', 'net.ipv4.conf.all.send_redirects=0',
            '--sysctl', 'net.ipv4.conf.default.send_redirects=0',
            '-v', str(directory / 'etc') + ':/opt/open-box/etc', '-v', str(directory / 'data') + ':/opt/open-box/data',
            '-v', str(verify) + ':/verify:ro']
    for value in env:
        args += ['-e', value]
    docker(*args, image)
    samples = None
    try:
        wait_panel()
        docker('exec', gateway, 'ip', 'route', 'add', '198.51.100.0/24', 'via', F)
        # The fixture does not forward packets: default traffic cannot reach WAN.
        # Docker --internal rejects our synthetic public IP aliases on the bridge.
        docker('exec', gateway, 'ip', 'route', 'replace', 'default', 'via', F)
        samples = Samples()
        api('seed')
        pause(samples, 'panel-idle', 5)
        samples.phase = '1000-node-import'
        api('batch')
        api('start')
        pause(samples, 'kernel-idle', 10)
        throughputs = []
        for mode in ['auto', 'tun']:
            api(mode)
            (directory / (mode + '-config.json')).write_text((directory / 'etc/config.json').read_text())
            for kind in ['direct', 'proxy']:
                domain = kind + '.bench.test'
                peer(domain)
                samples.phase = mode + '-' + kind + '-warmup'
                load(domain, 3)
                for repeat in range(2):
                    samples.phase = mode + '-' + kind + '-' + str(repeat + 1)
                    r = load(domain, a.seconds)
                    r.update({'mode': mode, 'kind': kind, 'repeat': repeat + 1})
                    assert r['errors'] == 0 and r['bytes'] > 0
                    throughputs.append(r)
        core_pid = docker('exec', gateway, 'cat', '/tmp/openbox-core.pid')
        panel_pid = docker('exec', gateway, 'cat', '/tmp/openbox-panel.pid')
        if name == 'default':
            samples.phase = 'rotation-under-load'
            job = subprocess.Popen(['docker', 'exec', client, '/verify/bench-net', 'load', '--seconds', '15', '--parallel', '4', '--mbps', str(a.mbps), 'http://proxy.bench.test:8080/bulk'], stdout=subprocess.PIPE, text=True)
            docker('exec', gateway, 'sh', '-c', "head -c 6291456 /dev/zero | tr '\\0' x >> /tmp/openbox-core.log; printf '\\nrotation-under-load\\n' >> /tmp/openbox-core.log")
            result = json.loads(job.communicate(timeout=30)[0])
            assert job.returncode == 0 and result['errors'] == 0
            assert core_pid == docker('exec', gateway, 'cat', '/tmp/openbox-core.pid')
            assert panel_pid == docker('exec', gateway, 'cat', '/tmp/openbox-panel.pid')
            docker('exec', gateway, 'test', '-f', '/tmp/openbox-core.log.1')
        state = api('status')
        assert state['running'] and state['autostart']
        samples.close()
        sampled_errors = [row for row in samples.rows if 'error' in row]
        assert not sampled_errors, sampled_errors
        output = {'arch': a.arch, 'case': name, 'image': image, 'env': env, 'limits': {'gatewayCPUs': 1, 'memoryMiB': 512, 'fixtureCPUs': 0.5, 'clientCPUs': 0.5},
                  'conditions': {'nodes': 1000, 'proxy': 'local SOCKS5, no encryption', 'streams': 4, 'rateLimitMbps': a.mbps}, 'throughput': throughputs, 'samples': samples.rows,
                  'containerState': json.loads(docker('inspect', '--format', '{{json .State}}', gateway))}
        path = results / (a.arch + '-' + name + ('' if a.label == 'target1000' else '-' + a.label) + '.json')
        path.write_text(json.dumps(output, indent=2) + '\n')
        print(json.dumps({'arch': a.arch, 'case': name, 'result': 'passed', 'results': str(path), 'throughputMbps': [round(r['mbps'], 1) for r in throughputs]}), flush=True)
    finally:
        if samples:
            samples.close()
        docker('rm', '-f', gateway, check=False)


try:
    arch = json.loads(docker('image', 'inspect', a.candidate))[0]['Architecture']
    assert arch == ('amd64' if a.arch == 'x64' else 'arm64')
    metadata = {'arch': a.arch, 'uname': os.uname().release, 'cpus': os.cpu_count(), 'docker': docker('version', '--format', '{{.Server.Version}}'), 'loadavg': Path('/proc/loadavg').read_text().strip() if Path('/proc/loadavg').exists() else '', 'created': time.time()}
    (results / (a.arch + '-host.json')).write_text(json.dumps(metadata, indent=2) + '\n')
    docker('network', 'create', '--subnet', a.subnet + '.0/24', network)
    socks = {'dns': {'servers': [{'type': 'udp', 'tag': 'fixture', 'server': '127.0.0.1'}], 'final': 'fixture'}, 'route': {'default_domain_resolver': 'fixture'}, 'log': {'level': 'warn'},
             'inbounds': [{'type': 'socks', 'tag': 'fixture', 'listen': '0.0.0.0', 'listen_port': 1080}], 'outbounds': [{'type': 'direct', 'tag': 'direct', 'inet4_bind_address': '198.51.100.8'}]}
    (verify / 'socks.json').write_text(json.dumps(socks))
    docker('run', '-d', '--name', fixture, '--network', network, '--ip', F, '--cpus', '0.5', '--cap-add', 'NET_ADMIN', '-v', str(verify) + ':/verify:ro', '--entrypoint', '/bin/sh', a.baseline,
           '-c', 'ip addr add 198.51.100.7/32 dev lo; ip addr add 198.51.100.8/32 dev lo; /opt/open-box/bin/sing-box run -c /verify/socks.json & exec /verify/bench-net server')
    docker('run', '-d', '--name', client, '--network', network, '--ip', C, '--cpus', '0.5', '--cap-add', 'NET_ADMIN', '-v', str(verify) + ':/verify:ro', '--entrypoint', '/bin/sh', a.baseline,
           '-c', 'ip route replace default via ' + G + '; printf "nameserver ' + G + '\n" > /etc/resolv.conf; exec sleep 3600')
    for name in a.cases.split(','):
        case(name)
except Exception:
    print(docker('logs', '--tail', '30', gateway, check=False), flush=True)
    print(docker('logs', '--tail', '10', fixture, check=False), flush=True)
    raise
finally:
    for name in [gateway, client, fixture]:
        docker('rm', '-f', name, check=False)
    docker('network', 'rm', network, check=False)
