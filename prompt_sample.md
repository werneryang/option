# from Alex (youtube)
## claude.md
First think through the problem, read the codebase for relevant files, and write a plan to tasks/todo.md.
The plan should have a list of todo items that you can check off as you complete them.
Before you begin working, check in with me and I will verify the plan.
Then, begin working on the todo items, marking them as complete as you go.
Please every step of the way just give me a high level explanation of what changes you made.
Make every task and code change you do as simple as possible. We want to avoid making any massive or complex changes. Every change should impact as little code as possible. Everything is about simplicity.
Finally, add a review section to the project.md file with a summary of the changes you made and any other relevant information.

## code prompt
I'm looking to build a simple OptionStrat clone. An advanced option analysis platform with optionchain, IV, IVR, historical volatility, Greeks analysis.
I'd like it to be built with Python + Streamlit and SQLite + Parquet. Before we start building this out though, I want to do a little planning with you.
I first want you to make a project plan for this. Inside @projectplan.md please build an in-depth plan for the system.
Have high-level checkpoints for each major step and feature, then in each checkpoint have a broken down list of small tasks you'll need to do to complete that checkpoint.
We will then review this plan together.


# Claude Opus 4
I'm looking to build an options analysis platform inspired by OptionStrat, focused on historical analysis and strategy evaluation.

**Core Features:**
- Option chain data display and analysis (using stored/downloaded data)
- IV (Implied Volatility) and IVR (IV Rank) calculations
- Historical volatility analysis with configurable lookback periods
- Complete Greeks calculation (Delta, Gamma, Theta, Vega, Rho)
- Option strategy builder with P&L visualization
- Historical data download from Interactive Brokers TWS API

**Tech Stack:**
- Frontend: Python + Streamlit
- Data Storage: SQLite (metadata) + Parquet files (time series data)
- Data Source: Interactive Brokers API for historical data downloads
- Computation: NumPy, Pandas, py_vollib for Black-Scholes

**Key Clarifications:**
- This is NOT a real-time trading system
- Focus on EOD (end-of-day) option chain analysis
- Data will be downloaded periodically and stored locally
- Analysis is performed on historical/stored data

**Project Structure:**
Please use standard Python project structure with src/, data/, tests/ directories.

Before we start building, I need a comprehensive project plan. Please create @projectplan.md with:

1. **Project Overview** - Brief description and objectives
2. **Technical Architecture** - Component diagram and data flow
3. **Development Phases** - Break down into 4-5 major milestones
4. **For each milestone:**
   - High-level goals
   - Detailed task breakdown (small, actionable items)
   - Dependencies and prerequisites
   - Estimated complexity (Simple/Medium/Complex)
   - Success criteria

5. **Data Management Strategy** - How we'll handle historical data storage and retrieval
6. **Testing Strategy** - How we'll validate each component

Start with the project plan first, and we'll review it together before implementation.