"""
数据库执行引擎模块
负责数据库连接管理、参数化查询执行
"""

from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional, Tuple

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, Session

from .config_loader import config_loader


class DatabaseEngine:
    """数据库执行引擎类"""

    def __init__(self):
        """初始化数据库引擎"""
        self._engines: Dict[str, Engine] = {}
        self._session_factories: Dict[str, sessionmaker] = {}
        self._ssh_tunnels: Dict[str, Any] = {}  # SSH 隧道缓存

    def _create_ssh_tunnel(self, db_config: Dict[str, Any]) -> Optional[Tuple[str, int]]:
        """
        创建 SSH 隧道
        
        Args:
            db_config: 数据库配置（包含 ssh 子配置）
            
        Returns:
            (本地绑定地址, 本地端口) 或 None（无需隧道）
        """
        ssh_config = db_config.get("ssh")
        if not ssh_config:
            return None
        
        try:
            from sshtunnel import SSHTunnelForwarder
        except ImportError:
            raise ImportError(
                "使用 SSH 隧道需要安装 sshtunnel: pip install sshtunnel"
            )
        
        # 目标数据库地址
        remote_host = db_config["host"]
        remote_port = db_config.get("port", 1521)
        
        # SSH 跳板机配置
        ssh_host = ssh_config["host"]
        ssh_port = ssh_config.get("port", 22)
        ssh_user = ssh_config["user"]
        ssh_password = ssh_config.get("password")
        ssh_key_file = ssh_config.get("key_file")
        
        # 生成隧道缓存 key
        tunnel_key = f"{ssh_host}:{ssh_port}->{remote_host}:{remote_port}"
        
        # 复用已存在的隧道
        if tunnel_key in self._ssh_tunnels:
            tunnel = self._ssh_tunnels[tunnel_key]
            if tunnel.is_active:
                return ("127.0.0.1", tunnel.local_bind_port)
            else:
                # 隧道已断开，移除
                del self._ssh_tunnels[tunnel_key]
        
        # 创建新隧道
        tunnel_kwargs = {
            "ssh_address_or_host": (ssh_host, ssh_port),
            "ssh_username": ssh_user,
            "remote_bind_address": (remote_host, remote_port),
            "local_bind_address": ("127.0.0.1",),  # 自动分配端口
        }
        
        if ssh_key_file:
            from os.path import expanduser
            tunnel_kwargs["ssh_pkey"] = expanduser(ssh_key_file)
        elif ssh_password:
            tunnel_kwargs["ssh_password"] = ssh_password
        
        tunnel = SSHTunnelForwarder(**tunnel_kwargs)
        tunnel.start()
        
        # 缓存隧道
        self._ssh_tunnels[tunnel_key] = tunnel
        
        return ("127.0.0.1", tunnel.local_bind_port)

    def _get_connection_url(self, db_config: Dict[str, Any]) -> str:
        """
        根据配置生成数据库连接 URL
        
        Args:
            db_config: 数据库配置字典
            
        Returns:
            SQLAlchemy 连接 URL
        """
        db_type = db_config.get("type", "mysql")
        user = db_config.get("user", "")
        password = db_config.get("password", "")
        
        # 检查是否需要 SSH 隧道
        tunnel_addr = self._create_ssh_tunnel(db_config)

        if db_type == "mysql":
            # 使用 PyMySQL 驱动
            if tunnel_addr:
                host, port = tunnel_addr
            else:
                host = db_config["host"]
                port = db_config.get("port", 3306)
            database = db_config["database"]
            charset = db_config.get("charset", "utf8mb4")
            return (
                f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
                f"?charset={charset}"
            )
        
        elif db_type == "oracle":
            # 使用 cx_Oracle 驱动（支持老版本 Oracle）
            
            # 方式1：使用 TNS 名称连接（不支持 SSH 隧道）
            if "tns_name" in db_config:
                tns_name = db_config["tns_name"]
                return f"oracle+cx_oracle://{user}:{password}@{tns_name}"
            
            # 方式2/3：使用 Host + SID 或 Service Name
            if tunnel_addr:
                host, port = tunnel_addr
            else:
                host = db_config["host"]
                port = db_config.get("port", 1521)
            database = db_config["database"]
            use_service_name = db_config.get("service_name", False)
            
            if use_service_name:
                # 使用 Service Name 连接
                return (
                    f"oracle+cx_oracle://{user}:{password}@{host}:{port}"
                    f"/?service_name={database}"
                )
            else:
                # 使用 SID 连接
                return f"oracle+cx_oracle://{user}:{password}@{host}:{port}/{database}"
        
        elif db_type == "postgresql":
            if tunnel_addr:
                host, port = tunnel_addr
            else:
                host = db_config["host"]
                port = db_config.get("port", 5432)
            database = db_config["database"]
            return f"postgresql://{user}:{password}@{host}:{port}/{database}"
        
        elif db_type == "sqlite":
            database = db_config["database"]
            return f"sqlite:///{database}"
        
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")

    def get_engine(self, env: str = "default") -> Engine:
        """
        获取指定环境的数据库引擎（带缓存）
        
        Args:
            env: 数据库环境名称
            
        Returns:
            SQLAlchemy Engine 实例
        """
        if env not in self._engines:
            db_config = config_loader.load_db_config(env)
            connection_url = self._get_connection_url(db_config)
            
            # 创建引擎，配置连接池
            self._engines[env] = create_engine(
                connection_url,
                pool_pre_ping=True,  # 自动检测断开的连接
                pool_recycle=3600,   # 1小时后回收连接
                pool_size=5,         # 连接池大小
                max_overflow=10,     # 最大溢出连接数
                echo=False,          # 不打印 SQL 日志
            )
            
            # 创建 Session 工厂
            self._session_factories[env] = sessionmaker(
                bind=self._engines[env],
                autocommit=False,
                autoflush=False,
            )

        return self._engines[env]

    @contextmanager
    def get_session(self, env: str = "default") -> Generator[Session, None, None]:
        """
        获取数据库会话的上下文管理器
        
        Args:
            env: 数据库环境名称
            
        Yields:
            SQLAlchemy Session 实例
        """
        # 确保引擎已初始化
        self.get_engine(env)
        
        session = self._session_factories[env]()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def test_connection(self, env: str = "default") -> Tuple[bool, str]:
        """
        测试数据库连接
        
        Args:
            env: 数据库环境名称
            
        Returns:
            (成功标志, 消息)
        """
        try:
            db_config = config_loader.load_db_config(env)
            db_type = db_config.get("type", "mysql")
            
            engine = self.get_engine(env)
            with engine.connect() as conn:
                # Oracle 需要 FROM DUAL
                if db_type == "oracle":
                    conn.execute(text("SELECT 1 FROM DUAL"))
                else:
                    conn.execute(text("SELECT 1"))
            return True, "数据库连接成功"
        except SQLAlchemyError as e:
            return False, f"数据库连接失败: {str(e)}"
        except Exception as e:
            return False, f"连接错误: {str(e)}"

    def execute_query(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        env: str = "default",
        show_comments: bool = True,
    ) -> pd.DataFrame:
        """
        执行查询语句（SELECT）
        
        使用参数化查询防止 SQL 注入
        
        Args:
            sql: SQL 查询语句，使用 :param 占位符
            params: 参数字典
            env: 数据库环境名称
            show_comments: 是否显示列注释（仅Oracle）
            
        Returns:
            查询结果的 DataFrame
            
        Raises:
            SQLAlchemyError: SQL 执行错误
        """
        engine = self.get_engine(env)
        params = params or {}
        
        # 获取数据库类型
        db_config = config_loader.load_db_config(env)
        db_type = db_config.get("type", "mysql")

        with engine.connect() as conn:
            # 使用 text() 包装 SQL，确保参数化查询
            result = conn.execute(text(sql), params)
            
            # 获取列名
            columns = list(result.keys())
            
            # 列名去重处理（防止 SQL 中 select t1.*, t2.* 导致重复列名）
            columns = self._deduplicate_columns(columns)
            
            # 获取所有数据
            rows = result.fetchall()
            
            # 转换为 DataFrame
            df = pd.DataFrame(rows, columns=columns)
            
            # Oracle: 获取列注释并重命名列
            if show_comments and db_type == "oracle" and len(df) > 0:
                df = self._apply_column_comments(df, sql, conn)
            
            return df
            
    def _deduplicate_columns(self, columns: List[str]) -> List[str]:
        """
        对列名列表进行去重
        如果存在重复，添加后缀 _1, _2 等
        
        Args:
            columns: 原始列名列表
            
        Returns:
            去重后的列名列表
        """
        counts = {}
        new_columns = []
        
        for col in columns:
            if col not in counts:
                counts[col] = 0
                new_columns.append(col)
            else:
                counts[col] += 1
                new_columns.append(f"{col}_{counts[col]}")
        
        return new_columns

    def _apply_column_comments(
        self, 
        df: pd.DataFrame, 
        sql: str, 
        conn
    ) -> pd.DataFrame:
        """
        为 DataFrame 列名添加注释
        
        Args:
            df: 原始 DataFrame
            sql: 原始查询 SQL
            conn: 数据库连接
            
        Returns:
            列名带注释的 DataFrame
        """
        try:
            # 从 SQL 中提取表名
            table_names = self._extract_table_names(sql)
            if not table_names:
                return df
            
            # 获取所有相关表的列注释
            comments_map = {}
            for table_name in table_names:
                table_comments = self._get_table_column_comments(conn, table_name)
                comments_map.update(table_comments)
            
            if not comments_map:
                return df
            
            # 重命名列：COLUMN_NAME -> COLUMN_NAME(注释)
            new_columns = []
            for col in df.columns:
                col_upper = col.upper()
                if col_upper in comments_map and comments_map[col_upper]:
                    comment = comments_map[col_upper]
                    # 截断过长的注释
                    if len(comment) > 10:
                        comment = comment[:10] + "..."
                    new_columns.append(f"{col}({comment})")
                else:
                    new_columns.append(col)
            
            df.columns = new_columns
            return df
        except Exception:
            # 获取注释失败不影响主查询
            return df

    def _extract_table_names(self, sql: str) -> List[str]:
        """
        从 SQL 中提取表名
        
        Args:
            sql: SQL 语句
            
        Returns:
            表名列表
        """
        import re
        
        # 简单匹配 FROM 和 JOIN 后的表名
        # 支持格式: FROM table_name, FROM schema.table_name, FROM table_name alias
        pattern = r'(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?)'
        matches = re.findall(pattern, sql, re.IGNORECASE)
        
        # 提取表名（去掉 schema 前缀）
        table_names = []
        for match in matches:
            if '.' in match:
                table_names.append(match.split('.')[-1].upper())
            else:
                table_names.append(match.upper())
        
        return list(set(table_names))

    def _get_table_column_comments(
        self, 
        conn, 
        table_name: str
    ) -> Dict[str, str]:
        """
        获取表的列注释
        
        Args:
            conn: 数据库连接
            table_name: 表名
            
        Returns:
            {列名: 注释} 字典
        """
        try:
            sql = """
                SELECT COLUMN_NAME, COMMENTS 
                FROM USER_COL_COMMENTS 
                WHERE TABLE_NAME = :table_name
            """
            result = conn.execute(text(sql), {"table_name": table_name.upper()})
            rows = result.fetchall()
            
            return {row[0]: row[1] for row in rows if row[1]}
        except Exception:
            return {}

    def execute_write(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        env: str = "default",
    ) -> int:
        """
        执行写入语句（INSERT/UPDATE/DELETE）
        
        使用参数化查询防止 SQL 注入，自动提交事务
        
        Args:
            sql: SQL 写入语句，使用 :param 占位符
            params: 参数字典
            env: 数据库环境名称
            
        Returns:
            受影响的行数
            
        Raises:
            SQLAlchemyError: SQL 执行错误
        """
        params = params or {}

        with self.get_session(env) as session:
            # 使用 text() 包装 SQL，确保参数化查询
            result = session.execute(text(sql), params)
            
            # 获取受影响的行数
            rowcount = result.rowcount
            
            # 提交事务
            session.commit()
            
            return rowcount

    def validate_read_only_sql(self, sql: str) -> Tuple[bool, str]:
        """
        验证 SQL 是否为只读查询
        
        Args:
            sql: SQL 语句
            
        Returns:
            (是否只读, 错误消息)
        """
        # 移除注释和多余空白
        cleaned_sql = sql.strip().upper()
        
        # 检查是否以 SELECT 开头
        if not cleaned_sql.startswith("SELECT"):
            return False, "只允许执行 SELECT 查询语句"
        
        # 检查是否包含危险关键字
        dangerous_keywords = [
            "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", 
            "TRUNCATE", "GRANT", "REVOKE", "EXEC", "EXECUTE",
            "INTO OUTFILE", "INTO DUMPFILE", "LOAD_FILE"
        ]
        
        for keyword in dangerous_keywords:
            if keyword in cleaned_sql:
                return False, f"SQL 中包含不允许的关键字: {keyword}"
        
        return True, ""

    def close_all(self) -> None:
        """关闭所有数据库连接和 SSH 隧道"""
        # 关闭数据库引擎
        for engine in self._engines.values():
            engine.dispose()
        self._engines.clear()
        self._session_factories.clear()
        
        # 关闭 SSH 隧道
        for tunnel in self._ssh_tunnels.values():
            try:
                tunnel.stop()
            except Exception:
                pass
        self._ssh_tunnels.clear()


# 全局数据库引擎实例
db_engine = DatabaseEngine()
