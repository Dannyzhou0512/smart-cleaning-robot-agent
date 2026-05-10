import sys
from pathlib import Path

print("当前 Python:", sys.executable)
print("当前工作目录:", Path.cwd())

from Agent_project.utils.path_tool import get_abs_path
from Agent_project.utils.config_handler import agents_config, chroma_config, prompts_config
from Agent_project.utils.logger_handler import logger

from agent.tools.middleware import monitor_tool, log_before_model, report_prompt_switch
from agent.tools.agent_tools import get_weather, get_user_location, get_user_id, get_current_month

print("轻量模块导入成功")
print("项目根目录:", get_abs_path(""))