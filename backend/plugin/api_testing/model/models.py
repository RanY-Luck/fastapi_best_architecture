#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from typing import List

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column

from backend.common.enums import StatusType
from backend.common.model import Base, id_key


class ApiProject(Base):
    """API项目表"""
    __tablename__ = 'api_project'

    id: Mapped[id_key] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(String(64), comment='项目名称')
    base_url: Mapped[str] = mapped_column(String(255), comment='基础URL')
    headers: Mapped[dict | None] = mapped_column(JSON, default=None, comment='全局请求头')
    variables: Mapped[dict | None] = mapped_column(JSON, default=None, comment='全局变量')
    status: Mapped[int] = mapped_column(default=StatusType.enable.value, comment='状态 1启用 0禁用')
    description: Mapped[str | None] = mapped_column(Text, default=None, comment='项目描述')

    # 关联关系
    test_cases: Mapped[List["ApiTestCase"]] = relationship("ApiTestCase", back_populates="project", init=False)
    test_suites: Mapped[List["ApiTestSuite"]] = relationship("ApiTestSuite", back_populates="project", init=False)
    batch_reports: Mapped[List["ApiBatchExecutionReport"]] = relationship(
        "ApiBatchExecutionReport",
        back_populates="project",
        init=False,
    )


class ApiTestCase(Base):
    """API测试用例表"""
    __tablename__ = 'api_test_case'

    id: Mapped[id_key] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(String(64), comment='用例名称')
    project_id: Mapped[int] = mapped_column(ForeignKey('api_project.id'), comment='所属项目ID')
    description: Mapped[str | None] = mapped_column(Text, default=None, comment='用例描述')
    pre_script: Mapped[str | None] = mapped_column(Text, default=None, comment='前置脚本')
    post_script: Mapped[str | None] = mapped_column(Text, default=None, comment='后置脚本')
    status: Mapped[int] = mapped_column(default=StatusType.enable.value, comment='状态 1启用 0禁用')

    # 关联关系
    project: Mapped["ApiProject"] = relationship("ApiProject", back_populates="test_cases", init=False)
    steps: Mapped[List["ApiTestStep"]] = relationship("ApiTestStep", back_populates="test_case", init=False)
    reports: Mapped[List["ApiTestReport"]] = relationship("ApiTestReport", back_populates="test_case", init=False)
    suite_cases: Mapped[List["ApiTestSuiteCase"]] = relationship("ApiTestSuiteCase", back_populates="test_case", init=False)


class ApiTestStep(Base):
    """API测试步骤表"""
    __tablename__ = 'api_test_step'

    id: Mapped[id_key] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(String(64), comment='步骤名称')
    test_case_id: Mapped[int] = mapped_column(ForeignKey('api_test_case.id'), comment='所属用例ID')
    url: Mapped[str] = mapped_column(String(255), comment='请求URL')
    method: Mapped[str] = mapped_column(String(16), comment='请求方法')
    order: Mapped[int] = mapped_column(comment='步骤顺序')
    status: Mapped[int] = mapped_column(default=StatusType.enable.value, comment='状态 1启用 0禁用')
    headers: Mapped[dict | None] = mapped_column(JSON, default=None, comment='请求头')
    params: Mapped[dict | None] = mapped_column(JSON, default=None, comment='查询参数')
    body: Mapped[dict | None] = mapped_column(JSON, default=None, comment='请求体')
    files: Mapped[dict | None] = mapped_column(JSON, default=None, comment='上传文件')
    auth: Mapped[dict | None] = mapped_column(JSON, default=None, comment='认证信息')
    extract: Mapped[dict | None] = mapped_column(JSON, default=None, comment='提取变量')
    validate: Mapped[dict | None] = mapped_column(JSON, default=None, comment='断言列表')
    sql_queries: Mapped[dict | None] = mapped_column(JSON, default=None, comment='SQL查询列表')
    timeout: Mapped[int] = mapped_column(default=30, comment='超时时间(秒)')
    retry: Mapped[int] = mapped_column(default=0, comment='重试次数')
    retry_interval: Mapped[int] = mapped_column(default=1, comment='重试间隔(秒)')

    # 关联关系
    test_case: Mapped["ApiTestCase"] = relationship("ApiTestCase", back_populates="steps", init=False)


class ApiTestReport(Base):
    """API测试报告表"""
    __tablename__ = 'api_test_report'

    id: Mapped[id_key] = mapped_column(init=False)
    test_case_id: Mapped[int] = mapped_column(ForeignKey('api_test_case.id'), comment='所属用例ID')
    name: Mapped[str] = mapped_column(String(64), comment='报告名称')
    total_steps: Mapped[int] = mapped_column(comment='总步骤数')
    success_steps: Mapped[int] = mapped_column(comment='成功步骤数')
    fail_steps: Mapped[int] = mapped_column(comment='失败步骤数')
    start_time: Mapped[datetime] = mapped_column(DateTime, comment='开始时间')
    end_time: Mapped[datetime] = mapped_column(DateTime, comment='结束时间')
    duration: Mapped[int] = mapped_column(comment='执行时长(毫秒)')
    details: Mapped[dict] = mapped_column(JSON, comment='报告详情')
    success: Mapped[int] = mapped_column(default=StatusType.enable.value,comment='是否成功 0失败 1成功')

    # 关联关系
    test_case: Mapped["ApiTestCase"] = relationship("ApiTestCase", back_populates="reports", init=False)


