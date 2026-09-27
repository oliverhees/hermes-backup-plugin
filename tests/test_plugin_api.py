from __future__ import annotations

import asyncio
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
API_PATH = REPO_ROOT / "dashboard" / "plugin_api.py"


def load_api_module():
    spec = importlib.util.spec_from_file_location("hermes_backup_plugin_api_test", API_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BackupSecurityTest(unittest.TestCase):
    def setUp(self):
        self.api = load_api_module()
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.api.HERMES_HOME = root / "hermes"
        self.api.STATE_DIR = self.api.HERMES_HOME / "aiianer"
        self.target = root / "backups"
        self.target.mkdir()
        self.api._backup_save({"target_dir": str(self.target), "enabled": True, "schedule": "manual", "retention": {"enabled": False, "keep": 5}})

    def tearDown(self):
        self.tmp.cleanup()

    def test_restore_prepare_rejects_archive_symlink_outside_target(self):
        outside = Path(self.tmp.name) / "outside.zip"
        outside.write_bytes(b"not a backup")
        (self.target / "aiianer-backup-2026T000000Z.zip").symlink_to(outside)
        with self.assertRaises(self.api.HTTPException) as caught:
            asyncio.run(self.api.backup_restore_prepare({"name": "aiianer-backup-2026T000000Z.zip"}))
        self.assertEqual(caught.exception.status_code, 404)

    def test_restore_confirm_uses_force_argv_after_exact_confirmation(self):
        archive = self.target / "aiianer-backup-2026T000000Z.zip"
        archive.write_bytes(b"zip")
        state = self.api._backup_state()
        state["restoreNonce"] = "nonce"
        self.api._backup_save(state)
        with mock.patch.object(self.api.subprocess, "run", return_value=mock.Mock(returncode=0)) as run:
            asyncio.run(self.api.backup_restore_confirm({"name": archive.name, "confirmationToken": "nonce", "confirmationText": self.api.RESTORE_CONFIRM.format(name=archive.name), "acknowledged": True}))
        argv = run.call_args.args[0]
        self.assertEqual(argv[1:4], ["import", "--force", str(archive.resolve())])


class CronDeduplicationTest(unittest.TestCase):
    def test_existing_named_job_is_edited_and_cli_failures_are_reported(self):
        api = load_api_module()
        responses = [mock.Mock(returncode=0, stdout="  abcdef123456 [active]\n    Name:      aiianer-backup\n", stderr=""), mock.Mock(returncode=7, stdout="", stderr="boom")]
        with mock.patch.object(api.subprocess, "run", side_effect=responses) as run:
            with self.assertRaises(RuntimeError) as caught:
                api._ensure_backup_cron("daily")
        self.assertIn("CRON_SETUP_FAILED", str(caught.exception))
        self.assertEqual(run.call_args_list[0].args[0][1:3], ["cron", "list"])
        self.assertEqual(run.call_args_list[1].args[0][1:3], ["cron", "edit"])
        self.assertEqual(run.call_args_list[1].args[0][3], "abcdef123456")

    def test_schedule_expression_supports_daily_and_weekly_clock_times(self):
        api = load_api_module()
        self.assertEqual(api._backup_schedule_expression("daily", "02:30", 0), "30 2 * * *")
        self.assertEqual(api._backup_schedule_expression("weekly", "04:05", 6), "5 4 * * 6")

    def test_paused_named_job_is_resumed_after_schedule_edit(self):
        api = load_api_module()
        responses = [
            mock.Mock(returncode=0, stdout="  abcdef123456 [paused]\n    Name:      aiianer-backup\n", stderr=""),
            mock.Mock(returncode=0, stdout="", stderr=""),
            mock.Mock(returncode=0, stdout="", stderr=""),
        ]
        with mock.patch.object(api.subprocess, "run", side_effect=responses) as run:
            api._ensure_backup_cron("weekly", "04:05", 6)
        self.assertEqual(run.call_args_list[1].args[0][1:3], ["cron", "edit"])
        self.assertEqual(run.call_args_list[2].args[0][1:3], ["cron", "resume"])
        self.assertEqual(run.call_args_list[2].args[0][3], "abcdef123456")


class BackupBrowserAndHistoryTest(unittest.TestCase):
    def setUp(self):
        self.api = load_api_module()
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.api.HERMES_HOME = root / "hermes"
        self.api.STATE_DIR = self.api.HERMES_HOME / "aiianer"
        self.folder = root / "backup-root"
        (self.folder / "eins").mkdir(parents=True)
        (self.folder / "zwei").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_backup_browser_returns_only_sorted_directories(self):
        (self.folder / "not-a-folder.txt").write_text("ignore")
        result = asyncio.run(self.api.backup_browse({"path": str(self.folder)}))
        self.assertEqual(result["path"], str(self.folder.resolve()))
        self.assertEqual([entry["name"] for entry in result["directories"]], ["eins", "zwei"])

    def test_backup_browser_rejects_hermes_home_and_symlink_into_it(self):
        self.api.HERMES_HOME.mkdir(parents=True)
        private = self.api.HERMES_HOME / "private"
        private.mkdir()
        alias = Path(self.tmp.name) / "alias-to-hermes"
        alias.symlink_to(self.api.HERMES_HOME, target_is_directory=True)
        for path in (self.api.HERMES_HOME, private, alias):
            with self.assertRaises(self.api.HTTPException) as caught:
                asyncio.run(self.api.backup_browse({"path": str(path)}))
            self.assertEqual(caught.exception.status_code, 422)

    def test_settings_preserve_runner_result_written_during_cron_update(self):
        self.api._backup_save({"state": "failed", "lastErrorCode": "HERMES_COMMAND_FAILED", "history": []})

        def runner_finishes(*_args):
            state = self.api._backup_state()
            state.update({"state": "success", "lastRun": "2026-09-10T12:00:00+00:00", "lastArchive": {"name": "aiianer-backup-test.zip"}, "lastErrorCode": None, "history": [{"at": "2026-09-10T12:00:00+00:00", "state": "success"}]})
            self.api._backup_save(state)

        with mock.patch.object(self.api, "_ensure_backup_cron", side_effect=runner_finishes):
            result = asyncio.run(self.api.backup_settings({"enabled": True, "target_dir": str(self.folder), "schedule": "daily", "scheduleTime": "02:30", "scheduleWeekday": 0, "retention": {"enabled": False, "keep": 5}}))
        self.assertEqual(result["state"], "success")
        self.assertEqual(result["history"][0]["state"], "success")
        self.assertEqual(result["lastArchive"]["name"], "aiianer-backup-test.zip")

    def test_backup_status_exposes_newest_first_run_history(self):
        self.api._backup_save({
            "target_dir": str(self.folder),
            "enabled": True,
            "schedule": "daily",
            "scheduleTime": "02:30",
            "scheduleWeekday": 0,
            "history": [
                {"at": "2026-09-10T10:00:00+00:00", "state": "success"},
                {"at": "2026-09-09T10:00:00+00:00", "state": "failed", "errorCode": "HERMES_COMMAND_FAILED"},
            ],
        })
        result = asyncio.run(self.api.backup_status())
        self.assertEqual(result["scheduleTime"], "02:30")
        self.assertEqual(result["history"][0]["state"], "success")
        self.assertEqual(len(result["history"]), 2)


if __name__ == "__main__":
    unittest.main()
