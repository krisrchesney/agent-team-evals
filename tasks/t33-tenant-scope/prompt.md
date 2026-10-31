`lanes` serves a single team. We are turning it into a service for many customers, called tenants,
who must never see or affect each other's data. Thread the tenant through every read and write.
Use only the Python standard library. The visible tests call the service without a tenant: update
them to create a tenant and pass it.

1. **Tenants.** `create_tenant(tenant_id, name)` returns `{"id", "name"}`. A tenant id is 2 to 20
   lower-case letters, digits or dashes, otherwise `InvalidInput` (`param="tenant"`); a duplicate
   is a `Conflict` (`param="tenant"`). `list_tenants()` returns `{"data": [{"id", "name"}, ...]}`
   sorted by id. Every other public method of `Lanes` takes `tenant` as its first argument, except
   `subscribe`, `dump`, `load` and the three tenant methods (`create_tenant`, `list_tenants`,
   `delete_tenant`). An unknown tenant raises `UnknownTenant` (code `unknown_tenant`,
   `param="tenant"`) before anything else happens, rate limiting included.
2. **Own ids.** Every tenant has its own id sequences: its first project is `p1`, its first member
   `u1`, its first task `t1` and its first comment `c1`, whatever other tenants have done.
3. **Strangers.** An id that belongs to another tenant is as unknown as one that does not exist: the
   same `NotFound`, with the same `param`, from every method that takes an id (projects, tasks,
   members, assignees, comment authors, labels, including the filters of `list_tasks`, the labels
   of `create_task`, `export_tasks_csv` and `project_summary`). Nothing is changed by a failed call,
   and nothing tells a caller that the other tenant's row exists.
4. **Names and quotas.** Project names, member emails and label names must be unique only within a
   tenant. `limits.MAX_PROJECTS` and `limits.MAX_TASKS_PER_PROJECT` apply to each tenant (and each
   project) separately.
5. **Rate limit.** `ratelimit.RATE_LIMIT` calls per `WINDOW_SECONDS` apply to each tenant on its own:
   one tenant using up its calls does not slow another. Calls with an unknown tenant and the three
   tenant methods do not count.
6. **Caches.** The task view cache, the search index and the project summary memo are per tenant. A
   write, delete, project delete or member removal in one tenant never changes what another tenant
   reads, even when both have rows with the same id.
7. **Events and audit.** `drain(tenant)` returns only that tenant's events and removes only those.
   Each event has a `tenant` field, and `seq` counts from 1 within the tenant. Subscribers added
   with `subscribe(fn)` still get every event of every tenant, with its `tenant`. `audit_log(tenant,
   limit)` returns only that tenant's entries, with `seq` counting from 1 within the tenant.
8. **Reports and exports.** `workload`, `overdue`, `label_counts`, `project_summary`,
   `export_tasks_csv` and `export_json` only ever cover the tenant they are called for.
9. **Removing a tenant.** `delete_tenant(tenant_id)` returns `{"id": id, "deleted": True}` and
   removes everything of the tenant, including its cached views, search entries, summaries, rate
   limit window, undrained events and audit entries. Other tenants are not touched. The id can be
   created again and starts empty. An unknown tenant is `UnknownTenant`.
10. **Save and load.** `dump()` covers every tenant and `load()` restores each one (its id sequences,
    audit entries and search). An older dump, which has no tenants, loads as the tenant `default`
    named `Default`.
