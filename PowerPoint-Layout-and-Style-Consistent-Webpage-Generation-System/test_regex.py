import re

raw_html_snippet = """        <div class="nav-arrow next" id="nextBtn" onclick="nextSlide()"><i class="fa-solid fa-chevron-right"></i></div>

        <!-- {{SLIDES_CONTENT}} 占位符 -->
        <div class="slide-container"><div class="slide cover">...cover...</div></div>
        <div class="slide-container"><div class="slide content">...content...</div></div>
        <!-- 额外示例页：compare / chart / timeline / qa 可自行添加，此处仅展示核心5页 -->
    </div>
</div>"""

# OLD (wrong): \}\{
old_result = re.sub(
    r'<!--\s*\}\{SLIDES_CONTENT\}[^-]*-->\s*(.*?)<!-- [^-]*额外示例页.*?-->\s*',
    r'\n{{SLIDES_CONTENT}}\n',
    raw_html_snippet,
    flags=re.DOTALL,
)
print("OLD (wrong):")
print(repr(old_result[:100]))
print()

# FIXED: match {{SLIDES_CONTENT}} with double braces
fixed_result = re.sub(
    r'<!--\s*\{\{SLIDES_CONTENT\}\}[^-]*-->\s*'
    r'(.*?)'
    r'<!-- [^-]*额外示例页.*?-->\s*',
    r'\n{{SLIDES_CONTENT}}\n',
    raw_html_snippet,
    flags=re.DOTALL,
)
print("=== FIXED RESULT ===")
print(fixed_result)
print()
print("has placeholder?", '{{SLIDES_CONTENT}}' in fixed_result)
print("no slide-container?", 'slide-container' not in fixed_result)
