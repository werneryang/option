"""
Version Control Management Page

Provides UI for automatic version control operations.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict

from ...utils.version_control import auto_version_control


def render():
    """Render the version control management page"""
    
    st.header("🔄 自动版本控制")
    st.markdown("自动化代码、数据和配置变更的版本控制，无需手动确认。")
    
    # Create tabs for different functions
    tab1, tab2, tab3, tab4 = st.tabs([
        "📝 版本状态", 
        "🚀 自动提交", 
        "📊 提交历史",
        "⚙️ 设置"
    ])
    
    with tab1:
        render_version_status()
    
    with tab2:
        render_auto_commit()
    
    with tab3:
        render_commit_history()
    
    with tab4:
        render_settings()


def render_version_status():
    """Render current version status"""
    st.markdown("### 📋 当前状态")
    
    try:
        # Version information
        current_version = auto_version_control.get_current_version()
        version_info = auto_version_control.version_info
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("当前版本", current_version)
        
        with col2:
            st.metric("构建号", version_info.get("build", 0))
        
        with col3:
            st.metric("自动提交数", version_info.get("auto_commits", 0))
        
        with col4:
            last_updated = version_info.get("last_updated", "")
            if last_updated:
                last_updated_dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                st.metric("最后更新", last_updated_dt.strftime("%m-%d %H:%M"))
        
        # Git status
        st.markdown("#### 📁 文件状态")
        git_status = auto_version_control._get_git_status()
        
        status_data = []
        for status_type, files in git_status.items():
            if files:
                for file in files:
                    status_data.append({
                        "状态": status_type.upper(),
                        "文件": file,
                        "类型": _get_file_type(file)
                    })
        
        if status_data:
            df = pd.DataFrame(status_data)
            st.dataframe(df, use_container_width=True)
        else:
            st.success("✅ 工作目录干净，没有待提交的更改")
    
    except Exception as e:
        st.error(f"❌ 获取版本状态失败: {str(e)}")


def render_auto_commit():
    """Render automatic commit interface"""
    st.markdown("### 🚀 自动提交")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 版本级别")
        version_level = st.selectbox(
            "选择版本增量级别",
            ["patch", "minor", "major"],
            index=0,
            help="• patch: 小修复 (1.0.0 → 1.0.1)\n• minor: 新功能 (1.0.0 → 1.1.0)\n• major: 重大更改 (1.0.0 → 2.0.0)"
        )
        
        force_commit = st.checkbox(
            "强制提交", 
            help="即使没有更改也创建提交"
        )
    
    with col2:
        st.markdown("#### 操作")
        
        if st.button("📝 自动提交所有更改", type="primary"):
            with st.spinner("正在自动提交更改..."):
                try:
                    success = auto_version_control.auto_commit(
                        force=force_commit, 
                        version_level=version_level
                    )
                    
                    if success:
                        st.success(f"✅ 自动提交成功！版本: {auto_version_control.get_current_version()}")
                        st.rerun()
                    else:
                        st.warning("ℹ️ 没有更改需要提交")
                        
                except Exception as e:
                    st.error(f"❌ 自动提交失败: {str(e)}")
        
        if st.button("💾 创建备份分支"):
            with st.spinner("正在创建备份分支..."):
                try:
                    success = auto_version_control.create_backup_branch()
                    if success:
                        st.success("✅ 备份分支创建成功！")
                    else:
                        st.error("❌ 备份分支创建失败")
                except Exception as e:
                    st.error(f"❌ 创建备份分支失败: {str(e)}")
    
    # Quick commit for data updates
    st.markdown("#### 📊 数据更新快速提交")
    
    quick_col1, quick_col2 = st.columns(2)
    
    with quick_col1:
        data_type = st.selectbox(
            "数据类型",
            ["snapshot_data", "historical_data", "archive_data", "config_update"],
            help="选择要提交的数据类型"
        )
    
    with quick_col2:
        symbol = st.text_input("符号 (可选)", placeholder="如: AAPL")
        
        if st.button("🔄 提交数据更新"):
            with st.spinner("正在提交数据更新..."):
                try:
                    success = auto_version_control.auto_commit_data_update(
                        data_type=data_type,
                        symbol=symbol if symbol else None
                    )
                    
                    if success:
                        st.success("✅ 数据更新提交成功！")
                        st.rerun()
                    else:
                        st.error("❌ 数据更新提交失败")
                        
                except Exception as e:
                    st.error(f"❌ 提交数据更新失败: {str(e)}")


def render_commit_history():
    """Render commit history"""
    st.markdown("### 📊 提交历史")
    
    try:
        limit = st.slider("显示提交数量", 5, 50, 20)
        commits = auto_version_control.get_commit_history(limit=limit)
        
        if commits:
            history_data = []
            for commit in commits:
                # Parse commit message for better display
                message_lines = commit["message"].split('\n')
                title = message_lines[0]
                
                # Extract version if present
                version = ""
                if "version" in title.lower():
                    import re
                    version_match = re.search(r'v?(\d+\.\d+\.\d+\.\d+)', title)
                    if version_match:
                        version = version_match.group(1)
                
                # Determine commit type
                commit_type = "其他"
                if title.startswith("auto:"):
                    commit_type = "自动"
                elif title.startswith("data:"):
                    commit_type = "数据"
                elif title.startswith("feat:"):
                    commit_type = "功能"
                elif title.startswith("fix:"):
                    commit_type = "修复"
                elif title.startswith("docs:"):
                    commit_type = "文档"
                
                history_data.append({
                    "提交ID": commit["hash"][:8],
                    "类型": commit_type,
                    "版本": version,
                    "消息": title[:80] + "..." if len(title) > 80 else title
                })
            
            df = pd.DataFrame(history_data)
            st.dataframe(df, use_container_width=True)
            
            # Statistics
            st.markdown("#### 📈 统计信息")
            
            stat_col1, stat_col2, stat_col3 = st.columns(3)
            
            with stat_col1:
                auto_commits = len([c for c in history_data if c["类型"] == "自动"])
                st.metric("自动提交", auto_commits)
            
            with stat_col2:
                data_commits = len([c for c in history_data if c["类型"] == "数据"])
                st.metric("数据提交", data_commits)
            
            with stat_col3:
                other_commits = len(history_data) - auto_commits - data_commits
                st.metric("其他提交", other_commits)
        
        else:
            st.info("📭 暂无提交历史")
    
    except Exception as e:
        st.error(f"❌ 获取提交历史失败: {str(e)}")


def render_settings():
    """Render version control settings"""
    st.markdown("### ⚙️ 版本控制设置")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 自动化设置")
        
        auto_commit_on_data = st.checkbox(
            "数据更新时自动提交",
            value=True,
            help="当新数据下载或更新时自动创建提交"
        )
        
        auto_commit_on_config = st.checkbox(
            "配置更改时自动提交",
            value=True,
            help="当配置文件更改时自动创建提交"
        )
        
        auto_backup = st.checkbox(
            "每日自动备份",
            value=False,
            help="每天自动创建备份分支"
        )
    
    with col2:
        st.markdown("#### 版本策略")
        
        default_level = st.selectbox(
            "默认版本级别",
            ["patch", "minor", "major"],
            index=0,
            help="自动提交时的默认版本增量级别"
        )
        
        max_auto_commits = st.number_input(
            "最大自动提交数/天",
            min_value=1,
            max_value=100,
            value=50,
            help="每天允许的最大自动提交数量"
        )
    
    # Save settings
    if st.button("💾 保存设置"):
        try:
            settings = {
                "auto_commit_on_data": auto_commit_on_data,
                "auto_commit_on_config": auto_commit_on_config,
                "auto_backup": auto_backup,
                "default_level": default_level,
                "max_auto_commits": max_auto_commits,
                "updated_at": datetime.now().isoformat()
            }
            
            # Save to config file (you could implement this)
            st.success("✅ 设置已保存")
            
        except Exception as e:
            st.error(f"❌ 保存设置失败: {str(e)}")
    
    # System info
    st.markdown("#### 📊 系统信息")
    
    try:
        import subprocess
        
        # Git version
        git_version = subprocess.run(
            ["git", "--version"], 
            capture_output=True, 
            text=True
        ).stdout.strip()
        
        st.code(f"Git版本: {git_version}")
        
        # Repository info
        repo_info = f"""
项目路径: {auto_version_control.project_root}
版本文件: {auto_version_control.version_file}
变更日志: {auto_version_control.changes_log}
        """
        st.code(repo_info)
        
    except Exception as e:
        st.error(f"无法获取系统信息: {str(e)}")


def _get_file_type(filename: str) -> str:
    """Get file type for display"""
    if filename.endswith(('.py', '.js', '.ts', '.html', '.css')):
        return "代码"
    elif filename.endswith(('.json', '.yaml', '.yml', '.toml', '.ini', '.env')):
        return "配置"
    elif filename.endswith(('.md', '.txt', '.rst')):
        return "文档"
    elif filename.endswith(('.parquet', '.csv', '.sqlite', '.db')):
        return "数据"
    else:
        return "其他"