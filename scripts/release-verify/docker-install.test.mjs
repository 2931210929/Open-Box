import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const repo = fileURLToPath(new URL('../../', import.meta.url))
const installer = path.join(repo, 'docker/install.sh')
const helper = path.join(repo, 'docker/bin/panel-port')
// The installer runs with a fake Linux Docker host. It must never touch the
// developer's daemon, LAN, containers or configuration during unit tests.
const cli = `#!${process.execPath}
const fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto');
const command = path.basename(process.argv[1]), args = process.argv.slice(2);
const file = process.env.TEST_DOCKER_STATE, state = JSON.parse(fs.readFileSync(file));
const save = () => fs.writeFileSync(file, JSON.stringify(state));
const fail = () => { save(); process.exit(1) };
const output = value => { console.log(value); save(); process.exit(0) };
state.calls.push([command, ...args]);
const option = key => args[args.indexOf(key) + 1];
const last = args.at(-1);
if (command === 'uname') output('Linux');
if (command === 'sleep') output('');
if (command === 'ip') {
 if (args.includes('default')) output('default via 192.168.1.1 dev eth0');
 if (args.includes('scope')) output('192.168.1.0/24 proto kernel scope link src 192.168.1.100');
 if (args.includes('addr')) output('2: eth0 inet 192.168.1.100/24 scope global eth0');
 output('2: eth0: <UP>');
}
if (command === 'sha256sum') output(crypto.createHash('sha256').update(fs.readFileSync(last)).digest('hex') + '  ' + last);
if (command === 'curl') {
 if (state.offline) fail();
 const url = args.find(arg => arg.startsWith('https:')), dest = option('-o');
 fs.writeFileSync(dest, url.endsWith('/latest') ? JSON.stringify({tag_name:'v0.1.325'}) : url.endsWith('.sha256') ? crypto.createHash('sha256').update('test image').digest('hex') : 'test image');
 output('');
}
if (command !== 'docker') fail();
if (args[0] === 'info') output(option('--format').includes('OSType') ? 'linux' : state.arch);
if (args[0] === 'image' && args[1] === 'inspect') { if (!state.images[last]) fail(); output(args.includes('--format') ? state.images[last] : '[]') }
if (args[0] === 'load') { state.images['open-box:0.1.325'] = state.arch; output('Loaded image: open-box:0.1.325') }
if (args[0] === 'container' && args[1] === 'inspect') { if (!state.containers[last]) fail(); output('[]') }
if (args[0] === 'inspect') {
 const c = state.containers[last]; if (!c) fail(); const format = option('--format');
 if (format.includes('State.Running')) output(String(c.running));
 const key = format.match(/Labels "([^"]+)"/)[1]; output(c.labels[key] || '');
}
if (args[0] === 'network') {
 if (args[1] === 'inspect') { const n = state.networks[last]; if (!n) fail(); output(args.includes('--format') ? [n.driver,n.parent,n.subnet,n.gateway].join(' ') : '[]') }
 if (args[1] === 'create') { state.networks[last] = {driver:option('-d'),parent:option('-o').split('=')[1],subnet:option('--subnet'),gateway:option('--gateway')}; output('network-id') }
 if (args[1] === 'disconnect') { state.containers[last].network = ''; output('') }
 if (args[1] === 'connect') { const c = state.containers[last]; c.network = args.at(-2); c.ip = option('--ip'); output('') }
}
if (args[0] === 'stop' || args[0] === 'start') { state.containers[last].running = args[0] === 'start'; output(last) }
if (args[0] === 'rename') { state.containers[last] = state.containers[args[1]]; delete state.containers[args[1]]; output('') }
if (args[0] === 'rm') { delete state.containers[last]; output(last) }
if (args[0] === 'run') {
 const labels = {}; for (let i=0;i<args.length;i++) if (args[i] === '--label') { const at=args[i+1].indexOf('='); labels[args[i+1].slice(0,at)] = args[i+1].slice(at+1) }
 const name = option('--name'); if (state.containers[name]) fail();
 // Stopped containers reserve their static IP until disconnected.
 if (Object.values(state.containers).some(c => c.network === option('--network') && c.ip === option('--ip'))) fail();
 state.containers[name] = { image:last, running:true, labels, network:option('--network'), ip:option('--ip'), args };
 output('container-id');
}
if (args[0] === 'exec') { const c = state.containers[args[1]]; if (!c || !c.running || state.failedImages.includes(c.image)) fail(); output('{"ok":true}') }
fail();
`
const setup = (t, { arch = 'amd64', offline = true } = {}) => {
  const temp = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'openbox-docker-install-')))
  t.after(() => fs.rmSync(temp, { recursive: true, force: true }))
  const bin = path.join(temp, 'bin'), dir = path.join(temp, 'installation'), file = path.join(temp, 'state.json')
  fs.mkdirSync(bin)
  for (const command of ['docker', 'ip', 'uname', 'curl', 'sleep', 'sha256sum']) fs.writeFileSync(path.join(bin, command), cli, { mode: 0o755 })
  const initial = { arch, offline, calls: [], images: { 'open-box:local-test': arch }, networks: {}, containers: {}, failedImages: [] }
  fs.writeFileSync(file, JSON.stringify(initial))
  const state = () => JSON.parse(fs.readFileSync(file))
  const setState = (s) => fs.writeFileSync(file, JSON.stringify(s))
  const run = (args = []) => spawnSync('sh', [installer, '--dir', dir, ...args], { encoding: 'utf8', env: { ...process.env, PATH: `${bin}:${process.env.PATH}`, TEST_DOCKER_STATE: file } })
  return { temp, dir, file, run, state, setState }
}
const success = r => assert.equal(r.status, 0, r.stdout + r.stderr)
const firstInstall = h => success(h.run(['--offline', '--image', 'open-box:local-test', '--ip', '192.168.1.2']))

