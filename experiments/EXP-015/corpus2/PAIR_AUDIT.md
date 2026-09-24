# Pair audit

`pairs.json` is the sole canonical registry: 36 unique STRONG records. Twelve
change only `TASK_BINDING`; eight each change `EXEC_CAPABILITY` and
`CWD_CAPABILITY`; four each change `EXEC_RESOURCE` and `CWD_RESOURCE`.

The integrity gate verifies registry uniqueness and strength count. Pair authors
hold argv, route, task contract except for the declared authority field, helper,
and fixture recipe constant. Resource pairs change the requested logical object
and its declared fixture only, which is the declared resource dimension.
