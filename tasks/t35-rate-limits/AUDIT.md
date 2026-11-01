# t35-rate-limits: where each hidden-test rule is shown

Every rule is written in `repo/docs/SPEC.md` (the prompt points to it). This file is outside `repo/`,
so agents never see it. Test values use binary-friendly numbers (rates 1 and 2, capacities 2 and 5), so
exact float comparisons are safe for any implementation that follows the formulas in the spec.

| Test group | Rule | SPEC.md section |
|---|---|---|
| `TestTokenBucket` fresh/drain/refill/fractional | starts full; refill linear and capped; `retry_after`, `remaining` (floor), `reset_after` formulas; returned state shape | TokenBucket |
| `test_cost_above_capacity_never_succeeds` | `retry_after = None`, updated state returned | TokenBucket |
| `test_backwards_*`, `test_skew_boundary_is_inclusive` | stored time in the future: within `max_skew` it stays and nothing refills (updated never moves back); beyond `max_skew` the anchor resets to now; boundary inclusive | TokenBucket steps 1 to 3 |
| `test_state_is_not_mutated` (window), `is_idle`, `test_validation` | purity, idle definition, argument checks (bools rejected) | Rules intro, TokenBucket, SlidingWindow |
| `TestSlidingWindow` | expiry at `t <= now - window`; cost adds hits; `retry_after` index formula for cost 1, 2, 3; never-succeeds; denial adds nothing; future hits within skew stay, beyond skew move to now, then sorted; `remaining`, `reset_after` | SlidingWindow |
| `TestLimiter` | state saved on denial; independent keys; `peek` saves nothing; `UnknownRule`; key/cost checks before the store is touched; clock read once per call (`hit`, `peek`, `hit_all`, `purge`; not `reset`); `max_skew` forwarded; headers | Limiter |
| `TestHitAll` | smallest remaining wins, first on tie; any denial saves nothing; largest `retry_after` wins, `None` counts as largest; argument errors leave the store empty | Limiter `hit_all` |
| `TestResetAndPurge` | reset one key / one rule; purge removes only idle entries, counts them, skips unknown rule names | Limiter |
| `TestJsonFileStore` | exact layout and `sort_keys`, re-read on every call, missing file never created by reads or deletes, parent directories, atomic write without leftovers, empty rule removed, fresh dicts, `StoreCorrupt` for six bad contents on all five methods with the file untouched | Stores |
| `test_limiter_state_survives_a_restart`, `test_skew_between_processes`, `test_two_limiters_share_one_file` | the parts together: persistence, a clock 100 s behind the stored times, shared file | Stores + rules + Limiter |

What makes it hard: the amount of detail in one spec and the way the parts interact. The three-step
refill and the skew rule (a stored future time is kept inside `max_skew` but reset outside it, and
`updated` never moves backwards), the sliding-window `retry_after` index, `hit_all` saving nothing on
any denial but `hit` saving on denial, one clock read per call, and the file store's corruption and
atomicity rules. Each is stated once, so the agent has to implement and then check each one.
