CREATE TABLE IF NOT EXISTS ai_assistant_conversation (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL,
  session_uuid VARCHAR(64) NOT NULL,
  title VARCHAR(255) NOT NULL DEFAULT '新会话',
  status VARCHAR(32) NOT NULL DEFAULT 'active',
  created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_time TIMESTAMPTZ NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ai_assistant_conversation_user_id ON ai_assistant_conversation (user_id);
CREATE INDEX IF NOT EXISTS idx_ai_assistant_conversation_session_uuid ON ai_assistant_conversation (session_uuid);

CREATE TABLE IF NOT EXISTS ai_assistant_message (
  id BIGSERIAL PRIMARY KEY,
  conversation_id BIGINT NOT NULL REFERENCES ai_assistant_conversation (id) ON DELETE CASCADE ON UPDATE CASCADE,
  role VARCHAR(16) NOT NULL,
  content TEXT NOT NULL,
  action_type VARCHAR(32) NULL,
  action_status VARCHAR(32) NULL,
  created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_time TIMESTAMPTZ NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ai_assistant_message_conversation_id ON ai_assistant_message (conversation_id);

CREATE TABLE IF NOT EXISTS ai_assistant_action_run (
  id BIGSERIAL PRIMARY KEY,
  conversation_id BIGINT NOT NULL REFERENCES ai_assistant_conversation (id) ON DELETE CASCADE ON UPDATE CASCADE,
  message_id BIGINT NOT NULL REFERENCES ai_assistant_message (id) ON DELETE CASCADE ON UPDATE CASCADE,
  user_id BIGINT NOT NULL,
  session_uuid VARCHAR(64) NOT NULL,
  route_type VARCHAR(32) NOT NULL,
  target_name VARCHAR(128) NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  celery_task_id VARCHAR(64) NULL,
  result_summary TEXT NULL,
  error_summary TEXT NULL,
  finished_time TIMESTAMPTZ NULL,
  created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_time TIMESTAMPTZ NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ai_assistant_action_run_conversation_id ON ai_assistant_action_run (conversation_id);
CREATE INDEX IF NOT EXISTS idx_ai_assistant_action_run_message_id ON ai_assistant_action_run (message_id);
CREATE INDEX IF NOT EXISTS idx_ai_assistant_action_run_user_id ON ai_assistant_action_run (user_id);
CREATE INDEX IF NOT EXISTS idx_ai_assistant_action_run_session_uuid ON ai_assistant_action_run (session_uuid);
CREATE INDEX IF NOT EXISTS idx_ai_assistant_action_run_celery_task_id ON ai_assistant_action_run (celery_task_id);
