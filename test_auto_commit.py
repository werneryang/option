#!/usr/bin/env python3
"""
测试自动版本控制功能

这是一个测试文件，用于演示自动版本控制系统的工作原理。
"""

from src.utils.version_control import auto_version_control
from datetime import datetime

def test_auto_version_control():
    """测试自动版本控制功能"""
    print("🔄 测试自动版本控制...")
    
    # 获取当前版本
    current_version = auto_version_control.get_current_version()
    print(f"📦 当前版本: {current_version}")
    
    # 获取Git状态
    git_status = auto_version_control._get_git_status()
    print(f"📁 文件状态:")
    print(f"  • 未跟踪: {len(git_status['untracked'])} 个文件")
    print(f"  • 已修改: {len(git_status['modified'])} 个文件")
    print(f"  • 已暂存: {len(git_status['staged'])} 个文件")
    
    # 执行自动提交
    print("\n🚀 执行自动提交...")
    success = auto_version_control.auto_commit(force=False, version_level="patch")
    
    if success:
        new_version = auto_version_control.get_current_version()
        print(f"✅ 自动提交成功！新版本: {new_version}")
    else:
        print("ℹ️ 没有变更需要提交")
    
    return success

if __name__ == "__main__":
    test_auto_version_control()