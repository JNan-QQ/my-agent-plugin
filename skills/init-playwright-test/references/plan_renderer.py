#!/usr/bin/env python
"""
将 JSON 测试计划渲染为 Markdown 文档
用法: python tools/plan_renderer.py specs/login.json
"""
import sys
import json
from pathlib import Path

REQUIRED_KEYS = {"plan_name", "url", "modules"}
REQUIRED_MODULE_KEYS = {"module_name", "scenarios"}
REQUIRED_SCENARIO_KEYS = {"scenario_name", "test_file", "steps"}


def validate_plan(plan: dict) -> list[str]:
    """校验测试计划 JSON 结构，返回错误列表"""
    errors = []

    missing = REQUIRED_KEYS - plan.keys()
    if missing:
        errors.append(f"缺少顶层字段: {', '.join(missing)}")
        return errors

    if not isinstance(plan["modules"], list):
        errors.append("modules 必须是数组")
        return errors

    for i, module in enumerate(plan["modules"]):
        missing_m = REQUIRED_MODULE_KEYS - module.keys()
        if missing_m:
            errors.append(f"modules[{i}] 缺少字段: {', '.join(missing_m)}")
            continue

        if not isinstance(module["scenarios"], list):
            errors.append(f"modules[{i}].scenarios 必须是数组")
            continue

        for j, scenario in enumerate(module["scenarios"]):
            missing_s = REQUIRED_SCENARIO_KEYS - scenario.keys()
            if missing_s:
                errors.append(
                    f"modules[{i}].scenarios[{j}] 缺少字段: {', '.join(missing_s)}"
                )

    return errors


def render_plan(json_path: str) -> str:
    """将 JSON 测试计划渲染为 Markdown"""
    with open(json_path, encoding="utf-8") as f:
        plan = json.load(f)

    errors = validate_plan(plan)
    if errors:
        raise ValueError(f"JSON 格式错误:\n" + "\n".join(f"  - {e}" for e in errors))

    lines = []
    lines.append(f"# 测试计划: {plan.get('plan_name', 'Untitled')}")
    lines.append("")
    lines.append(f"**目标 URL**: {plan.get('url', 'N/A')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    for module in plan.get("modules", []):
        lines.append(f"## {module.get('module_name', 'Unnamed Module')}")
        lines.append("")

        for i, scenario in enumerate(module.get("scenarios", []), 1):
            lines.append(f"### {i}. {scenario.get('scenario_name', 'Unnamed Scenario')}")
            lines.append("")
            lines.append(f"**测试文件**: `{scenario.get('test_file', 'N/A')}`")
            lines.append("")

            if scenario.get("preconditions"):
                lines.append("**前置条件**:")
                for pre in scenario["preconditions"]:
                    lines.append(f"- {pre}")
                lines.append("")

            lines.append("**步骤**:")
            for j, step in enumerate(scenario.get("steps", []), 1):
                action = step.get("action", "unknown")
                if action == "navigate":
                    lines.append(f"{j}. 访问 `{step.get('target', '')}`")
                elif action == "fill":
                    lines.append(f"{j}. 在 `{step.get('selector', '')}` 中输入 `{step.get('value', '')}`")
                elif action == "click":
                    lines.append(f"{j}. 点击 `{step.get('selector', '')}`")
                else:
                    lines.append(f"{j}. {action}: {step}")
            lines.append("")

            if scenario.get("assertions"):
                lines.append("**预期结果**:")
                for assertion in scenario["assertions"]:
                    atype = assertion.get("type", "unknown")
                    value = assertion.get("value", "")
                    if atype == "url_contains":
                        lines.append(f"- URL 包含 `{value}`")
                    elif atype == "text_visible":
                        lines.append(f"- 页面显示文本 `{value}`")
                    else:
                        lines.append(f"- {atype}: `{value}`")
                lines.append("")

            lines.append("---")
            lines.append("")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("用法: python tools/plan_renderer.py <json_path>")
        sys.exit(1)

    json_path = sys.argv[1]
    if not Path(json_path).exists():
        print(f"错误: 文件不存在: {json_path}")
        sys.exit(1)

    try:
        markdown = render_plan(json_path)
    except json.JSONDecodeError as e:
        print(f"错误: JSON 解析失败: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"错误: {e}")
        sys.exit(1)

    md_path = Path(json_path).with_suffix(".md")
    md_path.parent.mkdir(parents=True, exist_ok=True)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"已生成: {md_path}")


if __name__ == "__main__":
    main()
