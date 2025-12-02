import os
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

API_URL = "https://models.inference.ai.azure.com/chat/completions"
API_KEY = os.getenv('GITHUB_TOKEN', '')
MODEL = "gpt-4.1-mini"

PROMPT_TEMPLATE = '''أنت استشاري استراتيجية أعمال متخصص. يرجى تحليل المعلومات التجارية التالية وتقديم تحليل استراتيجي شامل.

فكرة العمل التجارية:
{idea}

أهداف العمل التجارية:
{goals}

يرجى تقديم تحليل استراتيجي مفصل يتضمن:
1. **تحليل فرص السوق**
   - حجم السوق المحتمل
   - مشهد المنافسة
   - الميزة القيمية الفريدة
2. **التوصيات الاستراتيجية**
   - عوامل النجاح الرئيسية
   - المخاطر المحتملة واستراتيجيات التخفيف
   - فرص النمو
3. **خطة التنفيذ**
   - أولويات المرحلة الأولى (أول 3-6 أشهر)
   - الإنجازات الرئيسية
   - الموارد المطلوبة
4. **الاعتبارات المالية**
   - احتياجات الاستثمار المقدرة
   - نموذج الإيرادات المحتمل
   - الجدول الزمني لتحقيق نقطة التعادل
5. **الخطوات التالية**
   - الإجراءات الفورية المراد اتخاذها
   - مؤشرات النجاح المراد تتبعها
يرجى تنظيم الإجابة بأقسام واضحة وتقديم رؤى قابلة للتطبيق.'''

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        idea = request.form.get('businessIdea', '').strip()
        goals = request.form.get('businessGoals', '').strip()
        
        if not idea or not goals:
            return render_template('index.html', error='يرجى ملء جميع الحقول المطلوبة.', result=None)
        
        prompt = PROMPT_TEMPLATE.format(idea=idea, goals=goals)
        
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {API_KEY}'
            }
            data = {
                'model': MODEL,
                'messages': [
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.7,
                'max_tokens': 2000,
                'top_p': 0.9
            }
            resp = requests.post(API_URL, headers=headers, json=data)
            if resp.status_code == 200:
                result = resp.json()['choices'][0]['message']['content']
                return render_template('index.html', result=result, error=None)
            else:
                return render_template('index.html', error='حدث خطأ أثناء الاتصال بنموذج الذكاء الاصطناعي.', result=None)
        except Exception as e:
            return render_template('index.html', error='تعذر الاتصال بالخدمة. يرجى المحاولة لاحقاً.', result=None)
    
    return render_template('index.html', result=None, error=None)

if __name__ == '__main__':
    app.run(debug=True)
