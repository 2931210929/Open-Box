import assert from 'node:assert/strict'
import { spawn, execFileSync } from 'node:child_process'
import { appendFileSync, existsSync, readFileSync, statSync, writeFileSync } from 'node:fs'
import { setTimeout as delay } from 'node:timers/promises'
import test from 'node:test'

// Run in a disposable container with --entrypoint node; never against a live gateway.
const file = '/tmp/openbox-core.log'
const helper = '/opt/open-box/docker/bin/openbox-log-rotate'
const logread = '/opt/open-box/docker/bin/logread'
const exited = (child) => new Promise((resolve) => child.once('exit', resolve))
const fill = () => appendFileSync(file, `${'x'.repeat(6 * 1024 * 1024)}\n`)
const waitFor = async (predicate) => {
  for (let i = 0; i < 150; i++) { if (predicate()) return; await delay(100) }
  assert.fail('rotation did not occur within 15 seconds')
}

test('runtime rotation preserves the open writer, bounds archives and keeps recent diagnostics', async () => {
  assert.equal(existsSync('/tmp/openbox-core.pid'), false, 'must run in a disposable container')
  writeFileSync(file, '')
  const inode = statSync(file).ino
  const writer = spawn(process.execPath, ['-e', `const fs=require('node:fs');const fd=fs.openSync('${file}','a');let i=0;setInterval(()=>fs.writeSync(fd,'live-'+(++i)+'\\n'),20)`], { stdio: 'ignore' })
  const worker = spawn(helper, [], { stdio: ['ignore', 'ignore', 'pipe'] })
  const errors = []
  worker.stderr.on('data', (chunk) => errors.push(chunk.toString()))
  try {
    await delay(200)
    fill()
    appendFileSync(file, 'sing-box[123]: FATAL fixture-before-rotation\n')
    await waitFor(() => existsSync(`${file}.1`))
    assert.equal(statSync(file).ino, inode)
    assert.ok(execFileSync(logread, { encoding: 'utf8' }).includes('FATAL fixture-before-rotation'))
    const first = readFileSync(file, 'utf8')
    await delay(150)
    assert.notEqual(readFileSync(file, 'utf8'), first, 'the same writer must keep writing after truncation')
    for (let n = 0; n < 3; n++) {
      fill()
      appendFileSync(file, `round-${n}\n`)
      execFileSync(helper, ['once'])
    }
    assert.ok(existsSync(`${file}.1`) && existsSync(`${file}.2`))
    assert.equal(existsSync(`${file}.3`), false)
    assert.equal(statSync(file).ino, inode)
    assert.ok(execFileSync(logread).length <= 262144)
    appendFileSync(file, 'sing-box[124]: FATAL fixture-after-rotation\n')
    assert.ok(execFileSync(logread, { encoding: 'utf8' }).includes('FATAL fixture-after-rotation'))
    assert.equal(worker.exitCode, null)
    assert.equal(writer.exitCode, null)
    assert.deepEqual(errors, [])
  } finally {
    const workerExit = exited(worker)
    const writerExit = exited(writer)
    worker.kill('SIGTERM'); writer.kill('SIGTERM')
    await Promise.all([workerExit, writerExit])
  }
})
