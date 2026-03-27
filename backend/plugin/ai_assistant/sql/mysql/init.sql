-- MySQL数据库初始化脚本(自增ID)

CREATE TABLE IF NOT EXISTS `ai_assistant_conversation` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user_id` bigint NOT NULL COMMENT '所属用户ID',
  `session_uuid` varchar(64) NOT NULL COMMENT '登录会话UUID',
  `title` varchar(255) NOT NULL DEFAULT '新会话' COMMENT '会话标题',
  `status` varchar(32) NOT NULL DEFAULT 'active' COMMENT '会话状态',
  `created_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_time` datetime NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_ai_assistant_conversation_user_id` (`user_id`),
  KEY `idx_ai_assistant_conversation_session_uuid` (`session_uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI助手会话表';

CREATE TABLE IF NOT EXISTS `ai_assistant_message` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `conversation_id` bigint NOT NULL COMMENT '所属会话ID',
  `role` varchar(16) NOT NULL COMMENT '消息角色',
  `content` longtext NOT NULL COMMENT '消息内容',
  `action_type` varchar(32) DEFAULT NULL COMMENT '动作类型',
  `action_status` varchar(32) DEFAULT NULL COMMENT '动作状态',
  `created_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_time` datetime NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_ai_assistant_message_conversation_id` (`conversation_id`),
  CONSTRAINT `fk_ai_assistant_message_conversation_id` FOREIGN KEY (`conversation_id`) REFERENCES `ai_assistant_conversation` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI助手消息表';

CREATE TABLE IF NOT EXISTS `ai_assistant_action_run` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `conversation_id` bigint NOT NULL COMMENT '所属会话ID',
  `message_id` bigint NOT NULL COMMENT '所属消息ID',
  `user_id` bigint NOT NULL COMMENT '所属用户ID',
  `session_uuid` varchar(64) NOT NULL COMMENT '登录会话UUID',
  `route_type` varchar(32) NOT NULL COMMENT '执行路由类型',
  `target_name` varchar(128) DEFAULT NULL COMMENT '目标动作名称',
  `status` varchar(32) NOT NULL DEFAULT 'pending' COMMENT '执行状态',
  `celery_task_id` varchar(64) DEFAULT NULL COMMENT 'Celery任务ID',
  `result_summary` longtext DEFAULT NULL COMMENT '结果摘要',
  `error_summary` longtext DEFAULT NULL COMMENT '错误摘要',
  `finished_time` datetime DEFAULT NULL COMMENT '完成时间',
  `created_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_time` datetime NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_ai_assistant_action_run_conversation_id` (`conversation_id`),
  KEY `idx_ai_assistant_action_run_message_id` (`message_id`),
  KEY `idx_ai_assistant_action_run_user_id` (`user_id`),
  KEY `idx_ai_assistant_action_run_session_uuid` (`session_uuid`),
  KEY `idx_ai_assistant_action_run_celery_task_id` (`celery_task_id`),
  CONSTRAINT `fk_ai_assistant_action_run_conversation_id` FOREIGN KEY (`conversation_id`) REFERENCES `ai_assistant_conversation` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_ai_assistant_action_run_message_id` FOREIGN KEY (`message_id`) REFERENCES `ai_assistant_message` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI助手动作执行表';
