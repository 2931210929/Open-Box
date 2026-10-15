import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('maintenance', Path(__file__).with_name('release-maintenance.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def release(n, client=None, draft=False, prerelease=False):
    names = [f'open-box-android-{client}.apk'] if client else []
    return {'id': n, 'tag_name': f'v0.1.{n}', 'published_at': f'2026-10-{n:02}T00:00:00Z', 'draft': draft, 'prerelease': prerelease, 'body': 'Changes',
            'assets': [{'name': name, 'state': 'uploaded', 'browser_download_url': f'https://example.test/{n}/{name}'} for name in names + [name + '.sha256' for name in names]]}


class RetentionTests(unittest.TestCase):
    def test_latest_clients_outside_ten_are_carried_before_deletion(self):
        retained, removed, latest, carry, target = m.plan([release(i, '0.1.99' if i == 1 else None) for i in range(1, 12)])
        self.assertEqual([r['id'] for r in retained], list(range(11, 1, -1)))
        self.assertEqual([r['id'] for r in removed], [1])
        self.assertEqual(carry['Android']['release']['id'], 1)
        self.assertEqual(target['id'], 11)

    def test_client_version_beats_release_date_and_drafts_are_untouched(self):
        rs = [release(1, '0.1.10'), release(2, '0.1.9'), release(3, '0.1.11', prerelease=True), release(4, '0.1.12', draft=True)]
        kept, deleted, latest, carry, _ = m.plan(rs)
        self.assertEqual(latest['Android']['release']['id'], 1)
        self.assertEqual(len(kept), 3)
        self.assertFalse(deleted or carry)

    def test_copy_into_window_removes_protection_block(self):
        rs = [release(i, '0.1.10' if i in (1, 11) else None) for i in range(1, 12)]
        _, removed, latest, carry, _ = m.plan(rs)
        self.assertEqual(latest['Android']['release']['id'], 11)
        self.assertFalse(carry)
        self.assertEqual(removed[0]['id'], 1)

    def test_missing_checksum_blocks_plan(self):
        rs = [release(i, '0.1.10' if i == 1 else None) for i in range(1, 12)]
        rs[0]['assets'].pop()
        with self.assertRaisesRegex(ValueError, 'checksum'):
            m.plan(rs)

    def test_links_keep_actual_installer_version_and_are_idempotent(self):
        latest = m.client_assets([release(2, '0.1.10')])
        body = m.with_client_links('Fix #577\n', latest)
        self.assertEqual(m.with_client_links(body, latest), body)
        self.assertIn('open-box-android-0.1.10.apk', body)
        self.assertIn('Fix #577', body)

    def test_incomplete_copy_inside_window_blocks_deletion(self):
        rs = [release(i, '0.1.10' if i in (1, 11) else None) for i in range(1, 12)]
        rs[-1]['assets'].pop()
        with self.assertRaisesRegex(ValueError, 'checksum'):
            m.plan(rs)

    def test_failed_carry_never_deletes(self):
        rs = [release(i, '0.1.10' if i == 1 else None) for i in range(1, 12)]
        with patch.object(m, 'inventory', return_value=rs), patch.object(m, 'preserve_client', side_effect=RuntimeError('download failed')), patch.object(m, 'gh') as gh, patch('sys.argv', ['maintenance', '--apply']):
            with self.assertRaisesRegex(RuntimeError, 'download failed'):
                m.main()
            self.assertFalse(any(call.args[:2] == ('release', 'delete') for call in gh.call_args_list))


if __name__ == '__main__':
    unittest.main()
