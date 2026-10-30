`pkgplan` plans installs for a toy package registry. You give it requirements such as `web>=2.0`, it picks
one version of every package it needs, works out an install order and prints a report. A first version
works for simple cases, but many details are wrong or missing. Bring the package to the behaviour
described below. Everything is standard library only. Existing tests are in `tests/`. The requirements
are numbered R1 to R29 and are spread over the text, so read all of it. Everything the package exports
from `pkgplan` today (`Version`, `Constraint`, `Registry`, `resolve`, `build_plan`, `format_report`,
`format_size`, `dump_lock`, `load_lock`, `parse_requirement`, `main` and the error classes) keeps its
name; some functions gain parameters.

**Versions.** R1. `Version(text)` parses `MAJOR.MINOR.PATCH` with an optional `-prerelease` and an optional
`+build`, in that order, like `1.2.3-rc.1+build.5`. It exposes `major`, `minor` and `patch` as ints,
`prerelease` and `build` as strings (or `None` when absent) and `is_prerelease`. The prerelease and the
build are dot-separated identifiers made only of letters, digits and hyphens, and no identifier may be
empty. Anything else (fewer or more than three numeric parts, a leading `v`, a trailing `-` or `+`, a
negative number) raises `VersionError`, which is a subclass of `ValueError`. R2. Versions order by
semantic-versioning precedence. Major, minor and patch compare as numbers. A version with a prerelease is
lower than the same numbers without one. Two prereleases compare identifier by identifier from the left:
identifiers made only of digits compare as numbers and are lower than all other identifiers, other
identifiers compare as ASCII text, and if every shared identifier is equal then the version with fewer
identifiers is lower. So `1.0.0-rc.2 < 1.0.0-rc.10`, `1.0.0-1 < 1.0.0-Beta < 1.0.0-alpha` and
`1.0.0-rc < 1.0.0-rc.1`. R3. Build metadata is kept and shown by `str()`, but it is ignored by `==`, by
ordering and by `hash()`, so `Version("1.0.0+a") == Version("1.0.0+b")`. This looks odd and is intended.

**Constraints.** R4. A `Constraint` is one or more clauses separated by commas, and every clause must
hold. A clause is `*` (any version) or an operator followed by a version, where the operator is one of
`==`, `!=`, `>=`, `>`, `<=`, `<`, `^` or `~`. A version with no operator means `==`. Whitespace anywhere in
the text is ignored, so `" >= 1.0 , < 2 "` is the same as `">=1.0,<2"`. In the six comparison forms (and
in the bare form) a version may leave out the minor and patch parts, which count as zero: `>=1.2` means
`>=1.2.0`, `<2` means `<2.0.0`, `==1.2` matches only `1.2.0`. Text that is empty, has an empty clause
(`">=1,,<2"`, `">=1,"`), has an unknown operator, has a bad version, or has an operator without a version
raises `ConstraintError`, a subclass of `ValueError`. `matches(version)` tells whether a `Version`
satisfies the whole constraint. R5. `^` allows changes that do not touch the leftmost non-zero part of the
version as written: `^1.2.3` means `>=1.2.3` and below `2.0.0`, `^0.2.3` means below `0.3.0`, `^0.0.3`
means below `0.0.4`. Only the parts that were written count: `^1.2` is `^1.2.0`, `^0.2` is below `0.3.0`,
`^0.0` is below `0.1.0`, `^0` is below `1.0.0`, `^0.0.0` is below `0.0.1`. R6. `~` allows patch-level
changes when a minor part was written and minor-level changes otherwise: `~1.2.3` and `~1.2` mean below
`1.3.0`, `~1` and `~0` mean below the next major version (`2.0.0`, `1.0.0`). R7. The upper limit that `^`
and `~` create also excludes every prerelease of the limit version, so `^1.2.3` does not match
`2.0.0-alpha` (but it does match `1.9.9-beta`). A plain upper bound that someone writes themselves does not
do this: `<2.0.0` matches `2.0.0-alpha`. Prerelease operands work in `^` and `~` as usual, and
`^1.0.0-beta.2` matches `1.0.0-beta.3` and `1.5.0`. R8. `str(constraint)` is the clauses with all
whitespace removed, joined with `,`, otherwise as written (`"~1.2.3 , != 1.2.5"` becomes `"~1.2.3,!=1.2.5"`
and a bare `1.2.3` stays `1.2.3`).

