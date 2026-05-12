# generate_with_weasyprint.py
from weasyprint import HTML
from questions_judge import judge_questions
from questions_single import single_questions
from questions_multi import multi_questions

# 生成 HTML 内容
html_content = '''
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
    body { font-family: "Noto Sans CJK SC", "WenQuanYi Micro Hei", "SimHei", sans-serif; margin: 2cm; }
    h1 { text-align: center; font-size: 20px; }
    h2 { font-size: 16px; margin-top: 20px; }
    .question { margin: 10px 0; }
    .answer-red { color: red; font-weight: bold; }
    .answer-gray { color: gray; }
    .option { margin-left: 20px; }
    .correct { color: red; }
    .wrong { color: gray; }
    hr { margin: 20px 0; }
</style>
</head>
<body>
<h1>全媒体运营师（创意策划）三级</h1>
<h1>理论知识试卷（含答案）</h1>
<p style="text-align:center">考试时间：90分钟    总分：100分</p>
'''

# 判断题
html_content += '<h2>一、判断题（每题0.5分，共20分）</h2>'
html_content += '<p>（正确的填"√"，错误的填"×"）</p>'
for idx, (question, is_true) in enumerate(judge_questions, 1):
    answer = '√' if is_true else '×'
    html_content += f'<p class="question">{idx}. {question} <span class="answer-red">答案：{answer}</span></p>'

# 单选题
html_content += '<h2>二、单项选择题（每题0.5分，共70分）</h2>'
option_letters = ['A', 'B', 'C', 'D']
for idx, (question, options, answer_idx) in enumerate(single_questions, 1):
    html_content += f'<p class="question">{idx}. {question}</p>'
    for opt_idx, opt_text in enumerate(options):
        prefix = f'{option_letters[opt_idx]}. {opt_text}'
        if opt_idx == answer_idx:
            html_content += f'<p class="option correct">✓ {prefix}</p>'
        else:
            html_content += f'<p class="option wrong">{prefix}</p>'

# 多选题
html_content += '<h2>三、多项选择题（每题1分，共10分）</h2>'
option_letters = ['A', 'B', 'C', 'D', 'E']
for idx, (question, options, answer_indices) in enumerate(multi_questions, 1):
    html_content += f'<p class="question">{idx}. {question}</p>'
    for opt_idx, opt_text in enumerate(options):
        prefix = f'{option_letters[opt_idx]}. {opt_text}'
        if opt_idx in answer_indices:
            html_content += f'<p class="option correct">✓ {prefix}</p>'
        else:
            html_content += f'<p class="option wrong">{prefix}</p>'

html_content += '</body></html>'

# 生成 PDF
HTML(string=html_content).write_pdf('全媒体运营师三级_理论知识试卷_含答案.pdf')
print("PDF已生成!")