# Career iOS Backend - Claude Configuration

## 📂 Project Information

- **Project Name**: Career iOS Backend
- **Platform**: FastAPI + PostgreSQL
- **Environment**: Staging/Production

## 🚀 Services

### Cloud Infrastructure
- **Platform**: Google Cloud Platform
- **Deployment**: Cloud Run
- **AI Services**: Vertex AI (Gemini)

### Database
- **Type**: PostgreSQL
- **Features**: Real-time subscriptions, Row-level security

## 🤖 Agent Configuration

### Enforcement Rules
- **TDD Required**: All new features must follow Test-Driven Development
- **Agent-Manager Required**: All coding tasks must go through agent-manager
- **Auto-invoke Subagents**: Subagents are automatically invoked based on task type

### Available Subagents
1. **agent-manager**: Routes tasks to appropriate subagents
2. **tdd-orchestrator**: Manages complete TDD workflow
3. **test-writer**: Writes tests first (RED phase)
4. **code-generator**: Implements code to pass tests (GREEN phase)
5. **test-runner**: Runs and fixes tests
6. **code-reviewer**: Reviews code quality (REFACTOR phase)

## 📁 Directory Structure

```
.claude/
├── README.md              # This file
├── hooks/                 # Claude hooks
│   └── check-agent-rules.py  # Enforces agent-manager usage
├── agents/                # Agent definitions
├── commands/              # Custom commands
└── skills/                # Reusable skills
```

## 🔧 Hooks

### check-agent-rules.py
Automatically detects coding tasks and enforces agent-manager usage to ensure:
- TDD compliance
- Code quality
- Consistent workflow

## 🌟 Project-Specific Keywords

The hook recognizes Career iOS Backend specific terms:
- **Session/Consultation**: 諮詢, 諮詢, 會談, reflection, 心得
- **Client Management**: 案主, 個案, counselor, 諮詢師
- **Features**: transcript keywords, 逐字稿關鍵字, keyword analysis
- **Reports**: 報告生成, report generation

## 📝 Configuration Updates

Last Updated: 2024-11-29
- Added Career iOS Backend specific keywords to hook
- Enhanced TDD enforcement rules
- Improved agent-manager detection patterns
