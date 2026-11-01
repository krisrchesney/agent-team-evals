import unittest

from jobd import Daemon
from jobd.config import loader
from jobd.errors import Conflict, ConfigError


class DaemonTest(unittest.TestCase):
    def test_runs_jobs_and_retries_failures(self):
        d = Daemon(loader.load(environ={"JOBD_RETRY_LIMIT": "1"}))
        calls = []
        d.registry.register("ok", lambda payload: calls.append(payload))
        d.registry.register("bad", lambda payload: 1 / 0)
        d.submit("ok", {"n": 1})
        d.submit("bad")
        d.run_until_idle()
        self.assertEqual(calls, [{"n": 1}])
        self.assertEqual(len(d.dead), 1)
        self.assertEqual(len(d.finished), 1)

    def test_in_flight_limit_is_twice_the_workers(self):
        d = Daemon(loader.load(environ={"JOBD_QUEUE_WORKERS": "2"}))
        d.registry.register("ok", lambda payload: None)
        for _ in range(10):
            d.submit("ok")
        self.assertEqual(d.scheduler.max_in_flight, 4)
        self.assertEqual(d.tick(), 2)

    def test_queue_full(self):
        d = Daemon(loader.load(environ={"JOBD_QUEUE_SIZE": "2", "JOBD_QUEUE_WORKERS": "1"}))
        d.registry.register("ok", lambda payload: None)
        d.submit("ok")
        d.submit("ok")
        with self.assertRaises(Conflict):
            d.submit("ok")

    def test_queue_smaller_than_workers_is_refused(self):
        with self.assertRaises(ConfigError):
            Daemon(loader.load(environ={"JOBD_QUEUE_SIZE": "2", "JOBD_QUEUE_WORKERS": "5"}))


if __name__ == "__main__":
    unittest.main()
