# Development Guidelines - Options Analysis Platform

## 概述

本文档为Options Analysis Platform项目的开发指南，总结了关键问题的解决方案和预防措施，确保未来开发的一致性和质量。

## 核心原则

### 1. 简化优先 (Simplicity First)
- 每个更改都应该尽可能简单
- 避免过度工程化
- 优先使用成熟、稳定的解决方案

### 2. 渐进增强 (Progressive Enhancement)
- 基础功能必须稳定可用
- 高级功能作为增强，不影响核心体验
- 降级策略确保系统健壮性

### 3. 配置驱动 (Configuration Driven)
- 行为通过配置文件控制，而非硬编码
- 支持开发/生产环境差异化配置
- 配置变更不需要代码修改

## 常见问题和解决方案

### UI相关问题

#### Deploy按钮隐藏
**问题**: Streamlit默认显示Deploy按钮，影响本地应用体验

**标准解决方案**:
```toml
# .streamlit/config.toml
[client]
toolbarMode = "minimal"
```

**兜底方案**:
```python
# 在main_application.py中添加CSS
st.markdown("""
<style>
    .stDeployButton { display: none; }
    [data-testid="stToolbar"] { display: none; }
</style>
""", unsafe_allow_html=True)
```

**检查清单**:
- [ ] 配置文件包含toolbarMode设置
- [ ] 所有页面测试Deploy按钮隐藏效果
- [ ] CSS兜底方案在主应用文件中

#### 响应式设计
**原则**: 
- 使用Streamlit内置列布局
- 避免复杂的自定义CSS
- 移动端友好的设计

### 异步编程问题

#### 事件循环冲突
**问题**: Streamlit UI线程与异步库事件循环冲突

**解决策略**:
1. **延迟导入**: 避免在UI模块顶层导入异步库
2. **同步包装**: 为异步操作提供同步接口
3. **线程隔离**: 在独立线程中运行异步操作

**代码模式**:
```python
# ❌ 避免
from async_library import AsyncClient

# ✅ 推荐
def get_async_client():
    from async_library import AsyncClient
    return AsyncClient()

# ✅ 同步包装器
def sync_operation(async_func, *args):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(async_func(*args))
    finally:
        loop.close()
```

### 数据处理问题

#### 大数据集处理
**原则**:
- 分页加载，避免一次性加载全部数据
- 使用缓存减少重复计算
- 异步处理用户界面响应

**实现模式**:
```python
@st.cache_data
def load_data_chunk(symbol, page, page_size=1000):
    # 分页加载数据
    pass

# 进度条显示
progress_bar = st.progress(0)
for i, chunk in enumerate(data_chunks):
    process_chunk(chunk)
    progress_bar.progress((i + 1) / len(data_chunks))
```

#### 数据持久化
**策略**:
- SQLite用于元数据和小数据集
- Parquet用于大数据集存储
- 定期数据清理和归档

## 架构模式

### 目录结构
```
src/
├── ui/                 # UI层 - 纯展示逻辑
│   ├── components/     # 可复用UI组件
│   ├── pages/         # 页面级组件
│   └── services/      # UI服务层
├── data_sources/      # 数据源层
├── services/          # 业务逻辑层
├── utils/            # 工具函数
└── tests/            # 测试
```

### 层级依赖原则
- UI层只依赖services层，不直接访问data_sources
- services层处理业务逻辑和数据转换
- data_sources层专注数据获取和存储

### 错误处理策略
```python
# 统一错误处理模式
try:
    result = risky_operation()
    if not result.get('success'):
        st.error(f"操作失败: {result.get('message')}")
        return
    # 处理成功结果
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    st.error("系统出现异常，请稍后重试")
```

## 测试策略

### 单元测试
- 每个数据处理函数都要有测试
- Mock外部依赖（API调用、文件系统等）
- 测试边界条件和错误情况

### UI测试
- 验证页面加载无错误
- 检查关键UI元素显示状态
- 测试用户交互流程

### 集成测试
- 端到端数据流测试
- 配置文件验证
- 依赖服务连接测试

## 性能优化

### Streamlit特定优化
```python
# 使用缓存避免重复计算
@st.cache_data
def expensive_computation(params):
    pass

# 避免在每次rerun时重新创建对象
if 'data_service' not in st.session_state:
    st.session_state.data_service = DataService()

# 使用columns控制布局性能
col1, col2, col3 = st.columns([2, 1, 1])
```

### 数据处理优化
- 使用pandas vectorized操作
- 适当的数据类型选择
- 内存使用监控

## 部署和运维

### 环境配置
- 使用requirements.txt固定依赖版本
- 环境变量配置敏感信息
- Docker化部署（推荐）

### 监控和日志
```python
# 使用loguru进行结构化日志
from loguru import logger

logger.add("logs/app.log", rotation="1 day", retention="7 days")
logger.info("Application started", extra={"version": "1.0.0"})
```

### 备份策略
- 定期备份SQLite数据库
- 重要Parquet文件版本控制
- 配置文件备份

## 代码质量

### 代码风格
- 使用black进行代码格式化
- 使用flake8进行代码检查
- 类型注解提高代码可读性

### 文档要求
- 每个函数都要有docstring
- 复杂业务逻辑要有注释说明
- API接口要有完整文档

### 版本控制
- 功能分支开发模式
- 提交信息要清晰描述变更
- 重要变更要有对应的文档更新

## 故障排除检查清单

### 应用启动失败
- [ ] 检查Python依赖是否安装完整
- [ ] 验证配置文件格式正确性
- [ ] 查看是否有端口冲突
- [ ] 检查日志文件错误信息

### UI显示异常
- [ ] 验证CSS样式是否正确加载
- [ ] 检查数据是否正确返回
- [ ] 确认浏览器兼容性
- [ ] 查看浏览器控制台错误

### 数据处理错误
- [ ] 验证数据源连接状态
- [ ] 检查数据格式是否符合预期
- [ ] 确认磁盘空间是否充足
- [ ] 查看数据库连接是否正常

## 持续改进

### 技术债务管理
- 定期review临时解决方案
- 优先级排序技术改进项目
- 性能瓶颈持续监控

### 用户反馈循环
- 收集用户使用数据
- 定期用户体验调研
- 快速响应关键问题

### 知识管理
- 更新troubleshooting文档
- 分享最佳实践案例
- 团队技术分享会

---

**最后更新**: 2025-06-23  
**负责人**: Development Team  
**版本**: 1.0

> 本指南是活文档，随着项目发展持续更新。如有问题或建议，请及时反馈。