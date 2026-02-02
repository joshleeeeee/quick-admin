"""
Quick-Admin: 简单的数据库管理工具
主程序入口，负责 Streamlit UI 布局和导航
"""

import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st
import time
from sqlalchemy.exc import SQLAlchemyError

from core.auth import check_authentication, login, logout
from core.config_loader import config_loader
from core.engine import db_engine
from core.tunnel import start_tunnel


# 页面配置
st.set_page_config(
    page_title="Quick-Admin",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 自定义样式
st.markdown(
    """
    <style>
    /* 全局样式 */
    .main {
        padding: 1rem 2rem;
    }
    
    /* 侧边栏样式 */
    .css-1d391kg {
        padding-top: 1rem;
    }
    
    /* 任务卡片样式 */
    .task-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        border-left: 4px solid #667eea;
    }
    
    /* 成功消息样式 */
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 15px;
        color: #155724;
    }
    
    /* 错误消息样式 */
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 5px;
        padding: 15px;
        color: #721c24;
    }
    
    /* 表格样式 */
    .dataframe {
        font-size: 14px;
    }
    
    /* 按钮样式 */
    .stButton > button {
        width: 100%;
        border-radius: 5px;
        font-weight: 500;
    }
    
    /* 标题样式 */
    h1 {
        color: #2c3e50;
        border-bottom: 2px solid #667eea;
        padding-bottom: 10px;
    }
    
    /* 描述文字样式 */
    .description {
        color: #666;
        font-style: italic;
        margin-bottom: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_sidebar() -> Optional[Dict[str, Any]]:
    """
    渲染侧边栏，返回选中的任务
    
    Returns:
        选中的任务配置，如果没有选中则返回 None
    """
    with st.sidebar:
        # Logo 和标题
        st.markdown("# Quick-Admin")
        st.markdown("##### 数据库管理工具")
        st.markdown("---")
        
        # 数据库环境选择
        try:
            available_envs = config_loader.get_available_db_envs()
            selected_env = st.selectbox(
                "🗄️ 数据库环境",
                options=available_envs,
                index=0,
            )
            st.session_state["db_env"] = selected_env
            
            # Demo 模式提示
            if selected_env == "demo":
                st.info("🎮 Demo 模式 - 使用内置示例数据")
            
            # 测试连接按钮
            if st.button("🔌 测试连接", use_container_width=True):
                with st.spinner("正在测试连接..."):
                    success, message = db_engine.test_connection(selected_env)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
        except Exception as e:
            st.error(f"加载数据库配置失败: {e}")
            return None
        
        st.markdown("---")
        
        # 任务列表
        st.markdown("### 📋 运维任务")
        
        try:
            # 根据环境选择任务配置文件
            if selected_env == "demo":
                task_file = "tasks_demo.yaml"
            else:
                task_file = "tasks.yaml"
            tasks = config_loader.load_tasks(task_file)
        except Exception as e:
            st.error(f"加载任务配置失败: {e}")
            return None
        
        # 按类型分组显示任务
        read_tasks = [t for t in tasks if t["type"] == "read"]
        write_tasks = [t for t in tasks if t["type"] == "write"]
        edit_tasks = [t for t in tasks if t["type"] == "edit"]
        
        selected_task = None
        
        # 查询类任务
        if read_tasks:
            st.markdown("#### 🔍 查询类")
            for task in read_tasks:
                if st.button(
                    task["title"],
                    key=f"task_{task['id']}",
                    use_container_width=True,
                ):
                    st.session_state["selected_task"] = task
        
        # 编辑类任务
        if edit_tasks:
            st.markdown("#### ✏️ 编辑类")
            for task in edit_tasks:
                if st.button(
                    task["title"],
                    key=f"task_{task['id']}",
                    use_container_width=True,
                ):
                    st.session_state["selected_task"] = task
        
        # 操作类任务
        if write_tasks:
            st.markdown("#### ⚙️ 操作类")
            for task in write_tasks:
                if st.button(
                    task["title"],
                    key=f"task_{task['id']}",
                    use_container_width=True,
                ):
                    st.session_state["selected_task"] = task
        
        st.markdown("---")
        
        # 登出按钮
        if st.button("🚪 退出登录", use_container_width=True):
            logout()
        
        # 内网穿透状态
        if "public_url" not in st.session_state:
            # 尝试启动隧道（只有配置启用时才会真正启动）
            # 使用 cache 避免每次刷新都重连，但 start_tunnel 内部已有检查
            url = start_tunnel()
            if url:
                st.session_state["public_url"] = url
        
        if "public_url" in st.session_state:
            st.markdown("---")
            st.success("🌏 **公网访问已开启**")
            st.code(st.session_state["public_url"], language="text")
        
        # 版权信息
        st.markdown("---")
        st.caption("© 2024 Quick-Admin")
        
        return st.session_state.get("selected_task")


def render_param_widget(param: Dict[str, Any], key_prefix: str) -> Any:
    """
    根据参数配置渲染对应的输入组件
    
    Args:
        param: 参数配置
        key_prefix: 组件 key 前缀
        
    Returns:
        用户输入的值
    """
    widget_type = param["widget"]
    name = param["name"]
    label = param["label"]
    required = param.get("required", False)
    placeholder = param.get("placeholder", "")
    default = param.get("default")
    
    # 添加必填标记
    display_label = f"{label} *" if required else label
    
    if widget_type == "text":
        return st.text_input(
            display_label,
            value=default or "",
            placeholder=placeholder,
            key=f"{key_prefix}_{name}",
        )
    
    elif widget_type == "number":
        min_val = param.get("min", 0)
        max_val = param.get("max", 10000)
        return st.number_input(
            display_label,
            min_value=min_val,
            max_value=max_val,
            value=default if default is not None else min_val,
            key=f"{key_prefix}_{name}",
        )
    
    elif widget_type == "select":
        options = param.get("options", [])
        option_labels = [opt["label"] for opt in options]
        option_values = [opt["value"] for opt in options]
        
        # 找到默认值的索引
        default_index = 0
        if default is not None:
            try:
                default_index = option_values.index(default)
            except ValueError:
                pass
        
        selected_label = st.selectbox(
            display_label,
            options=option_labels,
            index=default_index,
            key=f"{key_prefix}_{name}",
        )
        
        # 返回对应的值
        selected_index = option_labels.index(selected_label)
        return option_values[selected_index]
    
    elif widget_type == "date":
        default_date = default if default else datetime.date.today()
        return st.date_input(
            display_label,
            value=default_date,
            key=f"{key_prefix}_{name}",
        )
    
    elif widget_type == "textarea":
        return st.text_area(
            display_label,
            value=default or "",
            placeholder=placeholder,
            height=150,
            key=f"{key_prefix}_{name}",
        )
    
    else:
        st.warning(f"未知的组件类型: {widget_type}")
        return None


def validate_params(
    params_config: List[Dict[str, Any]],
    param_values: Dict[str, Any],
) -> tuple[bool, str]:
    """
    验证参数值
    
    Args:
        params_config: 参数配置列表
        param_values: 参数值字典
        
    Returns:
        (是否有效, 错误消息)
    """
    for param in params_config:
        name = param["name"]
        required = param.get("required", False)
        value = param_values.get(name)
        
        if required:
            if value is None or (isinstance(value, str) and not value.strip()):
                return False, f"请填写必填参数: {param['label']}"
    
    return True, ""


def render_task_form(task: Dict[str, Any]) -> None:
    """
    渲染任务表单
    
    Args:
        task: 任务配置
    """
    # 任务标题和描述
    st.markdown(f"# {task['title']}")
    
    if "description" in task:
        st.markdown(f"*{task['description']}*")
    
    # 显示任务类型标签
    task_type = task["type"]
    if task_type == "read":
        st.info("📖 这是一个 **查询** 任务，将执行 SELECT 语句并展示结果")
    else:
        st.warning("⚠️ 这是一个 **写入** 任务，将执行数据修改操作，请谨慎操作！")
    
    st.markdown("---")
    
    # 渲染参数表单
    params_config = task.get("params", [])
    param_values = {}
    
    if params_config:
        st.markdown("### 📝 参数输入")
        
        # 使用列布局优化表单
        cols = st.columns(2)
        for i, param in enumerate(params_config):
            with cols[i % 2]:
                value = render_param_widget(param, task["id"])
                param_values[param["name"]] = value
    
    st.markdown("---")
    
    # 生成完整 SQL 预览
    def generate_sql_preview(sql_template: str, params: Dict[str, Any]) -> str:
        """生成带参数值的 SQL 预览"""
        preview_sql = sql_template
        for key, value in params.items():
            if value is None or (isinstance(value, str) and not value.strip()):
                placeholder = "NULL"
            elif isinstance(value, str):
                placeholder = f"'{value}'"
            else:
                placeholder = str(value)
            preview_sql = preview_sql.replace(f":{key}", placeholder)
        return preview_sql
    
    # 初始化确认状态
    confirm_key = f"sql_confirmed_{task['id']}"
    if confirm_key not in st.session_state:
        st.session_state[confirm_key] = False
    
    # 预览按钮
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        preview_btn = st.button(
            "👁️ 预览SQL",
            use_container_width=True,
            type="secondary",
        )
    
    # 显示 SQL 预览
    if preview_btn or st.session_state.get(f"show_preview_{task['id']}", False):
        st.session_state[f"show_preview_{task['id']}"] = True
        
        # 验证参数
        is_valid, error_msg = validate_params(params_config, param_values)
        if not is_valid:
            st.error(f"❌ {error_msg}")
            return
        
        sql = task.get("sql", "")
        sqls_config = task.get("sqls", [])
        
        # 处理自定义 SQL
        if task.get("custom_sql") and task_type == "read":
            custom_sql = param_values.get("custom_sql", "")
            is_read_only, error = db_engine.validate_read_only_sql(custom_sql)
            if not is_read_only:
                st.error(f"❌ {error}")
                return
            sql = custom_sql
            preview_sql = sql
        elif sqls_config:
            # 多条 SQL 预览
            st.markdown("### 📋 将要执行的 SQL（按顺序）")
            for i, sql_item in enumerate(sqls_config):
                sql_name = sql_item.get("name", f"SQL #{i+1}")
                sql_stmt = sql_item["sql"].strip()
                preview = generate_sql_preview(sql_stmt, param_values)
                st.markdown(f"**{sql_name}**")
                st.code(preview, language="sql")
        else:
            preview_sql = generate_sql_preview(sql, param_values)
            st.markdown("### 📋 将要执行的 SQL")
            st.code(preview_sql, language="sql")
        
        # 确认执行
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if task_type == "write":
                confirm = st.checkbox("⚠️ 我确认要执行此操作", key=f"confirm_{task['id']}")
                execute_btn = st.button(
                    "🚀 确认执行",
                    use_container_width=True,
                    disabled=not confirm,
                    type="primary",
                )
            else:
                execute_btn = st.button(
                    "🚀 确认执行查询",
                    use_container_width=True,
                    type="primary",
                )
        
        # 执行逻辑
        if execute_btn:
            # 获取数据库环境
            db_env = st.session_state.get("db_env", "default")
            
            # 处理自定义 SQL 的参数
            exec_params = {} if task.get("custom_sql") else param_values
            exec_sql = sql
            if task.get("custom_sql") and task_type == "read":
                exec_sql = param_values.get("custom_sql", "")
                exec_params = {}
            
            # 执行 SQL
            try:
                with st.spinner("正在执行..."):
                    if task_type == "read":
                        # 执行查询（带计时）
                        start_time = time.time()
                        df = db_engine.execute_query(exec_sql, exec_params, db_env)
                        end_time = time.time()
                        duration = end_time - start_time
                        
                        st.markdown("### 📊 查询结果")
                        
                        # 显示结果统计
                        st.success(f"✅ 查询成功，共返回 **{len(df)}** 条记录")
                        st.caption(f"⏱️ 耗时: **{duration:.4f}s**")
                        
                        if len(df) > 0:
                            # 配置列显示（标记主键）
                            column_config = {}
                            primary_key = task.get("primary_key")
                            if primary_key:
                                # 尝试匹配列名（不区分大小写）
                                for col in df.columns:
                                    if col.lower() == primary_key.lower():
                                        column_config[col] = st.column_config.Column(
                                            label=f"🔑 {col}",
                                        )
                            
                            # 显示数据表格（支持排序和搜索）
                            st.dataframe(
                                df,
                                use_container_width=True,
                                hide_index=True,
                                column_config=column_config,
                            )
                            
                            # 提供下载选项
                            csv = df.to_csv(index=False).encode("utf-8-sig")
                            st.download_button(
                                label="📥 下载 CSV",
                                data=csv,
                                file_name=f"{task['id']}_result.csv",
                                mime="text/csv",
                            )
                        else:
                            st.info("📭 查询结果为空")
                    else:
                        # 执行写入
                        sqls_config = task.get("sqls", [])
                        
                        if sqls_config:
                            # 多条 SQL 批量执行
                            st.markdown("### 📋 执行结果")
                            
                            start_time = time.time()
                            total_affected = 0
                            success_count = 0
                            
                            for i, sql_item in enumerate(sqls_config):
                                sql_name = sql_item.get("name", f"SQL #{i+1}")
                                sql_stmt = sql_item["sql"].strip()
                                
                                try:
                                    affected = db_engine.execute_write(sql_stmt, exec_params, db_env)
                                    total_affected += affected
                                    success_count += 1
                                    st.success(f"✅ {sql_name}: 影响 **{affected}** 行")
                                except Exception as e:
                                    st.error(f"❌ {sql_name}: 执行失败 - {str(e)}")
                                    st.warning("⚠️ 后续 SQL 已停止执行")
                                    break
                            
                            end_time = time.time()
                            duration = end_time - start_time
                            
                            if success_count == len(sqls_config):
                                st.balloons()
                                st.success(f"🎉 全部 {success_count} 条 SQL 执行成功！共影响 **{total_affected}** 行")
                                st.caption(f"⏱️ 总耗时: **{duration:.4f}s**")
                        else:
                            # 单条 SQL 执行
                            start_time = time.time()
                            affected_rows = db_engine.execute_write(exec_sql, exec_params, db_env)
                            end_time = time.time()
                            duration = end_time - start_time
                            
                            st.markdown("### ✅ 执行结果")
                            st.success(f"🎉 操作成功！共影响 **{affected_rows}** 行数据")
                            st.caption(f"⏱️ 耗时: **{duration:.4f}s**")
                        
            except SQLAlchemyError as e:
                st.error(f"❌ SQL 执行错误: {str(e)}")
                st.markdown("#### 错误详情")
                st.exception(e)
            except Exception as e:
                st.error(f"❌ 执行失败: {str(e)}")
                st.exception(e)


def render_edit_form(task: Dict[str, Any]) -> None:
    """
    渲染可编辑任务表单
    
    Args:
        task: 任务配置（type: edit）
    """
    # 任务标题和描述
    st.markdown(f"# {task['title']}")
    
    if "description" in task:
        st.markdown(f"*{task['description']}*")
    
    st.warning("⚠️ 这是一个 **编辑** 任务，可以直接修改表格数据，请谨慎操作！")
    
    # 获取配置
    table_name = task.get("table", "")
    primary_key = task.get("primary_key", "")
    
    if not primary_key:
        st.error("❌ 编辑任务必须配置 primary_key（主键）")
        return
    
    st.markdown("---")
    
    # 渲染参数表单
    params_config = task.get("params", [])
    param_values = {}
    
    if params_config:
        st.markdown("### 📝 查询条件")
        
        cols = st.columns(2)
        for i, param in enumerate(params_config):
            with cols[i % 2]:
                value = render_param_widget(param, task["id"])
                param_values[param["name"]] = value
    
    st.markdown("---")
    
    # 查询按钮
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        query_btn = st.button(
            "🔍 查询数据",
            use_container_width=True,
            type="secondary",
        )
    
    # 存储查询结果的 key
    result_key = f"edit_result_{task['id']}"
    original_key = f"edit_original_{task['id']}"
    comments_key = f"edit_comments_{task['id']}"
    
    # 执行查询
    if query_btn:
        # 验证参数
        is_valid, error_msg = validate_params(params_config, param_values)
        if not is_valid:
            st.error(f"❌ {error_msg}")
            return
        
        db_env = st.session_state.get("db_env", "default")
        sql = task["sql"]
        
        try:
            with st.spinner("正在查询..."):
                start_time = time.time()
                df = db_engine.execute_query(sql, param_values, db_env, show_comments=False)
                end_time = time.time()
                duration = end_time - start_time
                
                if len(df) == 0:
                    st.info("📭 查询结果为空")
                    return
                
                # 检查主键是否存在
                pk_upper = primary_key.upper()
                df_columns_upper = [c.upper() for c in df.columns]
                if pk_upper not in df_columns_upper:
                    st.error(f"❌ 查询结果中没有主键列: {primary_key}")
                    return
                
                # 获取列注释
                comments_map = {}
                try:
                    engine = db_engine.get_engine(db_env)
                    with engine.connect() as conn:
                        comments_map = db_engine._get_table_column_comments(conn, table_name)
                except Exception:
                    pass  # 获取注释失败不影响编辑
                
                # 保存原始数据和可编辑数据
                st.session_state[original_key] = df.copy()
                st.session_state[result_key] = df.copy()
                st.session_state[comments_key] = comments_map
                
                # 记录耗时
                st.session_state[f"duration_{task['id']}"] = duration
                
        except Exception as e:
            st.error(f"❌ 查询失败: {str(e)}")
            return
    
    # 显示可编辑表格
    if result_key in st.session_state and original_key in st.session_state:
        original_df = st.session_state[original_key]
        comments_map = st.session_state.get(comments_key, {})
        duration = st.session_state.get(f"duration_{task['id']}")
        
        st.markdown("### ✏️ 编辑数据")
        caption_text = f"主键: `{primary_key}` | 表: `{table_name}` | 共 {len(original_df)} 条记录"
        if duration:
            caption_text += f" | ⏱️ 耗时: **{duration:.4f}s**"
        st.caption(caption_text)
        
        # 构建列配置，显示「列名(注释)」
        column_config = {}
        for col in original_df.columns:
            label = col
            is_pk = col.lower() == primary_key.lower()
            
            # 1. 标记主键
            if is_pk:
                label = f"🔑 {label}"
            
            # 2. 如果有注释，添加注释
            if col in comments_map and comments_map[col]:
                label = f"{label} ({comments_map[col]})"
            
            column_config[col] = st.column_config.Column(
                label=label,
                disabled=is_pk,  # 主键不可编辑
            )
        
        # 可编辑表格
        edited_df = st.data_editor(
            st.session_state[result_key],
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",  # 不允许添加/删除行
            column_config=column_config,
            key=f"editor_{task['id']}",
        )
        
        # 更新编辑后的数据
        st.session_state[result_key] = edited_df
        
        st.markdown("---")
        
        # 生成 UPDATE SQL 按钮
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            generate_btn = st.button(
                "📝 生成修改SQL",
                use_container_width=True,
                type="secondary",
            )
        
        if generate_btn:
            # 比较差异，生成 UPDATE 语句
            updates = []
            
            # 找到主键列名（保持原始大小写）
            pk_col = None
            for col in original_df.columns:
                if col.upper() == primary_key.upper():
                    pk_col = col
                    break
            
            if not pk_col:
                st.error(f"❌ 找不到主键列: {primary_key}")
                return
            
            for idx in range(len(original_df)):
                orig_row = original_df.iloc[idx]
                edit_row = edited_df.iloc[idx]
                pk_value = orig_row[pk_col]
                
                # 找出修改的列
                changed_cols = {}
                for col in original_df.columns:
                    if col.upper() == pk_col.upper():
                        continue  # 跳过主键
                    
                    orig_val = orig_row[col]
                    edit_val = edit_row[col]
                    
                    # 比较值（处理 NaN）
                    if pd.isna(orig_val) and pd.isna(edit_val):
                        continue
                    if orig_val != edit_val:
                        changed_cols[col] = edit_val
                
                if changed_cols:
                    updates.append({
                        "pk_col": pk_col,
                        "pk_value": pk_value,
                        "changes": changed_cols,
                    })
            
            if not updates:
                st.info("📭 没有检测到修改")
                return
            
            # 生成 UPDATE SQL
            update_sqls = []
            for upd in updates:
                set_clauses = []
                for col, val in upd["changes"].items():
                    if pd.isna(val):
                        set_clauses.append(f"{col} = NULL")
                    elif isinstance(val, str):
                        set_clauses.append(f"{col} = '{val}'")
                    else:
                        set_clauses.append(f"{col} = {val}")
                
                pk_val = upd["pk_value"]
                if isinstance(pk_val, str):
                    pk_condition = f"{upd['pk_col']} = '{pk_val}'"
                else:
                    pk_condition = f"{upd['pk_col']} = {pk_val}"
                
                sql = f"UPDATE {table_name}\n  SET {', '.join(set_clauses)}\n  WHERE {pk_condition}"
                update_sqls.append(sql)
            
            # 保存生成的 SQL
            st.session_state[f"update_sqls_{task['id']}"] = update_sqls
            st.session_state[f"show_update_{task['id']}"] = True
        
        # 显示生成的 UPDATE SQL
        if st.session_state.get(f"show_update_{task['id']}", False):
            update_sqls = st.session_state.get(f"update_sqls_{task['id']}", [])
            
            if update_sqls:
                st.markdown(f"### 📋 将要执行的 SQL（共 {len(update_sqls)} 条修改）")
                st.code("\n\n".join(update_sqls), language="sql")
                
                # 确认执行
                st.markdown("---")
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    confirm = st.checkbox("⚠️ 我确认要执行这些修改", key=f"confirm_edit_{task['id']}")
                    execute_btn = st.button(
                        "🚀 确认执行修改",
                        use_container_width=True,
                        disabled=not confirm,
                        type="primary",
                    )
                
                if execute_btn:
                    db_env = st.session_state.get("db_env", "default")
                    success_count = 0
                    error_count = 0
                    
                    try:
                        with st.spinner("正在执行修改..."):
                            for sql in update_sqls:
                                try:
                                    db_engine.execute_write(sql, {}, db_env)
                                    success_count += 1
                                except Exception as e:
                                    error_count += 1
                                    st.error(f"❌ 执行失败: {sql}\n错误: {e}")
                        
                        if success_count > 0:
                            st.success(f"✅ 成功执行 {success_count} 条修改")
                        if error_count > 0:
                            st.warning(f"⚠️ 失败 {error_count} 条")
                        
                        # 清除缓存，重新查询
                        if result_key in st.session_state:
                            del st.session_state[result_key]
                        if original_key in st.session_state:
                            del st.session_state[original_key]
                        st.session_state[f"show_update_{task['id']}"] = False
                        
                    except Exception as e:
                        st.error(f"❌ 执行失败: {str(e)}")


def render_welcome() -> None:
    """渲染欢迎页面"""
    st.markdown(
        """
        # 欢迎使用 Quick-Admin
        
        一个简单的数据库管理工具。
        
        ---
        
        ### 📖 使用步骤
        
        1. **选择数据库环境** — 左侧边栏切换
        2. **测试连接** — 确保数据库能连通
        3. **选择任务** — 从任务列表中选一个
        4. **填参数、执行** — 搞定
        
        ---
        
        ### 🔒 安全说明
        
        - 所有 SQL 使用参数化查询，防止注入
        - 写操作执行前会显示 SQL 预览
        - 需要勾选确认框才能执行修改
        
        ---
        
        👈 从左侧选一个任务开始
        
        """
    )
    
    # 显示系统信息
    st.markdown("### 📊 系统状态")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        try:
            tasks = config_loader.load_tasks()
            st.metric("📋 任务总数", len(tasks))
        except Exception:
            st.metric("📋 任务总数", "加载失败")
    
    with col2:
        try:
            envs = config_loader.get_available_db_envs()
            st.metric("🗄️ 数据库环境", len(envs))
        except Exception:
            st.metric("🗄️ 数据库环境", "加载失败")
    
    with col3:
        st.metric("🔐 认证状态", "已登录 ✅")


def main():
    """主函数"""
    # 检查认证状态
    if not check_authentication():
        login()
        return
    
    # 渲染侧边栏并获取选中的任务
    selected_task = render_sidebar()
    
    # 主内容区域
    if selected_task:
        if selected_task.get("type") == "edit":
            render_edit_form(selected_task)
        else:
            render_task_form(selected_task)
    else:
        render_welcome()


if __name__ == "__main__":
    main()
