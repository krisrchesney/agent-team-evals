import contextlib
import inspect
import io
import json
import os
import tempfile
import time
import unittest

from jobflow import ConfigError, Job, Result, load_jobs, run
from jobflow.cli import main
from jobflow.report import render, to_dicts


def jobs_from(*raw):
    return load_jobs({"jobs": list(raw)})


def ok(**kw):
    return kw.get("value", "fine")


def boom(**kw):
    raise RuntimeError(kw.get("message", "boom"))


def flaky(fail_times):
    """An action that raises `fail_times` times and then returns the number of calls."""
    state = {"calls": 0}

    def action(**kw):
        state["calls"] += 1
        if state["calls"] <= fail_times:
            raise RuntimeError(f"fail #{state['calls']}")
        return state["calls"]

    action.state = state
    return action


class Sleeper:
    def __init__(self):
        self.calls = []

    def __call__(self, seconds):
        self.calls.append(seconds)


ACTIONS = {"ok": ok, "boom": boom}


def run_jobs(jobs, actions=None, only=None):
    sleeper = Sleeper()
    results = run(jobs, actions or ACTIONS, sleeper, only)
    return results, sleeper


def by_name(results):
    return {r.name: r for r in results}


class HiddenJobflow(unittest.TestCase):
    # R1: new Job fields and spec keys

    def test_r1_job_defaults_and_field_order(self):
        j = Job("a", "ok")
        self.assertEqual((j.retries, j.backoff, j.allow_failure, j.when), (0, 0.0, False, "success"))
        j = Job("a", "ok", (), {}, 2, 1.5, True, "always")
        self.assertEqual((j.retries, j.backoff, j.allow_failure, j.when), (2, 1.5, True, "always"))

    def test_r1_load_jobs_passes_keys_through(self):
        (j,) = jobs_from({"name": "a", "action": "ok", "retries": 3, "backoff": 0.5,
                          "allow_failure": True, "when": "failure"})
        self.assertEqual((j.retries, j.backoff, j.allow_failure, j.when), (3, 0.5, True, "failure"))

    def test_r1_load_jobs_defaults(self):
        (j,) = jobs_from({"name": "a", "action": "ok"})
        self.assertEqual((j.retries, j.backoff, j.allow_failure, j.when), (0, 0, False, "success"))

    # R2: validation messages

    def test_r2_bad_retries(self):
        for bad in (-1, 1.5, 2.0, True, "2", None):
            with self.assertRaises(ConfigError, msg=repr(bad)) as ctx:
                jobs_from({"name": "x", "action": "ok", "retries": bad})
            self.assertEqual(str(ctx.exception), "job 'x': retries must be a non-negative integer")

    def test_r2_bad_backoff(self):
        for bad in (-0.5, -1, True, "1", None):
            with self.assertRaises(ConfigError, msg=repr(bad)) as ctx:
                jobs_from({"name": "x", "action": "ok", "backoff": bad})
            self.assertEqual(str(ctx.exception), "job 'x': backoff must be a non-negative number")

    def test_r2_bad_allow_failure(self):
        for bad in ("yes", 1, 0, None):
            with self.assertRaises(ConfigError, msg=repr(bad)) as ctx:
                jobs_from({"name": "x", "action": "ok", "allow_failure": bad})
            self.assertEqual(str(ctx.exception), "job 'x': allow_failure must be true or false")

    def test_r2_bad_when(self):
        for bad in ("sometimes", "ALWAYS", "", None, True):
            with self.assertRaises(ConfigError, msg=repr(bad)) as ctx:
                jobs_from({"name": "x", "action": "ok", "when": bad})
            self.assertEqual(str(ctx.exception),
                             "job 'x': when must be one of success, always, failure")

    def test_r2_edge_values_are_accepted(self):
        jobs_from({"name": "x", "action": "ok", "retries": 0, "backoff": 0},
                  {"name": "y", "action": "ok", "backoff": 2, "when": "always"},
                  {"name": "z", "action": "ok", "backoff": 0.25, "allow_failure": False})

    # R3: retries and attempts

    def test_r3_succeeds_on_a_later_try(self):
        action = flaky(2)
        (r,), _ = run_jobs(jobs_from({"name": "a", "action": "f", "retries": 3}), {"f": action})
        self.assertEqual((r.status, r.attempts, r.output, r.error), ("ok", 3, 3, ""))

    def test_r3_all_tries_fail(self):
        action = flaky(99)
        (r,), _ = run_jobs(jobs_from({"name": "a", "action": "f", "retries": 2}), {"f": action})
        self.assertEqual((r.status, r.attempts, r.error), ("failed", 3, "fail #3"))
        self.assertEqual(action.state["calls"], 3)

    def test_r3_no_retries_means_one_try(self):
        action = flaky(99)
        (r,), _ = run_jobs(jobs_from({"name": "a", "action": "f"}), {"f": action})
        self.assertEqual((r.status, r.attempts), ("failed", 1))
        self.assertEqual(action.state["calls"], 1)

    def test_r3_first_try_success_with_retries_set(self):
        action = flaky(0)
        (r,), sleeper = run_jobs(jobs_from({"name": "a", "action": "f", "retries": 5, "backoff": 1}),
                                 {"f": action})
        self.assertEqual((r.status, r.attempts), ("ok", 1))
        self.assertEqual(sleeper.calls, [])

    def test_r3_unknown_action_is_never_retried(self):
        (r,), sleeper = run_jobs(jobs_from({"name": "a", "action": "nope", "retries": 3, "backoff": 1}))
        self.assertEqual((r.status, r.attempts, r.error), ("failed", 1, "unknown action 'nope'"))
        self.assertEqual(sleeper.calls, [])

    def test_r3_skipped_job_has_zero_attempts(self):
        results, _ = run_jobs(jobs_from({"name": "a", "action": "boom"},
                                        {"name": "b", "action": "ok", "deps": ["a"], "retries": 2}))
        self.assertEqual([r.attempts for r in results], [1, 0])

    def test_r3_exception_without_message_uses_class_name(self):
        def silent(**kw):
            raise KeyError()

        (r,), _ = run_jobs(jobs_from({"name": "a", "action": "s", "retries": 1}), {"s": silent})
        self.assertEqual((r.error, r.attempts), ("KeyError", 2))

    def test_r3_result_defaults(self):
        r = Result("a", "ok")
        self.assertEqual((r.attempts, r.stage), (0, 0))

    # R4: backoff

    def test_r4_exponential_sleeps(self):
        _, sleeper = run_jobs(jobs_from({"name": "a", "action": "f", "retries": 3, "backoff": 1.5}),
                              {"f": flaky(99)})
        self.assertEqual(sleeper.calls, [1.5, 3.0, 6.0])

    def test_r4_no_sleep_after_success(self):
        (r,), sleeper = run_jobs(jobs_from({"name": "a", "action": "f", "retries": 3, "backoff": 2}),
                                 {"f": flaky(2)})
        self.assertEqual(r.attempts, 3)
        self.assertEqual(sleeper.calls, [2, 4])

    def test_r4_no_sleep_after_the_last_failed_try(self):
        _, sleeper = run_jobs(jobs_from({"name": "a", "action": "f", "retries": 1, "backoff": 7}),
                              {"f": flaky(99)})
        self.assertEqual(sleeper.calls, [7])

    def test_r4_zero_backoff_never_sleeps(self):
        _, sleeper = run_jobs(jobs_from({"name": "a", "action": "f", "retries": 3}), {"f": flaky(99)})
        self.assertEqual(sleeper.calls, [])

    def test_r4_no_retries_never_sleeps(self):
        _, sleeper = run_jobs(jobs_from({"name": "a", "action": "boom", "backoff": 5}))
        self.assertEqual(sleeper.calls, [])

    def test_r4_sleeps_are_per_job(self):
        _, sleeper = run_jobs(jobs_from(
            {"name": "a", "action": "f", "retries": 1, "backoff": 1},
            {"name": "b", "action": "g", "retries": 2, "backoff": 10}), {"f": flaky(1), "g": flaky(2)})
        self.assertEqual(sleeper.calls, [1, 10, 20])

    def test_r4_run_signature(self):
        params = list(inspect.signature(run).parameters)
        self.assertEqual(params[:4], ["jobs", "actions", "sleep", "only"])
        self.assertIs(inspect.signature(run).parameters["sleep"].default, time.sleep)
        self.assertIsNone(inspect.signature(run).parameters["only"].default)

    # R5: when = success and allow_failure

    def test_r5_allowed_failure_does_not_block(self):
        results, _ = run_jobs(jobs_from(
            {"name": "a", "action": "boom", "allow_failure": True},
            {"name": "b", "action": "ok", "deps": ["a"]}))
        self.assertEqual([(r.name, r.status) for r in results], [("a", "failed"), ("b", "ok")])

    def test_r5_plain_failure_blocks_with_reason(self):
        results, _ = run_jobs(jobs_from(
            {"name": "a", "action": "boom"},
            {"name": "b", "action": "ok", "deps": ["a"]}))
        self.assertEqual((results[1].status, results[1].reason), ("skipped", "dependency 'a' failed"))

    def test_r5_skipped_dependency_blocks(self):
        results, _ = run_jobs(jobs_from(
            {"name": "a", "action": "boom"},
            {"name": "b", "action": "ok", "deps": ["a"]},
            {"name": "c", "action": "ok", "deps": ["b"]}))
        self.assertEqual(results[2].reason, "dependency 'b' skipped")

    def test_r5_allowed_failure_behind_a_skip_still_blocks(self):
        results, _ = run_jobs(jobs_from(
            {"name": "a", "action": "boom"},
            {"name": "b", "action": "boom", "deps": ["a"], "allow_failure": True},
            {"name": "c", "action": "ok", "deps": ["b"]}))
        self.assertEqual([r.status for r in results], ["failed", "skipped", "skipped"])
        self.assertEqual(results[2].reason, "dependency 'b' skipped")

    def test_r5_reason_names_first_blocking_dependency_in_listed_order(self):
        results, _ = run_jobs(jobs_from(
            {"name": "x", "action": "boom"},
            {"name": "y", "action": "boom"},
            {"name": "z", "action": "ok", "deps": ["y", "x"]}))
        self.assertEqual(results[2].reason, "dependency 'y' failed")

    def test_r5_blocking_dependency_is_not_an_allowed_one(self):
        results, _ = run_jobs(jobs_from(
            {"name": "x", "action": "boom", "allow_failure": True},
            {"name": "y", "action": "boom"},
            {"name": "z", "action": "ok", "deps": ["x", "y"]}))
        self.assertEqual(results[2].reason, "dependency 'y' failed")

    def test_r5_allowed_failure_keeps_failed_status_and_error(self):
        results, _ = run_jobs(jobs_from({"name": "a", "action": "boom", "allow_failure": True}))
        self.assertEqual((results[0].status, results[0].error), ("failed", "boom"))

    # R6: when = always / failure

    def test_r6_always_runs_after_failure_and_skip(self):
        results, _ = run_jobs(jobs_from(
            {"name": "a", "action": "boom"},
            {"name": "b", "action": "ok", "deps": ["a"]},
            {"name": "c", "action": "ok", "deps": ["a", "b"], "when": "always"}))
        self.assertEqual([r.status for r in results], ["failed", "skipped", "ok"])

    def test_r6_always_runs_after_success_too(self):
        results, _ = run_jobs(jobs_from(
            {"name": "a", "action": "ok"},
            {"name": "b", "action": "ok", "deps": ["a"], "when": "always"}))
        self.assertEqual([r.status for r in results], ["ok", "ok"])

    def test_r6_always_is_still_ordered_after_its_dependencies(self):
        results, _ = run_jobs(jobs_from(
            {"name": "late", "action": "ok", "deps": ["early"], "when": "always"},
            {"name": "early", "action": "ok"}))
        self.assertEqual([r.name for r in results], ["early", "late"])

    def test_r6_failure_runs_when_a_dependency_failed(self):
        results, _ = run_jobs(jobs_from(
            {"name": "a", "action": "ok"},
            {"name": "b", "action": "boom"},
            {"name": "cleanup", "action": "ok", "deps": ["a", "b"], "when": "failure"}))
        self.assertEqual(results[2].status, "ok")

    def test_r6_failure_counts_allowed_failures(self):
        results, _ = run_jobs(jobs_from(
            {"name": "a", "action": "boom", "allow_failure": True},
            {"name": "alert", "action": "ok", "deps": ["a"], "when": "failure"}))
        self.assertEqual(results[1].status, "ok")

    def test_r6_failure_skipped_when_all_dependencies_ok(self):
        results, _ = run_jobs(jobs_from(
            {"name": "a", "action": "ok"},
            {"name": "alert", "action": "ok", "deps": ["a"], "when": "failure"}))
        self.assertEqual((results[1].status, results[1].reason, results[1].attempts),
                         ("skipped", "no dependency failed", 0))

    def test_r6_failure_skipped_when_dependency_was_only_skipped(self):
        results, _ = run_jobs(jobs_from(
            {"name": "a", "action": "boom"},
            {"name": "b", "action": "ok", "deps": ["a"]},
            {"name": "alert", "action": "ok", "deps": ["b"], "when": "failure"}))
        self.assertEqual((results[2].status, results[2].reason), ("skipped", "no dependency failed"))

    def test_r6_failure_without_dependencies_is_skipped(self):
        results, _ = run_jobs(jobs_from({"name": "alert", "action": "ok", "when": "failure"}))
        self.assertEqual((results[0].status, results[0].reason), ("skipped", "no dependency failed"))

    def test_r6_failure_only_looks_at_direct_dependencies(self):
        results, _ = run_jobs(jobs_from(
            {"name": "a", "action": "boom"},
            {"name": "b", "action": "ok", "deps": ["a"], "when": "always"},
            {"name": "alert", "action": "ok", "deps": ["b"], "when": "failure"}))
        self.assertEqual([r.status for r in results], ["failed", "ok", "skipped"])

    def test_r6_retried_failure_counts_after_the_last_try(self):
        results, _ = run_jobs(jobs_from(
            {"name": "a", "action": "f", "retries": 1},
            {"name": "alert", "action": "ok", "deps": ["a"], "when": "failure"}), {**ACTIONS, "f": flaky(1)})
        self.assertEqual([r.status for r in results], ["ok", "skipped"])

    # R7: only

    def chain(self):
        return jobs_from(
            {"name": "a", "action": "ok"},
            {"name": "b", "action": "ok", "deps": ["a"]},
            {"name": "c", "action": "ok", "deps": ["b"]},
            {"name": "d", "action": "ok"},
            {"name": "e", "action": "ok", "deps": ["d", "a"]})

    def test_r7_only_adds_transitive_dependencies(self):
        results, _ = run_jobs(self.chain(), only=["c"])
        self.assertEqual([r.name for r in results], ["a", "b", "c"])

    def test_r7_several_names(self):
        results, _ = run_jobs(self.chain(), only=["e", "b"])
        self.assertEqual([r.name for r in results], ["a", "b", "d", "e"])

    def test_r7_none_runs_everything(self):
        results, _ = run_jobs(self.chain(), only=None)
        self.assertEqual([r.name for r in results], ["a", "b", "c", "d", "e"])

    def test_r7_unselected_jobs_do_not_run(self):
        calls = []

        def spy(**kw):
            calls.append(kw["tag"])

        jobs = jobs_from({"name": "a", "action": "spy", "args": {"tag": "a"}},
                         {"name": "b", "action": "spy", "args": {"tag": "b"}})
        run(jobs, {"spy": spy}, Sleeper(), ["b"])
        self.assertEqual(calls, ["b"])

    def test_r7_unknown_name(self):
        with self.assertRaises(ConfigError) as ctx:
            run_jobs(self.chain(), only=["a", "nope"])
        self.assertEqual(str(ctx.exception), "unknown job 'nope'")

    def test_r7_policies_still_apply_to_selected_jobs(self):
        jobs = jobs_from({"name": "a", "action": "boom", "allow_failure": True},
                         {"name": "b", "action": "ok", "deps": ["a"]},
                         {"name": "c", "action": "ok"})
        results, _ = run_jobs(jobs, only=["b"])
        self.assertEqual([(r.name, r.status) for r in results], [("a", "failed"), ("b", "ok")])

    # R8: stage

    def test_r8_stages_of_a_diamond(self):
        results, _ = run_jobs(jobs_from(
            {"name": "a", "action": "ok"},
            {"name": "b", "action": "ok", "deps": ["a"]},
            {"name": "c", "action": "ok", "deps": ["a"]},
            {"name": "d", "action": "ok", "deps": ["b", "c"]}))
        self.assertEqual([(r.name, r.stage) for r in results],
                         [("a", 1), ("b", 2), ("c", 2), ("d", 3)])

    def test_r8_stage_is_one_plus_the_highest_dependency_stage(self):
        results, _ = run_jobs(jobs_from(
            {"name": "a", "action": "ok"},
            {"name": "b", "action": "ok", "deps": ["a"]},
            {"name": "c", "action": "ok", "deps": ["b"]},
            {"name": "d", "action": "ok"},
            {"name": "e", "action": "ok", "deps": ["d", "c"]}))
        self.assertEqual(by_name(results)["e"].stage, 4)
        self.assertEqual(by_name(results)["d"].stage, 1)

    def test_r8_skipped_results_have_a_stage(self):
        results, _ = run_jobs(jobs_from(
            {"name": "a", "action": "boom"},
            {"name": "b", "action": "ok", "deps": ["a"]},
            {"name": "c", "action": "ok", "deps": ["b"], "when": "failure"}))
        self.assertEqual([r.stage for r in results], [1, 2, 3])

    def test_r8_stage_with_only(self):
        results, _ = run_jobs(self.chain_for_stage(), only=["c"])
        self.assertEqual([(r.name, r.stage) for r in results], [("a", 1), ("c", 2)])

    def chain_for_stage(self):
        return jobs_from({"name": "a", "action": "ok"}, {"name": "b", "action": "ok"},
                         {"name": "c", "action": "ok", "deps": ["a"]})

    # R9: report

    def test_r9_text_attempts_suffix(self):
        results = [
            Result("a", "ok", attempts=3, stage=1),
            Result("b", "failed", error="boom", attempts=2, stage=1),
            Result("c", "ok", attempts=1, stage=1),
            Result("d", "failed", error="bad", attempts=1, stage=1),
            Result("e", "skipped", reason="dependency 'b' failed", attempts=0, stage=2),
        ]
        self.assertEqual(render(results).splitlines(), [
            "a: ok (3 attempts)",
            "b: failed: boom (2 attempts)",
            "c: ok",
            "d: failed: bad",
            "e: skipped: dependency 'b' failed",
            "5 jobs: 2 ok, 2 failed, 1 skipped",
        ])

    def test_r9_to_dicts_keys(self):
        (d,) = to_dicts([Result("a", "ok", output="hi", attempts=2, stage=3)])
        self.assertEqual(d, {"name": "a", "status": "ok", "output": "hi", "error": "",
                             "reason": "", "attempts": 2, "stage": 3})

    # R10: CLI

    def cli(self, spec, *extra):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = os.path.join(tmp.name, "spec.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(spec, f)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main([path, *extra])
        return code, out.getvalue(), err.getvalue()

    SPEC = {"jobs": [
        {"name": "a", "action": "echo", "args": {"text": "hi"}},
        {"name": "b", "action": "echo", "deps": ["a"]},
        {"name": "c", "action": "echo"},
    ]}

    def test_r10_only_option(self):
        code, out, err = self.cli(self.SPEC, "--only", "b")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out.splitlines(), ["a: ok", "b: ok", "2 jobs: 2 ok, 0 failed, 0 skipped"])

    def test_r10_only_is_repeatable(self):
        code, out, _ = self.cli(self.SPEC, "--only", "a", "--only", "c")
        self.assertEqual(out.splitlines()[-1], "2 jobs: 2 ok, 0 failed, 0 skipped")
        self.assertEqual(code, 0)

    def test_r10_unknown_only_name(self):
        code, out, err = self.cli(self.SPEC, "--only", "zzz")
        self.assertEqual((code, out), (2, ""))
        self.assertEqual(err.strip(), "jobflow: error: unknown job 'zzz'")

    def test_r10_exit_status_one_for_a_plain_failure(self):
        spec = {"jobs": [{"name": "a", "action": "fail", "args": {"message": "x"}}]}
        code, out, _ = self.cli(spec)
        self.assertEqual(code, 1)
        self.assertIn("a: failed: x", out)

    def test_r10_exit_status_zero_when_only_allowed_failures(self):
        spec = {"jobs": [
            {"name": "a", "action": "fail", "allow_failure": True},
            {"name": "b", "action": "echo", "deps": ["a"]},
        ]}
        code, out, _ = self.cli(spec)
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines()[0], "a: failed: failed")

    def test_r10_exit_status_one_if_any_failure_is_not_allowed(self):
        spec = {"jobs": [
            {"name": "a", "action": "fail", "allow_failure": True},
            {"name": "b", "action": "fail"},
        ]}
        self.assertEqual(self.cli(spec)[0], 1)

    def test_r10_skipped_alone_is_exit_zero(self):
        spec = {"jobs": [
            {"name": "a", "action": "echo"},
            {"name": "alert", "action": "echo", "deps": ["a"], "when": "failure"},
        ]}
        code, out, _ = self.cli(spec)
        self.assertEqual(code, 0)
        self.assertIn("alert: skipped: no dependency failed", out)

    def test_r10_json_output_has_attempts_and_stage(self):
        spec = {"jobs": [
            {"name": "a", "action": "fail", "retries": 2},
            {"name": "b", "action": "echo", "deps": ["a"]},
        ]}
        code, out, _ = self.cli(spec, "--json")
        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertEqual([(d["name"], d["status"], d["attempts"], d["stage"]) for d in data],
                         [("a", "failed", 3, 1), ("b", "skipped", 0, 2)])

    def test_r10_config_error_from_new_keys(self):
        spec = {"jobs": [{"name": "a", "action": "echo", "retries": -1}]}
        code, out, err = self.cli(spec)
        self.assertEqual((code, out), (2, ""))
        self.assertEqual(err.strip(), "jobflow: error: job 'a': retries must be a non-negative integer")

    # R11: old behaviour

    def test_r11_declaration_order_among_ready_jobs(self):
        results, _ = run_jobs(jobs_from(
            {"name": "z", "action": "ok"},
            {"name": "m", "action": "ok", "deps": ["z"]},
            {"name": "a", "action": "ok"}))
        self.assertEqual([r.name for r in results], ["z", "m", "a"])

    def test_r11_cycle_and_unknown_dependency_errors(self):
        with self.assertRaises(ConfigError) as ctx:
            jobs_from({"name": "a", "action": "ok", "deps": ["b"]},
                      {"name": "b", "action": "ok", "deps": ["a"]})
        self.assertEqual(str(ctx.exception), "dependency cycle involving: a, b")
        with self.assertRaises(ConfigError) as ctx:
            jobs_from({"name": "a", "action": "ok", "deps": ["ghost"]})
        self.assertEqual(str(ctx.exception), "job 'a' depends on unknown job 'ghost'")

    def test_r11_old_text_report_is_unchanged(self):
        results, _ = run_jobs(jobs_from(
            {"name": "a", "action": "boom", "args": {"message": "no luck"}},
            {"name": "b", "action": "ok", "deps": ["a"]},
            {"name": "c", "action": "ok"}))
        self.assertEqual(render(results).splitlines(), [
            "a: failed: no luck",
            "b: skipped: dependency 'a' failed",
            "c: ok",
            "3 jobs: 1 ok, 1 failed, 1 skipped",
        ])

    def test_r11_old_dict_keys_keep_their_values(self):
        results, _ = run_jobs(jobs_from({"name": "a", "action": "ok", "args": {"value": 7}}))
        d = to_dicts(results)[0]
        self.assertEqual({k: d[k] for k in ("name", "status", "output", "error", "reason")},
                         {"name": "a", "status": "ok", "output": 7, "error": "", "reason": ""})

    def test_r11_run_with_default_actions_registry(self):
        jobs = jobs_from({"name": "a", "action": "echo", "args": {"text": "yo"}})
        (r,) = run(jobs)
        self.assertEqual((r.status, r.output, r.attempts), ("ok", "yo", 1))


if __name__ == "__main__":
    unittest.main()
