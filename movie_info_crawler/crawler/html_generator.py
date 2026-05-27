"""HTML报告生成模块"""

from datetime import datetime
from string import Template
from typing import List
from pathlib import Path

from .models import MovieResult, MovieField
from .config_manager import ConfigManager

_CHECKBOX_FIELDS = [f for f in MovieField if f != MovieField.DOUBAN_LINK]


class HTMLGenerator:
    """HTML报告生成器"""
    
    def __init__(self, config: ConfigManager, output_dir: str = 'output'):
        self.config = config
        self.output_dir = Path(output_dir)
        self._ensure_output_dir()
    
    def _ensure_output_dir(self) -> None:
        """确保输出目录存在"""
        self.output_dir.mkdir(exist_ok=True)
    
    def generate(self, results: List[MovieResult], fields: list = None) -> str:
        """生成HTML报告"""
        if fields is None:
            fields = _CHECKBOX_FIELDS
        total = len(results)
        found = sum(1 for r in results if r.found)
        not_found = total - found

        movie_cards = []
        for idx, result in enumerate(results):
            if result.found and result.info:
                card = self._generate_success_card(idx, result, fields)
            else:
                card = self._generate_not_found_card(idx, result)
            movie_cards.append(card)

        is_summary_selected = MovieField.SUMMARY in fields
        checkboxes_html = '\n'.join(
            f'            <label><input type="checkbox" data-field="{f.key}" checked> {f.label}</label>'
            for f in fields
            if f != MovieField.SUMMARY or is_summary_selected
        )
        html_content = self._get_html_template().safe_substitute(
            generate_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            total_movies=total,
            found_movies=found,
            not_found_movies=not_found,
            field_checkboxes=checkboxes_html,
            movie_cards='\n'.join(movie_cards)
        )
        
        output_file = self.output_dir / 'douban_movies_report.html'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(output_file.absolute())
    
    def _generate_success_card(self, idx: int, result: MovieResult, fields: list) -> str:
        """生成成功获取的电影卡片"""
        info = result.info

        fields_html = ""
        for field in fields:
            if field in (MovieField.TITLE, MovieField.DOUBAN_LINK, MovieField.SUMMARY):
                continue
            value = info.get(field)
            if value:
                fields_html += f"""
                        <div class="info-item" data-field="{field.key}">
                            <div class="info-label">{field.label}</div>
                            <div class="info-value">{self._escape_html(value)}</div>
                        </div>
                        """

        rating_html = ""
        rating = info.get(MovieField.RATING)
        if rating:
            rating_html = f'<span class="rating">[评分] {rating}</span>'

        title = info.get(MovieField.TITLE) or result.search_name

        card = f"""
                <div class="movie-card">
                    <div class="movie-header" onclick="toggleCard({idx})">
                        <h2>{self._escape_html(title)} {rating_html}</h2>
                        <div class="status">点击展开详情</div>
                    </div>
                    <div class="movie-body" id="movie-body-{idx}">
                        <div class="info-grid">
                            {fields_html}
                        </div>
                """

        summary = info.get(MovieField.SUMMARY)
        if summary and MovieField.SUMMARY in fields:
            card += f"""
                        <div class="summary" data-field="summary">
                            <h4>[剧情简介]</h4>
                            <p>{self._escape_html(summary)}</p>
                        </div>
                    """

        card += """
                    </div>
                </div>
                """

        return card
    
    def _generate_not_found_card(self, idx: int, result: MovieResult) -> str:
        """生成未找到的电影卡片"""
        error_msg = result.error or "未能从豆瓣找到相关信息"
        
        return f"""
                <div class="movie-card">
                    <div class="movie-header" onclick="toggleCard({idx})">
                        <h2>{self._escape_html(result.search_name)}</h2>
                        <div class="status">未找到</div>
                    </div>
                    <div class="movie-body" id="movie-body-{idx}">
                        <div class="not-found">
                            <p>{self._escape_html(error_msg)}</p>
                            <p style="margin-top: 10px; font-size: 0.9em;">可能原因：电影未在豆瓣收录、搜索名称不匹配或网络问题</p>
                        </div>
                    </div>
                </div>
                """
    
    def _escape_html(self, text: str) -> str:
        """转义HTML特殊字符"""
        if not text:
            return ''
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))
    
    def _get_html_template(self) -> Template:
        """获取HTML模板"""
        return Template("""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>豆瓣电影信息报告</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header .info {
            font-size: 0.9em;
            opacity: 0.9;
        }
        
        .stats {
            display: flex;
            justify-content: space-around;
            padding: 20px;
            background: #f8f9fa;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .stat-card {
            text-align: center;
        }
        
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }
        
        .stat-label {
            font-size: 0.9em;
            color: #666;
            margin-top: 5px;
        }
        
        .content {
            padding: 30px;
        }
        
        .movie-card {
            background: white;
            border-radius: 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 30px;
            overflow: hidden;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        
        .movie-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        }
        
        .movie-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 25px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .movie-header h2 {
            font-size: 1.5em;
            margin: 0;
        }
        
        .movie-header .status {
            font-size: 0.9em;
            background: rgba(255,255,255,0.2);
            padding: 5px 12px;
            border-radius: 20px;
        }
        
        .movie-body {
            padding: 25px;
            display: none;
        }
        
        .movie-body.active {
            display: block;
        }
        
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 25px;
        }
        
        .info-item {
            background: #f8f9fa;
            padding: 12px 15px;
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }
        
        .info-label {
            font-weight: bold;
            color: #667eea;
            font-size: 0.85em;
            text-transform: uppercase;
            margin-bottom: 5px;
        }
        
        .info-value {
            color: #333;
            font-size: 1em;
            word-wrap: break-word;
        }
        
        .summary {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-top: 20px;
        }
        
        .summary h4 {
            color: #667eea;
            margin-bottom: 10px;
        }
        
        .summary p {
            color: #666;
            line-height: 1.6;
        }
        
        .rating {
            display: inline-block;
            background: #ff6b6b;
            color: white;
            padding: 5px 10px;
            border-radius: 5px;
            font-weight: bold;
            font-size: 0.8em;
            margin-left: 10px;
        }
        
        .not-found {
            padding: 25px;
            text-align: center;
            color: #999;
        }
        
        .footer {
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 0.85em;
            border-top: 1px solid #e0e0e0;
        }
        
        .field-filter {
            background: #f8f9fa;
            padding: 20px 25px;
            border-bottom: 1px solid #e0e0e0;
        }

        .field-filter h3 {
            color: #667eea;
            margin-bottom: 12px;
            font-size: 1em;
        }

        .field-checkboxes {
            display: flex;
            flex-wrap: wrap;
            gap: 8px 16px;
        }

        .field-checkboxes label {
            font-size: 0.88em;
            color: #333;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 4px;
            user-select: none;
        }

        .field-checkboxes input[type="checkbox"] {
            cursor: pointer;
        }

        .toggle-all {
            margin: 20px 0;
            text-align: center;
        }
        
        .toggle-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 0.9em;
            transition: background 0.3s;
        }
        
        .toggle-btn:hover {
            background: #764ba2;
        }
        
        @media (max-width: 768px) {
            .info-grid {
                grid-template-columns: 1fr;
            }
            
            .movie-header h2 {
                font-size: 1.2em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>豆瓣电影信息报告</h1>
            <div class="info">生成时间: $generate_time</div>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">$total_movies</div>
                <div class="stat-label">总电影数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">$found_movies</div>
                <div class="stat-label">成功获取</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">$not_found_movies</div>
                <div class="stat-label">未找到</div>
            </div>
        </div>
        
        <div class="toggle-all">
            <button class="toggle-btn" onclick="toggleAll()">展开/收起所有详情</button>
        </div>
        
        <div class="field-filter">
            <h3>显示字段</h3>
            <div class="field-checkboxes">
                $field_checkboxes
            </div>
        </div>

        <div class="content">
            $movie_cards
        </div>
        
        <div class="footer">
            <p>数据来源：豆瓣电影 | 本报告由 MovieInfoCrawler 自动生成</p>
            <p style="margin-top: 5px;">注意：数据仅供参考，实际信息以豆瓣官网为准</p>
        </div>
    </div>
    
    <script>
        function toggleCard(index) {
            var body = document.getElementById('movie-body-' + index);
            if (body) {
                body.classList.toggle('active');
            }
        }
        
        function toggleAll() {
            var bodies = document.querySelectorAll('.movie-body');
            var anyActive = false;
            for (var i = 0; i < bodies.length; i++) {
                if (bodies[i].classList.contains('active')) {
                    anyActive = true;
                    break;
                }
            }
            
            for (var i = 0; i < bodies.length; i++) {
                if (anyActive) {
                    bodies[i].classList.remove('active');
                } else {
                    bodies[i].classList.add('active');
                }
            }
        }

        document.querySelectorAll('.field-filter input[type="checkbox"]').forEach(function(cb) {
            cb.addEventListener('change', function() {
                var key = this.dataset.field;
                document.querySelectorAll('[data-field="' + key + '"]').forEach(function(el) {
                    el.style.display = this.checked ? '' : 'none';
                }.bind(this));
                localStorage.setItem('field_' + key, this.checked);
            });
            var saved = localStorage.getItem('field_' + cb.dataset.field);
            if (saved !== null) {
                cb.checked = saved === 'true';
            }
            cb.dispatchEvent(new Event('change'));
        });
    </script>
</body>
</html>""")