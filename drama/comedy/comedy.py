import os
import time
import json
import re
from openai import OpenAI

# ========== 配置 ==========
API_KEY = "your-api-key-here"
BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-chat"

# ========== 喜剧类型配置 ==========
COMEDY_CONFIGS = {
    "单口相声": {
        "num_performers": 1,
        "structure": "垫话(引入) -> 正活(主体故事) -> 攒底(结尾包袱)",
        "writer_prompt": """你是一位单口相声演员兼编剧。请创作一段单人相声(单口)。

【主题】：{topic}
【字数】：{word_count}字左右
【风格】：{style}

【结构要求】：
1. 垫话：用3-5句话引入话题，抓住观众注意力
2. 正活：讲述一个完整故事，至少3个层次，层层递进
3. 攒底：结尾要有一个响亮的包袱，让观众回味

【创作要点】：
- 一人分饰多角时，用"(模仿XXX语气)"标注
- 善用"歪批""曲解""谐音梗"等单口常用技巧
- 要有"我有个朋友""我小时候"这类个人叙述视角
- 至少4个笑点，最后一个要最响
- 用【笑点设计】标注每个包袱

请直接输出完整文本：""",
        "audience_suffix": "注意单口相声的节奏：铺垫要稳，包袱要脆。"
    },
    
    "对口相声": {
        "num_performers": 2,
        "structure": "开场垫话 -> 入活(进入正题) -> 正活(三番四抖) -> 攒底",
        "writer_prompt": """你是一位对口相声编剧。请创作一段对口相声(逗哏+捧哏)。

【主题】：{topic}
【字数】：{word_count}字左右
【风格】：{style}

【角色】：
- A(逗哏)：主导叙述，承担主要笑点
- B(捧哏)：配合、反问、烘托，台词精简

【结构要求】：
1. 垫话：A逗B捧，3-5个来回
2. 入活：B问"您刚才说的这个XXX，到底怎么回事？"
3. 正活：用"三番四抖"结构，至少3个包袱
4. 攒底：最后一个大包袱收尾

【捧哏常用语】："嗯""啊""是""哎""对""不像话""您别挨骂了""去你的吧"

【格式】：
A：
B：

用【笑点设计】标注每个包袱。

请直接输出完整剧本：""",
        "audience_suffix": "注意捧逗配合的默契度，这是对口相声的灵魂。"
    },
    
    "群口相声": {
        "num_performers": 3,
        "structure": "多人出场 -> 角色冲突 -> 矛盾升级 -> 底包袱",
        "writer_prompt": """你是一位群口相声编剧。请创作一段群口相声(3人及以上)。

【主题】：{topic}
【字数】：{word_count}字左右
【风格】：{style}

【角色设计】(至少3个)：
- 请用【角色设定】先定义每个角色的性格特点
- 例如：A(急性子)、B(慢性子)、C(和事佬)

【结构要求】：
1. 角色逐个登场，各有立场
2. 围绕主题产生分歧或争论
3. "腻缝"角色负责穿针引线、制造笑点
4. 最后用一个"底"(大包袱)统一收尾

【创作要点】：
- 角色性格要鲜明，台词风格不同
- 善用"接话茬""抢话""互怼"制造喜剧感
- 至少4个笑点

格式：
A：
B：
C：

用【笑点设计】标注每个包袱。

请直接输出完整剧本：""",
        "audience_suffix": "注意多人之间的化学反应，角色不要沦为背景板。"
    },
    
    "脱口秀": {
        "num_performers": 1,
        "structure": "开场破冰 -> 主题展开 -> 连环笑点 -> 高潮收尾",
        "writer_prompt": """你是一位脱口秀编剧(单口喜剧)。请创作一段脱口秀段子。

【主题】：{topic}
【字数】：{word_count}字左右
【风格】：{style}

【结构要求】：
1. 开场破冰：一句话抓住观众，建立连接
2. 主题展开：从个人经历切入，约3-4个段落
3. 每段话要有"预期违背"，结尾反转
4. 高潮收尾：最炸的梗放在最后

【创作要点】：
- 使用"你们有没有发现……""说实话……""我最近……"等口语
- 每80-120字设置一个笑点
- 善用"callback"(前面梗的呼应)
- 观察式喜剧：从日常小事挖掘荒诞感
- 至少5个笑点

请直接输出完整脚本，用【笑点设计】标注每个梗。

请直接输出完整脚本：""",
        "audience_suffix": "关注观众的即时反应，脱口秀的笑点密度很重要。"
    },
    
    "漫才": {
        "num_performers": 2,
        "structure": "3-5个小段子串联，每段一个独立包袱",
        "writer_prompt": """你是一位漫才编剧。请创作一段漫才(日本式双人喜剧)。

【主题】：{topic}
【字数】：{word_count}字左右
【风格】：{style}

【角色】：
- 装傻(A)：负责提出荒诞的设想、夸张的比喻
- 吐槽(B)：负责戳穿、吐槽、把观众拉回现实

【结构要求】：
1. 由3-5个独立的小段子组成，每个30秒-1分钟
2. 每段模式：装傻抛出荒谬观点 -> 吐槽犀利反驳
3. 整体节奏：快！快！快！不要拖沓

【经典模式】：
- "XX是什么？""XX就是……""不对！那是YY！"
- A：我有一个梦想…… B：你醒醒！
- 用词要直白，动作感强

【格式】：
A(装傻)：
B(吐槽)：

用【笑点设计】标注每个段子的笑点。

请直接输出完整脚本：""",
        "audience_suffix": "漫才讲究'秒笑'，如果观众反应慢半拍就失败了。"
    }
}

