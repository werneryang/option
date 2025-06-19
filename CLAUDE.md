# Claude Code Working Instructions

## Workflow Process

1. **Analysis Phase**
   - First think through the problem carefully
   - Read the codebase for relevant files
   - Write a detailed plan to `tasks/todo.md`
   - The plan should have checkable todo items: `- [ ] Task description`
   - Create `project.md` if it doesn't exist to track overall progress

2. **Verification Phase**
   - Before starting implementation, present the plan for review
   - Wait for approval before proceeding

3. **Implementation Phase**
   - Work on todo items one by one
   - Mark items as complete: `- [x] Task description`
   - After each task, provide a high-level summary of changes
   - Update `project.md` with progress and decisions
   - Commit changes with clear messages

## Core Principles

- **Simplicity First**: Make every change as simple as possible
- **Minimal Impact**: Each change should affect the least amount of code
- **Incremental Progress**: Small, focused changes over large refactors
- **Clear Communication**: Explain what you're doing at each step

## Documentation Requirements

### For `tasks/todo.md`:
- Create when starting a new phase or major feature
- Include analysis summary of current state
- Break down work into specific, actionable items
- Use checkable format: `- [ ] Task description`
- Include success criteria and dependencies
- Update task status as work progresses

### For `project.md`:
- Create if it doesn't exist when starting significant work
- Track overall project progress and status
- Document completed phases/features
- Record design decisions and rationale
- Note known issues or future improvements
- Include test results and performance metrics
- Update after completing major tasks or phases

### When to Create/Update:
- **Create `project.md`**: When starting work on a project that lacks this file
- **Update `project.md`**: After completing each major task or phase
- **Create `tasks/todo.md`**: When beginning a new phase or complex feature
- **Update `tasks/todo.md`**: Mark tasks complete and add new ones as discovered

## Project Context

- **Project Type**: Options Analysis Platform
- **Tech Stack**: Python, Streamlit, SQLite, Parquet
- **Focus**: Historical data analysis, NOT real-time trading
- **Current Phase**: Phase 4 - User Interface Development