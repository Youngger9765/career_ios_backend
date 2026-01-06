# 牌卡系统 Schema 参考文档

> 基于职游系统的 Client & Case 架构

---

## 📋 概述

牌卡系统可以直接采用职游系统的 Client 和 Case schema 设计。

**对照关系：**
```
职游系统              牌卡系统
─────────────────────────────
Client (客户)    →   client
Case (案件)      →   room
Counselor        →   (待确认)
```

**主要差异：**
- ❌ **移除 `tenant_id`** (牌卡是单租户系统)
- ✅ 其他字段完全相同
- ✅ Case 可改名为 Room

---

## 📊 Client Schema (客户)

### 完整字段列表

```python
# === 核心识别 ===
id: UUID                     # 主键
code: str                    # 客户编号 (唯一)
name: str                    # 姓名
nickname: str | None         # 昵称

# === 必填字段 ===
email: str                   # Email
gender: str                  # 性别：男/女/其他/不透露
birth_date: date             # 生日
phone: str                   # 手机

# === 身份状态 (必填) ===
identity_option: str         # 身份：学生/社会新鲜人/转职者/在职者/其他
current_status: str          # 当前状况 (用于快速分类)

# === 选填字段 ===
age: int | None              # 年龄 (从 birth_date 自动计算)
education: str | None        # 学历：高中/大学/研究所等
current_job: str | None      # 目前工作 (职位/年资)
career_status: str | None    # 职涯状态：探索中/转职准备/面试中/已在职等
occupation: str | None       # 职业
location: str | None         # 地点/居住地

# === 咨询历史 ===
has_consultation_history: str | None    # 过往咨询经验 (Yes/No + 说明)
has_mental_health_history: str | None   # 心理/精神病史 (敏感资料)

# === 背景信息 ===
economic_status: str | None             # 经济状况
family_relations: str | None            # 家庭关系描述 (Text)

# === 弹性字段 ===
other_info: dict                        # 其他信息 (JSON, default={})
tags: list                              # 标签 (JSON, default=[])
notes: str | None                       # 私密笔记 (咨询师专用, Text)

# === 关联 ===
counselor_id: UUID           # 负责咨询师 (如牌卡不需要可改为选填)

# === 时间戳 ===
created_at: datetime
updated_at: datetime | None
```

### 数据库约束

**职游版 (多租户)：**
```python
__table_args__ = (
    UniqueConstraint('tenant_id', 'code', name='uix_tenant_client_code'),
)
```

**牌卡版 (单租户)：**
```python
__table_args__ = (
    UniqueConstraint('code', name='uix_client_code'),
)
```

### 索引字段

```python
code: indexed=True
email: indexed=True
```

---

## 📋 Case/Room Schema (案件/房间)

### 完整字段列表

```python
# === 核心字段 ===
id: UUID                     # 主键
case_number: str             # 案号 (牌卡可改为 room_number)
client_id: UUID              # 所属客户
counselor_id: UUID           # 负责咨询师

# === 状态管理 ===
status: str                  # Enum: active/completed/suspended/referred
                            # default: active

# === 内容字段 ===
summary: str | None          # 摘要 (Text)
goals: str | None            # 目标 (Text)
problem_description: str | None  # 问题描述/咨询目的 (Text)

# === 时间戳 ===
created_at: datetime
updated_at: datetime | None
```

### Status Enum 定义

```python
class CaseStatus(str, enum.Enum):
    ACTIVE = "active"           # 进行中
    COMPLETED = "completed"     # 已完成
    SUSPENDED = "suspended"     # 暂停
    REFERRED = "referred"       # 转介
```

### 数据库约束

**职游版 (多租户)：**
```python
__table_args__ = (
    UniqueConstraint('tenant_id', 'case_number', name='uix_tenant_case_number'),
)
```

**牌卡版 (单租户)：**
```python
__table_args__ = (
    UniqueConstraint('case_number', name='uix_case_number'),
    # 或改为
    UniqueConstraint('room_number', name='uix_room_number'),
)
```

### 关联关系

```python
# Relationships
counselor = relationship("Counselor", back_populates="cases")
client = relationship("Client", back_populates="cases")
sessions = relationship("Session", back_populates="case")  # 会谈记录
reminders = relationship("Reminder", back_populates="case")  # 提醒事项
```

---

