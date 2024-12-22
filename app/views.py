from django.shortcuts import render
from django.shortcuts import redirect
from .models import UserDetails, CollectedData
from django.http import HttpResponse
import PyPDF2
import json
import google.generativeai as genai
from django.contrib.auth.decorators import login_required
from django.conf import settings
import os,re,ast
import speech_recognition as sr
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import logging
from django.shortcuts import get_object_or_404
import whisper
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet
model=whisper.load_model("base")
logger = logging.getLogger(__name__)

genai.configure(api_key='AIzaSyDpcJfbSdYPtTug4HDdsYPX6aVTB60drQw')

def login_page(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        try:
            user = UserDetails.objects.get(email=email)
            if user.password == password:
                request.session['logged_in']=True
                request.session['username'] = user.email
                return redirect('home')
            else:
                return render(request, "login.html", {"error": "Password is incorrect."})
        except UserDetails.DoesNotExist:
            return render(request, "login.html", {"error": "User does not exist, please register."})
    return render(request, "login.html")

def register_page(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        print(email, password)
        if UserDetails.objects.filter(email=email).exists():
            return render(request, "signup.html", {"error": "User already exists, please login."})
        else:
            UserDetails.objects.create(email=email, password=password)
            return render(request, "login.html")
    return render(request, "signup.html")

def home_page(request):
    if request.session.get('logged_in'):
        if request.method == "POST":
            content=request.POST.get("content")
            file=request.FILES.get("file")
            # print(content,file)
            if not content and not file:
                return render(request, "home.html", {"username": request.session["username"], "error": "Please enter content or upload a file."})
            extracted_text=""
            if content:
                extracted_text+=content
            if file:
                if file.name.endswith(".pdf"):
                    # print("hii")
                    extracted_text+=extractor(file)
                else:
                    return render(request, "home.html", {"username": request.session["username"], "error": "Please upload a PDF file."})
            # print(extracted_text)
            question_answer=get_questions_and_answers_from_openai(extracted_text)
            print("before json===============",question_answer)
            question_answer=question_answer[8:-5]
            print("after json=============",question_answer)
            question_answer=json.loads(question_answer)
            CollectedData.objects.all().delete()
            database(question_answer)
            request.session['total']=CollectedData.objects.count()
            return redirect('starttestpage')

        return render(request, "home.html", {"username": request.session["username"]})
    else:
        return render(request, "login.html")   
    
def extractor(file):
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
        print(text)
    return text
       
def get_questions_and_answers_from_openai(content):
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(f"generate all possible question with answer in a dictionary  for {content} with question as key and answer as value without any backtick and without any other text, only json format")
    return response.text

def database(question_answer):
    for question, answer in question_answer.items():
        CollectedData.objects.create(question=question, answer=answer)

def starttestpage(request):
    return render(request, "starttestpage.html")  
        
def logout(request):
    if request.session.get('logged_in'):
        CollectedData.objects.all().delete()
        request.session.flush()
        return redirect('login')
    else:
        return redirect('login')
   
def showquestions(request):
    if not request.session.get('logged_in'):
        return redirect('login')
    return redirect('questions',question_number=1)

def questions(request, question_number):
    if not request.session.get('logged_in'):
        return redirect('login')
    if question_number>request.session['total']:
        return redirect('scorepage')
    try:
        question = CollectedData.objects.get(question_id=question_number)
    except CollectedData.DoesNotExist:
         print(question_number)
         return redirect('questions', question_number=question_number+1)
    else:
        return render(request, 'question.html', {'question': question, 'question_number': question_number})
def scorepage(request):
    if not request.session.get('logged_in'):
        return redirect('login')
    return render( request,'scorepage.html')

@csrf_exempt
def convert_audio(request):
    if request.method == 'POST' and request.FILES.get('audio'):
        audio_file = request.FILES['audio']
        question_number = request.POST.get('question_number')  # Get question number from the form data
        if not question_number:
            return JsonResponse({'error': 'Question number is missing.'}, status=400)
        file_path = os.path.join('media', 'uploaded_audio.webm')  # Save file temporarily
        with open(file_path, 'wb') as f:
            for chunk in audio_file.chunks():
                f.write(chunk)
        try:
            result = model.transcribe(file_path)
            transcribed_text = result['text']
            question = CollectedData.objects.get(question_id=question_number)
            question.useranswer = transcribed_text
            question.save()
            return JsonResponse({'success': True, 'transcribed_text': transcribed_text})
        except Exception as e:
            return JsonResponse({'error': f'Error during transcription: {str(e)}'}, status=500)
    else:
        return JsonResponse({'error': 'No audio file provided.'}, status=400)
        
def get_next_question(request):
     question_number = request.GET.get('question_number')
     return redirect('questions', question_number=question_number)
def generate_pdf(results_with_status):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    left_margin = 50
    right_margin = 50
    y_position = height - 50  # Starting position
    p.setFont("Helvetica-Bold", 16)
    p.drawString(left_margin, y_position, "Analysis Report")
    y_position -= 30  # Space after title
    p.setFont("Helvetica", 12)

    def draw_wrapped_text(canvas, x, y, text, max_width):
        from reportlab.lib.utils import simpleSplit
        lines = simpleSplit(text, "Helvetica", 12, max_width)
        for line in lines:
            if y < 50:  # Check if space is running out at the bottom
                canvas.showPage()  # Create new page
                canvas.setFont("Helvetica", 12)  # Reset font
                y = height - 50  # Reset Y position for the new page
            canvas.drawString(x, y, line)
            y -= 15  # Move Y position down after each line
        return y

    for result in results_with_status:
        question_text = f"Q{result['question_id']}: {result['question']}"
        actual_answer_text = f"Actual Answer: {result['answer']}"
        user_answer_text = f"Your Answer: {result['useranswer']}"
        status_text = f"Status: {result['status']}"
        correct_text = f"Correct? {'Yes' if result['correct'] else 'No'}"

        y_position = draw_wrapped_text(p, left_margin, y_position, question_text, width - right_margin - left_margin)
        y_position -= 10
        y_position = draw_wrapped_text(p, left_margin, y_position, actual_answer_text, width - right_margin - left_margin)
        y_position -= 10
        y_position = draw_wrapped_text(p, left_margin, y_position, user_answer_text, width - right_margin - left_margin)
        y_position -= 10
        y_position = draw_wrapped_text(p, left_margin, y_position, status_text, width - right_margin - left_margin)
        y_position -= 10
        y_position = draw_wrapped_text(p, left_margin, y_position, correct_text, width - right_margin - left_margin)
        y_position -= 20  # Space after question block

        if not result['correct']:
            p.setFillColorRGB(1, 0, 0)  # Red text for incorrect answers
            p.drawString(left_margin, y_position + 10, "Note: Your answer is incorrect.")
            p.setFillColorRGB(0, 0, 0)  # Reset to black
            y_position -= 20

        # Check if we are near the bottom of the page and switch to a new page if necessary
        if y_position < 50:
            p.showPage()  # Start a new page
            p.setFont("Helvetica", 12)  # Reset font
            y_position = height - 50  # Reset Y position

    p.save()
    buffer.seek(0)
    return buffer

def analysis(request):
    try:
        result = []
        for i in range(1, CollectedData.objects.count() + 1):
            question = CollectedData.objects.filter(question_id=i).first()
            if question:  
                result.append({'answer': question.answer, 'useranswer': question.useranswer})
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            f"Evaluate the similarity between the provided actual and user answers, focusing on both meaning and accuracy for {result} and return only a single list of 'yes' and 'no' for each response in return"
)
        print(response.text)
        ans=response.text
        response_text= ast.literal_eval(response.text)
        print(type(response_text),response_text)
        response_list = response_text
        total = len(response_list)
        correct = 0
        wrong = 0
        results_with_status = []  

        for i in range(1, total + 1):
            question = CollectedData.objects.filter(question_id=i).first()

            ai_response = response_list[i - 1].strip().lower()  
            print(ai_response)

            if ai_response == "yes":
                correct += 1
            elif ai_response == "no":
                wrong += 1
           
            results_with_status.append({
                'question_id': question.question_id,
                'question': question.question,
                'answer': question.answer,
                'useranswer': question.useranswer,
                'status': ai_response, 
                'correct': ai_response == "yes"
                })

        if 'download_report' in request.GET:
            pdf = generate_pdf(results_with_status)
            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="analysis_report.pdf"'
            return response

        return render(request, 'analysis.html', {
            'total': total,
            'correct': correct,
            'wrong': wrong,
            'results_with_status': results_with_status  
        })

    except Exception as e:
        print(f"Error in analysis: {e}")
        return HttpResponse("An error occurred during analysis.")