class ApiTestSuite(Base):
    """API测试集合表"""
    __tablename__ = 'api_test_suite'

    id: Mapped[id_key] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(String(64), comment='集合名称')
    project_id: Mapped[int] = mapped_column(ForeignKey('api_project.id'), comment='所属项目ID')
    description: Mapped[str | None] = mapped_column(Text, default=None, comment='集合描述')
    status: Mapped[int] = mapped_column(default=StatusType.enable.value, comment='状态 1启用 0禁用')

    project: Mapped["ApiProject"] = relationship("ApiProject", back_populates="test_suites", init=False)
    suite_cases: Mapped[List["ApiTestSuiteCase"]] = relationship("ApiTestSuiteCase", back_populates="suite", init=False)
    batch_reports: Mapped[List["ApiBatchExecutionReport"]] = relationship(
        "ApiBatchExecutionReport",
        back_populates="suite",
        init=False,
    )


class ApiTestSuiteCase(Base):
    """API测试集合成员表"""
    __tablename__ = 'api_test_suite_case'

    id: Mapped[id_key] = mapped_column(init=False)
    suite_id: Mapped[int] = mapped_column(ForeignKey('api_test_suite.id'), comment='所属集合ID')
    test_case_id: Mapped[int] = mapped_column(ForeignKey('api_test_case.id'), comment='所属用例ID')
    order: Mapped[int] = mapped_column(comment='集合内顺序')

    suite: Mapped["ApiTestSuite"] = relationship("ApiTestSuite", back_populates="suite_cases", init=False)
    test_case: Mapped["ApiTestCase"] = relationship("ApiTestCase", back_populates="suite_cases", init=False)


class ApiBatchExecutionReport(Base):
    """API批量执行报告表"""
    __tablename__ = 'api_batch_execution_report'

    id: Mapped[id_key] = mapped_column(init=False)
    project_id: Mapped[int] = mapped_column(ForeignKey('api_project.id'), comment='所属项目ID')
    name: Mapped[str] = mapped_column(String(64), comment='批量执行名称')
    target_type: Mapped[str] = mapped_column(String(16), comment='执行目标类型 project/suite')
    total_cases: Mapped[int] = mapped_column(comment='总用例数')
    success_cases: Mapped[int] = mapped_column(comment='成功用例数')
    fail_cases: Mapped[int] = mapped_column(comment='失败用例数')
    max_concurrency: Mapped[int] = mapped_column(comment='最大并发数')
    start_time: Mapped[datetime] = mapped_column(DateTime, comment='开始时间')
    end_time: Mapped[datetime] = mapped_column(DateTime, comment='结束时间')
    duration: Mapped[int] = mapped_column(comment='执行时长(毫秒)')
    details: Mapped[dict] = mapped_column(JSON, comment='批量执行详情')
    success: Mapped[int] = mapped_column(comment='是否成功 0失败 1成功')
    suite_id: Mapped[int | None] = mapped_column(ForeignKey('api_test_suite.id'), default=None, comment='所属集合ID')

    project: Mapped["ApiProject"] = relationship("ApiProject", back_populates="batch_reports", init=False)
    suite: Mapped["ApiTestSuite"] = relationship("ApiTestSuite", back_populates="batch_reports", init=False)


class ApiSqlExecutionTask(Base):
    """API SQL异步执行任务表"""
    __tablename__ = 'api_sql_execution_task'

    id: Mapped[id_key] = mapped_column(init=False)
    task_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, comment='任务ID')
    name: Mapped[str] = mapped_column(String(128), comment='任务名称')
    query_payload: Mapped[dict] = mapped_column(JSON, comment='SQL查询载荷')
    celery_task_id: Mapped[str | None] = mapped_column(String(64), default=None, comment='Celery任务ID')
    status: Mapped[str] = mapped_column(String(32), default='pending', comment='任务状态')
    result: Mapped[dict | None] = mapped_column(JSON, default=None, comment='执行结果')
    error: Mapped[str | None] = mapped_column(Text, default=None, comment='错误信息')
    start_time: Mapped[datetime | None] = mapped_column(DateTime, default=None, comment='开始时间')
    end_time: Mapped[datetime | None] = mapped_column(DateTime, default=None, comment='结束时间')
    duration: Mapped[int | None] = mapped_column(default=None, comment='执行时长(毫秒)')

