#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流式任务执行器 - 千桃Claw
支持复杂的多步骤任务，每个步骤实时推送进度到飞书
"""

import json
import time
import subprocess
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from feishu_pusher import (
    get_token, send_msg, send_to_master, send_progress,
    send_complete, send_start, send_error, make_bar, USER_OPEN_ID
)


def run_stream_task(task_name, steps, target_open_id=None):
    """
    运行流式任务
    
    Args:
        task_name: 任务名称
        steps: 步骤列表
              [{"name": "步骤名", "cmd": "shell命令", "wait": 秒数}, ...]
        target_open_id: 目标用户open_id
    
    Returns:
        bool: 是否全部成功
    """
    global USER_OPEN_ID
    if target_open_id:
        USER_OPEN_ID = target_open_id
    
    token = get_token()
    if not token:
        print("❌ 无法获取飞书访问令牌")
        return False
    
    start_time = time.time()
    total = len(steps)
    success = True
    
    # 发送开始消息
    send_start(token, task_name, total)
    print(f"🚀 {task_name} 已启动 (共{total}步)")
    
    for i, step in enumerate(steps, 1):
        # 解析步骤配置
        if isinstance(step, dict):
            step_name = step.get("name", f"步骤{i}")
            cmd = step.get("cmd", "")
            wait = step.get("wait", 0.5)
        else:
            step_name = str(step)
            cmd = ""
            wait = 0.5
        
        percent = int(i * 100 / total)
        elapsed = int(time.time() - start_time)
        
        # 发送进度更新
        send_progress(token, task_name, percent, step_name, i, total, elapsed)
        print(f"  [{percent:3d}%] 步骤{i}: {step_name}")
        
        # 执行命令
        if cmd:
            try:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5分钟超时
                )
                if result.returncode != 0:
                    error_msg = result.stderr[:200] if result.stderr else "未知错误"
                    send_error(token, task_name, f"步骤{i}失败: {error_msg}")
                    print(f"  ❌ 失败: {error_msg}")
                    success = False
                    break
            except subprocess.TimeoutExpired:
                send_error(token, task_name, f"步骤{i}执行超时（5分钟）")
                print(f"  ❌ 执行超时")
                success = False
                break
            except Exception as e:
                send_error(token, task_name, f"步骤{i}异常: {str(e)[:100]}")
                print(f"  ❌ 异常: {e}")
                success = False
                break
        else:
            # 没有命令则等待
            time.sleep(wait)
    
    # 完成消息
    elapsed = int(time.time() - start_time)
    if success:
        send_complete(token, task_name, elapsed)
        print(f"✅ {task_name} 完成！总用时: {elapsed//60}分{elapsed%60}秒")
    else:
        send_error(token, task_name, f"任务中断，总用时: {elapsed//60}分{elapsed%60}秒")
        print(f"⚠️ {task_name} 中断！总用时: {elapsed//60}分{elapsed%60}秒")
    
    return success


def main():
    if len(sys.argv) < 3:
        print("""
📊 流式任务执行器 - 千桃Claw
============================

用法:
  python3 stream_task.py "<任务名>" '<步骤JSON>'

示例:
  # 下载并处理论文
  python3 stream_task.py "精读5篇论文" '[{"name":"下载PDF","cmd":"echo 下载中..."},{"name":"解析文献","cmd":"sleep 1"},{"name":"写笔记","cmd":"echo 完成"}]'

  # 简单等待测试
  python3 stream_task.py "测试任务" '[{"name":"步骤1","wait":1},{"name":"步骤2","wait":1}]'
""")
        sys.exit(1)
    
    task_name = sys.argv[1]
    steps_json = sys.argv[2]
    
    # 解析JSON
    try:
        steps = json.loads(steps_json)
        if not isinstance(steps, list):
            print("❌ 步骤必须是数组格式")
            sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析失败: {e}")
        sys.exit(1)
    
    # 执行
    success = run_stream_task(task_name, steps)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
