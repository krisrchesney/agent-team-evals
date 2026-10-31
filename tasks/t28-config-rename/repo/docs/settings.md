# jobd settings

Every setting can be given in a config file (`--config jobd.json` or `jobd.ini`, section `[jobd]`),
as an environment variable (`JOBD_<NAME>`), or as a flag (`--<name-with-dashes>`). Later sources win:
defaults, then the file, then the environment, then flags.

| Setting | Type | Default | Meaning |
|---|---|---|---|
| `log_level` | str | `info` | Verbosity of the log: debug, info, warning or error. |
| `queue_workers` | int | `4` | How many worker threads run jobs at the same time (1 to 256). |
| `queue_size` | int | `1000` | Most jobs that may wait in the queue. Must be at least `queue_workers`. |
| `retry_limit` | int | `3` | How many times a failed job is retried (0 to 20). |
| `retry_backoff_s` | float | `1.5` | Seconds before the first retry; doubles each time. |
| `poll_interval_s` | float | `0.5` | Seconds between looks at an empty queue. |
| `metrics_port` | int | `9102` | Port for the metrics endpoint; 0 turns it off. |
| `shutdown_grace_s` | float | `30` | Seconds running jobs get to finish on shutdown. |
| `heartbeat_s` | float | `5` | Seconds between heartbeats to peers. |
| `pool_name` | str | `default` | Name of this worker pool in logs and metrics. |
| `max_payload_kb` | int | `256` | Largest accepted job payload, in kilobytes. |
| `job_timeout_s` | float | `300` | Seconds before a running job is cancelled. |

## Renamed settings

The old name still works in every place above. It prints a warning and will be removed in 2.0.

| Old name | New name | Since |
|---|---|---|
| `loglevel` | `log_level` | 1.2 |
