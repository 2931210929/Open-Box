#!/usr/bin/env python3
"""Plan release retention; --apply preserves client downloads before deleting old Releases."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

CLIENTS = {
    'Android': r'open-box-android-(\d+(?:\.\d+)*)\.apk',
    'macOS arm64': r'open-box-macos-(\d+(?:\.\d+)*)-arm64\.dmg',
    'Windows x64': r'open-box-windows-(\d+(?:\.\d+)*)-x64-setup\.exe',
    'Linux amd64': r'open-box-desktop-linux-(\d+(?:\.\d+)*)-amd64\.deb',
    'iOS': r'open-box-ios-(\d+(?:\.\d+)*)\.ipa',
}
START, END = '<!-- openbox-client-downloads:start -->', '<!-- openbox-client-downloads:end -->'


def gh(*args):
    return subprocess.check_output(['gh', *args], text=True)


def inventory(repo):
    pages = json.loads(gh('api', f'repos/{repo}/releases?per_page=100', '--paginate', '--slurp'))
    return [release for page in pages for release in page]


def client_assets(releases):
    latest = {}
    for release in sorted(releases, key=lambda r: r.get('published_at') or '', reverse=True):
        if release.get('draft') or release.get('prerelease'):
            continue
        for asset in release['assets']:
            for platform, pattern in CLIENTS.items():
                match = re.fullmatch(pattern, asset['name'])
                if not match or asset.get('state', 'uploaded') != 'uploaded':
                    continue
                version = tuple(map(int, match[1].split('.')))
                version += (0,) * (8 - len(version))
                if platform not in latest or version > latest[platform]['version']:
                    latest[platform] = {'version': version, 'release': release, 'asset': asset}
    return latest


def plan(releases, keep=10):
    published = sorted((r for r in releases if not r.get('draft')), key=lambda r: r['published_at'], reverse=True)
    retained, removed = published[:keep], published[keep:]
    latest = client_assets(published)
    retained_ids = {r['id'] for r in retained}
    carry = {p: c for p, c in latest.items() if c['release']['id'] not in retained_ids}
    target = next((r for r in retained if not r.get('prerelease')), None)
    if carry and target is None:
        raise ValueError('No stable release in retained window; cannot safely preserve stable clients')
    # Also reject an incomplete copy left by an interrupted earlier upload.
    for item in latest.values():
        name = item['asset']['name']
        if not any(a['name'] == name + '.sha256' and a.get('state', 'uploaded') == 'uploaded' for a in item['release']['assets']):
            raise ValueError(f'Missing client checksum: {name}; no releases will be deleted')
    return retained, removed, latest, carry, target


def with_client_links(body, latest):
    # Older panels render HTML comments literally. Keep public notes marker-free,
    # and use the visible heading to replace this section on subsequent runs.
    lines = ['### 客户端下载', '']
    for platform, item in latest.items():
        asset = item['asset']
        version = re.fullmatch(CLIENTS[platform], asset['name'])[1]
        lines.append(f"- [{platform} · {version}]({asset['browser_download_url']})")
    section = '\n'.join(lines)
    if START in body:
        if END not in body:
            raise ValueError('Unclosed client download section')
        return re.sub(re.escape(START) + r'.*?' + re.escape(END), lambda _: section, body, flags=re.S).strip() + '\n'
    heading = r'^### 客户端下载[ \t]*(?:\r?\n|$)[\s\S]*?(?=^#{1,3}[ \t]+|\Z)'
    if re.search(heading, body, flags=re.M):
        return re.sub(heading, lambda _: section + '\n\n', body, count=1, flags=re.M).strip() + '\n'
    return body.rstrip() + '\n\n' + section + '\n'


def publish_notes(repo, tag, body):
    # The updater also downloads this asset when the GitHub API is unavailable.
    with tempfile.TemporaryDirectory(prefix='openbox-release-notes-') as tmp:
        note = Path(tmp) / 'release-notes.md'
        note.write_text(body)
        checksum = Path(tmp) / 'release-notes.md.sha256'
        checksum.write_text(hashlib.sha256(note.read_bytes()).hexdigest() + '  release-notes.md\n')
        gh('release', 'upload', tag, str(note), str(checksum), '--repo', repo, '--clobber')
        gh('release', 'edit', tag, '--repo', repo, '--notes-file', str(note))
    remote = json.loads(gh('api', f'repos/{repo}/releases/tags/{tag}'))
    assert remote['body'].strip() == body.strip(), 'Published release body mismatch'
    asset = next(a for a in remote['assets'] if a['name'] == 'release-notes.md')
    assert asset.get('digest') == 'sha256:' + hashlib.sha256(body.encode()).hexdigest(), 'Published notes digest mismatch'


def preserve_client(repo, item, target):
    source, asset = item['release'], item['asset']
    name = asset['name']
    if any(a['name'] == name for a in target['assets']):
        raise ValueError(f'Conflicting client asset in target release: {name}')
    with tempfile.TemporaryDirectory(prefix='openbox-preserve-client-') as tmp:
        gh('release', 'download', source['tag_name'], '--repo', repo, '--pattern', name, '--pattern', name + '.sha256', '--dir', tmp)
        binary = Path(tmp) / name
        checksum = Path(tmp) / (name + '.sha256')
        cells = checksum.read_text().strip().split()
        digest = hashlib.sha256(binary.read_bytes()).hexdigest()
        assert len(cells) == 2 and cells[0] == digest and cells[1].lstrip('*') == name, 'Client checksum mismatch'
        assert binary.stat().st_size == asset['size'], 'Client size mismatch'
        assert not asset.get('digest') or asset['digest'] == 'sha256:' + digest, 'GitHub client digest mismatch'
        gh('release', 'upload', target['tag_name'], str(binary), str(checksum), '--repo', repo)
        current = json.loads(gh('api', f"repos/{repo}/releases/{target['id']}"))
        uploaded = next(a for a in current['assets'] if a['name'] == name)
        assert uploaded.get('digest') == 'sha256:' + digest and uploaded['size'] == asset['size'], 'Carried client verification failed'
        uploaded_checksum = next(a for a in current['assets'] if a['name'] == checksum.name)
        assert uploaded_checksum.get('digest') == 'sha256:' + hashlib.sha256(checksum.read_bytes()).hexdigest(), 'Carried client checksum verification failed'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', default='liandu2024/Open-Box')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--notes-file', type=Path, help='Replace latest stable notes, retaining latest client links')
    args = parser.parse_args()
    if not re.fullmatch(r'[\w.-]+/[\w.-]+', args.repo):
        parser.error('Invalid repository')
    releases = inventory(args.repo)
    retained, removed, latest, carry, target = plan(releases)
    print(json.dumps({'keep': [r['tag_name'] for r in retained], 'delete': [r['tag_name'] for r in removed],
        'latestClients': {p: c['release']['tag_name'] for p, c in latest.items()},
        'carryBeforeDelete': {p: c['asset']['name'] for p, c in carry.items()}}, ensure_ascii=False, indent=2))
    if not args.apply:
        return
    if not target:
        raise ValueError('No stable release to maintain')
    for item in carry.values():
        preserve_client(args.repo, item, target)
    refreshed = inventory(args.repo)
    kept_now, removed_now, clients_now, pending, current = plan(refreshed)
    # Concurrent publishing must be reviewed in another run, not silently delete a changed set.
    assert [r['id'] for r in kept_now] == [r['id'] for r in retained], 'Releases changed during maintenance; nothing deleted'
    assert [r['id'] for r in removed_now] == [r['id'] for r in removed], 'Release deletion set changed; nothing deleted'
    assert not pending, 'Latest clients remain outside retained window; nothing deleted'
    body = args.notes_file.read_text() if args.notes_file else current.get('body', '')
    body = with_client_links(body, clients_now)
    if body != current.get('body', ''):
        publish_notes(args.repo, current['tag_name'], body)
    for release in removed:
        gh('release', 'delete', release['tag_name'], '--repo', args.repo, '--yes')
    final = inventory(args.repo)
    kept_final, extra, _, outstanding, _ = plan(final)
    assert not extra and not outstanding, 'Retention verification failed'
    assert len(kept_final) == min(10, len(retained)), 'Unexpected remaining release count'
    print('Verified: at most 10 published releases; latest client installers and links retained. Drafts and Git tags unchanged.')


if __name__ == '__main__':
    main()