## 🔄 关系结构图

```
Counselor (1)
    ├─→ (N) Client
    │       └─→ (N) Case/Room
    │               ├─→ (N) Session (会谈记录)
    │               └─→ (N) Reminder (提醒事项)
    │
    └─→ (N) Case/Room (直接关联)
```

---

## 🛠️ 迁移指南

### 步骤 1: 复制职游代码

**Models:**
```bash
cp app/models/client.py → 牌卡项目/models/client.py
cp app/models/case.py → 牌卡项目/models/room.py
```

**Schemas:**
```bash
cp app/schemas/client.py → 牌卡项目/schemas/client.py
cp app/schemas/case.py → 牌卡项目/schemas/room.py
```

### 步骤 2: 修改代码

#### 2.1 移除 `tenant_id`

**models/client.py:**
```python
# 删除这行
tenant_id = Column(String, nullable=False, index=True)

# 修改约束
__table_args__ = (
    UniqueConstraint('code', name='uix_client_code'),  # 移除 tenant_id
)
```

**models/room.py (原 case.py):**
```python
# 删除这行
tenant_id = Column(String, nullable=False, index=True)

# 修改约束
__table_args__ = (
    UniqueConstraint('room_number', name='uix_room_number'),  # 移除 tenant_id
)
```

#### 2.2 改名 Case → Room (选择性)

**models/room.py:**
```python
# 类名
class Case(Base, BaseModel):  →  class Room(Base, BaseModel):

# 表名
__tablename__ = "cases"  →  __tablename__ = "rooms"

# 字段名
case_number = Column(...)  →  room_number = Column(...)
```

**schemas/room.py:**
```python
class CaseBase:  →  class RoomBase:
class CaseCreate:  →  class RoomCreate:
class CaseUpdate:  →  class RoomUpdate:
class CaseResponse:  →  class RoomResponse:

case_number: str  →  room_number: str
```

#### 2.3 调整 Schemas (Pydantic)

**schemas/client.py:**
```python
# ClientResponse 中删除
tenant_id: str  # 删除这行
```

**schemas/room.py:**
```python
# RoomResponse 中删除
tenant_id: str  # 删除这行
```

### 步骤 3: 数据库迁移

```bash
# 生成迁移文件
alembic revision --autogenerate -m "Add client and room tables"

# 执行迁移
alembic upgrade head
```

---

## ✅ 字段分级建议

如果牌卡系统不需要所有字段，可以分级采用：

### Level 1: 最小核心 (必须)
```python
# Client
id, code, name, email, phone, gender, birth_date
identity_option, current_status
counselor_id, created_at, updated_at

# Room
id, room_number, client_id, counselor_id, status
created_at, updated_at
```

### Level 2: 基础扩充 (建议)
```python
# Client
nickname, age, education, occupation, location
tags, notes

# Room
summary, goals, problem_description
```

### Level 3: 专业功能 (看需求)
```python
# Client
current_job, career_status
has_consultation_history, has_mental_health_history
economic_status, family_relations
other_info (JSON)
```

---

## 📁 职游参考档案位置

```
app/
├── models/
│   ├── client.py         # Client ORM 模型
│   ├── case.py           # Case ORM 模型
│   └── base.py           # BaseModel (含 created_at, updated_at)
│
└── schemas/
    ├── client.py         # Client Pydantic schemas
    ├── case.py           # Case Pydantic schemas
    └── base.py           # BaseSchema, BaseResponse
```

---

## 💡 优点

✅ **字段命名清晰**：经过实战验证
✅ **扩充性强**：`other_info` JSON 字段可存放任意额外数据
✅ **关联清楚**：Client → Room → Session 层次分明
✅ **未来整合性**：如果职游和牌卡未来合并，schema 完全兼容
✅ **类型安全**：完整的 type hints 和 Pydantic validation

---

## 🚨 注意事项

1. **counselor_id**: 如果牌卡系统不需要"负责人"概念，可以改为选填
2. **age 自动计算**: 需要在 model 中实现 `@hybrid_property` 或在保存时计算
3. **code 自动生成**: 建议实现自动生成逻辑（如：C001, C002...）
4. **敏感字段**: `has_mental_health_history` 需要特别处理权限控制

---

**Version**: 1.0
**基于**: 职游系统 (career_ios_backend)
**更新时间**: 2025-11-20
