import signal
import sys
from loguru import logger

def cleanup():
    """清理函数"""
    logger.info("🧹 正在清理资源...")
    # 这里可以添加任何需要的清理操作
    logger.success("✨ 清理完成")

def handle_exit(signum, frame):
    """处理退出信号"""
    logger.warning("\n⚠️ 检测到程序退出信号")
    cleanup()
    logger.info("👋 感谢使用，再见！")
    sys.exit(0)

def setup_signal_handlers():
    """设置信号处理器"""
    signal.signal(signal.SIGINT, handle_exit)  # Ctrl+C
    signal.signal(signal.SIGTERM, handle_exit)  # 终止信号 
