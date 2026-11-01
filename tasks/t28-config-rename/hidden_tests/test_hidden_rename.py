"""Hidden tests for t28-config-rename. Every rule is stated in the prompt or shown by the code; see AUDIT.md."""
import io
import json
import os
import tempfile
import unittest
import warnings

from jobd import Daemon, capacity, cli, health, metrics
from jobd.admin import config_show, doctor, report, status
from jobd.config import DeprecatedSettingWarning, SETTINGS, loader
from jobd.errors import ConfigError
from jobd.queue import JobQueue
from jobd.runtime.autoscale import Autoscaler
from jobd.runtime.backpressure import Backpressure
from jobd.runtime.limits import check_consistency
from jobd.runtime.pool import WorkerPool
from jobd.runtime.scheduler import Scheduler


def load_recording(**kwargs):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        settings = loader.load(**kwargs)
    return settings, [w for w in caught if issubclass(w.category, DeprecatedSettingWarning)]


def write(directory, name, text):
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


class Tmp(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = self._tmp.name


class TestNewName(Tmp):
    def test_default_is_unchanged(self):
        s, warned = load_recording(environ={})
        self.assertEqual(s.worker_threads, 4)
        self.assertEqual(warned, [])

    def test_new_name_in_a_json_file(self):
        s, warned = load_recording(path=write(self.dir, "c.json", '{"worker_threads": 8}'), environ={})
        self.assertEqual((s.worker_threads, warned), (8, []))

    def test_new_name_in_an_ini_file(self):
        s, warned = load_recording(path=write(self.dir, "c.ini", "[jobd]\nworker_threads = 6\n"), environ={})
        self.assertEqual((s.worker_threads, warned), (6, []))

    def test_new_name_in_the_environment(self):
        s, warned = load_recording(environ={"JOBD_WORKER_THREADS": "9"})
        self.assertEqual((s.worker_threads, warned), (9, []))

    def test_new_name_as_a_flag(self):
        args = cli.build_parser().parse_args(["--worker-threads", "5", "status"])
        s, warned = load_recording(environ={}, args=args)
        self.assertEqual((s.worker_threads, warned), (5, []))

    def test_the_old_name_is_gone_from_the_schema_and_as_dict(self):
        self.assertIn("worker_threads", SETTINGS)
        self.assertNotIn("queue_workers", SETTINGS)
        self.assertIn("worker_threads", loader.load(environ={}).as_dict())
        self.assertNotIn("queue_workers", loader.load(environ={}).as_dict())

    def test_range_errors_use_the_new_name(self):
        for environ in ({"JOBD_WORKER_THREADS": "0"}, {"JOBD_WORKER_THREADS": "999"}, {"JOBD_WORKER_THREADS": "many"}):
            with self.assertRaises(ConfigError) as ctx:
                loader.load(environ=environ)
            self.assertIn("worker_threads", str(ctx.exception))
            self.assertNotIn("queue_workers", str(ctx.exception))


class TestOldName(Tmp):
    def assertOneWarning(self, warned):
        self.assertEqual(len(warned), 1)
        text = str(warned[0].message)
        self.assertIn("'queue_workers'", text)
        self.assertIn("'worker_threads'", text)

    def test_old_name_in_a_json_file(self):
        s, warned = load_recording(path=write(self.dir, "c.json", '{"queue_workers": 8}'), environ={})
        self.assertEqual(s.worker_threads, 8)
        self.assertOneWarning(warned)

    def test_old_name_in_an_ini_file(self):
        s, warned = load_recording(path=write(self.dir, "c.ini", "[jobd]\nqueue_workers = 6\n"), environ={})
        self.assertEqual(s.worker_threads, 6)
        self.assertOneWarning(warned)

    def test_old_name_in_the_environment(self):
        s, warned = load_recording(environ={"JOBD_QUEUE_WORKERS": "7"})
        self.assertEqual(s.worker_threads, 7)
        self.assertOneWarning(warned)

    def test_old_flag(self):
        args = cli.build_parser().parse_args(["--queue-workers", "3", "status"])
        s, warned = load_recording(environ={}, args=args)
        self.assertEqual(s.worker_threads, 3)
        self.assertOneWarning(warned)

    def test_old_flag_stays_out_of_help(self):
        self.assertNotIn("queue-workers", cli.build_parser().format_help())
        self.assertIn("worker-threads", cli.build_parser().format_help())

    def test_new_name_wins_when_a_source_has_both(self):
        s, warned = load_recording(path=write(self.dir, "c.json", '{"queue_workers": 2, "worker_threads": 12}'),
                                   environ={})
        self.assertEqual(s.worker_threads, 12)
        self.assertOneWarning(warned)

    def test_source_priority_ignores_which_name_was_used(self):
        path = write(self.dir, "c.json", '{"worker_threads": 2}')
        s, _ = load_recording(path=path, environ={"JOBD_QUEUE_WORKERS": "11"})
        self.assertEqual(s.worker_threads, 11)
        path = write(self.dir, "d.json", '{"queue_workers": 2}')
        s, _ = load_recording(path=path, environ={"JOBD_WORKER_THREADS": "13"})
        self.assertEqual(s.worker_threads, 13)

    def test_errors_in_the_old_name_name_the_new_one(self):
        with self.assertRaises(ConfigError) as ctx:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                loader.load(environ={"JOBD_QUEUE_WORKERS": "0"})
        self.assertIn("worker_threads", str(ctx.exception))

    def test_old_attribute_still_reads_with_a_warning(self):
        s = loader.load(environ={"JOBD_WORKER_THREADS": "5"})
        with self.assertWarns(DeprecatedSettingWarning) as ctx:
            self.assertEqual(s.queue_workers, 5)
        self.assertIn("worker_threads", str(ctx.warning))

    def test_reg_loglevel_still_works_everywhere(self):
        s, warned = load_recording(environ={"JOBD_LOGLEVEL": "debug"})
        self.assertEqual((s.log_level, len(warned)), ("debug", 1))
        args = cli.build_parser().parse_args(["--loglevel", "error", "status"])
        s, warned = load_recording(environ={}, args=args)
        self.assertEqual((s.log_level, len(warned)), ("error", 1))


class TestEverythingUsesTheNewName(Tmp):
    def setUp(self):
        super().setUp()
        self.settings = loader.load(environ={"JOBD_WORKER_THREADS": "3", "JOBD_QUEUE_SIZE": "100"})

    def strict(self, fn):
        """Run `fn` with the old attribute turned into an error: no module may still read it."""
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecatedSettingWarning)
            return fn()

    def test_pool_scheduler_autoscaler_backpressure(self):
        s = self.settings
        pool = self.strict(lambda: WorkerPool(s))
        self.assertEqual((pool.size, len(pool.workers)), (3, 3))
        self.assertEqual(self.strict(lambda: Scheduler(s)).max_in_flight, 6)
        scaler = self.strict(lambda: Autoscaler(s))
        self.assertEqual((scaler.desired(1000), scaler.desired(5)), (3, 1))
        roomy = loader.load(environ={"JOBD_WORKER_THREADS": "3"})
        bp = self.strict(lambda: Backpressure(roomy))
        self.assertEqual((bp.warn_depth, bp.level(150), bp.level(149), bp.level(1000)), (150, "warn", "ok", "reject"))

    def test_health_and_metrics(self):
        s = self.settings
        pool, queue = WorkerPool(s), JobQueue(s.queue_size)
        rep = self.strict(lambda: health.report(s, pool, queue))
        self.assertEqual((rep["workers"], rep["idle"]), (3, 3))
        snap = self.strict(lambda: metrics.snapshot(s, pool, queue))
        self.assertEqual(snap["jobd_configured_workers"][0], 3)

    def test_status_and_report_text(self):
        s = self.settings
        pool, queue = WorkerPool(s), JobQueue(s.queue_size)
        text = self.strict(lambda: status.format_status(s, pool, queue))
        self.assertIn("workers: 0/3 busy", text)
        text = self.strict(lambda: report.summary(s, pool, queue))
        self.assertIn("3 worker(s)", text)

    def test_capacity(self):
        s = self.settings
        self.assertEqual(self.strict(lambda: capacity.jobs_per_minute(s, 2.0)), 90.0)
        self.assertTrue(self.strict(lambda: capacity.fits(s, 1.0, 2.0)))
        self.assertFalse(self.strict(lambda: capacity.fits(s, 2.0, 2.0)))

    def test_doctor_messages(self):
        s = loader.load(environ={"JOBD_WORKER_THREADS": "20"})
        findings = self.strict(lambda: doctor.check(s, cpu_count=2))
        text = doctor.format_findings(findings)
        self.assertIn("worker_threads (20) is more than 4x the CPU count (2)", text)
        self.assertNotIn("queue_workers", text)
        one = loader.load(environ={"JOBD_WORKER_THREADS": "1"})
        self.assertIn("worker_threads is 1", doctor.format_findings(doctor.check(one, cpu_count=8)))

    def test_consistency_check_message(self):
        s = loader.load(environ={"JOBD_WORKER_THREADS": "5", "JOBD_QUEUE_SIZE": "2"})
        with self.assertRaises(ConfigError) as ctx:
            self.strict(lambda: check_consistency(s))
        self.assertIn("queue_size (2) must be at least worker_threads (5)", str(ctx.exception))

    def test_config_show_and_defaults(self):
        shown = config_show.show(self.settings)
        self.assertRegex(shown, r"worker_threads\s+= 3")
        self.assertNotIn("queue_workers", shown)
        defaults = json.loads(config_show.dump_defaults())
        self.assertEqual(defaults["worker_threads"], 4)
        self.assertNotIn("queue_workers", defaults)
        self.assertIn("worker_threads", config_show.describe())

    def test_daemon_runs_with_the_new_name(self):
        d = self.strict(lambda: Daemon(self.settings))
        d.registry.register("ok", lambda payload: None)
        for _ in range(9):
            d.submit("ok")
        self.strict(d.run_until_idle)
        self.assertEqual(len(d.finished), 9)


