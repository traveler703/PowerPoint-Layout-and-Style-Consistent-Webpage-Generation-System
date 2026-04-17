"""
PPT组合服务 - LandPPT原版
步骤11: 组合输出 - 合并所有幻灯片为完整HTML
"""
import base64
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class PptCombiner:
    """PPT组合服务 - 合并幻灯片为完整HTML"""
    
    @staticmethod
    def combine_slides_to_html(
        slides: List[Dict[str, Any]],
        title: str = "PPT演示文稿"
    ) -> str:
        """
        合并所有幻灯片为完整HTML
        
        Args:
            slides: 幻灯片列表，每项包含 page_number, title, slide_type, html
            title: PPT标题
            
        Returns:
            完整HTML文档
        """
        logger.info(f"组合{len(slides)}页幻灯片")
        
        # 构建幻灯片容器
        slides_html = ""
        for slide in slides:
            slides_html += f'''
        <div class="slide" id="slide-{slide['page_number']}" data-type="{slide.get('slide_type', 'content')}">
            {slide['html']}
        </div>'''
        
        full_html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        html, body {{
            width: 100%;
            height: 100%;
            overflow: hidden;
            font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
        }}
        
        .ppt-container {{
            width: 100%;
            height: 100%;
            display: flex;
            justify-content: center;
            align-items: center;
            background: #1a1a2e;
        }}
        
        .slide {{
            display: none;
            width: 1280px;
            height: 720px;
            background: white;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
            position: relative;
            overflow: hidden;
        }}
        
        .slide.active {{
            display: block;
        }}
        
        .navigation {{
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 10px;
            z-index: 1000;
        }}
        
        .nav-btn {{
            padding: 10px 20px;
            background: rgba(255, 255, 255, 0.9);
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
        }}
        
        .nav-btn:hover {{
            background: white;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
        }}
        
        .nav-btn:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}
        
        .page-indicator {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: rgba(0, 0, 0, 0.6);
            color: white;
            padding: 8px 16px;
            border-radius: 4px;
            font-size: 14px;
            z-index: 1000;
        }}
        
        .slide-counter {{
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(0, 0, 0, 0.6);
            color: white;
            padding: 8px 16px;
            border-radius: 4px;
            font-size: 14px;
            z-index: 1000;
        }}
        
        .thumbnail-nav {{
            position: fixed;
            left: 10px;
            top: 50%;
            transform: translateY(-50%);
            display: flex;
            flex-direction: column;
            gap: 5px;
            max-height: 80vh;
            overflow-y: auto;
            z-index: 1000;
        }}
        
        .thumbnail {{
            width: 60px;
            height: 34px;
            background: rgba(255, 255, 255, 0.8);
            border: 2px solid transparent;
            border-radius: 4px;
            cursor: pointer;
            opacity: 0.6;
            transition: all 0.3s;
            font-size: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }}
        
        .thumbnail:hover {{
            opacity: 1;
        }}
        
        .thumbnail.active {{
            border-color: #667eea;
            opacity: 1;
        }}
    </style>
</head>
<body>
    <div class="ppt-container">
{slides_html}
    </div>
    
    <div class="thumbnail-nav" id="thumbnailNav"></div>
    
    <div class="navigation">
        <button class="nav-btn" id="prevBtn" onclick="prevSlide()">上一页</button>
        <button class="nav-btn" id="nextBtn" onclick="nextSlide()">下一页</button>
    </div>
    
    <div class="slide-counter" id="slideCounter"></div>
    
    <script>
        let currentSlide = 1;
        const totalSlides = {len(slides)};
        
        function showSlide(n) {{
            if (n < 1) n = 1;
            if (n > totalSlides) n = totalSlides;
            
            currentSlide = n;
            
            // 切换幻灯片显示
            document.querySelectorAll('.slide').forEach((slide, index) => {{
                slide.classList.remove('active');
                if (index + 1 === currentSlide) {{
                    slide.classList.add('active');
                }}
            }});
            
            // 更新缩略图
            document.querySelectorAll('.thumbnail').forEach((thumb, index) => {{
                thumb.classList.remove('active');
                if (index + 1 === currentSlide) {{
                    thumb.classList.add('active');
                }}
            }});
            
            // 更新按钮状态
            document.getElementById('prevBtn').disabled = currentSlide === 1;
            document.getElementById('nextBtn').disabled = currentSlide === totalSlides;
            
            // 更新计数器
            document.getElementById('slideCounter').textContent = `${{currentSlide}} / ${{totalSlides}}`;
        }}
        
        function nextSlide() {{
            showSlide(currentSlide + 1);
        }}
        
        function prevSlide() {{
            showSlide(currentSlide - 1);
        }}
        
        function goToSlide(n) {{
            showSlide(n);
        }}
        
        // 键盘导航
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'ArrowRight' || e.key === 'ArrowDown' || e.key === ' ') {{
                e.preventDefault();
                nextSlide();
            }} else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {{
                e.preventDefault();
                prevSlide();
            }} else if (e.key === 'Home') {{
                e.preventDefault();
                showSlide(1);
            }} else if (e.key === 'End') {{
                e.preventDefault();
                showSlide(totalSlides);
            }}
        }});
        
        // 点击导航
        document.querySelectorAll('.slide').forEach((slide) => {{
            slide.addEventListener('click', (e) => {{
                // 如果点击的是按钮，不切换
                if (e.target.closest('button')) return;
                nextSlide();
            }});
        }});
        
        // 初始化缩略图
        function initThumbnails() {{
            const nav = document.getElementById('thumbnailNav');
            for (let i = 1; i <= totalSlides; i++) {{
                const thumb = document.createElement('div');
                thumb.className = 'thumbnail' + (i === 1 ? ' active' : '');
                thumb.textContent = i;
                thumb.onclick = () => goToSlide(i);
                nav.appendChild(thumb);
            }}
        }}
        
        // 初始化
        initThumbnails();
        showSlide(1);
    </script>
</body>
</html>'''
        
        logger.info("PPT组合完成")
        return full_html
    
    @staticmethod
    def encode_html_to_base64(html: str) -> str:
        """将HTML编码为Base64"""
        return base64.b64encode(html.encode('utf-8')).decode('utf-8')
    
    @staticmethod
    def decode_base64_to_html(base64_str: str) -> str:
        """将Base64解码为HTML"""
        return base64.b64decode(base64_str.encode('utf-8')).decode('utf-8')
    
    @staticmethod
    def get_slide_count(html: str) -> int:
        """获取HTML中的幻灯片数量"""
        import re
        matches = re.findall(r'id="slide-(\d+)"', html)
        return len(matches)
