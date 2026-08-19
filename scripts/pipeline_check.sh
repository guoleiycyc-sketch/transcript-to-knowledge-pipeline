#!/usr/bin/env bash
# pipeline_check.sh — 一键必查（场内 6 项 + 跨会话 1 项）
# 用法：bash scripts/pipeline_check.sh <场次目录> [人名1 人名2 ...]
# 不传人名时，自动从 01_清洗稿.md 头部映射块提取「## xxx」「🟢/🟣 说话人」以外的实名

set +e   # grep -c 返回 0 时不退出
DIR="${1:?用法: bash pipeline_check.sh <场次目录> [人名...]}"
shift || true

# 颜色（macOS bash 兼容，无 tput 也不报错）
R='\033[0;31m'; G='\033[0;32m'; Y='\033[0;33m'; B='\033[0;34m'; N='\033[0m'
ok() { echo -e "${G}✓${N} $*"; }
warn() { echo -e "${Y}⚠${N} $*"; }
err() { echo -e "${R}✗${N} $*"; }

cd "$DIR"

echo
echo "=========================================="
echo " pipeline_check.sh · $(basename "$DIR")"
echo "=========================================="

# === 自动提取人名（来源：正文回合标签 `**【xxx】** [ts]`）===
# 头部映射格式多样（emoji/中文等号），不如直接抓正文实际出现的回合标签，最稳。
if [ $# -eq 0 ]; then
  BODY_NAMES=$(grep -oE '\*\*【[^】]+】\*\*' 01_清洗稿.md 2>/dev/null \
    | sed 's/\*\*【//;s/】\*\*//' \
    | grep -vE '^现场$|^参会者$|^未识别$' \
    | sort -u)
  if [ -z "$BODY_NAMES" ]; then
    err "无法自动提取人名，请传参: bash pipeline_check.sh <dir> <人名1> ..."
    exit 2
  fi
  NAMES="$BODY_NAMES"
  echo "人名（自动提取）: $(echo "$NAMES" | tr '\n' ' ')"
else
  NAMES="$*"
fi

# === 检查 1：说话人一致性 ===
echo
echo -e "${B}[检查 1] 说话人一致性${N}"
# LC_ALL=C 让 grep 把 CJK 当单字节处理，避免 illegal byte sequence
BAD=$(LC_ALL=C grep -cE '^\*\*【[^】]*\*\* \[' 01_清洗稿.md)
[ "$BAD" -eq 0 ] && ok "残缺标签=0" || err "残缺标签=$BAD（漏 】）"
for n in $NAMES; do
  C=$(LC_ALL=C grep -cE "^\*\*【$n】\*\* \[" 01_清洗稿.md)
  echo "  $n: $C 回合"
done
REM=$(LC_ALL=C grep -cE '^\*\*【说话人|^\*\*【华霖富】|^\*\*【赵辉】' 01_清洗稿.md)
[ "$REM" -eq 0 ] && ok "ASR/旧标签残留=0" || err "ASR/旧标签残留=$REM"

# === 检查 2：ASR 残留 ===
echo
echo -e "${B}[检查 2] ASR 残留与订正${N}"
D=$(LC_ALL=C grep -c '\[ASR/存疑' 01_清洗稿.md)
echo "  [ASR/存疑] 标注: $D 处"
TAB=$(awk '/^## ASR 修正对照表/{f=1;next} /^## /{if(f)exit;next} f{print}' 01_清洗稿.md | LC_ALL=C grep -cE '^\|')
echo "  对照表条目: $TAB 条"
OLD_NAME_PATTERN="赵辉|本服|力宏|华霖富|凯瑞|凯莉|卡瑞"
LEAK=$(grep -rE "$OLD_NAME_PATTERN" --include="*.md" . 2>/dev/null \
  | grep -v "曾作\|原文\|疑" \
  | grep -v "^Binary" | wc -l | tr -d ' ')
[ "$LEAK" -eq 0 ] && ok "旧名/账号名无意义残留=0" || warn "旧名/账号名残留=$LEAK（请 grep 检查）"

# === 检查 3：金句格式 ===
echo
echo -e "${B}[检查 3] 金句格式${N}"
GOLD=$(LC_ALL=C grep -cE '^[0-9]+\. \*\*【' 01_清洗稿.md)
[ "$GOLD" -ge 5 ] && ok "附录 B 金句速查: $GOLD 条" || warn "金句速查仅 $GOLD 条"
ANCHOR=$(LC_ALL=C grep -c 'APPEND_MARKER' 01_清洗稿.md)
[ "$ANCHOR" -eq 0 ] && ok "锚点残留=0" || err "锚点残留=$ANCHOR"

# === 检查 4：结构完整性 ===
echo
echo -e "${B}[检查 4] 结构完整性${N}"
for f in 01_清洗稿.md 02_主题整理 03_方法论清单.md 04_术语表.md \
         05_人物角色卡.md 06_关键数据速查.md 07_议题关联地图.md \
         08_洞察卡片.md 09_战略诊断与行动清单.md README.md index.html; do
  [ -e "$f" ] && ok "$f" || err "MISSING $f"
done
NSEG=$(ls 02_主题整理/ 2>/dev/null | grep -cE '^第[0-9]+段')
echo "  02 段数: $NSEG"
CARDS=$(LC_ALL=C grep -cE '^## 卡 [0-9]+' 08_洞察卡片.md 2>/dev/null)
COUNTER=$(LC_ALL=C grep -c '^\*\*反方\*\*' 08_洞察卡片.md 2>/dev/null)
[ "$CARDS" -gt 0 ] && [ "$CARDS" -eq "$COUNTER" ] && ok "洞察卡 $CARDS 张，反方数匹配" \
  || warn "洞察卡 $CARDS 张，反方 $COUNTER 处（应相等）"
MUTI=$(grep -cE '^\*\*母题\*\*' 07_议题关联地图.md 2>/dev/null)
[ "$MUTI" -ge 1 ] && ok "议题地图有母题" || warn "议题地图缺母题"
CODEBLOCKS=$(awk '/^```$/{c++; if(c>=2) exit} END{print c}' 07_议题关联地图.md 2>/dev/null)
[ "$CODEBLOCKS" -ge 2 ] && ok "议题地图 ASCII 图在代码块内" || warn "议题地图代码块不足"

# === 检查 5：HTML 渲染 ===
echo
echo -e "${B}[检查 5] HTML 渲染${N}"
if [ -f index.html ]; then
  SIZE=$(wc -c < index.html)
  echo "  index.html: $SIZE bytes"
  EXTLINK=$(grep -cE 'https?://[^\"'"'"' ]+\.(js|css)' index.html)
  [ "$EXTLINK" -eq 0 ] && ok "无外部 CDN 链接" || warn "外部 CDN: $EXTLINK"
else
  err "index.html 未生成"
fi

# === 检查 6：跨会话同步（必查补丁）===
echo
echo -e "${B}[检查 6] 跨会话同步${N}"
THEME_DIR=$(dirname "$DIR")
PROJ_NAME=$(basename "$DIR" | sed 's/_[0-9-]\{8,\}$//')
PROJ_NAME=$(echo "$PROJ_NAME" | sed 's/_[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}$//')

# 6.1 主题总 README 是否含本场次目录名
if [ -f "$THEME_DIR/README.md" ]; then
  if grep -q "$(basename "$DIR")" "$THEME_DIR/README.md" 2>/dev/null; then
    ok "主题总 README 含本场次目录名"
  else
    warn "主题总 README 未含本场次目录名（可能需要追加）"
  fi
fi

# 6.2 总览 HTML 链接校验
for overview in "$THEME_DIR"/_渠道与交付战略_*.html; do
  [ -f "$overview" ] || continue
  BROKEN=$(grep -oE '\(\.\./[^)]+\)' "$overview" | tr -d '()' | sort -u | while read link; do
    test -f "$THEME_DIR/$link" || echo "BROKEN $link"
  done)
  if [ -z "$BROKEN" ]; then
    ok "$(basename "$overview") 链接完整"
  else
    err "$(basename "$overview") 断链: $BROKEN"
  fi
done

# 6.3 来源索引（得到大脑）
for idx in "$THEME_DIR"/../得到大脑录音/_索引.md "$THEME_DIR"/../腾讯会议录音/_索引.md; do
  [ -f "$idx" ] || continue
  if grep -q "$(basename "$DIR")" "$idx" 2>/dev/null; then
    ok "$(basename "$idx") 含本场次"
  else
    warn "$(basename "$idx") 未含本场次（可能未在统计范围内）"
  fi
done

# === 检查 7：全局层同步（v2）===
echo
echo -e "${B}[检查 7] 全局层同步（v2）${N}"
GLOBAL_DIR="$THEME_DIR/../_全局资产"
if [ -d "$GLOBAL_DIR" ]; then
  for asset in 引语库.md 方法论总库.md 干系人档案.md 决策与行动日志.md 母题总图.md; do
    [ -f "$GLOBAL_DIR/$asset" ] && echo "  ✓ $asset" || warn "$asset 缺失"
  done
  # 本场次是否已登记进引语库（按场次短号）
  SHORTID=$(basename "$DIR" | grep -oE '2026-08-[0-9]{2}' | head -1 | sed 's/2026-08-/08-/')
  if [ -n "$SHORTID" ] && grep -q "$SHORTID" "$GLOBAL_DIR/引语库.md" 2>/dev/null; then
    ok "引语库已含本场（$SHORTID）"
  else
    warn "引语库未登记本场——完成后应把金句/方法论/决策登记进 _全局资产/"
  fi
else
  warn "_全局资产/ 目录不存在（v2 全局层未建设）"
fi

echo
echo "=========================================="
echo " 总结：交付前如出现 err，请修复后再发布"
echo "=========================================="