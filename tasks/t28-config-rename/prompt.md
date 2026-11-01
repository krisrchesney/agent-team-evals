`queue_workers` in `jobd` is a bad name: it is the number of worker threads, not workers of a queue. Rename the setting to `worker_threads`. Same type, default and range.

Real deployments still use the old name in their config files, environment and scripts, so it has to keep working everywhere it works today, with a deprecation warning, the same way the other renamed setting already does. Everything that shows or uses the setting should use the new name.

Existing behaviour must keep working. Use only the Python standard library. Existing tests are in `tests/`.