test('fresh x64 and arm64 installs infer LAN settings, use 3036 and stay offline', t => {
  for (const arch of ['amd64', 'arm64']) {
    const h = setup(t, { arch }); firstInstall(h)
    const s = h.state(), c = s.containers['open-box']
    assert.equal(c.ip, '192.168.1.2')
    assert.deepEqual(s.networks['open-box-lan'], { driver:'macvlan', parent:'eth0', subnet:'192.168.1.0/24', gateway:'192.168.1.1' })
    assert.ok(c.args.includes('OPENBOX_PANEL_PORT=3036'))
    assert.equal(c.args[c.args.indexOf('--pull') + 1], 'never')
    assert.ok(c.args.includes(`${h.dir}/data:/opt/open-box/data`))
    assert.equal(s.calls.filter(c => c[0] === 'curl').length, 0)
    assert.equal(fs.statSync(path.join(h.dir, 'install.env')).mode & 0o777, 0o600)
    assert.equal(fs.existsSync(path.join(h.dir, '.install.lock')), false)
  }
})

test('online install selects the architecture, checks SHA256 and loads the release image', t => {
  const h = setup(t, { arch:'arm64', offline:false })
  success(h.run(['--ip','192.168.1.2','--driver','ipvlan']))
  assert.equal(h.state().containers['open-box'].image, 'open-box:0.1.325')
  assert.ok(h.state().calls.some(c => c[0] === 'curl' && c.some(a => a.endsWith('/open-box-v0.1.325-docker-linux-arm64.tar.gz'))))
  assert.ok(h.state().calls.some(c => c[0] === 'sha256sum'))
  assert.equal(h.state().networks['open-box-lan'].driver, 'ipvlan')
})

