DRAFT for LinkedIn. Not posted. Post it yourself if you want it.

---

Do teams of AI agents write better code than one agent? I built a small harness to find out.

Same coding tasks, hidden tests the agent never sees, three setups on Claude Sonnet 5.5: one Claude Code agent; a builder plus a reviewer; and a planner, builder and reviewer. I measured pass rate and tokens.

In a 45-run pilot, the single agent passed 14 of 15. Both teams passed 15 of 15. The one miss was printing "0" where the spec said "0.00". The teams used 1.6x and 2.8x the tokens.

Then I tried to make the single agent fail. I wrote 16 more tasks, from long specs with up to 134 hidden tests to short requests where the rules live only in the repo's own docs and code. It passed all of them, and a weaker model (Haiku) passed the five I gave it. That's 39 single-agent runs with one failure.

The reviewer did catch real bugs: it asked for changes 4 times in 30 team runs, and every fix turned into a pass. But on these tasks the single agent rarely left anything to catch.

The sample is small: tasks I wrote myself, small repos, one model family. I'd expect teams to earn their cost on larger codebases and vaguer requests, and I haven't tested those yet.

Full write-up, numbers and code: https://krisrchesney.github.io/agent-team-evals/post.html