**Registry.** `Registry.add(name, version, deps=None, size=0, yanked=False)` adds one published version
(`version` is a string or a `Version`; `deps` maps a dependency name to a constraint string; `size` is
the download size in bytes). `Registry.from_dict(data)` builds a registry from
`{"name": {"1.0.0": {"deps": {...}, "size": 10, "yanked": false}, ...}, ...}`, where every key inside a
version entry is optional. R9. A package is found by its lookup key: the name lowercased, with every run
of `-`, `_` and `.` replaced by a single `-`, and leading and trailing whitespace dropped. `Foo_Bar`,
`foo-bar` and `FOO.BAR` are one package. This applies to `in`, `versions(name)` (highest version first),
`get(name, version)` (the entry or `None`), `display_name(name)`, and to names given as dependencies,
requirements, installed sets and upgrade lists everywhere. A package's display name is the spelling used
the first time it was added, and every output uses it. `names()` returns the display names sorted by lookup
key, which is not the same as sorting the display names (`apple` comes before `Zeta`). `search(prefix)`
returns the display names whose lookup key starts with the prefix's lookup key, in the same order; it is
a prefix match and not a substring match, and this is intended. `versions()` of an unknown package raises
`KeyError`. R10. `add` raises `ValueError` if `size` is not a non-negative int, or if the package already
has that version (build metadata does not make versions different), and in both cases the registry is
left as it was. Without `deps`, `size` or `yanked` the entry has no dependencies, size 0 and is not yanked.

**Resolving.** `resolve(registry, requirements, installed=None, upgrade=(), upgrade_all=False,
prerelease=False)` takes requirement strings such as `web>=2.0,<3` (a package name of letters, digits,
`.`, `_` and `-` followed by an optional constraint, with whitespace allowed around everything, and `*`
when the constraint is missing; `parse_requirement(text)` returns the name and the `Constraint`, and
raises `ConstraintError` for text it cannot read). It returns a list of `PackageVersion` objects, each with
`name` (display name), `version`, `deps`, `size` and `yanked`, in the order the packages were chosen.
R11. All requested requirements are noted first, so asking for one package twice merges the constraints.
Then packages are chosen from a queue that starts with the requested packages in the order they first
appear. When a package has been chosen, each of its dependencies is noted with that dependency's
constraint, in alphabetical order of lookup key, and joins the end of the queue unless it is already
there or already chosen. R12. A package is chosen the first time the queue reaches it, using every
constraint that has been noted for it up to that moment: it gets the highest version that satisfies all of
them and is allowed by R13 and R14. A chosen package is never reconsidered. When a later requirement does
not fit the version already chosen it is an error (R16), even if some other choice earlier on would have
made everything fit. This greedy behaviour is intended.

R13. Prerelease versions are skipped unless `prerelease=True` was passed or at least one of the constraints
noted for that package has a clause whose own version is a prerelease (so `>=2.0.0-rc.1` and
`^2.0.0-rc.1` make them eligible, `>=1.0.0` does not). R14. Yanked versions are skipped, unless one of the
noted constraints pins that exact version, meaning a clause that is `==` (or a bare version) and equals
it. Ranges such as `>=2.0.0` or `^2.0.0` never pin, and a pin lets in only the version it names. R15.
`installed` maps package names (any spelling) to version strings or `Version`s. When a package is
installed at a version that exists in the registry and satisfies all constraints noted so far, that
version is chosen and not the highest one, whether or not it is a prerelease or yanked. This does not
apply to a package named in `upgrade` or when `upgrade_all` is true, which choose as if nothing were
installed. An installed version the registry does not have is ignored. R16. If a requirement noted after a
package was chosen is not satisfied by the chosen version, `resolve` raises `ResolutionError` with the
message `conflict on {name}: {chosen} was chosen for {earlier} but {new} is required by {who}`, where
`{name}` is the display name, `{chosen}` is the chosen version as `str()` shows it, `{earlier}` is every
constraint noted before the new one (each as `str(constraint)`) joined with `,`, `{new}` is the new
constraint and `{who}` is the display name of the package that asked for it. R17. If no version is
allowed, `resolve` raises `ResolutionError` with `no version of {name} satisfies {constraints} (required
by {requirers})`, where `{constraints}` are all constraints noted for the package joined with `,` in the
order they were noted and `{requirers}` are the packages that asked, in order, each once, joined with
`, `, with `<root>` standing for a requested requirement. A package that is not in the registry raises
`ResolutionError` with `unknown package {name}`, using the name as it was written in the requirement or
dependency; dependencies are checked when their package has been chosen.

**Plans.** `build_plan(resolved, installed=None)` returns a list of `Step` objects with `name`, `version`,
`action`, `size` and `yanked`, in install order. R18. A step's action is `install` if the package is not
installed, `keep` if its installed version equals the chosen one (build metadata ignored), `upgrade` if
the chosen version is higher and `downgrade` if it is lower. Installed packages that are not part of the
resolution do not appear. R19. Dependencies are placed before the packages that need them. Whenever
several packages could be placed next, the one with the smallest lookup key goes first (so a package that
becomes ready after a small one was placed can still jump ahead of larger packages that were ready
earlier). A package that depends on itself is not a problem. R20. If some packages can never be placed
because they depend on each other, directly or through other packages that do, `build_plan` raises
`ResolutionError` with `dependency cycle among: {names}`, listing every package that could not be placed,
by display name, sorted by lookup key and joined with `, `. Resolution itself accepts cycles.

