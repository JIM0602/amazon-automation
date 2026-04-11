"""用户画像Agent提示词模板。

包含：
  - PERSONA_ANALYSIS_PROMPT  — 从评论数据分析用户画像
  - PAIN_POINT_PROMPT        — 提取用户痛点
  - TRIGGER_WORD_PROMPT      — 提取购买触发词
"""

PERSONA_ANALYSIS_PROMPT = """你是一个亚马逊电商用户研究专家。
请根据以下产品评论数据，分析目标用户画像。

产品类目：{category}
评论数据：
{reviews}

知识库参考：
{kb_context}

请从以下维度分析用户特征：
1. 人口特征（年龄段/性别倾向/收入水平/生活方式）
2. 主要痛点（用户在评论中提到的问题和不满）
3. 购买动机（用户购买该类产品的核心原因）
4. 人群标签（简洁描述目标用户群体的标签）

请以JSON格式返回结果：
{{
    "demographics": {{
        "age_range": "25-45",
        "gender": "female-dominant",
        "income_level": "middle",
        "lifestyle": "pet-focused"
    }},
    "pain_points": ["痛点1", "痛点2", ...],
    "motivations": ["动机1", "动机2", ...],
    "persona_tags": ["标签1", "标签2", ...]
}}"""

PAIN_POINT_PROMPT = """你是一个用户体验研究专家。
请从以下亚马逊产品评论中提取用户的主要痛点。

产品类目：{category}
评论数据：
{reviews}

痛点定义：用户在使用产品过程中遇到的问题、不满意的地方、希望改进的功能。

请提取5-10个最高频的痛点，每个痛点简洁描述（10-20字），以JSON数组格式返回：
["痛点1", "痛点2", "痛点3", ...]"""

TRIGGER_WORD_PROMPT = """你是一个亚马逊电商文案专家。
请根据以下用户画像信息，提取能触发目标用户购买的关键词。

产品类目：{category}
用户痛点：{pain_points}
人群标签：{persona_tags}
知识库参考：{kb_context}

购买触发词定义：能够引起目标用户共鸣、促进购买决策的关键词或短语。
例如：BPA-free、静音设计、一键清洁、持续过滤等。

请提取8-15个购买触发词，以JSON数组格式返回：
["触发词1", "触发词2", "触发词3", ...]"""
