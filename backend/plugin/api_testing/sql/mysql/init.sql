-- MySQL数据库初始化脚本(自增ID)

-- API项目表
CREATE TABLE IF NOT EXISTS `api_project` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name` varchar(64) NOT NULL COMMENT '项目名称',
  `description` text COMMENT '项目描述',
  `base_url` varchar(255) NOT NULL COMMENT '基础URL',
  `headers` json DEFAULT NULL COMMENT '全局请求头',
  `variables` json DEFAULT NULL COMMENT '全局变量',
  `status` tinyint(1) NOT NULL DEFAULT '1' COMMENT '状态 1启用 0禁用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='API项目表';

-- API测试用例表
CREATE TABLE IF NOT EXISTS `api_test_case` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name` varchar(64) NOT NULL COMMENT '用例名称',
  `project_id` int(11) NOT NULL COMMENT '所属项目ID',
  `description` text COMMENT '用例描述',
  `pre_script` text COMMENT '前置脚本',
  `post_script` text COMMENT '后置脚本',
  `status` tinyint(1) NOT NULL DEFAULT '1' COMMENT '状态 1启用 0禁用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_project_id` (`project_id`),
  CONSTRAINT `fk_api_test_case_project_id` FOREIGN KEY (`project_id`) REFERENCES `api_project` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='API测试用例表';

-- API测试步骤表
CREATE TABLE IF NOT EXISTS `api_test_step` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name` varchar(64) NOT NULL COMMENT '步骤名称',
  `test_case_id` int(11) NOT NULL COMMENT '所属用例ID',
  `url` varchar(255) NOT NULL COMMENT '请求URL',
  `method` varchar(16) NOT NULL COMMENT '请求方法',
  `headers` json DEFAULT NULL COMMENT '请求头',
  `params` json DEFAULT NULL COMMENT '查询参数',
  `body` json DEFAULT NULL COMMENT '请求体',
  `files` json DEFAULT NULL COMMENT '上传文件',
  `auth` json DEFAULT NULL COMMENT '认证信息',
  `extract` json DEFAULT NULL COMMENT '提取变量',
  `validate` json DEFAULT NULL COMMENT '断言列表',
  `sql_queries` json DEFAULT NULL COMMENT 'SQL查询列表',
  `timeout` int(11) NOT NULL DEFAULT '30' COMMENT '超时时间(秒)',
  `retry` int(11) NOT NULL DEFAULT '0' COMMENT '重试次数',
  `retry_interval` int(11) NOT NULL DEFAULT '1' COMMENT '重试间隔(秒)',
  `order` int(11) NOT NULL COMMENT '步骤顺序',
  `status` tinyint(1) NOT NULL DEFAULT '1' COMMENT '状态 1启用 0禁用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_test_case_id` (`test_case_id`),
  KEY `idx_order` (`test_case_id`, `order`),
  CONSTRAINT `fk_api_test_step_test_case_id` FOREIGN KEY (`test_case_id`) REFERENCES `api_test_case` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='API测试步骤表';

-- API测试报告表
CREATE TABLE IF NOT EXISTS `api_test_report` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `test_case_id` int(11) NOT NULL COMMENT '所属用例ID',
  `name` varchar(64) NOT NULL COMMENT '报告名称',
  `success` tinyint(1) NOT NULL COMMENT '是否成功',
  `total_steps` int(11) NOT NULL COMMENT '总步骤数',
  `success_steps` int(11) NOT NULL COMMENT '成功步骤数',
  `fail_steps` int(11) NOT NULL COMMENT '失败步骤数',
  `start_time` datetime NOT NULL COMMENT '开始时间',
  `end_time` datetime NOT NULL COMMENT '结束时间',
  `duration` int(11) NOT NULL COMMENT '执行时长(毫秒)',
  `details` json NOT NULL COMMENT '报告详情',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_test_case_id` (`test_case_id`),
  CONSTRAINT `fk_api_test_report_test_case_id` FOREIGN KEY (`test_case_id`) REFERENCES `api_test_case` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='API测试报告表';

CREATE TABLE IF NOT EXISTS `api_test_suite` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name` varchar(64) NOT NULL COMMENT '集合名称',
  `project_id` int(11) NOT NULL COMMENT '所属项目ID',
  `description` text COMMENT '集合描述',
  `status` tinyint(1) NOT NULL DEFAULT '1' COMMENT '状态 1启用 0禁用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_project_id` (`project_id`),
  CONSTRAINT `fk_api_test_suite_project` FOREIGN KEY (`project_id`) REFERENCES `api_project` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='API测试集合表';

