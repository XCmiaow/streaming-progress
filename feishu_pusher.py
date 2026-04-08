#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书流式进度推送器 - 千桃Claw
基于桃桃Claw的streaming-progress实现
"""

import urllib.request
import json
import time
import subprocess
import sys
import ssl

# 忽略SSL证书验证
ssl._create_default_https_context = ssl._create_unverified_context

# ============ 配置区域 ============
APP_ID = "cli_a95e53c3d878dccc"
APP_SECRET = "uTSMziLzVZv6y6DaHbXGLgA5pcVtCqh4"
USER_OPEN_ID = "ou_00fe99c0db51b21e6a286d63f463d060"  # 默认主人

# 主人和姐姐们的open_id
USERS = {
    "master": "ou_00fe99c0db51b21e6a286d63f463d060",  # 主人
}

# ============ 核心函数 ============

def get_token():
    """获取飞书访问令牌"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": APP_ID, "app_secret": APP_SECRET}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if result.get("code") == 0:
                return result["tenant_access_token"]
            else:
                print(f"获取token失败: {result}")
                return None
    except Exception as e:
        print(f"获取token异常: {e}")
        return None


def send_msg(token, open_id, content):
    """发送飞书消息"""
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    data = {
        "receive_id": open_id,
        "msg_type": "text",
        "content": json.dumps({"text": content})
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result.get("code") == 0
    except Exception as e:
        print(f"发送消息异常: {e}")
        return False


def send_to_master(token, content):
    """发送消息给主人"""
    return send_msg(token, USER_OPEN_ID, content)


def make_bar(percent, width=20):
    """生成进度条"""
    bars = int(percent / (100 / width))
    return "█" * bars + "░" * (width - bars)


def send_progress(token, task_name, percent, current, step_num, total_steps, elapsed):
    """发送进度更新"""
    bar = make_bar(percent)
    mins, secs = divmod(elapsed, 60)
    content = f"""🟢 {task_name}
━━━━━━━━━━━━━━━━━━
进度：[{bar}] {percent}% ({step_num}/{total_steps})
━━━━━━━━━━━━━━━━━━
当前：{current}
已用时：{mins}分{secs}秒"""
    return send_to_master(token, content)


def send_complete(token, task_name, elapsed):
    """发送完成消息"""
    mins, secs = divmod(elapsed, 60)
    bar = make_bar(100)
    content = f"""✅ {task_name} 完成！
━━━━━━━━━━━━━━━━━━
进度：[{bar}] 100%
━━━━━━━━━━━━━━━━━━
总用时：{mins}分{secs}秒"""
    return send_to_master(token, content)


def send_start(token, task_name, total_steps):
    """发送开始消息"""
    content = f"🚀 {task_name} 已启动\n共{total_steps}个步骤"
    return send_to_master(token, content)


def send_error(token, task_name, error_msg):
    """发送错误消息"""
    content = f"❌ {task_name} 出错！\n{error_msg}"
    return send_to_master(token, content)


def run_stream_task(task_name, steps, target_open_id=None):
    """
    运行流式任务
    
    Args:
        task_name: 任务名称
        steps: 步骤列表，每个元素是dict或tuple
              {"name": "步骤名", "cmd": "shell命令"}
        target_open_id: 目标用户open_id，默认主人
    """
    global USER_OPEN_ID
    if target_open_id:
        USER_OPEN_ID = target_open_id
    
    token = get_token()
    if not token:
        print("无法获取访问令牌")
        return False
    
    start_time = time.time()
    total = len(steps)
    
    # 发送开始消息
    send_start(token, task_name, total)
    
    for i, step in enumerate(steps, 1):
        # 支持两种格式：dict 或 tuple
        if isinstance(step, dict):
            step_name = step.get("name", f"步骤{i}")
            cmd = step.get("cmd", "")
        else:
            step_name = step
            cmd = ""
        
        percent = int(i * 100 / total)
        elapsed = int(time.time() - start_time)
        
        # 发送进度
        send_progress(token, task_name, percent, step_name, i, total, elapsed)
        
        # 执行命令
        if cmd:
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True
            )
            if result.returncode != 0:
                send_error(token, task_name, f"步骤{i}执行失败: {result.stderr[:200]}")
                return False
        else:
            time.sleep(0.5)
    
    # 完成消息
    elapsed = int(time.time() - start_time)
    send_complete(token, task_name, elapsed)
    return True


# ============ CLI接口 ============

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法:")
        print("  python3 feishu_pusher.py <任务名> <步骤数>")
        print("  python3 feishu_pusher.py <任务名> '<JSON步骤数组>'")
        print("")
        print("示例:")
        print('  python3 feishu_pusher.py "下载5篇论文" 5')
        print('  python3 feishu_pusher.py "精读论文" \'[{"name":"下载PDF"},{"name":"解析文献"},{"name":"写笔记"}]\'')
        sys.exit(1)
    
    task_name = sys.argv[1]
    arg2 = sys.argv[2] if len(sys.argv) > 2 else "5"
    
    # 解析步骤
    try:
        # 尝试作为JSON解析
        import ast
        steps = ast.literal_eval(arg2)
        if isinstance(steps, list):
            pass
        else:
            # 是数字，创建虚拟步骤
            n = int(arg2)
            steps = [{"name": f"步骤{i+1}", "cmd": ""} for i in range(n)]
    except:
        # 是数字，创建虚拟步骤
        try:
            n = int(arg2)
            steps = [{"name": f"步骤{i+1}", "cmd": ""} for i in range(n)]
        except:
            print(f"无法解析参数: {arg2}")
            sys.exit(1)
    
    # 执行任务
    success = run_stream_task(task_name, steps)
    sys.exit(0 if success else 1)
