insert into sys_menu (
  title,
  name,
  path,
  sort,
  icon,
  type,
  component,
  perms,
  status,
  display,
  cache,
  link,
  remark,
  parent_id,
  created_time,
  updated_time
)
select
  '运行日志',
  'ApiTestingExecutionStream',
  '/plugins/testcase-execution-stream',
  11,
  null,
  1,
  '/plugins/api_testing/views/testcase-execution-stream/index',
  null,
  1,
  0,
  1,
  '',
  'API testing execution stream detail page',
  parent_menu.id,
  now(),
  null
from sys_menu parent_menu
where parent_menu.name = 'ApiTesting'
  and not exists (
    select 1
    from sys_menu current_menu
    where current_menu.name = 'ApiTestingExecutionStream'
  );
