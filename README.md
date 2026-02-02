# Quick-Admin

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red.svg)](https://streamlit.io)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**一个简单的数据库管理工具** — 写 YAML 配置，自动生成网页界面，查数据、改数据更方便。

适合：开发、DBA、业务人员日常查数据、改数据、跑脚本。

---

## ✨ 特性

| 特性 | 说明 |
|------|------|
| 📝 **YAML 驱动** | 通过配置文件定义任务，无需编写代码 |
| 🔍 **查询任务** | 支持参数化查询，结果可导出 CSV |
| ✏️ **编辑任务** | 表格直接编辑，自动生成 UPDATE SQL |
| ⚙️ **批量操作** | 多条 SQL 按顺序执行，失败自动停止 |
| 🔒 **安全防护** | 参数化查询、SQL 预览、二次确认 |
| 💬 **列注释显示** | 自动显示数据库字段注释（Oracle） |
| 🌐 **多数据库支持** | MySQL、Oracle、PostgreSQL、SQLite |
| 🔗 **SSH 隧道** | 支持跳板机连接内网数据库 |

---

## 🚀 快速开始

### 方式一：Demo 模式（推荐体验）

```bash
# 克隆项目
git clone https://github.com/joshleeeeee/quick-admin.git
cd quick-admin

# 安装依赖
pip install -r requirements.txt

# 初始化 Demo 数据库
python scripts/init_demo.py

# 启动应用
streamlit run app.py
```

访问 http://localhost:8501，密码：`admin`，选择 **demo** 环境体验！

### 方式二：连接自己的数据库

```bash
# 复制配置模板
cp configs/db_config.example.yaml configs/db_config.yaml
cp configs/tasks.example.yaml configs/tasks.yaml

# 编辑配置文件
# - db_config.yaml: 配置数据库连接
# - tasks.yaml: 定义任务

# 启动应用
streamlit run app.py
```

> 💡 **配置文件说明**
> - `*.example.yaml` — 模板文件，提交到 Git
> - `*.yaml` — 本地配置，已被 `.gitignore` 忽略，不会提交
> - 这样你可以安全地修改配置，不用担心提交敏感数据

---

## 📝 任务配置指南

### 任务类型

| 类型 | 说明 | 用途 |
|------|------|------|
| `read` | 查询任务 | SELECT 查询，结果可导出 |
| `write` | 写入任务 | INSERT/UPDATE/DELETE 操作 |
| `edit` | 编辑任务 | 表格直接编辑，生成 UPDATE |

### 查询任务示例

```yaml
- id: "query_users"
  title: "🔍 查询用户"
  description: "根据条件查询用户信息"
  type: "read"
  sql: |
    SELECT * FROM users
    WHERE username LIKE '%' || :keyword || '%'
      OR :keyword IS NULL
  params:
    - name: "keyword"
      label: "关键词"
      widget: "text"
      placeholder: "输入用户名（可选）"
      required: false
```

### 编辑任务示例

```yaml
- id: "edit_users"
  title: "✏️ 编辑用户"
  type: "edit"
  table: "users"           # 目标表名
  primary_key: "user_id"   # 主键（必须）
  sql: |
    SELECT user_id, username, email, status
    FROM users WHERE user_id = :user_id
  params:
    - name: "user_id"
      label: "用户ID"
      widget: "text"
      required: true
```

### 批量操作示例

```yaml
- id: "batch_update"
  title: "⚠️ 批量更新"
  type: "write"
  sqls:                    # 多条 SQL 按顺序执行
    - name: "1. 备份数据"
      sql: |
        INSERT INTO backup_table SELECT * FROM main_table WHERE id = :id
    - name: "2. 更新数据"
      sql: |
        UPDATE main_table SET status = 'processed' WHERE id = :id
  params:
    - name: "id"
      label: "记录ID"
      widget: "text"
      required: true
```

### 参数组件类型

| Widget | 说明 | 示例 |
|--------|------|------|
| `text` | 单行文本 | 用户名、ID |
| `number` | 数字 | 金额、数量 |
| `textarea` | 多行文本 | SQL、备注 |
| `select` | 下拉选择 | 状态、类型 |
| `date` | 日期选择 | 开始/结束日期 |

---

## 🔧 高级配置

### SSH 隧道连接

```yaml
oracle_via_jump:
  type: oracle
  host: 10.75.3.9          # 目标数据库内网IP
  port: 1522
  user: db_user
  password: db_password
  database: service_name
  service_name: true
  ssh:                     # SSH 跳板机配置
    host: 10.75.2.54       # 跳板机IP
    port: 22
    user: ssh_user
    password: ssh_password
    # key_file: ~/.ssh/id_rsa  # 或使用密钥
```

### 管理员密码配置

默认密码为 `admin123`。修改方式：

1. **配置文件（推荐）**

   ```bash
   cp configs/auth.example.yaml configs/auth.yaml
   ```
   
   在 `auth.yaml` 中设置密码：
   
   ```yaml
   password: "your_new_password"
   ```

2. **环境变量**

   ```bash
   export QUICK_ADMIN_PASSWORD="your_new_password"
   ```

### Oracle Instant Client

macOS 用户需要安装 Oracle Instant Client：

```bash
# 运行安装指引脚本
./scripts/install_oracle_client.sh

# 使用启动脚本（自动设置环境变量）
./start.sh
```

---

## 🔐 安全特性

- ✅ **参数化查询**：所有 SQL 使用绑定变量，防止 SQL 注入
- ✅ **SQL 预览**：执行前显示完整 SQL，确认后再执行
- ✅ **二次确认**：写入操作需勾选确认框
- ✅ **只读验证**：自定义 SQL 验证是否为只读操作
- ✅ **密码保护**：需要登录才能访问系统

---

## 📁 项目结构

```
quick-admin/
├── app.py                          # 主程序入口
├── requirements.txt                # Python 依赖
├── start.sh                        # 启动脚本（Oracle需要）
├── configs/
│   ├── db_config.example.yaml      # 数据库配置模板 ✅ 提交
│   ├── db_config.yaml              # 数据库配置（本地）❌ 忽略
│   ├── tasks.example.yaml          # 任务配置模板 ✅ 提交
│   ├── tasks.yaml                  # 任务配置（本地）❌ 忽略
│   ├── tasks_demo.yaml             # Demo 任务 ✅ 提交
│   ├── auth.example.yaml           # 认证配置模板 ✅ 提交
│   └── auth.yaml                   # 认证配置（本地）❌ 忽略
├── core/
│   ├── auth.py                     # 认证模块
│   ├── config_loader.py            # 配置加载器
│   └── engine.py                   # 数据库引擎
├── scripts/
│   ├── init_demo.py                # Demo 数据库初始化
│   └── install_oracle_client.sh    # Oracle 客户端安装指引
└── data/                           # 数据目录 ❌ 忽略
    └── demo.db                     # Demo SQLite 数据库
```

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启 Pull Request

---

## 📄 开源协议

本项目采用 [MIT 协议](LICENSE) 开源。

---

## 🙏 致谢

- [Streamlit](https://streamlit.io/) - 强大的 Python Web 框架
- [SQLAlchemy](https://www.sqlalchemy.org/) - SQL 工具包和 ORM

