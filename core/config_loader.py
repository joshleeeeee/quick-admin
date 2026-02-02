"""
配置加载器模块
负责安全地读取和解析 YAML 配置文件
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class ConfigLoader:
    """配置加载器类，用于加载和管理 YAML 配置文件"""

    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化配置加载器
        
        Args:
            config_dir: 配置文件目录路径，默认为项目根目录下的 configs 文件夹
        """
        if config_dir is None:
            # 默认使用项目根目录下的 configs 文件夹
            self.config_dir = Path(__file__).parent.parent / "configs"
        else:
            self.config_dir = Path(config_dir)

    def _safe_load_yaml(self, file_path: Path) -> Any:
        """
        安全地加载 YAML 文件
        使用 yaml.safe_load 防止代码注入攻击
        
        Args:
            file_path: YAML 文件路径
            
        Returns:
            解析后的配置数据
            
        Raises:
            FileNotFoundError: 文件不存在
            yaml.YAMLError: YAML 解析错误
        """
        if not file_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            try:
                return yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise yaml.YAMLError(f"YAML 解析错误 ({file_path}): {e}")

    def _get_config_file(self, base_name: str) -> Path:
        """
        获取配置文件路径，优先使用本地配置，否则回退到 example 模板
        
        Args:
            base_name: 基础文件名，如 'db_config.yaml'
            
        Returns:
            配置文件路径
        """
        # 优先使用本地配置
        local_file = self.config_dir / base_name
        if local_file.exists():
            return local_file
        
        # 回退到 example 模板
        example_name = base_name.replace(".yaml", ".example.yaml")
        example_file = self.config_dir / example_name
        if example_file.exists():
            return example_file
        
        # 都不存在则返回本地配置路径（让后续报错）
        return local_file


    def load_db_config(self, env: str = "default") -> Dict[str, Any]:
        """
        加载数据库配置
        
        Args:
            env: 环境名称，如 'default', 'dev', 'test', 'prod'
            
        Returns:
            数据库配置字典
            
        Raises:
            KeyError: 指定的环境配置不存在
        """
        config_file = self._get_config_file("db_config.yaml")
        all_config = self._safe_load_yaml(config_file)

        if env not in all_config:
            available_envs = list(all_config.keys())
            raise KeyError(
                f"数据库环境 '{env}' 不存在，可用环境: {available_envs}"
            )

        db_config = all_config[env]
        
        # 验证必要的配置项
        required_keys = ["type", "host", "user", "password", "database"]
        missing_keys = [key for key in required_keys if key not in db_config]
        if missing_keys:
            raise ValueError(f"数据库配置缺少必要字段: {missing_keys}")

        return db_config

    def get_available_db_envs(self) -> List[str]:
        """
        获取所有可用的数据库环境名称
        
        Returns:
            环境名称列表
        """
        config_file = self._get_config_file("db_config.yaml")
        all_config = self._safe_load_yaml(config_file)
        return list(all_config.keys())

    def load_tasks(self, task_file: str = "tasks.yaml") -> List[Dict[str, Any]]:
        """
        加载运维任务配置
        
        Args:
            task_file: 任务配置文件名，默认 tasks.yaml
        
        Returns:
            任务配置列表
        """
        # demo 文件不回退，其他文件支持回退到 example
        if task_file == "tasks_demo.yaml":
            config_file = self.config_dir / task_file
        else:
            config_file = self._get_config_file(task_file)
        tasks = self._safe_load_yaml(config_file)

        if not isinstance(tasks, list):
            raise ValueError(f"{task_file} 应该包含一个任务列表")

        # 验证每个任务的必要字段
        for i, task in enumerate(tasks):
            self._validate_task(task, i)

        return tasks

    def _validate_task(self, task: Dict[str, Any], index: int) -> None:
        """
        验证任务配置的完整性
        
        Args:
            task: 任务配置字典
            index: 任务在列表中的索引
            
        Raises:
            ValueError: 任务配置不完整
        """
        required_keys = ["id", "title", "type"]
        missing_keys = [key for key in required_keys if key not in task]
        
        if missing_keys:
            raise ValueError(
                f"任务 #{index + 1} 缺少必要字段: {missing_keys}"
            )
        
        # sql 和 sqls 必须有一个
        if "sql" not in task and "sqls" not in task:
            raise ValueError(
                f"任务 '{task['id']}' 必须配置 'sql' 或 'sqls'"
            )

        # 验证 type 字段
        if task["type"] not in ["read", "write", "edit"]:
            raise ValueError(
                f"任务 '{task['id']}' 的 type 必须是 'read'、'write' 或 'edit'"
            )

        # 验证参数配置
        if "params" in task:
            for j, param in enumerate(task["params"]):
                self._validate_param(param, task["id"], j)

    def _validate_param(
        self, param: Dict[str, Any], task_id: str, index: int
    ) -> None:
        """
        验证参数配置的完整性
        
        Args:
            param: 参数配置字典
            task_id: 所属任务的 ID
            index: 参数在列表中的索引
            
        Raises:
            ValueError: 参数配置不完整
        """
        required_keys = ["name", "label", "widget"]
        missing_keys = [key for key in required_keys if key not in param]
        
        if missing_keys:
            raise ValueError(
                f"任务 '{task_id}' 的参数 #{index + 1} 缺少必要字段: {missing_keys}"
            )

        # 验证 widget 类型
        valid_widgets = ["text", "number", "select", "date", "textarea"]
        if param["widget"] not in valid_widgets:
            raise ValueError(
                f"任务 '{task_id}' 的参数 '{param['name']}' 的 widget 类型无效，"
                f"有效类型: {valid_widgets}"
            )

        # select 类型必须有 options
        if param["widget"] == "select" and "options" not in param:
            raise ValueError(
                f"任务 '{task_id}' 的参数 '{param['name']}' 是 select 类型，"
                f"但缺少 options 配置"
            )

    def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        根据 ID 获取特定任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            任务配置字典，如果不存在则返回 None
        """
        tasks = self.load_tasks()
        for task in tasks:
            if task["id"] == task_id:
                return task
        return None


# 全局配置加载器实例
config_loader = ConfigLoader()
