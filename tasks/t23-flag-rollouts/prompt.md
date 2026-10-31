We want to raise a feature's rollout on a schedule instead of editing the percentage by hand. Add a `ramp`
flag type to `flagkit`:

- A ramp has `steps`, a list of `{"at": <time>, "percent": <number>}`. The steps can be given in any
  order. The list cannot be empty, and no two steps can start at the same time.
- At any moment the ramp's percentage is the percentage of the latest step that has started. Before the
  first step starts, nobody is in.
- Users are in or out the way they are for the other percentage-based flags: a user who is in at 10%
  stays in at 20%.

Build it the way the other flag types are built, so it works everywhere they do (loading from a list of
dicts, `to_dict`, the client, the CLI). Existing behaviour must keep working. Use only the Python
standard library. Existing tests are in `tests/`.