class TestCommandLineAndDocs(Tmp):
    def run_cli(self, *argv, environ=None):
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(list(argv), out=out, err=err, environ=environ or {})
        return code, out.getvalue(), err.getvalue()

    def test_status_with_the_new_flag(self):
        code, out, err = self.run_cli("--worker-threads", "2", "status")
        self.assertEqual((code, err), (0, ""))
        self.assertIn("workers: 0/2 busy", out)

    def test_old_flag_warns_on_stderr_and_still_applies(self):
        code, out, err = self.run_cli("--queue-workers", "2", "status")
        self.assertEqual(code, 0)
        self.assertIn("workers: 0/2 busy", out)
        self.assertIn("'queue_workers'", err)
        self.assertIn("'worker_threads'", err)

    def test_config_show_prints_the_new_name_only(self):
        code, out, err = self.run_cli("config", "show", environ={"JOBD_QUEUE_WORKERS": "6"})
        self.assertEqual(code, 0)
        self.assertRegex(out, r"worker_threads\s+= 6")
        self.assertNotIn("queue_workers", out)
        self.assertIn("deprecated", err)

    def test_the_documentation_lists_the_new_name_and_the_old_one_as_renamed(self):
        with open(os.path.join("docs", "settings.md"), encoding="utf-8") as handle:
            text = handle.read()
        main_table, _, renamed = text.partition("## Renamed settings")
        self.assertIn("| `worker_threads` |", main_table)
        self.assertNotIn("| `queue_workers` |", main_table)
        self.assertIn("`queue_workers`", renamed)
        self.assertIn("`worker_threads`", renamed)
        self.assertIn("`loglevel`", renamed)

    def test_example_configs_use_the_new_name(self):
        for name in ("jobd.json", "jobd.ini"):
            path = os.path.join("examples", name)
            with open(path, encoding="utf-8") as handle:
                self.assertNotIn("queue_workers", handle.read())
            s, warned = load_recording(path=path, environ={})
            self.assertEqual(warned, [])
        self.assertEqual(loader.load(path=os.path.join("examples", "jobd.json"), environ={}).worker_threads, 8)


if __name__ == "__main__":
    unittest.main()