# ========== 观众智能体 ==========
AUDIENCE_PROMPT = """你是一个专业的喜剧观众观察员。请阅读以下{comedy_type}脚本，模拟真实观众的反应。

【脚本】：
{script}

【特别关注】：{audience_suffix}

请逐句或按段落分析观众反应，只输出JSON格式：

{{
  "reactions": [
    {{
      "text": "具体的台词或段落(原文引用，不超过50字)",
      "laughter_level": 0-10,
      "laughter_type": "无反应|轻笑|大笑|爆笑|持续爆笑|冷场",
      "trigger": "分析为什么好笑或不好笑",
      "is_expected": true/false,
      "expected_level": 0-10
    }}
  ],
  "summary": {{
    "total_laughs": 0,
    "avg_laughter": 0,
    "peak_laughter": 0,
    "total_words": 0,
    "laugh_density": 0,
    "hits": 0,
    "misses": 0,
    "unexpected_hits": 0,
    "overall_rating": "冷场|一般|好笑|非常好笑|炸场",
    "timing_issues": "节奏问题描述",
    "character_balance": "角色戏份是否均衡",
    "suggestions": "改进建议(200字以内)"
  }}
}}"""


# ========== 核心函数 ==========
def generate_comedy(topic, word_count, comedy_type="脱口秀", style="幽默风趣"):
    """生成喜剧脚本并模拟观众反应"""
    
    if not API_KEY or API_KEY == "your-api-key-here":
        return None, None, "[错误] 请先设置有效的 API_KEY"
    
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    config = COMEDY_CONFIGS.get(comedy_type, COMEDY_CONFIGS["脱口秀"])
    
    # 第1步：编剧生成
    print(f"[{comedy_type}] 第1步：编剧创作中...")
    print(f"  结构：{config['structure']}")
    
    writer_prompt = config["writer_prompt"].format(
        topic=topic,
        word_count=word_count,
        style=style
    )
    
    try:
        writer_response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": f"你是专业{comedy_type}编剧，擅长结构设计和包袱创作。"},
                {"role": "user", "content": writer_prompt}
            ],
            temperature=0.85,
            max_tokens=min(word_count * 2, 8192)
        )
        script = writer_response.choices[0].message.content
        print(f"  [完成] 脚本生成({len(script)}字符)")
    except Exception as e:
        return None, None, f"[错误] 编剧失败：{str(e)}"
    
    # 第2步：观众模拟
    print("[观众] 第2步：观众智能体模拟反应...")
    
    expected_laughs = re.findall(r'【笑点设计[：:]\s*([^】]*)】', script)
    print(f"  检测到 {len(expected_laughs)} 个预期笑点")
    
    audience_prompt = AUDIENCE_PROMPT.format(
        comedy_type=comedy_type,
        script=script,
        audience_suffix=config["audience_suffix"]
    )
    
    try:
        audience_response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "你是观众反应分析专家，只输出JSON。"},
                {"role": "user", "content": audience_prompt}
            ],
            temperature=0.3,
            max_tokens=4096
        )
        raw_json = audience_response.choices[0].message.content
        json_match = re.search(r'(\{.*\})', raw_json, re.DOTALL)
        if json_match:
            raw_json = json_match.group(1)
        audience_data = json.loads(raw_json)
        print("  [完成] 观众反应分析完成")
    except Exception as e:
        print(f"  [警告] 观众分析异常，使用备用方案：{e}")
        audience_data = fallback_analysis(script, expected_laughs)
    
    # 第3步：生成报告
    print("[报告] 第3步：生成评估报告...")
    report = generate_report(script, audience_data, comedy_type, topic, config)
    
    return script, audience_data, report


