- a node returns a partial dict, not the whole state. LangGraph merges it into the state. This is a key idea — nodes don't mutate; they return updates.


sqlite3 agent_checkpoints.db "SELECT thread_id, COUNT(*) FROM checkpoints GROUP BY thread_id;"

You should see one row per run. This proves the checkpointer works. In Phase 7, we'll use these thread IDs to resume interrupted runs.
