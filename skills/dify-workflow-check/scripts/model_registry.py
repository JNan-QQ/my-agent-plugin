DEEPSEEK_V3_1 = {
    'name': '灵犀生产专用模型-DeepSeek-V3.1-w8a8-671b（DeepSeek-V3.1-w8a8）',
    'provider': 'langgenius/xinference/xinference',
    'mode': 'chat',
    'completion_params': {'temperature': 0.7},
}

TARGET_MODEL = DEEPSEEK_V3_1

ALIASES = {
    'deepseek-v3.1': DEEPSEEK_V3_1,
    'DeepSeek-V3.1': DEEPSEEK_V3_1,
    '灵犀生产专用模型-DeepSeek-V3.1-w8a8-671b（DeepSeek-V3.1-w8a8）': DEEPSEEK_V3_1,
}


def resolve_model(name_or_alias: str) -> dict | None:
    return ALIASES.get(name_or_alias)