def fallback_analysis(script, expected_laughs):
    """备用观众分析"""
    exclamation = script.count('！') + script.count('!')
    question = script.count('？') + script.count('?')
    laugh_markers = len(re.findall(r'哈+|笑', script))
    
    base_score = min(8, 3 + exclamation // 8 + question // 10 + laugh_markers // 2)
    
    return {
        "reactions": [
            {"text": script[:100] + "...", "laughter_level": base_score,
             "laughter_type": "大笑" if base_score > 5 else "轻笑",
             "trigger": "基于文本兴奋度估算", "is_expected": True, "expected_level": base_score}
        ],
        "summary": {
            "total_laughs": max(1, len(expected_laughs) or 1),
            "avg_laughter": base_score,
            "peak_laughter": min(10, base_score + 2),
            "total_words": len(script),
            "laugh_density": len(expected_laughs) / max(1, len(script) / 100),
            "hits": len(expected_laughs) // 2,
            "misses": len(expected_laughs) // 2,
            "unexpected_hits": 0,
            "overall_rating": "一般" if base_score < 5 else "好笑" if base_score < 7 else "非常好笑",
            "timing_issues": "建议加强节奏控制",
            "character_balance": "建议检查角色互动",
            "suggestions": "建议增加更多具体场景和反转"
        }
    }


def generate_report(script, audience_data, comedy_type, topic, config):
    """生成评估报告"""
    s = audience_data.get("summary", {})
    
    def laughter_bar(level):
        bar = "=" * min(10, int(level)) + "-" * (10 - min(10, int(level)))
        return f"[{bar}] {level}/10"
    
    density = s.get("laugh_density", 0)
    density_desc = "稀疏" if density < 2 else "正常" if density < 5 else "密集"
    rating_map = {"冷场": "[冷场]", "一般": "[一般]", "好笑": "[好笑]", "非常好笑": "[非常好笑]", "炸场": "[炸场]"}
    rating_text = rating_map.get(s.get("overall_rating", "一般"), "[一般]")
    
    report = f"""
{'='*70}
喜剧效果评估报告
{'='*70}

[基本信息]
  主题：{topic}
  类型：{comedy_type} ({config['num_performers']}人)
  结构：{config['structure']}

[核心数据]
  整体评价：{rating_text}
  总笑点数：{s.get('total_laughs', 0)} 次
  平均笑声：{laughter_bar(s.get('avg_laughter', 0))}
  峰值笑声：{laughter_bar(s.get('peak_laughter', 0))}
  笑点密度：{density:.1f} 个/百字 -> {density_desc}
  脚本字数：{s.get('total_words', len(script))} 字

[预期 vs 实际]
  命中(设计有效)：{s.get('hits', 0)} 个
  未命中(设计失效)：{s.get('misses', 0)} 个
  意外之喜(没设计但笑了)：{s.get('unexpected_hits', 0)} 个
  命中率：{s.get('hits', 0) / max(1, s.get('hits', 0) + s.get('misses', 0)) * 100:.0f}%

[改进建议]
  节奏问题：{s.get('timing_issues', '无明显问题')}
  角色平衡：{s.get('character_balance', '无需调整')}
  具体建议：{s.get('suggestions', '暂无建议')}

[逐段观众反应]
"""
    
    for i, reaction in enumerate(audience_data.get("reactions", [])[:8], 1):
        level = reaction.get('laughter_level', 0)
        level_label = "无反应" if level < 2 else "轻笑" if level < 4 else "大笑" if level < 7 else "爆笑"
        expected = "[命中]" if reaction.get('is_expected', True) else "[意外]"
        text = reaction.get('text', '')[:50]
        trigger = reaction.get('trigger', '')[:60]
        
        report += f"""
  [{i}] 强度：{level}/10 ({level_label}) {expected}
      "{text}..."
      原因：{trigger}
"""
    
    report += f"""
{'='*70}
"""
    return report


# ========== 主程序 ==========
def main():
    print("=" * 70)
    print("喜剧五型智能创作系统")
    print("编剧 + 观众 + 裁判 = 三智能体协作")
    print("=" * 70)
    print()
    
    # 显示类型列表
    print("[支持的喜剧类型]")
    types = list(COMEDY_CONFIGS.keys())
    for i, t in enumerate(types, 1):
        config = COMEDY_CONFIGS[t]
        print(f"  {i}. {t} ({config['num_performers']}人) - {config['structure'][:20]}...")
    print()
    
    # 输入
    topic = input("主题：").strip() or "日常生活"
    
    try:
        word_count = int(input("字数(200-3000，默认500)：").strip() or "500")
        word_count = max(200, min(3000, word_count))
    except:
        word_count = 500
    
    try:
        type_idx = int(input("选择类型(输入序号，默认4脱口秀)：").strip() or "4")
        comedy_type = types[min(type_idx - 1, len(types) - 1)]
    except:
        comedy_type = "脱口秀"
    
    style = input("风格(辛辣讽刺/温馨治愈/荒诞夸张，默认幽默风趣)：").strip() or "幽默风趣"
    
    print(f"\n{'='*70}")
    print(f"[开始] 创作【{comedy_type}】主题：【{topic}】目标字数：【{word_count}字】")
    print(f"{'='*70}\n")
    
    start = time.time()
    script, audience_data, report = generate_comedy(
        topic, word_count, comedy_type, style
    )
    elapsed = time.time() - start
    
    if script is None:
        print(audience_data)
        return
    
    print(f"\n[完成] 总耗时：{elapsed:.1f} 秒\n")
    
    print("=" * 70)
    print("完整脚本")
    print("=" * 70)
    print(script)
    print("\n" + report)
    
    # 保存
    filename = f"{comedy_type}_{topic}_{int(time.time())}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"类型：{comedy_type}\n主题：{topic}\n风格：{style}\n字数：{word_count}\n\n")
        f.write("="*70 + "\n脚本\n" + "="*70 + "\n\n")
        f.write(script)
        f.write("\n\n" + report)
    print(f"\n[保存] {filename}")


if __name__ == "__main__":
    main()