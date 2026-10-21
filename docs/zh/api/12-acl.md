# ACL API

ACL API 管理 `viking://resources/...` 共享资源的直接授权，并返回节点继承后的有效权限。个人资源不接受 ACL，需要分享时应移动到共享区。

权限模型和继承规则请先阅读 [资源访问控制（ACL）](../concepts/15-acl.md)。

## 接口总览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/acl?uri={uri}` | 获取直接、继承和有效 ACL |
| PUT | `/api/v1/acl` | 替换当前节点的直接 ACL |
| DELETE | `/api/v1/acl?uri={uri}` | 清空当前节点的直接 ACL |
| POST | `/api/v1/acl/grant` | 设置一个 principal 的直接权限级别 |
| POST | `/api/v1/acl/revoke` | 删除一个 principal 的直接授权 |

所有接口都要求调用者对目标节点拥有 `manage`。共享资源由 account `ADMIN` 隐式管理。

`viking://resources` 是固定共享 scope，不能设置直接 ACL。账号配置
`acl.enabled` 默认为 `false`。关闭时，共享资源完全使用原有公开规则，不执行 ACL
鉴权；开启后，新建共享文件、目录和 `add-resource` 根节点会给创建者直接
`manage`，同时继承父目录 ACL。已有且未设置 ACL 的内容仍按公开规则访问；
`add-resource` 的内部节点只继承，不重复写直接权限。

## 数据结构

### ACL entry

```json
{
  "principal": "user:bob",
  "level": "read"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `principal` | string | `user:{user_id}`、`group:{group_id}` 或 `user:*` |
| `level` | string | `read`、`write` 或 `manage` |

`group_id` 由调用者通过 [Admin API](./08-admin.md#用户组) 指定，是 account 内唯一且稳定的标识；用户组没有单独的展示名称。删除用户组后，旧 principal 不再匹配请求，除非重新创建同一个 `group_id`。

### ACL report

```json
{
  "uri": "viking://resources/project-a",
  "acl_enabled": true,
  "direct_entries": [
    {"principal": "user:bob", "level": "read"}
  ],
  "inherited_entries": [
    {"principal": "group:engineering", "level": "write"}
  ],
  "effective_entries": [
    {"principal": "group:engineering", "level": "write"},
    {"principal": "user:bob", "level": "read"}
  ]
}
```

| 字段 | 说明 |
|------|------|
| `direct_entries` | 只包含当前节点直接设置的条目 |
| `inherited_entries` | 所有祖先目录直接 ACL 的合并结果 |
| `effective_entries` | `direct_entries` 与 `inherited_entries` 的合并结果 |
| `acl_enabled` | 当前节点或任一祖先存在直接 ACL 时为 `true`；只读派生字段 |

account `ADMIN` 的隐式 `manage` 权限不出现在这些列表中。

## 获取 ACL

```
GET /api/v1/acl?uri={uri}
```

GET 可以在目标尚无 context 记录时返回结果：`direct_entries` 为空，继承权限从已有祖先 context 计算。修改 ACL 的接口要求目标已有 context 记录。

```bash
curl "http://localhost:1933/api/v1/acl?uri=viking%3A%2F%2Fresources%2Fproject-a" \
  -H "X-API-Key: your-key"
```

**Python SDK**

```python
report = client.acl_get("viking://resources/project-a")
```

**Go SDK**

```go
report, err := client.ACL(ctx, "viking://resources/project-a")
```

## 替换直接 ACL

```
PUT /api/v1/acl
```

请求体：

```json
{
  "uri": "viking://resources/project-a",
  "entries": [
    {"principal": "user:bob", "level": "read"},
    {"principal": "group:engineering", "level": "write"}
  ]
}
```

`entries` 会完整替换当前节点的直接 ACL，不影响祖先或后代节点自己的直接 ACL。重复 principal 会保留最高权限级别。传入空数组等价于删除当前节点的直接 ACL。

```bash
curl -X PUT http://localhost:1933/api/v1/acl \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "uri": "viking://resources/project-a",
    "entries": [
      {"principal": "user:bob", "level": "read"},
      {"principal": "group:engineering", "level": "write"}
    ]
  }'
```

**Python SDK**

```python
report = client.acl_set(
    "viking://resources/project-a",
    [
        {"principal": "user:bob", "level": "read"},
        {"principal": "group:engineering", "level": "write"},
    ],
)
```

异步客户端使用相同方法名：

```python
report = await client.acl_set(uri, entries)
```

**Go SDK**

```go
report, err := client.SetACL(ctx, "viking://resources/project-a", []openviking.ACLEntry{
    {Principal: "user:bob", Level: "read"},
    {Principal: "group:engineering", Level: "write"},
})
```

**CLI**

```bash
ov acl set viking://resources/project-a \
  --entry user:bob=read \
  --entry group:engineering=write
