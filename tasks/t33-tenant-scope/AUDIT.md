# t33-tenant-scope: where each hidden-test rule is shown

Category `cross-module`: the prompt lists ten numbered requirements and the hidden tests (named
`test_r<N>_...`) exercise every module, every shared structure and every id-taking method for leaks
between two tenants whose ids collide. Every rule is in the prompt. This file is outside `repo/`, so
agents never see it.

| Test(s) | Rule | Shown by |
|---|---|---|
| `test_r1_create_and_list`, `_bad_ids_and_duplicates` | tenant admin methods, id format, `InvalidInput` / `Conflict` with `param="tenant"` | prompt 1 |
| `test_r1_every_method_checks_the_tenant`, `_unknown_tenant_is_checked_before_anything_else` | every public method that takes a tenant (31) and `delete_tenant` raise `UnknownTenant`; not rate limited | prompt 1 and 5; `service.py` lists the methods |
| `test_r5_tenant_admin_calls_do_not_count` | admin calls are outside the limiter | prompt 5 |
| `test_r2_*` | per-tenant id sequences | prompt 2; `ids.py` |
| `test_r3_other_tenants_ids_are_not_found` (24 id-taking paths) | a stranger's id is `NotFound` with the usual `param`; failed calls change nothing | prompt 3; `store.py` accessors and their `param` arguments |
| `test_r3_a_shared_id_changes_only_the_callers_row`, `_deleting_a_shared_id_...` | same ids in two tenants never touch each other | prompt 2, 3 and 6 |
| `test_r4_*` | names, emails, labels unique per tenant; project and task quotas per tenant | prompt 4; `limits.py`, `store.py` indexes |
| `test_r5_*` | one rate-limit window per tenant, sliding, unaffected by others | prompt 5; `ratelimit.py` (module-level `_HITS`) |
| `test_r6_*` (7 tests) | task cache, search index, summary memo are per tenant and are invalidated per tenant on writes, deletes, project deletes and member removal | prompt 6; the process-wide modules `cache.py`, `search.py`, `summaries.py` (and `ratelimit.py` for 5) and the `reset()` calls in `Lanes.__init__` |
| `test_r7_*` (5 tests) | events and audit per tenant with `tenant` and per-tenant `seq`; subscribers see all | prompt 7; `outbox.py`, `audit.py` |
| `test_r8_*` (3 tests) | reports, lists, filters, exports only cover the tenant | prompt 8 |
| `test_r9_*` (3 tests) | `delete_tenant` clears every shared structure; recreate starts empty; others untouched | prompt 9 |
| `test_r10_*` (3 tests) | dump/load for every tenant, isolation after load, older dump becomes `default` | prompt 10; `snapshot.py` |

What makes it hard: the tenant has to reach seven kinds of state. Two are on the service object
(store, outbox, audit) and four are module-level singletons keyed by a bare id (task cache, search
index, summary memo, rate limiter). Because each tenant's first task is `t1`, a cache or index that is
keyed by id alone passes every single-tenant test and then serves or drops the wrong tenant's row. The
`reset()` calls in `Lanes.__init__` are the only hint that the module-level state exists, and each of
the four needs its own change (key, invalidation, and removal in `delete_tenant`).
