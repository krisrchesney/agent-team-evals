# Why this exists

*Written November 2026. Results come from tasks written for this project and one family of AI models, so treat them as a method and a first answer, not a verdict.*

## In 30 seconds

People are building "teams" of AI agents, where one plans, one writes the code and one reviews it. This project tests whether a team writes better code than a single agent, and what it costs in AI usage. It runs the same coding tasks through each setup and grades the results with tests the agents never see.

## Why I built it

I had used a planner, builder and reviewer pattern on another project (Boxwatch) and wanted to know if it was worth the extra cost or just felt more thorough. Most claims about agent teams come from a single demo that worked. I wanted counted passes and failures, with the rules fixed in advance.

## How it works

1. **Write a coding task** with a short request, a small starting codebase and hidden tests.
2. **Check the task itself.** The hidden tests must fail on the starting code and pass on a reference solution.
3. **Run it three ways:** one agent; a builder plus a reviewer; a planner, builder and reviewer.
4. **Count passes and failures** on the hidden tests, along with AI usage and time. Every run counts.

## Choices I made, and why

- **Hidden tests as the grader**, so agents can't fit to it.
- **Every task is checked before use**, so a broken task can't hide real differences.
- **Harder tasks when the first ones were too easy.** A single agent solved almost everything at first.
- **Report AI usage, not dollars.** The runs use a subscription with no per-use bill.
- **Rules fixed before running, with no retakes.**
- **Plain counts, not fancy statistics.** With this few runs, anything more would look more certain than it is.

## What I found

- **A team didn't write better code than a single agent, and it cost more.** On the hard tasks, one agent passed 15 of 55 tries and a builder plus reviewer passed 11 of 55, using about 1.5 times the AI usage. The difference is small enough to be luck.
- **The reviewer was a poor check.** It approved 46 of 55 tries, and 35 of those failed the hidden tests.
- **A larger model and mixed teams didn't help either.** A smaller model did clearly worse.
- **Making the right decisions mattered most.** On tasks where a short request left rules unstated, runs that covered every decision passed, and runs that didn't did not.

[Full results.](README.md)

**What not to trust:** one family of models, tasks I wrote myself, small codebases, and a fixed order of who works when. Long-running and very large projects are untested.

## What's not finished

- More studies are listed in `TASKS.md`. Those that use a lot of AI usage wait for my approval first.
- Letting the model decide who works when is untested.

## Where to look

[Overview page](https://krisrchesney.github.io/agent-team-evals/) · [README with all results](README.md) · [Design and reasons](DESIGN.md) · [Second test](docs/study2-main-sweep.md) · [Model comparison](docs/study2-model-matrix.md)
