# 跨会话同步与下游收尾（08）

> **为什么需要这个文件**：本 skill 在 6 次发布前必查里只覆盖了场次目录内的产物质量。但实战中，**遗漏造成的实际返工往往不在场内，而在场与场之间、场与记忆之间**。本文件把这些跨会话同步点集中成可执行清单。

> **何时读取**：阶段 ⑤⑥（README + 跨场呼应）读一遍；在做身份订正后必读——订正会跨文件扩散。

---

## 一、身份订正的波及清单

**陷阱**：本 skill 把身份订正视为局部动作（头部映射改一下）。但实际上一处订正（如「华霖富→秋萍」「赵辉→赵晖」「本服→赵本福」）会扩散到 8 个位置。任何遗漏都会导致场次之间人物链条断裂、知识包互相打架。

**波及 8 点**（按波及范围由近到远）：

1. **01_清洗稿.md**
   - 头部映射块（`> **说话人映射**`）
   - 对照表（`## ASR 修正对照表`）的原词/还原两列
   - 正文回合（`【旧名】`→`【新名】`）
   - 附录 C（说话人说明）、附录 D（忠实性说明）

2. **02_主题整理/** 全部 `第N段_*.md`
   - 段内人名
   - 文件名（如 `第1段_赵辉病倒.md` → `第1段_赵晖病倒.md`）

3. **03_方法论清单.md** —— 引用说话人处

4. **04_术语表.md**
   - 若该人名作为术语条目（### 人名），重命名整个块
   - 引用该人的方法论条目的出处段号

5. **05_人物角色卡.md**
   - 人物卡标题（`## 人名`）
   - 代表发言的标签

6. **06_关键数据速查.md** —— 表格里的「说话人·[时间戳]」列

7. **07_议题关联地图.md** / **08_洞察卡片.md** / **09_战略诊断与行动清单.md** —— 证据原话、行动清单 owner

8. **场次 README.md** —— 金句速查、已知瑕疵段、跨场呼应

**波及检查命令**（订正后必跑）：

```bash
cd "<场次目录>"
echo "--- 旧名残留（应=0，注记语境如 '曾作「旧名」' 除外）---"
grep -rn "旧名" --include="*.md" . | grep -v "曾作\|原文\|疑\|注记" | head
echo "--- 新名计数（应 = 各文件预期数）---"
for f in 01_清洗稿.md 02_主题整理/*.md 03_方法论清单.md 04_术语表.md \
         05_人物角色卡.md 06_关键数据速查.md 07_议题关联地图.md \
         08_洞察卡片.md 09_战略诊断与行动清单.md README.md; do
  echo "$(basename $(dirname $f))/$(basename $f): $(grep -c '新名' $f)"
done
```

---

## 二、第三种说话人映射陷阱：账号名 ≠ 本人

本 skill 已记录两类陷阱（P1 称呼≠身份、P11 用户确认不绝对），本文件追加**第三种**：

**陷阱**：转写标签看起来是实名（「华霖富」），实际是**某位参会者的腾讯会议账号名**，得到大脑按参会账号名标注转写。

**首次发现**：2026-08-19 管网场——秋萍（邱平）使用腾讯会议账号「华霖富」入会，docx 全部回合被转写标签为「华霖富」。用户口头确认「华霖富就是秋萍」。

**检测**：

- 头部映射写「docx「华霖富」218 回合」但本人从未自我介绍过此名
- 转写标签虽然有完整姓名形式，但与会者都未当面叫过此名（只叫「秋萍/邱平/郭老师」）
- **跨场搜索**：在其他录音中查此名（如 `grep 华霖富 <录音项目根>`）——无匹配 → 高概率是账号名

**修复**：与 P1/P11 同——原话称呼/账号名保留（金句原则），头部映射显式说明「转写标签「X」= 该参会者的腾讯会议账号名」。

**入档**：本次发现后已入 `recording-project-people.md` 与本文件。

---

## 三、双源对齐骨架

**陷阱**：很多场次有主源 + 交叉源（如腾讯会议全程 docx + 郭磊手机端得到大脑版；或腾讯会议全员版 + 单方手机录音）。时间戳偏移可达数分钟，错引就坐错。

**双源骨架（01_清洗稿头部第三段之后写入）**：

```
> 来源（主源）：<主源文件路径>（<平台/账号>，<YYYY-MM-DD HH:MM> 入会，<通话时长/段数>）
> 来源（交叉校验源）：<交叉源文件路径>（<平台/账号>，时间戳偏移 X 分钟，<差异点>）
> 时戳基线：所有清洗稿时间戳均按主源口径，引用交叉源时标注 [交叉源≈主源 ±X 分钟]
```

**已知差异点速查**：

| 组合 | 偏移 | 差异点 |
|---|---|---|
| 腾讯会议 docx + 郭磊手机端得到大脑 | ≈ 2 分钟（主源在前） | 主源有接通段/纪要元数据；交叉源有漏字 ASR |
| 腾讯会议全程 + 单方手机录音 | ≈ 0-5 分钟 | 同上 |
| 同一场两段录音（同云端 ID） | 0 | 内容一致但标题不同——见 P-注① |

---

## 四、下游同步清单（场次完成后的 6 处更新）

阶段 ⑥ README 完成后，**必须**按这个清单逐处同步，遗漏任何一处都会让跨场叙事断裂：

| 同步点 | 位置 | 更新内容 | 风险 |
|---|---|---|---|
| 1. 场次 README | `<场次目录>/README.md` | 「已知瑕疵」「金句速查」「跨场呼应」 | 漏 = 本场不可检索 |
| 2. 主题总 README | `<主题目录>/README.md` | 链表追加新行（如八场链→九场链） | 漏 = 主题目录断裂 |
| 3. **总览 HTML** | `<主题目录>/_渠道与交付战略_*.html` | 链表章节、相对链接 | **断档**：仍停在 5 场而实际已 10 场 |
| 4. 来源索引 | `得到大脑录音/_索引.md` 或 `腾讯会议录音/_索引.md` | 「状态」列改「已清洗→场次目录」 | 漏 = 总索引误导 |
| 5. 人物映射记忆 | `~/.claude/projects/.../memory/recording-project-people.md` | 新人物/新 ASR 变体/新陷阱 | 漏 = 下次清洗重蹈覆辙 |
| 6. 进度记忆 | `~/.claude/projects/.../memory/recording-cleansing-progress.md` | 场次 N+1 段加新场次摘要 | 漏 = 用户跨会话失去全局视角 |

**同步检查**：

```bash
# 主题目录链表是否包含新场次
grep "<新场次目录名>" "<主题目录>/README.md"
# 总览 HTML 链接校验
for d in $(grep -oE '\[([^\]]+)\]\(([^)]+)\)' "<主题目录>/_渠道与交付战略_*.html" \
         | grep -oE '\(\.\./[^)]+\)' | tr -d '()' | sort -u); do
  test -f "<主题目录>/$d" || echo "BROKEN $d"
done
# 来源索引状态
grep "<新场次标题>" "得到大脑录音/_索引.md"
```

---

## 五、得到大脑 Intake（route 表补全）

**陷阱**：skill 的 SKILL.md「输入形态与路由」表只列了飞书妙记/本地文件/doubao-stt。本录音项目的实际入场路径是**得到大脑**（biji.com），加上腾讯会议导出的 docx。这两类都不在原表里，导致 Intake 方法只能靠 memory 反复注入。

**得到大脑 Intake 三步法**（2026-08-13 起沿用）：

```bash
# 1. 列表（按时间倒序）
getnote notes --limit N -o json > /tmp/biji_recent.json
python3 -c "
import json
d = json.load(open('/tmp/biji_recent.json'))
notes = d.get('data',{}).get('notes',[]) if isinstance(d,dict) else d
for n in notes:
    print(n.get('created_at','?'), '|', n.get('note_type','?'), '|', n.get('id','?'), '|', n.get('title','')[:50])
"

# 2. 单条详情（取 audio.original = 原文逐字稿，非 ASR 总结）
python3 << 'EOF'
import json, urllib.request, os
cfg = json.load(open(os.path.expanduser('~/.getnote/config.json')))
API_KEY = cfg['api_key']; CLIENT_ID = cfg['client_id']
url = f"https://openapi.biji.com/open/api/v1/resource/note/detail?id=<id>"
req = urllib.request.Request(url, headers={"Authorization": API_KEY, "X-Client-ID": CLIENT_ID})
data = json.load(urllib.request.urlopen(req, timeout=60))
print(data['data']['note']['audio']['original'])  # = 原文，原样保留
print('时长ms:', data['data']['note']['attachments'][0]['duration'])  # = 毫秒
EOF

# 3. ⚠️ 云端重复上传陷阱：同一音频可能被 AI 起不同标题二次上传
# 增量拉取时若两条头尾/字数/时长全同，先 md5 校验再落盘
md5 <file1> <file2>
# 重复只留先到一条，_索引.md 注明并档
```

**字段速记**：

| API 字段 | 含义 | 备注 |
|---|---|---|
| `data.note.audio.original` | 原文逐字稿 | 格式 `🟢 说话人 [时间戳]\n内容` |
| `data.note.attachments[0].duration` | 时长 | **毫秒**（÷1000 得秒） |
| `data.notes[].note_type` | local_audio / meeting / recorder_audio / audio / class_audio | 五类支持 audio.original；其余 link/plain_text/img_text 跳过 |
| `data.notes[].content` | AI 智能总结 | **不是原文**，别误用 |

**腾讯会议 docx Intake**：

```bash
# 腾讯会议录制的逐字稿导出为 docx，会话方发到群里的"参考资料"常是 docx
python3 << 'EOF'
import zipfile, re
p = "<docx 文件路径>"
z = zipfile.ZipFile(p)
xml = z.read('word/document.xml').decode('utf-8')
texts = re.findall(r'<w:t[^>]*>(.*?)</w:t>', xml, re.S)
full = ''.join(texts)
# 格式：「姓名(HH:MM:SS): 内容」连排，按时间戳切回合
EOF
```

docx 标签可靠（腾讯会议按账号实名转写），是双源结构中的主源首选。

---

## 六、订正后落盘顺序（防漏 checklist）

```
身份订正确认（用户口头/文字）后：
  □ 跑「波及检查命令」（第八点）
  □ 批量替换（含各文件标题、文件名）
  □ 头部映射块的「新名字段」+「账号名说明」
  □ 对照表（原词+还原双列）
  □ 跑全套 scripts/pipeline_check.sh
  □ 重渲染 HTML（render_pack.py）
  □ 同步人物映射记忆 + 进度记忆
  □ 同步主题总 README + 总览 HTML 链表
  □ 来源索引状态列
  □ 自检命令 grep -rn "旧名" --include="*.md" . | grep -v "曾作\|原文\|疑" → 应为空
```