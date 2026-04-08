#!/bin/bash
# 进度追踪Shell脚本 - 千桃Claw
# 用法: ./progress_tracker.sh <任务ID> <任务名> <总步骤数> [每步命令]

TASK_ID="$1"
TASK_NAME="$2"
TOTAL_STEPS="$3"
shift 3

# 获取飞书token (需要Python环境)
get_token() {
    python3 -c "
import urllib.request, json
data = json.dumps({'app_id': 'cli_a95e53c3d878dccc', 'app_secret': ''}).encode()
req = urllib.request.Request('https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal', data=data, headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(req, timeout=10) as resp:
    print(json.loads(resp.read()).get('tenant_access_token', ''))
" 2>/dev/null
}

# 发送消息
send_msg() {
    local token="$1"
    local content="$2"
    python3 -c "
import urllib.request, json
data = json.dumps({
    'receive_id': 'ou_00fe99c0db51b21e6a286d63f463d060',
    'msg_type': 'text',
    'content': json.dumps({'text': '''$content'''})
}).encode()
req = urllib.request.Request(
    'https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id',
    data=data,
    headers={'Content-Type': 'application/json', 'Authorization': 'Bearer $token'},
    method='POST'
)
with urllib.request.urlopen(req, timeout=10) as resp:
    pass
" 2>/dev/null
}

# 生成进度条
make_bar() {
    local percent=$1
    local bars=$((percent / 5))
    printf '%*s' "$bars" '' | tr ' ' '█'
    printf '%*s' $((20 - bars)) '' | tr ' ' '░'
}

# 初始化任务
init_task() {
    TOKEN=$(get_token)
    if [ -z "$TOKEN" ]; then
        echo "❌ 无法获取token"
        return 1
    fi
    send_msg "$TOKEN" "🚀 $TASK_NAME 已启动 (共${TOTAL_STEPS}步)"
}

# 更新进度
update_progress() {
    local step=$1
    local step_name="$2"
    local elapsed=$3
    
    TOKEN=$(get_token)
    if [ -z "$TOKEN" ]; then
        echo "⚠️ 无法获取token"
        return 1
    fi
    
    local percent=$((step * 100 / TOTAL_STEPS))
    local bar=$(make_bar $percent)
    local mins=$((elapsed / 60))
    local secs=$((elapsed % 60))
    
    local msg="🟢 $TASK_NAME
━━━━━━━━━━━━━━━━━━
进度：[${bar}] ${percent}% (${step}/${TOTAL_STEPS})
━━━━━━━━━━━━━━━━━━
当前：${step_name}
已用时：${mins}分${secs}秒"
    
    send_msg "$TOKEN" "$msg"
}

# 完成任务
complete_task() {
    local elapsed=$1
    
    TOKEN=$(get_token)
    if [ -z "$TOKEN" ]; then
        echo "⚠️ 无法获取token"
        return 1
    fi
    
    local mins=$((elapsed / 60))
    local secs=$((elapsed % 60))
    local bar=$(make_bar 100)
    
    local msg="✅ $TASK_NAME 完成！
━━━━━━━━━━━━━━━━━━
进度：[${bar}] 100%
━━━━━━━━━━━━━━━━━━
总用时：${mins}分${secs}秒"
    
    send_msg "$TOKEN" "$msg"
}

# 主逻辑
case "$1" in
    init)
        init_task
        ;;
    update)
        update_progress "$2" "$3" "$4"
        ;;
    complete)
        complete_task "$2"
        ;;
    *)
        echo "用法:"
        echo "  $0 init <任务名> <总步骤数>      # 初始化任务"
        echo "  $0 update <步骤> <步骤名> <已用秒>  # 更新进度"
        echo "  $0 complete <已用秒>              # 完成任务"
        ;;
esac
