# Harness observation fixtures

`codex-native.jsonl` and `claude-native.jsonl` are small stable outer-event
excerpts selected from the real, already retained `acceptance/07` streams.
They are independent test fixtures; tests never regenerate or rewrite retained
evidence.

The retained Claude sessions ended at authentication and contain no real
`tool_use` event. Claude Read, Write, and Bash cases in the tests therefore
derive content-block mutations from the recorded assistant outer envelope.
They verify the parser and shared audit policy but are not represented as a
real Claude tool-use recording.
