You are doing subtask $subtask_index of $subtask_count of a larger task. Earlier subtasks (if any) are
already in the working tree.

## Full task (for context)

$task_prompt

## Planner's risks

$risks

## Your subtask: $subtask_title

Requirements covered: $subtask_requirements
Files: $subtask_files

$subtask_instructions

Done when: $subtask_done_when

Do only this subtask. Run `python -m unittest discover -s tests -t .` before you stop; it must pass.
