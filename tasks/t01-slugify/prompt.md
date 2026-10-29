`textkit.slug.slugify()` produces bad URL slugs. Fix it so that:

1. Accented Latin letters are transliterated to plain ASCII (`"Crème Brûlée"` -> `"creme-brulee"`).
   Characters with no ASCII form are dropped.
2. The result is lowercase and contains only `a-z`, `0-9` and single `-` separators.
   Runs of spaces, underscores, punctuation or dashes collapse into one `-`.
3. There is never a leading or trailing `-`.
4. A new keyword argument `max_length: int | None = None` truncates the slug to at most
   `max_length` characters, cutting at a `-` boundary when possible so words are not split.
   If the first word alone is longer than `max_length`, hard-cut that word.
   There is no trailing `-` after truncation.
5. An empty or all-symbol input returns `""`.

Keep the public signature backward compatible (`slugify(text)` still works).
Use only the Python standard library. Existing tests are in `tests/`.