CREATE TABLE IF NOT EXISTS `api_test_suite_case` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `suite_id` int(11) NOT NULL COMMENT '所属集合ID',
  `test_case_id` int(11) NOT NULL COMMENT '所属用例ID',
  `order` int(11) NOT NULL COMMENT '集合内顺序',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_suite_id` (`suite_id`),
  KEY `idx_test_case_id` (`test_case_id`),
  CONSTRAINT `fk_api_test_suite_case_suite` FOREIGN KEY (`suite_id`) REFERENCES `api_test_suite` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_api_test_suite_case_case` FOREIGN KEY (`test_case_id`) REFERENCES `api_test_case` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='API测试集合成员表';

CREATE TABLE IF NOT EXISTS `api_batch_execution_report` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `project_id` int(11) NOT NULL COMMENT '所属项目ID',
  `suite_id` int(11) DEFAULT NULL COMMENT '所属集合ID',
  `name` varchar(64) NOT NULL COMMENT '批量执行名称',
  `target_type` varchar(16) NOT NULL COMMENT '执行目标类型 project/suite',
  `success` tinyint(1) NOT NULL COMMENT '是否成功',
  `total_cases` int(11) NOT NULL COMMENT '总用例数',
  `success_cases` int(11) NOT NULL COMMENT '成功用例数',
  `fail_cases` int(11) NOT NULL COMMENT '失败用例数',
  `max_concurrency` int(11) NOT NULL COMMENT '最大并发数',
  `start_time` datetime NOT NULL COMMENT '开始时间',
  `end_time` datetime NOT NULL COMMENT '结束时间',
  `duration` int(11) NOT NULL COMMENT '执行时长(毫秒)',
  `details` json NOT NULL COMMENT '批量执行详情',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_project_id` (`project_id`),
  KEY `idx_suite_id` (`suite_id`),
  CONSTRAINT `fk_api_batch_execution_project` FOREIGN KEY (`project_id`) REFERENCES `api_project` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_api_batch_execution_suite` FOREIGN KEY (`suite_id`) REFERENCES `api_test_suite` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='API批量执行报告表';

CREATE TABLE IF NOT EXISTS `api_sql_execution_task` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `task_id` varchar(64) NOT NULL COMMENT '任务ID',
  `celery_task_id` varchar(64) DEFAULT NULL COMMENT 'Celery任务ID',
  `name` varchar(128) NOT NULL COMMENT '任务名称',
  `status` varchar(32) NOT NULL DEFAULT 'pending' COMMENT '任务状态',
  `query_payload` json NOT NULL COMMENT 'SQL查询载荷',
  `result` json DEFAULT NULL COMMENT '执行结果',
  `error` text COMMENT '错误信息',
  `start_time` datetime DEFAULT NULL COMMENT '开始时间',
  `end_time` datetime DEFAULT NULL COMMENT '结束时间',
  `duration` int(11) DEFAULT NULL COMMENT '执行时长(毫秒)',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_api_sql_execution_task_task_id` (`task_id`),
  KEY `idx_api_sql_execution_task_status` (`status`),
  KEY `idx_api_sql_execution_task_celery_task_id` (`celery_task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='API SQL异步执行任务表';