test('reinstall keeps legacy ports and data, releases the old static IP and removes only its backup', t => {
  const h = setup(t)
  fs.mkdirSync(path.join(h.dir, 'data'), {recursive:true})
  fs.writeFileSync(path.join(h.dir,'data/panel-port'),'2026\n')
  fs.writeFileSync(path.join(h.dir,'data/user-state'),'preserve')
  firstInstall(h)
  const before = fs.readFileSync(path.join(h.dir,'install.env'),'utf8')
  success(h.run(['--offline']))
  assert.ok(h.state().containers['open-box'].args.includes('OPENBOX_PANEL_PORT=2026'))
  assert.equal(fs.readFileSync(path.join(h.dir,'data/user-state'),'utf8'),'preserve')
  assert.equal(fs.readFileSync(path.join(h.dir,'install.env'),'utf8'), before)
  assert.deepEqual(Object.keys(h.state().containers), ['open-box'])
  assert.ok(h.state().calls.some(c => c[0] === 'docker' && c[1] === 'network' && c[2] === 'disconnect'))
  success(h.run(['--offline','--port','3037']))
  assert.ok(h.state().containers['open-box'].args.includes('OPENBOX_PANEL_PORT=3037'))
  success(h.run(['--offline']))
  assert.ok(h.state().containers['open-box'].args.includes('OPENBOX_PANEL_PORT=3037'))
})

test('a failed upgrade restores the old image, running/stopped state, IP and installer metadata', t => {
  for (const running of [true,false]) {
    const h = setup(t); firstInstall(h)
    const s = h.state(); s.containers['open-box'].running = running
    s.images['open-box:bad'] = 'amd64'; s.failedImages.push('open-box:bad'); h.setState(s)
    const before = fs.readFileSync(path.join(h.dir,'install.env'),'utf8')
    const result = h.run(['--offline','--image','open-box:bad'])
    assert.notEqual(result.status,0)
    const c = h.state().containers['open-box']
    assert.equal(c.image,'open-box:local-test')
    assert.equal(c.running,running)
    assert.equal(c.network,'open-box-lan')
    assert.equal(c.ip,'192.168.1.2')
    assert.equal(fs.readFileSync(path.join(h.dir,'install.env'),'utf8'), before)
    assert.deepEqual(Object.keys(h.state().containers),['open-box'])
    assert.equal(fs.existsSync(path.join(h.dir,'.install.lock')), false)
  }
})

test('bad archives, foreign containers and conflicting networks do not replace an existing installation', t => {
  const h = setup(t); firstInstall(h)
  const archive = path.join(h.temp,'image.tar.gz')
  fs.writeFileSync(archive,'corrupted'); fs.writeFileSync(`${archive}.sha256`,'0'.repeat(64))
  const count = h.state().calls.length
  assert.notEqual(h.run(['--offline','--archive',archive]).status,0)
  assert.ok(!h.state().calls.slice(count).some(c => c[0] === 'docker' && ['load','stop','run','rm','rename'].includes(c[1])))
  let s = h.state(); s.containers['open-box'].labels['com.openbox.install-dir']='/someone-else'; h.setState(s)
  assert.notEqual(h.run(['--offline','--image','open-box:local-test']).status,0)
  assert.equal(h.state().containers['open-box'].running,true)
  s = h.state(); s.containers['open-box'].labels['com.openbox.install-dir']=h.dir; s.networks['open-box-lan'].parent='other-interface'; h.setState(s)
  assert.notEqual(h.run(['--offline','--image','open-box:local-test']).status,0)
  assert.equal(h.state().containers['open-box'].running,true)
})

test('panel port selection shares entrypoint and healthcheck defaults while preserving old volumes', t => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(),'openbox-docker-port-'))
  t.after(() => fs.rmSync(temp,{recursive:true,force:true}))
  fs.mkdirSync(path.join(temp,'data'))
  const readPort = port => spawnSync('sh',['-c','. "$1"; printf "%s" "$PORT"','sh',helper],{encoding:'utf8',env:{...process.env,OPENBOX_ROOT:temp,OPENBOX_PANEL_PORT:port}})
  assert.equal(readPort('').stdout,'3036')
  fs.writeFileSync(path.join(temp,'data/panel-port'),'2026\n')
  assert.equal(readPort('').stdout,'2026')
  assert.equal(readPort('3037').stdout,'3037')
  for (const port of ['0','03036','65536','3036;echo unsafe','53','7853','7854','7891','9095']) assert.notEqual(readPort(port).status,0)
})
