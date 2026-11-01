The nightly `tracelens` run over our event logs used to finish in seconds. Traffic has grown to tens of thousands of events per run and `tracelens.pipeline.run` now takes minutes. Make it fast on large inputs: it should take a few seconds at most for 40,000 events, however the events are spread over users and pages.

Results must not change at all, including the order of results and how ties are broken. Existing behaviour must keep working. Use only the Python standard library. Existing tests are in `tests/`.