```

## 设置单个 principal 权限

```
POST /api/v1/acl/grant
```

```json
{
  "uri": "viking://resources/project-a",
  "principal": "user:bob",
  "level": "write"
}
```

该接口将 Bob 在当前节点上的直接 level 设置为 `write`。如果已有直接条目，则更新该条目；其他用户条目不变。

```bash
curl -X POST http://localhost:1933/api/v1/acl/grant \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "uri": "viking://resources/project-a",
    "principal": "user:bob",
    "level": "write"
  }'
```

```python
report = client.acl_grant(
    "viking://resources/project-a",
    principal="user:bob",
    level="write",
)
```

```bash
ov acl grant viking://resources/project-a --principal user:bob --level write
```

## 删除单个 principal 的直接授权

```
POST /api/v1/acl/revoke
```

```json
{
  "uri": "viking://resources/project-a",
  "principal": "user:bob"
}
```

`revoke` 只删除当前节点上 Bob 的直接条目。Bob 从祖先继承的权限仍然有效。

```python
report = client.acl_revoke("viking://resources/project-a", principal="user:bob")
```

```bash
ov acl revoke viking://resources/project-a --principal user:bob
```

## 清空当前节点的直接 ACL

```
DELETE /api/v1/acl?uri={uri}
```

该接口不删除后代节点的直接 ACL。清空后，当前节点从祖先 ACL 重新继承；每个后代继续由其祖先与自身的直接 ACL 计算有效权限。

```bash
curl -X DELETE \
  "http://localhost:1933/api/v1/acl?uri=viking%3A%2F%2Fresources%2Fproject-a" \
  -H "X-API-Key: your-key"
```

```python
report = client.acl_delete("viking://resources/project-a")
```

```bash
ov acl rm viking://resources/project-a
```

## 大小写别名与 ACL

使用 `localfs` 且底层文件系统大小写不敏感时，ACL 按请求 URI 解析权限，底层文件系统可能把仅大小写不同的 URI 解析到同一个真实文件或目录。若别名 URI 的权限判断被放行，后续 `read`、`stat`、`ls`、`write`、`rm`、`cp`、`mv` 等操作可能作用到真实对象。

直观例子：

```bash
# Bob 的目录只给 Bob 权限
ov acl set viking://resources/bob-private --acl-mode restricted --entry user:bob=manage

# Alice 读取精确路径，应返回 403
ov read viking://resources/bob-private/private.md

# 在大小写不敏感的 localfs 上，别名目录可能命中同一个真实目录
ov read viking://resources/BOB-PRIVATE/private.md
ov ls viking://resources/BOB-PRIVATE
ov write viking://resources/BOB-PRIVATE/private.md --content changed --mode replace
```

同一风险也适用于共享资源树中可通过公开 URI 访问的系统生成文件，例如 `.abstract.md` 和 `.overview.md`。例如真实文件是 `viking://resources/bob-private/.overview.md` 时，`viking://resources/BOB-PRIVATE/.OVERVIEW.md` 也可能命中它。未通过公开 URI 暴露的底层内部数据库、队列或锁文件不属于该 URI 别名问题的直接影响范围。

大小写敏感系统上，`BOB-PRIVATE` 和 `bob-private` 是不同路径；别名目标不存在时返回 `NOT_FOUND`，不会触发该问题。

## 错误处理

接口先校验 manage，再向已授权调用者确认 URI 是否存在，避免通过错误类型探测资源。

| 场景 | 错误 |
|------|------|
| URI 不在 `viking://resources/...` | `INVALID_ARGUMENT` |
| 调用者没有 manage | `PERMISSION_DENIED` |
| 已授权调用者访问不存在的 URI | `NOT_FOUND` |
| 修改 ACL 时 URI 尚无 context 记录 | `INVALID_ARGUMENT`，需先完成索引 |
| `principal` 格式非法，或使用 `group:*` | `INVALID_ARGUMENT` |
| level 不是 `read/write/manage` | `INVALID_ARGUMENT` |
| 请求包含 `acl_enabled` 等未知字段 | `INVALID_ARGUMENT` |

ACL 的 direct 和 inherited 字段都保存在 context。更新会在同一子树批处理中修改目标 direct 并重算后代 inherited；写入失败时恢复原 context ACL 字段。

## 相关文档

- [资源访问控制（ACL）](../concepts/15-acl.md) - 权限、继承和检索语义
- [认证](../guides/04-authentication.md) - 请求身份与 account 角色
- [文件系统 API](./03-filesystem.md) - 受 ACL 控制的文件操作
- [检索 API](./06-retrieval.md) - `find/search` 接口
