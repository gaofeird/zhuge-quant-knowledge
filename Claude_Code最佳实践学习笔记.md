# Claude Code 最佳实践学习笔记

> 来源：[shanraisshan/claude-code-best-practice](https://github.com/shanraisshan/claude-code-best-practice)
> 
> 整理时间：2026年4月

---

## 目录

1. [核心概念详解](#1-核心概念详解)
2. [Boris Cherny 的 Tips 整理](#2-boris-cherny-的-tips-整理)
3. [Orchestration Workflow 模式](#3-orchestration-workflow-模式)
4. [实用配置模板](#4-实用配置模板)
5. [最佳实践总结](#5-最佳实践总结)

---

## 1. 核心概念详解

### 1.1 Subagents（子代理）

**定义**：在独立隔离上下文中运行的自主行为者，拥有自定义工具、权限、模型、记忆和持久身份。

**文件位置**：`.claude/agents/<name>.md`

**Frontmatter 字段（16个）**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 唯一标识符，使用小写字母和连字符 |
| `description` | string | 是 | 何时调用，使用 `"PROACTIVELY"` 启用自动调用 |
| `tools` | string/list | 否 | 工具白名单，支持 `Agent(agent_type)` 语法 |
| `disallowedTools` | string/list | 否 | 禁止使用的工具列表 |
| `model` | string | 否 | 模型：`haiku`, `sonnet`, `opus`, `inherit` |
| `permissionMode` | string | 否 | 权限模式：`acceptEdits`, `auto`, `bypassPermissions`, `plan` |
| `maxTurns` | integer | 否 | 最大代理轮次 |
| `skills` | list | 否 | 预加载到上下文的技能列表 |
| `mcpServers` | list | 否 | MCP 服务器配置 |
| `hooks` | object | 否 | 生命周期钩子 |
| `memory` | string | 否 | 持久记忆：`user`, `project`, `local` |
| `background` | boolean | 否 | 是否作为后台任务运行 |
| `effort` | string | 否 | 努力级别：`low`, `medium`, `high`, `max` |
| `isolation` | string | 否 | 设置为 `"worktree"` 在临时 git worktree 中运行 |
| `initialPrompt` | string | 否 | 自动作为第一个用户消息提交 |
| `color` | string | 否 | 显示颜色：`red`, `blue`, `green`, `yellow`, `purple`, `orange`, `pink`, `cyan` |

**内置 Agent 类型（5个）**：

| Agent | 模型 | 工具 | 描述 |
|-------|------|------|------|
| `general-purpose` | inherit | All | 复杂多步骤任务 - 默认代理类型 |
| `Explore` | haiku | Read-only | 快速代码库搜索和探索 |
| `Plan` | inherit | Read-only | 计划模式前的预规划研究 |
| `statusline-setup` | sonnet | Read, Edit | 配置状态栏设置 |
| `claude-code-guide` | haiku | Glob, Grep, Read, WebFetch, WebSearch | 回答 Claude Code 功能问题 |

**使用场景**：

```markdown
# 子代理定义示例
---
name: code-reviewer
description: 代码审查代理
model: sonnet
tools: Read, Glob, Grep
skills:
  - adversarial-review
  - code-style
---
```

**最佳实践**：

- 创建**特性特定**的子代理而非通用 QA/后端工程师
- 使用子代理进行上下文管理 - 问自己"我需要再次使用这个工具输出，还是只需要结论？"
- 20次文件读取 + 12次 grep + 3个死胡同保持在子代理上下文中，只有最终报告返回
- 使用 `context: fork` 在隔离的子代理上下文中运行技能

---

### 1.2 Commands（命令）

**定义**：用户调用的提示模板，将知识注入现有上下文，用于工作流编排。

**文件位置**：`.claude/commands/<name>.md`

**Frontmatter 字段（14个）**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 否 | 显示名称和 `/slash-command` 标识符 |
| `description` | string | 推荐 | 命令功能描述 |
| `when_to_use` | string | 否 | 何时调用的附加上下文 |
| `argument-hint` | string | 否 | 自动完成提示（如 `[issue-number]`）|
| `disable-model-invocation` | boolean | 否 | 设为 `true` 防止自动调用 |
| `user-invocable` | boolean | 否 | 设为 `false` 从 `/` 菜单隐藏 |
| `paths` | string/list | 否 | glob 模式限制技能激活范围 |
| `allowed-tools` | string | 否 | 活动时不需权限提示的工具 |
| `model` | string | 否 | 运行命令的模型 |
| `effort` | string | 否 | 覆盖模型努力级别 |
| `context` | string | 否 | 设为 `fork` 在隔离子代理中运行 |
| `agent` | string | 否 | `context: fork` 时的子代理类型 |
| `shell` | string | 否 | `` !`command` `` 块的 shell |
| `hooks` | object | 否 | 生命周期钩子 |

**使用场景**：

- 每天多次执行的"内循环"工作流
- 构建 `/techdebt` 命令查找重复代码
- 创建上下文转储命令同步多个数据源

**最佳实践**：

- 对于重复性工作流，优先使用 Commands 而非独立 Agents
- 使用 `--` 分隔符传递参数：`/weather-orchestrator -- celsius`

---

### 1.3 Skills（技能）

**定义**：将知识注入现有上下文的可配置、可预加载、可自动发现的单元，支持上下文分叉和渐进式披露。

**文件位置**：`.claude/skills/<name>/SKILL.md`

**Frontmatter 字段**：

```yaml
name: skill-name
description: 何时触发此技能（触发器描述）
argument-hint: [parameter-name]
disable-model-invocation: true  # 防止自动调用
user-invocable: false          # 从 / 菜单隐藏
allowed-tools: [Tool1, Tool2]
model: haiku
context: fork                  # 在隔离子代理中运行
agent: general-purpose         # context: fork 时的子代理类型
```

**核心理解**：

- **Skills 是文件夹，不是文件** - 可以包含脚本、资产、数据等
- 使用 `references/`, `scripts/`, `examples/` 子目录实现**渐进式披露**
- 描述字段是**触发器**，不是摘要 - 写给模型看（"我何时该触发？"）

---

### 1.4 Hooks（钩子）

**定义**：在特定事件发生时，在代理循环外部运行的用户定义处理器（脚本、HTTP、提示词、代理）。

**文件位置**：`.claude/hooks/`

**可用事件（26个）**：

| 事件 | 说明 | 常见用途 |
|------|------|----------|
| `SessionStart` | 会话启动时 | 动态加载上下文 |
| `SessionEnd` | 会话结束时 | 清理和保存状态 |
| `PreToolUse` | 工具使用前 | 日志记录、格式化、权限检查 |
| `PostToolUse` | 工具使用后 | 自动格式化代码 |
| `PreCompact` | 压缩前 | 自定义压缩提示 |
| `PostCompact` | 压缩后 | 验证压缩质量 |
| `PermissionRequest` | 权限请求时 | 路由到 Opus 扫描攻击 |
| `Stop` | 代理停止时 | 提示继续或验证工作 |
| `SubagentStart` | 子代理启动时 | 记录子代理活动 |
| `SubagentStop` | 子代理停止时 | 汇总子代理结果 |

**钩子类型**：

```yaml
hooks:
  PreToolUse:
    - hooks:
        - type: "command"
          command: "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/hooks.py"
          timeout: 5000
          async: true
          statusMessage: "PreToolUse"
```

**最佳实践**：

- 使用按需钩子：`/careful` 阻止破坏性命令，`/freeze` 阻止目录外编辑
- 使用 PostToolUse 钩子自动格式化代码
- 通过钩子路由权限请求到 Opus 进行安全扫描

---

### 1.5 Memory（记忆）

**定义**：通过 CLAUDE.md 文件和 `@path` 导入实现持久上下文。

**记忆位置**：

| 位置 | 说明 |
|------|------|
| `CLAUDE.md` | 项目级记忆 |
| `.claude/rules/` | 规则分割存储 |
| `~/.claude/rules/` | 全局规则 |
| `~/.claude/projects/<project>/memory/` | 项目级记忆 |

**最佳实践**：

- CLAUDE.md 应控制在 **200 行以内**
- 使用 `<important if="...">` 标签包裹领域特定规则
- 使用多个 CLAUDE.md 处理大型仓库（祖先 + 后代加载）
- 每次修正后结束："更新你的 CLAUDE.md 以避免再次犯错"
- Claude 非常擅长为自己编写规则

---

## 2. Boris Cherny 的 Tips 整理

### 2.1 Boris 的 13 个基础 Tips（2026年1月3日）

**核心原则**：

1. **不要事无巨细** - 向 Claude 提供目标，让它自己决定路径
2. **上下文优先** - 上下文是最重要的输入
3. **使用 Skills** - 创建可重用的 Skills 和 Commands
4. **善用规划** - 计划模式是最被低估的功能
5. **验证是关键** - 给 Claude 一种验证其工作的方法

**实践技巧**：

- 挑战 Claude："审查这些变更，在我通过测试前不要创建 PR"
- 中等修复后："用你现在知道的一切，废弃这个，实现优雅的方案"
- Claude 自己修复大部分 bug - 粘贴 bug，说"修复"，不要微观管理
- 使用 Git Worktrees 做并行开发
- 让第二个 Claude 作为 Staff Engineer 审查计划

---

### 2.2 Boris 的 10 个团队 Tips（2026年2月1日）

**1. 更多并行**
- 同时启动 3-5 个 Git Worktrees
- 使用 shell 别名快速切换（如 `2a`, `2b`, `2c`）

**2. 每个复杂任务从计划模式开始**
- 在计划中投入精力，让 Claude 一次性实现
- 出现问题时，切换回计划模式重新规划

**3. 投资你的 CLAUDE.md**
- 每次修正后："更新你的 CLAUDE.md"
- 无情编辑，持续迭代直到错误率下降

**4. 创建你自己的 Skills 并提交到 Git**
- 每天重复一次以上的事情 → 变成 Skill 或 Command
- 构建 `/techdebt` 命令
- 设置同步数据源的命令

**5. Claude 自己修复大部分 Bug**
- 启用 Slack MCP，粘贴 bug 线程说"修复"
- 指向 Docker 日志排查分布式系统

**6. 提升你的 Prompting**
- 挑战模式："Grill me on these changes"
- 详细规范减少歧义
- Prototype > PRD - 构建 20-30 个版本而非写规范

**7. 终端和环境设置**
- 使用 Ghostty 终端
- 自定义状态栏显示上下文使用和 git 分支
- 使用语音输入（快 3 倍）

**8. 使用子代理**
- 追加 "use subagents" 分配更多计算
- 卸载任务保持主上下文干净

**9. 使用 Claude 进行数据和分析**
- 使用 bq CLI 进行 BigQuery 查询
- 6 个月没写一行 SQL

**10. 用 Claude 学习**
- 启用 Explanatory 或 Learning 输出风格
- 让 Claude 生成可视化 HTML 演示文稿
- 构建间隔重复学习技能

---

### 2.3 Boris 的 12 个自定义 Tips（2026年2月12日）

**1. 配置你的终端**
- 运行 `/config` 设置明/暗主题
- 运行 `/terminal-setup` 启用 Shift+Enter

**2. 调整努力级别**
- `Low` - 更少 token，更快响应
- `Medium` - 平衡行为
- `High` - 更多 token，更高智能
- **Boris 偏好：所有事情都用 High**

**3. 安装插件、MCP 和 Skills**
- 运行 `/plugin` 开始
- 创建公司内部市场

**4. 创建自定义 Agents**
- 在 `.claude/agents` 中放入 `.md` 文件
- 每个 agent 可有自定义名称、颜色、工具集、权限、模型

**5. 预批准常见权限**
- 运行 `/permissions`
- 支持通配符语法：`Bash(bun run *)`

**6. 启用沙箱**
- 运行 `/sandbox`
- 支持文件和网络隔离

**7. 添加状态栏**
- 运行 `/statusline`
- 显示模型、目录、剩余上下文、成本

**8. 自定义按键绑定**
- 运行 `/keybindings`
- 设置实时重载

**9. 设置 Hooks**
- 自动路由权限请求
- 提示 Claude 继续工作
- 预处理/后处理工具调用

**10. 自定义 Spinner Verbs**
- 添加或替换默认动词列表
- 提交到 source control 共享

**11. 使用输出风格**
- **Explanatory** - 熟悉新代码库
- **Learning** - 让 Claude 指导你做修改
- **Custom** - 创建自定义风格

**12. 自定义所有内容**
- 37 个设置 + 84 个环境变量
- 多层级配置（代码库/文件夹/个人/企业）

---

### 2.4 Boris 的 15 个隐藏功能 Tips（2026年3月30日）

**1. Claude Code 有移动 App**
- 下载 iOS/Android 应用
- 导航到 **Code** 标签
- 可以审查变更、批准 PR、直接写代码

**2. 移动/Web/桌面间移动会话**
- `/teleport` - 拉取云会话到本地
- `/remote-control` - 从任何设备控制本地会话

**3. /loop 和 /schedule - 最强大功能**
- `/loop 5m /babysit` - 自动处理代码审查
- `/loop 30m /slack-feedback` - 每 30 分钟发布 PR
- `/loop 1h /pr-pruner` - 关闭过时 PR

**4. 使用 Hooks 运行确定性逻辑**
- 动态加载上下文
- 记录每个 bash 命令
- 路由权限请求

**5. Cowork Dispatch**
- 安全远程控制 Claude Desktop 应用
- 使用 MCP、浏览器、计算机

**6. 使用 Chrome 扩展做前端工作**
- **最重要的提示：给 Claude 一种验证其输出的方法**
- 给了浏览器后，Claude 会迭代直到结果完美

**7. 使用 Claude Desktop App 自动启动和测试 Web 服务器**
- 内置运行 Web 服务器和测试功能

**8. Fork 你的会话**
- `/branch` 或 `claude --fork-session`

**9. 使用 /btw 做边查**
- 不中断代理工作的情况下快速提问

**10. 使用 Git Worktrees**
- Boris 同时运行**数十个 Claude 实例**
- `claude -w` 启动 worktree 中的新会话

**11. 使用 /batch 扇出大规模变更**
- 访谈后，Claude 扇出到尽可能多的 worktree agents

**12. 使用 --bare 加速 SDK 启动 10 倍**
```bash
claude -p "summarize this codebase" \
    --output-format=stream-json \
    --verbose \
    --bare
```

**13. 使用 --add-dir 访问更多文件夹**
- 同时工作于多个仓库时使用

**14. 使用 --agent 自定义系统提示和工具**
- 创建只读代理、专业审查代理、领域特定工具

**15. 使用 /voice 启用语音输入**
- Boris 大部分编码是通过说话而非打字完成

---

### 2.5 Boris 的 6 个 Opus 4.7 Tips（2026年4月16日）

**1. Auto Mode - 不再有权限提示**
- 权限路由到基于模型的分类器
- 安全则自动批准，有风险则暂停
- 可以运行更多并行的 Claude

**2. /fewer-permission-prompts 技能**
- 扫描会话历史
- 找到常见但安全的命令
- 推荐加入白名单

**3. Recaps**
- 简短总结代理做了什么、接下来是什么
- 长时间任务后回来时非常有用

**4. Focus Mode**
- 隐藏中间工作，只关注最终结果
- 运行 `/focus` 切换

**5. 配置努力级别**
- 5 个级别：low · medium · high · xhigh · max
- 左侧速度，右侧智能

**6. 给 Claude 一种验证其工作的方法**
- **后端**：让 Claude 运行服务器/服务端到端测试
- **前端**：使用 Chrome 扩展控制浏览器
- **桌面应用**：使用 Computer Use
- Boris 的 prompt：`Claude do blah blah /go`

---

### 2.6 Thariq 的 Session 管理 Tips（2026年4月16日）

**上下文基础知识**：
- 1M token 上下文窗口
- **上下文腐化**在 ~300-400k tokens 时开始发生
- 压缩是总结任务并在新上下文窗口继续

**每个 Turn 都是分支点**：

| 操作 | 上下文保留 | 适用场景 |
|------|-----------|----------|
| Continue | 全部保留 | 相同任务，相关上下文仍有用 |
| Rewind (Esc Esc) | 保留前缀，裁剪尾部 | Claude 走了错误路径 |
| /compact | 有损摘要 | 会话臃肿，中间任务 |
| /clear | 只带你的 brief | 全新任务开始 |
| Subagent | 全部 + 结果 | 需要大量中间输出的下一步 |

**何时开始新会话**：
- 通用规则：**开始新任务时开始新会话**
- 灰色地带：相关任务（如写刚实现的功能的文档）

**Rewind > Correct**：
- **纠正**：context = reads + 2失败尝试 + 2修正 + 修复
- **Rewind**：context = reads + 一个明智的提示 + 修复

**Compacting vs Fresh Sessions**：

| 场景 | 方法 | 原因 |
|------|------|------|
| 中间任务 | /compact | 低成本，保持动力 |
| 高风险下一步 | /clear + brief | 精确控制 |

**子代理作为上下文管理**：
- 子代理获取自己的新鲜上下文窗口
- 大量中间输出只返回最终报告
- 思考测试：**我需要再次使用这个工具输出，还是只需要结论？**

---

## 3. Orchestration Workflow 模式

### 3.1 核心架构：Command → Agent → Skill

```
╔══════════════════════════════════════════════════════════════════╗
║              ORCHESTRATION WORKFLOW                              ║
║           Command  →  Agent  →  Skill                            ║
╚══════════════════════════════════════════════════════════════════╝
                         ┌───────────────────┐
                         │  User Interaction │
                         └─────────┬─────────┘
                                   │
                                   ▼
         ┌─────────────────────────────────────────────────────┐
         │  Command — Entry Point (处理用户交互)                │
         └─────────────────────────┬───────────────────────────┘
                                   │
                              Step 1
                                   │
                                   ▼
                      ┌────────────────────────┐
                      │  AskUser — 交互选择     │
                      └────────────┬───────────┘
                                   │
                         Step 2 — Agent tool
                                   │
                                   ▼
         ┌─────────────────────────────────────────────────────┐
         │  Agent ● skills: [preloaded skill] (获取数据)       │
         └─────────────────────────┬───────────────────────────┘
                                   │
                          Returns: 结果
                                   │
                         Step 3 — Skill tool
                                   │
                                   ▼
         ┌─────────────────────────────────────────────────────┐
         │  Skill (独立创建输出)                               │
         └─────────────────────────┬───────────────────────────┘
                                   │
                          ┌────────┴────────┐
                          │                 │
                          ▼                 ▼
                   ┌────────────┐    ┌────────────┐
                   │  输出文件1  │    │  输出文件2  │
                   └────────────┘    └────────────┘
```

### 3.2 组件详解

#### Command（编排器）

```yaml
# .claude/commands/weather-orchestrator.md
---
name: weather-orchestrator
description: 获取天气数据并创建 SVG 天气卡片
model: haiku
---
# 1. 询问用户温度单位
# 2. 调用 weather-agent 获取温度
# 3. 调用 weather-svg-creator 创建 SVG
```

**职责**：
- 入口点，处理用户交互
- 协调工作流
- 组合多个 Agent 和 Skill

#### Agent with Preloaded Skill（代理技能）

```yaml
# .claude/agents/weather-agent.md
---
name: weather-agent
description: 获取实时天气数据
skills:
  - weather-fetcher    # 预加载到上下文中
model: sonnet
color: green
---
# 使用预加载的 weather-fetcher 技能获取数据
# 返回温度值和单位给 Command
```

**特点**：
- Skills 在启动时完整注入上下文
- Agent 遵循技能的指令
- 不是动态调用，而是参考材料

#### Skill（技能 - 独立调用）

```yaml
# .claude/skills/weather-svg-creator/SKILL.md
---
name: weather-svg-creator
description: 创建可视化 SVG 天气卡片
---
# 接收来自 Command 的数据
# 创建 SVG 文件
# 写入输出摘要
```

**特点**：
- 通过 Skill 工具调用
- 独立执行
- 从命令上下文接收数据

### 3.3 两种 Skill 模式对比

| 特性 | Agent Skill（预加载） | Skill（独立调用） |
|------|---------------------|-----------------|
| 调用方式 | 启动时注入 | 通过 Skill 工具调用 |
| 执行上下文 | Agent 内部 | Command 上下文 |
| 数据传递 | Agent 使用技能知识 | 通过会话上下文 |
| 适用场景 | 数据获取、API 调用 | 输出创建、渲染 |

### 3.4 设计原则

1. **两种 Skill 模式**：展示 agent skills（预加载）和 skills（直接调用）
2. **Command 作为编排器**：处理用户交互和协调工作流
3. **Agent 用于数据获取**：使用预加载技能获取数据后返回
4. **Skill 用于输出**：独立运行，接收来自 Command 的数据
5. **清晰分离**：Fetch（Agent）→ Render（Skill）- 每个组件单一职责

---

## 4. 实用配置模板

### 4.1 settings.json 完整配置

```json
{
  "permissions": {
    "allow": [
      "Edit(*)",
      "Write(*)",
      "Bash(*)",
      "WebFetch(domain:*)",
      "WebSearch",
      "mcp__*"
    ],
    "deny": [],
    "ask": [
      "Bash(rm *)",
      "Bash(dd *)",
      "Bash(mkfs *)",
      "Bash(chmod *)",
      "Bash(chown *)",
      "Bash(kill *)"
    ]
  },
  "spinnerVerbs": {
    "mode": "replace",
    "verbs": [
      "Thinking...",
      "Analyzing...",
      "Planning...",
      "Executing..."
    ]
  },
  "outputStyle": "Explanatory",
  "statusLine": {
    "type": "command",
    "command": "echo \"${MODEL} | ${DIR} | ${CONTEXT}%\"",
    "padding": 0
  },
  "attribution": {
    "commit": "Co-Authored-By: Claude <noreply@anthropic.com>",
    "pr": "Generated with [Claude Code](https://claude.ai/code)"
  },
  "respectGitignore": true,
  "env": {
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "80"
  },
  "enableAllProjectMcpServers": true,
  "disableAllHooks": false
}
```

### 4.2 Hooks 配置示例

```json
{
  "hooks": {
    "PreToolUse": [{
      "hooks": [{
        "type": "command",
        "command": "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/pre_tool.py",
        "timeout": 5000,
        "async": true,
        "statusMessage": "PreToolUse"
      }]
    }],
    "PostToolUse": [{
      "hooks": [{
        "type": "command",
        "command": "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/post_tool.py",
        "timeout": 5000,
        "async": true,
        "statusMessage": "PostToolUse"
      }]
    }],
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/session_start.py",
        "timeout": 5000,
        "async": true,
        "once": true,
        "statusMessage": "SessionStart"
      }]
    }]
  }
}
```

### 4.3 MCP 配置

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["-y", "@playwright/mcp"]
    },
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"]
    },
    "deepwiki": {
      "command": "npx",
      "args": ["-y", "deepwiki-mcp"]
    }
  }
}
```

### 4.4 CLAUDE.md 模板

```markdown
# CLAUDE.md

## 项目概述
简要描述项目是什么、做什么的。

## 技术栈
- 框架/语言版本
- 关键依赖

## 项目结构
```
src/
├── components/    # 组件
├── utils/         # 工具函数
└── ...
```

## 关键约定

### 代码风格
- 使用什么 linter/formatter
- 命名规范

### Git 工作流
- 分支命名规则
- Commit 消息格式
- PR 要求

### 测试
- 测试命令
- 覆盖率要求

## 常用命令
```bash
npm install    # 安装依赖
npm run dev    # 开发服务器
npm test       # 运行测试
```

## 注意事项
- 部署相关限制
- 环境变量要求
- 敏感信息处理

## 回答最佳实践问题
当被问及最佳实践时，**首先搜索本仓库**（best-practice/, reports/, tips/, implementation/）。
只有当答案不在这里时才回退到外部文档。
```

### 4.5 子代理定义模板

```yaml
# .claude/agents/feature-reviewer.md
---
name: feature-reviewer
description: 特性审查代理，审查新功能的代码质量和安全性
model: sonnet
tools:
  - Read
  - Glob
  - Grep
  - Bash
skills:
  - adversarial-review
  - code-style
hooks:
  PreToolUse:
    - hooks:
        - type: "prompt"
          prompt: "确保工具调用是安全的"
memory: project
color: blue
---
# 专业化代理，用于审查新功能
# 预加载了对抗审查和代码风格技能
# 遵循项目代码标准进行审查
```

### 4.6 Skill 定义模板

```yaml
# .claude/skills/my-skill/SKILL.md
---
name: my-skill
description: 当需要执行 X 任务或处理 Y 场景时使用此技能
argument-hint: [optional-parameter]
user-invocable: true
allowed-tools:
  - Read
  - Edit
  - Bash
---

## 何时使用
描述这个技能应该在什么情况下被调用。

## 使用方法
详细说明如何使用这个技能，包括参数和示例。

## 注意事项
- 重要的约束和限制
- 常见的错误和如何避免

## Gotchas
⚠️ **已知问题**：
1. 常见失败点 1
2. 常见失败点 2
3. 如何从失败中恢复

## 参考资料
- references/api.md - API 详细文档
- scripts/helper.py - 辅助脚本
- examples/ - 使用示例
```

---

## 5. 最佳实践总结

### 5.1 核心原则

| 原则 | 说明 | 实践 |
|------|------|------|
| **给目标不给路径** | 提供目标，让 Claude 决定如何实现 | 不要写死步骤 |
| **验证是关键** | 始终给 Claude 验证其工作的方法 | Chrome/测试/截图 |
| **上下文管理** | 善用压缩、重写、子代理 | 保持上下文干净 |
| **渐进式披露** | 细节分层，按需加载 | Skills 文件夹结构 |
| **迭代改进** | Claude.md 持续优化 | 每次修正后更新 |

### 5.2 决策树

```
开始新任务
    │
    ├─ 复杂任务？ → 是 → 计划模式开始
    │                      │
    │                      └─ 第二个 Claude 审查计划
    │
    ├─ 需要并行？ → 是 → Git Worktrees + 多个 Claude
    │
    ├─ 重复工作？ → 是 → 变成 Skill 或 Command
    │
    └─ 需要验证？ → 是 → Chrome 扩展 / 测试 / 截图
```

### 5.3 会话管理决策表

| 情况 | 操作 | 原因 |
|------|------|------|
| 相同任务，上下文仍有用 | **Continue** | 不必重建已加载内容 |
| Claude 走了错误路径 | **Rewind** (Esc Esc) | 丢弃失败尝试，保留文件读取 |
| 中间任务但会话臃肿 | **/compact** | 低成本，Claude 决定重点 |
| 开始全新任务 | **/clear** | 零腐化，你控制内容 |
| 下一步产生大量输出 | **Subagent** | 中间噪音留在子上下文 |

### 5.4 实用技巧清单

**Prompting**
- [ ] 挑战模式："Grill me on these changes"
- [ ] 中等修复后："用你现在知道的一切，实现优雅的方案"
- [ ] Bug → 直接说"修复"

**CLAUDE.md**
- [ ] 保持 200 行以内
- [ ] 使用 `<important if="...">` 标签
- [ ] 每次修正后更新
- [ ] Claude 非常擅长为自己写规则

**Skills**
- [ ] Skills 是文件夹，不只是文件
- [ ] 构建 Gotchas 部分
- [ ] 描述是触发器，不是摘要
- [ ] 不要说显而易见的事

**子代理**
- [ ] 特性特定而非通用
- [ ] 问："需要再次使用工具输出吗？"
- [ ] 使用 `context: fork` 隔离

**工作流**
- [ ] 复杂任务 → 计划模式
- [ ] 重复任务 → Command/Skill
- [ ] 并行任务 → Worktrees
- [ ] 验证任务 → Chrome 扩展

### 5.5 配置层级

```
优先级从高到低：
1. Managed (组织强制)
2. CLI 参数
3. settings.local.json (个人)
4. settings.json (团队)
5. ~/.claude/settings.json (全局)
```

### 5.6 学习资源

- [Claude Code 官方文档](https://code.claude.com/docs)
- [Official Skills](https://github.com/anthropics/skills/tree/main/skills)
- [Best Practice 仓库](https://github.com/shanraisshan/claude-code-best-practice)
- [Prompt Engineering 教程](https://github.com/anthropics/prompt-eng-interactive-tutorial)

---

## 附录：关键文档索引

| 文档 | 位置 | 说明 |
|------|------|------|
| 子代理最佳实践 | `best-practice/claude-subagents.md` | 16个 frontmatter 字段 |
| 命令最佳实践 | `best-practice/claude-commands.md` | 70个内置命令 |
| 编排工作流 | `orchestration-workflow/orchestration-workflow.md` | Command→Agent→Skill 模式 |
| Boris Tips | `tips/claude-boris-*.md` | 56个 Tips |
| Thariq Tips | `tips/claude-thariq-*.md` | Skills 和 Session 管理 |

---

> 📝 **笔记整理**：本笔记整理自 [shanraisshan/claude-code-best-practice](https://github.com/shanraisshan/claude-code-best-practice) 仓库，汇集了 Claude Code 官方团队和社区的最佳实践。
