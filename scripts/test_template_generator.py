"""
模板生成器测试脚本

测试模板生成器在各种场景下的表现。

运行方式:
    python scripts/test_template_generator.py
    python scripts/test_template_generator.py --quick          # 快速测试（只用 fallback）
    python scripts/test_template_generator.py --api http://localhost:5000  # 测试 API 模式
    python scripts/test_template_generator.py --validate-file templates/data/ink.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.template_generator import (
    TemplateGenerator,
    validate_template,
    extract_json_from_response,
    merge_with_defaults,
    REQUIRED_FIELDS,
    REQUIRED_PAGE_TYPES,
)

# ============================================================
# 测试用例
# ============================================================

TEST_CASES = [
    {
        "name": "商务专业风格",
        "description": "设计一个商务风格的PPT模板，主色调是深蓝色，简洁大气",
        "expected_style": "business",
        "expected_keywords": ["蓝色", "商务", "专业"],
    },
    {
        "name": "赛博朋克科技风",
        "description": "设计一个科技感十足的赛博朋克风格模板，霓虹光效",
        "expected_style": "cyber",
        "expected_keywords": ["科技", "赛博", "霓虹"],
    },
    {
        "name": "水墨中国风",
        "description": "设计一个水墨中国风的模板，清新淡雅，适合诗词展示",
        "expected_style": "ink",
        "expected_keywords": ["水墨", "中国", "淡雅"],
    },
    {
        "name": "儿童教育风格",
        "description": "设计一个儿童教育风格的模板，活泼可爱，色彩明亮",
        "expected_style": "kids",
        "expected_keywords": ["儿童", "活泼", "可爱"],
    },
    {
        "name": "极简主义风格",
        "description": "设计一个极简主义风格的PPT，大量留白，黑白灰配色",
        "expected_style": "minimal",
        "expected_keywords": ["极简", "留白", "黑白"],
    },
    {
        "name": "极简风格（英文）",
        "description": "Create a minimalist PPT template with lots of white space, black and white",
        "expected_style": "minimal",
        "expected_keywords": ["minimalist", "white space", "simple"],
    },
    {
        "name": "模糊需求",
        "description": "给我做一个PPT模板",
        "expected_style": "fallback",
        "expected_keywords": [],
    },
    {
        "name": "学术报告风格",
        "description": "设计一个学术报告风格的模板，适合论文答辩和学术演示",
        "expected_style": "academic",
        "expected_keywords": ["学术", "论文", "答辩"],
    },
    {
        "name": "清新自然风格",
        "description": "设计一个清新自然的模板，薄荷绿为主色调，适合环保主题",
        "expected_style": "nature",
        "expected_keywords": ["自然", "清新", "环保"],
    },
    {
        "name": "创意插画风格",
        "description": "设计一个创意插画风格的PPT模板，手绘感强，适合创意展示",
        "expected_style": "creative",
        "expected_keywords": ["插画", "创意", "手绘"],
    },
]


# ============================================================
# 验证函数
# ============================================================

def check_css_color合法性(color: str) -> bool:
    """检查颜色值是否合法。"""
    if not color:
        return False
    color = color.strip()
    # rgba 格式
    if color.startswith("rgba"):
        return True
    # 十六进制 #RRGGBB 或 #RGB
    if color.startswith("#"):
        hex_part = color[1:]
        if len(hex_part) in (3, 6):
            try:
                int(hex_part, 16)
                return True
            except ValueError:
                return False
    return False


def check_skeleton有效性(skeleton: str, required_placeholders: list[str]) -> tuple[bool, str]:
    """检查骨架 HTML 是否有效。"""
    if not skeleton or len(skeleton.strip()) < 15:
        return False, "骨架太短或为空"

    # 检查必需占位符
    for ph in required_placeholders:
        if "{{" + ph + "}}" not in skeleton:
            return False, f"缺少占位符: {{{{{ph}}}}}"

    # 检查基本 HTML 结构
    if "<div" not in skeleton and "<section" not in skeleton:
        return False, "骨架缺少 div/section 标签"

    if "</div>" not in skeleton and "</section" not in skeleton:
        return False, "骨架缺少闭合标签"

    return True, "OK"


def deep_validate_template(template: dict, test_name: str) -> dict[str, Any]:
    """
    对模板进行深度验证。

    Returns:
        {
            "passed": bool,
            "score": int,       # 0-100
            "issues": list[str], # 发现的问题
            "warnings": list[str], # 警告（不影响通过）
            "praises": list[str],  # 做得好的地方
        }
    """
    issues = []
    warnings = []
    praises = []
    score = 100

    # 1. 必需字段
    for field in REQUIRED_FIELDS:
        if field not in template:
            issues.append(f"缺少必需字段: {field}")
            score -= 15

    # 2. viewport
    vp = template.get("viewport", {})
    if vp.get("width") != 1280 or vp.get("height") != 720:
        issues.append("viewport 不是 1280x720")
        score -= 10

    # 3. page_types 数量
    pt = template.get("page_types", {})
    pt_count = len(pt)
    if pt_count < 4:
        issues.append(f"page_types 只有 {pt_count} 种，建议至少 4 种（cover/content/toc/ending）")
        score -= (4 - pt_count) * 5

    # 4. 必需页面类型
    for req_type in REQUIRED_PAGE_TYPES:
        if req_type not in pt:
            issues.append(f"缺少必需页面类型: {req_type}")
            score -= 10

    # 5. 页面骨架验证
    skeleton_placeholders = {
        "cover": ["title"],
        "content": ["title"],
        "toc": ["toc_items"],
        "ending": ["title"],
        "section": ["title"],
    }
    for ptype, required_pls in skeleton_placeholders.items():
        if ptype not in pt:
            continue
        pconfig = pt[ptype]
        if not isinstance(pconfig, dict):
            continue
        skeleton = pconfig.get("skeleton", "")
        valid, msg = check_skeleton有效性(skeleton, required_pls)
        if not valid:
            issues.append(f"{ptype} 页面骨架: {msg}")
            score -= 5
        else:
            praises.append(f"{ptype} 页面骨架设计合理")

    # 6. CSS 变量验证
    css = template.get("css_variables", {})
    color_vars = [k for k in css if k.startswith("color-")]

    if len(color_vars) < 4:
        warnings.append(f"color 变量只有 {len(color_vars)} 个，建议至少 4 个")
        score -= 5

    for var_name, var_val in css.items():
        if var_name.startswith("color-") and var_val:
            if not check_css_color合法性(var_val):
                issues.append(f"CSS 变量 {var_name} 颜色值不合法: {var_val}")
                score -= 3

    # 7. 字体验证
    font_body = css.get("font-body", "")
    font_heading = css.get("font-heading", "")
    if not font_body:
        warnings.append("未设置 font-body")
        score -= 2
    if not font_heading:
        warnings.append("未设置 font-heading")
        score -= 2

    # 8. template_id 格式
    tid = template.get("template_id", "")
    if not tid:
        issues.append("template_id 为空")
        score -= 10
    elif not tid.islower() and not all(c.isalnum() or c == "_" for c in tid):
        warnings.append(f"template_id 格式不规范: {tid}（建议全小写+下划线）")
        score -= 2

    # 9. 标签
    tags = template.get("tags", [])
    if len(tags) == 0:
        warnings.append("没有设置标签")
        score -= 2
    elif len(tags) > 5:
        warnings.append(f"标签过多: {len(tags)} 个，建议不超过 5 个")

    # 10. 正面加分项
    if "compare" in pt:
        praises.append("包含对比页（compare）")
        score = min(100, score + 3)
    if "chart" in pt:
        praises.append("包含图表页（chart）")
        score = min(100, score + 3)
    if "timeline" in pt:
        praises.append("包含时间线页（timeline）")
        score = min(100, score + 3)
    if "qa" in pt:
        praises.append("包含问答页（qa）")
        score = min(100, score + 3)

    # 字体是否区分 body 和 heading
    if font_body and font_heading and font_body != font_heading:
        praises.append("正文字体和标题字体有区分")
        score = min(100, score + 2)

    # 是否有 accent 颜色
    accent_count = len([k for k in css if "accent" in k])
    if accent_count >= 2:
        praises.append(f"有 {accent_count} 个点缀色变量")
        score = min(100, score + 2)

    score = max(0, min(100, score))

    return {
        "passed": len(issues) == 0,
        "score": score,
        "issues": issues,
        "warnings": warnings,
        "praises": praises,
    }


# ============================================================
# 测试运行器
# ============================================================

def run_single_test(
    test_case: dict,
    generator: TemplateGenerator | None,
    use_api: str | None,
    timeout: float = 30.0,
) -> dict:
    """运行单个测试用例。"""
    name = test_case["name"]
    description = test_case["description"]

    print(f"\n{'='*60}")
    print(f"测试: {name}")
    print(f"描述: {description}")
    print(f"期望风格: {test_case['expected_style']}")
    print("-" * 60)

    t0 = time.time()
    result = {
        "name": name,
        "description": description,
        "expected_style": test_case["expected_style"],
        "success": False,
        "llm_response": "",
        "template": None,
        "validation": None,
        "deep_validation": None,
        "elapsed_ms": 0,
        "error": None,
        "api_mode": use_api is not None,
    }

    try:
        if use_api:
            # API 模式
            import requests

            resp = requests.post(
                f"{use_api}/api/llm/chat",
                json={
                    "messages": [{"role": "user", "content": description}],
                    "mode": "template",
                },
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()

            result["success"] = data.get("success", False)
            result["llm_response"] = data.get("response", "")
            result["template"] = data.get("parsed")
            result["elapsed_ms"] = (time.time() - t0) * 1000

            if data.get("validation"):
                result["validation"] = {
                    "valid": data["validation"].get("valid"),
                    "errors": data["validation"].get("errors", []),
                }

        else:
            # 直接调用
            gen = generator or TemplateGenerator()
            raw = gen.generate_sync(description, mode="one-shot")

            result["success"] = raw["success"]
            result["llm_response"] = raw.get("response", "")
            result["template"] = raw.get("parsed")
            result["elapsed_ms"] = (time.time() - t0) * 1000

            if raw.get("validation"):
                result["validation"] = {
                    "valid": raw["validation"][0],
                    "errors": raw["validation"][1],
                }

    except Exception as e:
        result["error"] = str(e)
        result["elapsed_ms"] = (time.time() - t0) * 1000

    # 深度验证
    if result["template"]:
        result["deep_validation"] = deep_validate_template(
            result["template"], name
        )

    # 打印结果
    status = "通过" if result["success"] else "失败"
    if result["error"]:
        print(f"  结果: 错误 - {result['error']}")
    else:
        print(f"  结果: {status}")
        print(f"  耗时: {result['elapsed_ms']:.0f}ms")

        if result["validation"]:
            v = result["validation"]
            v_status = "通过" if v["valid"] else "失败"
            print(f"  基础校验: {v_status}")
            for err in v.get("errors", []):
                print(f"    - {err}")

        if result["deep_validation"]:
            dv = result["deep_validation"]
            print(f"  深度校验得分: {dv['score']}/100 ({'通过' if dv['passed'] else '有问题'})")
            for issue in dv["issues"]:
                print(f"    [问题] {issue}")
            for warn in dv["warnings"]:
                print(f"    [警告] {warn}")
            if dv["praises"]:
                for praise in dv["praises"]:
                    print(f"    [优点] {praise}")

        if result["template"]:
            tpl = result["template"]
            print(f"  模板ID: {tpl.get('template_id')}")
            print(f"  模板名: {tpl.get('template_name')}")
            print(f"  页面类型: {', '.join(tpl.get('page_types', {}).keys())}")

            # 显示主配色
            css = tpl.get("css_variables", {})
            primary = css.get("color-primary", "N/A")
            secondary = css.get("color-secondary", "N/A")
            print(f"  主色调: {primary}")
            print(f"  次色调: {secondary}")

    return result


def print_summary(results: list[dict]):
    """打印测试汇总。"""
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)

    total = len(results)
    success_count = sum(1 for r in results if r["success"])
    passed_count = sum(
        1 for r in results if r["deep_validation"] and r["deep_validation"]["passed"]
    )
    avg_score = sum(
        r["deep_validation"]["score"] for r in results if r["deep_validation"]
    ) / max(1, sum(1 for r in results if r["deep_validation"]))

    print(f"  总测试数: {total}")
    print(f"  LLM 生成成功: {success_count}/{total}")
    print(f"  深度校验通过: {passed_count}/{total}")
    print(f"  平均质量得分: {avg_score:.1f}/100")

    print("\n逐项结果:")
    print(f"  {'测试名':<25} {'状态':>6} {'得分':>6} {'耗时':>8}")
    print(f"  {'-'*25} {'-'*6} {'-'*6} {'-'*8}")
    for r in results:
        dv = r.get("deep_validation")
        score_str = f"{dv['score']}/100" if dv else "N/A"
        status_str = "通过" if (dv and dv["passed"]) else ("失败" if dv else ("错误" if r["error"] else "未完成"))
        elapsed = f"{r['elapsed_ms']:.0f}ms" if r["elapsed_ms"] else "N/A"
        name = r["name"][:24]
        print(f"  {name:<25} {status_str:>6} {score_str:>6} {elapsed:>8}")

    # 统计常见问题
    all_issues = []
    all_warnings = []
    for r in results:
        if r.get("deep_validation"):
            all_issues.extend(r["deep_validation"]["issues"])
            all_warnings.extend(r["deep_validation"]["warnings"])

    if all_issues:
        print(f"\n最常见问题 (Top 5):")
        from collections import Counter
        for issue, count in Counter(all_issues).most_common(5):
            print(f"  [{count}次] {issue}")

    if all_warnings:
        print(f"\n警告统计 (Top 5):")
        for warn, count in Counter(all_warnings).most_common(5):
            print(f"  [{count}次] {warn}")

    print("\n结论:", end=" ")
    if passed_count == total:
        print("全部通过！")
    elif passed_count >= total * 0.7:
        print("大部分通过，质量良好。")
    else:
        print("需要改进。")


def validate_existing_file(filepath: str) -> dict:
    """验证已有的模板 JSON 文件。"""
    print(f"\n验证文件: {filepath}")
    print("-" * 60)

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            template = json.load(f)
    except Exception as e:
        print(f"  读取失败: {e}")
        return {"passed": False, "error": str(e)}

    dv = deep_validate_template(template, os.path.basename(filepath))
    print(f"  得分: {dv['score']}/100 ({'通过' if dv['passed'] else '有问题'})")
    print(f"  模板ID: {template.get('template_id')}")
    print(f"  模板名: {template.get('template_name')}")
    print(f"  页面类型: {', '.join(template.get('page_types', {}).keys())}")

    print(f"\n  问题 ({len(dv['issues'])} 项):")
    for issue in dv["issues"]:
        print(f"    - {issue}")
    print(f"  警告 ({len(dv['warnings'])} 项):")
    for warn in dv["warnings"]:
        print(f"    - {warn}")
    print(f"  优点 ({len(dv['praises'])} 项):")
    for praise in dv["praises"]:
        print(f"    + {praise}")

    return dv


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="模板生成器测试脚本")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="快速测试（只验证 fallback，不调用 LLM）",
    )
    parser.add_argument(
        "--api",
        type=str,
        default=None,
        help="API 模式：指定后端地址，如 http://localhost:5000",
    )
    parser.add_argument(
        "--validate-file",
        type=str,
        dest="validate_file",
        help="验证指定的 JSON 文件，不运行测试",
    )
    parser.add_argument(
        "--test",
        type=str,
        default=None,
        dest="test_name",
        help="只运行指定名称的测试",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        dest="output_dir",
        help="生成的模板保存到的目录",
    )

    args = parser.parse_args()

    # 验证文件模式
    if args.validate_file:
        dv = validate_existing_file(args.validate_file)
        sys.exit(0 if dv["passed"] else 1)

    # 快速测试：只验证 fallback 逻辑
    if args.quick:
        print("快速测试模式：验证 fallback 模板生成逻辑")
        print("=" * 60)

        from scripts.template_generator import _build_fallback_template

        test_keywords = [
            ("商务", "business"),
            ("科技", "cyber"),
            ("水墨", "ink"),
            ("儿童", "kids"),
            ("模糊", "fallback"),
        ]

        all_passed = True
        for kw, style in test_keywords:
            tpl = _build_fallback_template(f"测试{kw}关键词")
            dv = deep_validate_template(tpl, kw)
            status = "通过" if dv["passed"] else "失败"
            print(f"  {kw}: {status} (得分: {dv['score']}/100)")
            if not dv["passed"]:
                for issue in dv["issues"]:
                    print(f"    - {issue}")
                all_passed = False

        print(f"\nFallback 测试: {'全部通过' if all_passed else '有失败项'}")
        sys.exit(0 if all_passed else 1)

    # 完整测试
    print("PPT 模板生成器 - 测试套件")
    print("=" * 60)
    print(f"API 模式: {'是 (' + args.api + ')' if args.api else '否（直接调用）'}")
    print(f"测试用例数: {len(TEST_CASES)}")

    generator = None if args.api else TemplateGenerator()

    results = []
    for tc in TEST_CASES:
        if args.test_name and args.test_name not in tc["name"]:
            continue

        r = run_single_test(tc, generator, args.api)
        results.append(r)

        # 如果是直接调用，限制每次测试间隔
        if not args.api and len(results) < len(TEST_CASES):
            time.sleep(0.5)

    print_summary(results)

    # 保存详细报告
    output_dir = args.output_dir or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "output",
    )
    os.makedirs(output_dir, exist_ok=True)

    report_path = os.path.join(output_dir, f"template_test_report_{int(time.time())}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        # 不保存原始 LLM 响应（太长）
        clean_results = []
        for r in results:
            clean = {k: v for k, v in r.items() if k != "llm_response"}
            clean_results.append(clean)
        json.dump(
            {"results": clean_results, "timestamp": time.time()},
            f, ensure_ascii=False, indent=2
        )
    print(f"\n详细报告已保存: {report_path}")

    # 保存生成的模板
    saved = 0
    for r in results:
        if r["template"]:
            tpl = r["template"]
            tid = tpl.get("template_id", f"test_{int(time.time())}")
            tpl_dir = os.path.join(output_dir, "generated_templates")
            os.makedirs(tpl_dir, exist_ok=True)
            tpl_path = os.path.join(tpl_dir, f"{tid}.json")
            with open(tpl_path, "w", encoding="utf-8") as f:
                json.dump(tpl, f, ensure_ascii=False, indent=2)
            saved += 1

    if saved:
        print(f"已保存 {saved} 个生成的模板到: {tpl_dir}")

    # 返回码：0=全部通过, 1=有失败
    passed = sum(1 for r in results if r["deep_validation"] and r["deep_validation"]["passed"])
    sys.exit(0 if passed == len(results) else 1)