**Report.** `format_report(steps)` returns the text of the report; every line ends with a newline.
R21. `format_size(count)` writes a number of bytes: below 1024 it is `{count} B`; otherwise it is the
number in KiB, MiB or GiB (units of 1024, using the largest unit that stays at or above 1) with one decimal,
rounded half up (so 1280 bytes is `1.3 KiB`). A value that would be shown as `1024.0` of a unit is shown in
the next unit instead (1048575 bytes is `1.0 MiB`). GiB is the largest unit. A negative count raises
`ValueError`. R22. A report starts with `Plan: {n} install, {n} upgrade, {n} downgrade, {n} keep` giving the
number of steps of each action (always those four words, whatever the numbers). A row follows for every
step, in plan order: the 1-based position right-aligned to the width of the largest position, then `. `,
the name left-aligned to the longest name, a space, the version as `str()` shows it (build metadata
included) left-aligned to the longest version, a space, the action left-aligned to 9 characters, a space,
and the size right-aligned to the longest size text. The size is `format_size(step.size)`, or `-` for a
`keep` step because nothing is downloaded. After the rows comes `Total download: ` and the size of
everything that is not a `keep` step. For example:

```
Plan: 1 install, 1 upgrade, 0 downgrade, 1 keep
1. json-lite 0.9.2 keep            -
2. router    2.1.0 upgrade     310 B
3. app       1.0.0 install   4.8 KiB
Total download: 5.1 KiB
```

R23. If every step is `keep`, or there are no steps, the report is just `Nothing to do.` R24. After that
(after the `Total download` line, or after `Nothing to do.`) the report has one line
`warning: {name} {version} is yanked` for each step whose chosen version is yanked, whatever its action,
sorted by lookup key.

**Lock files.** R25. `dump_lock(steps)` returns `# pkgplan lock v1` followed by one line
`{name}=={version}` for every step (kept ones too), with the display name and the version as `str()` shows
it, sorted by lookup key, each line ending in a newline. R26. `load_lock(text)` returns a dict from lookup
key to `Version`. Blank lines and lines that start with `#` (after trimming) are skipped, and whitespace
around the name and the version is ignored. A line without `==` or with an empty name raises `LockError`
(a subclass of `ValueError`) with `line {n}: expected name==version`; a package that appears twice (by
lookup key) raises `LockError` with `line {n}: duplicate package {name}` for the second occurrence, with
the name as written on that line; `{n}` counts every line of the text from 1. A bad version raises
`VersionError`. The returned dict can be passed to `resolve` and `build_plan` as `installed`.

**Command line.** `main(argv, out=None, err=None)` runs the command line and returns the exit code; `out`
and `err` are file-like objects that default to `sys.stdout` and `sys.stderr` when the call is made.
R27. `plan REQUIREMENT... --registry FILE` (the registry is a JSON file in the format above) prints the
report on `out` and returns 0. It also accepts `--installed LOCKFILE` (versions already installed, read
with `load_lock`), `--upgrade NAME` (repeatable), `--upgrade-all`, `--prerelease` (all passed on to
`resolve`) and `--write-lock FILE`, which writes `dump_lock` of the plan to the file (UTF-8, `\n` line
ends) after printing, also when the plan has nothing to do. Options may appear anywhere after the command.
A `ResolutionError` prints `error: {message}` and a newline on `err`, prints nothing on `out`, writes no
lock file and returns 2. R28. Bad input prints a single line `error: {message}` on `err`, nothing on `out`,
and returns 64: no command or an unknown one, no requirements for `plan`, a missing `--registry`, an
unknown option, an option without its value, a registry or lock file that cannot be read or parsed (bad
JSON, a bad version, a bad size, a bad lock line), and a requirement that is not a valid requirement.
R29. The other commands behave as they do now. `show NAME --registry FILE` prints the display name and then
one line per version, highest first, as two spaces and the version, followed by ` (yanked)` for yanked ones.
`list --registry FILE` prints one line per package, `{display name} {number of versions}`, in lookup-key
order. `rdeps NAME --registry FILE` prints the display name of every package that has some version
depending on `NAME`, one per line in lookup-key order. `reach NAME --registry FILE` prints every package
reachable from any version of `NAME` by following dependencies (not `NAME` itself, dependencies that are not
in the registry ignored), one per line in lookup-key order. Each of them returns 2 with
`error: unknown package {name}` for a package that is not in the registry, and 64 when it is given the wrong
number of arguments. Names are matched by lookup key (R9).
