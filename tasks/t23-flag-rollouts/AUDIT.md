# t23-flag-rollouts: where each hidden-test rule is shown

The repo has no docs folder: every rule the hidden tests check, beyond the prompt, is shown by the four
existing flag types (`boolean`, `rollout`, `schedule`, `segment` in `flagkit/types/`), by the base class
in `flag.py`, or by the helpers. This file is outside `repo/`, so agents never see it.

| Test | Rule | Shown by (repo/) |
|---|---|---|
| `test_ramp_is_a_supported_type` | the module is registered with `@flag_type("ramp")` and imported in `types/__init__.py` | `types/__init__.py` comment; `flag.py` |
| `test_before_the_first_step_nobody_is_in` | before the first step: off, reason `outside_ramp` | prompt; reason naming in `rollout.py` / `schedule.py` |
| `test_latest_started_step_wins_whatever_the_order` | pick the step with the greatest time that has started, not the last in the list | prompt ("any order", "latest step that has started") |
| `test_a_step_counts_from_the_moment_it_starts`, `test_one_second_before...` | a time boundary is inclusive at its start (`start <= now`) | `types/schedule.py` |
| `test_percentage_can_go_down`, `test_last_step_holds_forever` | no implicit monotonicity or end time | prompt |
| `test_the_bucket_boundary_is_exclusive` | in when `bucket < int(percent * 100)` | `types/rollout.py`, `types/segment.py` |
| `test_fractional_percentages` | percent is in 1/100ths, buckets 0..9999 | `hashing.BUCKETS`; `rollout.py` |
| `test_zero_and_hundred` | 0 admits nobody, 100 admits everybody (bucket 9999) | follows from the rule above |
| `test_same_users_as_a_rollout_with_the_same_salt` | `bucket(self.salt, user)` with `user = ctx.user_key()` | `types/rollout.py`; prompt ("the way the other percentage-based flags" work) |
| `test_default_salt_is_the_flag_key` | `self.salt` (defaults to the key) is the hash salt, not the key and not a new salt | `flag.py` `Flag.__init__` |
| `test_users_stay_in_as_the_ramp_rises` | no time or percentage goes into the hash | prompt; `rollout.py` docstring |
| `test_user_ids_are_compared_as_stripped_strings` | `ctx.user_key()` normalises ids (int, whitespace) | `context.py`; `rollout.py` |
| `test_reasons` | in: the type name (`ramp`); out: `outside_<type>` | `rollout`/`schedule`/`segment` reasons |
| `test_disabled_comes_first` | order: disabled, then anonymous, then override, then the rule; `disabled` also wins for anonymous users and overrides | every percentage-based type |
| `test_anonymous_users_are_never_in` | no user key means off with reason `anonymous`, even at 100% | `rollout.py`, `segment.py` |
| `test_override_beats_the_percentage_both_ways` | `self.overrides[user]` decides, reason `override`, before any percentage | `rollout.py`, `segment.py` |
| `test_to_dict` | `type_fields()` supplies the type-specific keys; times are written back with `format_time`; steps keep the order given | `flag.py` `to_dict`; `schedule.py` `type_fields` |
| `test_round_trip` | `from_dict(to_dict())` is lossless | `flag.py`; every type |
| `test_the_definition_is_not_changed` | loading never mutates the input dict | prompt (steps "in any order": sort a copy) |
| `test_bad_steps_are_config_errors_on_load` | bad config raises `FlagConfigError(flag=key, field=...)` while loading, message `flag 'key': <field>: ...`; times via `parse_time` (strict `...Z` form); percent validated as in rollout (0..100, not bool, number); duplicate times (stated in prompt) | `errors.py`, `timeutil.py`, `rollout.py` `from_spec` |
| `test_a_bad_ramp_is_not_added`, `test_common_fields_are_validated_too` | validation happens before the flag is registered; common fields go through `Flag.from_dict` | `flag.py`, `client.py` |
| `test_evaluate_all_and_exposures`, CLI tests | works through client and CLI once registered | `client.py`, `cli.py` |
| `test_existing_types_unchanged` | regression | `tests/test_flags.py` |

What makes it hard: the new type has no template to fill in. Every convention (hash arguments, `<` against
`int(percent * 100)`, the order disabled / anonymous / override / rule, anonymous users off even at 100%,
reason names, `parse_time` and `FlagConfigError` for config, `format_time` in `to_dict`) is only visible by
reading the existing types side by side, and an agent that writes the obvious ramp from the prompt gets
most of them wrong in small ways.
