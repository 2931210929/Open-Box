import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
const [stage, fixture] = process.argv.slice(2)
const port = readFileSync('/opt/open-box/data/panel-port', 'utf8').trim()
const base = `http://127.0.0.1:${port}`
const password = 'isolated-performance-fixture'
const login = await fetch(`${base}/api/auth/${stage === 'seed' ? 'setup' : 'login'}`, {
  method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ password }),
})
assert.equal(login.status, 200)
const cookie = login.headers.get('set-cookie').split(';')[0]
const api = async (path, method = 'GET', body) => {
  const response = await fetch(`${base}/api/openbox${path}`, {
    method, headers: { cookie, 'content-type': 'application/json' },
    ...(body ? { body: JSON.stringify(body) } : {}), signal: AbortSignal.timeout(120000),
  })
  const value = await response.json()
  assert.equal(response.status, 200, path)
  return value
}
if (stage === 'seed') {
  await api('/subscriptions', 'POST', { name: 'PerfFixture', content: `socks5://${fixture}:1080#PerfNode0`, renameOptions: { enabled: false, excludeKeywords: [] } })
  const { groups } = await api('/groups')
  await api('/groups', 'PUT', { groups: [...groups.filter((g) => g.kind), { id: 'perf', name: 'PerfGroup', type: 'selector', mode: 'static', members: ['PerfNode0'], enabled: true }] })
  await api('/profile', 'PUT', {
    ipv6: false, directForNodes: false, rejectQuic: false, clientRoutes: [], bypassPorts: '', directBypass: true,
    dns: { region: 'intl', mode: 'hijack', direct: fixture, proxy: fixture, proxyProtocol: 'udp', split: true, fakeIpForProxy: true, filter: { enabled: false, lists: [], allowDomains: [] }, rewrite: { enabled: false, rules: [] } },
    tun: { autoRedirect: true }, routing: { policies: [{ id: 'direct', name: 'PerfDirect', domain: ['direct.bench.test'], default: '直连', enabled: true }], fallbackDefault: 'PerfGroup' },
  })
} else if (stage === 'batch') {
  const { subscriptions } = await api('/subscriptions')
  const sub = subscriptions.find((s) => s.name === 'PerfFixture')
  assert.ok(sub)
  const content = Array.from({ length: 1000 }, (_, i) => `socks5://${fixture}:${1080 + i}#PerfNode${i}`).join('\n')
  await api(`/subscriptions/${sub.id}`, 'PATCH', { content })
} else if (stage === 'tun' || stage === 'auto') {
  await api('/profile', 'PUT', { tun: { autoRedirect: stage === 'auto' } })
  const result = await api('/service/core/restart', 'POST', {})
  assert.equal(result.ok, true)
} else if (stage === 'start') {
  const result = await api('/service/core/start', 'POST', {})
  assert.equal(result.ok, true)
} else if (stage === 'stop') {
  const result = await api('/service/core/stop', 'POST', {})
  assert.equal(result.ok, true)
}
const status = await api('/service/status')
const profile = (await api('/profile')).profile
assert.equal(status.platform, 'container')
if (stage === 'auto' || stage === 'tun' || stage === 'start') assert.equal(status.core.running, true)
if (stage === 'stop') assert.equal(status.core.running, false)
console.log(JSON.stringify({ stage, version: JSON.parse(readFileSync('/opt/open-box/meta.json')).version, running: status.core.running, autostart: status.core.autostart, mode: status.container.mode, routing: status.container.routing, profilePresent: Boolean(profile) }))
