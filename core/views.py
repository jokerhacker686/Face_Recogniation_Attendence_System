import base64
import io
import random
import string
import json
from datetime import date
from PIL import Image, ImageOps
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import Student, Employee, Attendance
from django.contrib.auth.decorators import login_required

def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/home.html')

def student_register(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        enrollment_number = request.POST.get('enrollment_number')
        address = request.POST.get('address')
        mobile_number = request.POST.get('mobile_number')
        parent_number = request.POST.get('parent_number')
        parent_email = request.POST.get('parent_email')
        student_class = request.POST.get('student_class')
        photo_data = request.POST.get('photo_data') # base64 image
        password = request.POST.get('password') # User defined password

        if User.objects.filter(username=enrollment_number).exists() or User.objects.filter(email=email).exists():
            messages.error(request, "A student with this enrollment number or email already exists.")
            return redirect('student_register')

        # Create User
        user = User.objects.create_user(username=enrollment_number, email=email, password=password, first_name=name)

        # Process Base64 Image
        format, imgstr = photo_data.split(';base64,') 
        ext = format.split('/')[-1] 
        photo_file = ContentFile(base64.b64decode(imgstr), name=f"{enrollment_number}_photo.{ext}")

        # Create Student Profile
        student = Student.objects.create(
            user=user,
            enrollment_number=enrollment_number,
            mobile_number=mobile_number,
            address=address,
            parent_number=parent_number,
            parent_email=parent_email,
            student_class=student_class,
            photo=photo_file
        )

        # Send Email Notification
        email_subject = 'Welcome to AuraSense Attendance System'
        email_body = f"""Hello {name},

You have been successfully registered in the Face Recognition Attendance System.
Your User ID / Enrollment Number is: {enrollment_number}
(You can login using the password you created during registration)

Regards,
Admin Team"""

        send_mail(
            email_subject,
            email_body,
            'admin@aurasense.com',
            [email, parent_email],
            fail_silently=False,
        )

        messages.success(request, f"Registration successful! You can now log in using your ID and the password you created.")
        return redirect('login')

    return render(request, 'core/register.html')


def decode_base64_image(image_data):
    if ',' in image_data:
        image_data = image_data.split(',', 1)[1]
    return base64.b64decode(image_data)


def image_average_hash(image, hash_size=16):
    image = ImageOps.grayscale(image).resize((hash_size, hash_size), resample=Image.LANCZOS)
    pixels = list(image.getdata())
    avg = sum(pixels) / len(pixels)
    bits = ''.join('1' if pixel >= avg else '0' for pixel in pixels)
    return bits


def hamming_distance(hash1, hash2):
    if len(hash1) != len(hash2):
        return max(len(hash1), len(hash2))
    return sum(ch1 != ch2 for ch1, ch2 in zip(hash1, hash2))


def faces_match(captured_b64, reference_path, threshold=22):
    try:
        captured_data = decode_base64_image(captured_b64)
        captured_img = Image.open(io.BytesIO(captured_data))
        captured_hash = image_average_hash(captured_img)

        reference_img = Image.open(reference_path)
        reference_hash = image_average_hash(reference_img)

        distance = hamming_distance(captured_hash, reference_hash)
        return distance <= threshold, distance
    except Exception:
        return False, None


def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        login_type = request.POST.get('login_type', 'student')
        user_id = request.POST.get('user_id', '').strip()
        password = request.POST.get('password', '')

        if not user_id or not password:
            messages.error(request, "Please enter both ID and password.")
            return render(request, 'core/login.html')

        # Authenticate user
        user = authenticate(request, username=user_id, password=password)
        
        if user is not None:
            # Check if user is a student
            is_student = hasattr(user, 'student_profile')
            is_employee = hasattr(user, 'employee_profile')
            is_admin = user.is_staff or user.is_superuser
            
            # Validate login type matches user profile
            if login_type == 'student' and is_student:
                login(request, user)
                messages.success(request, f"Welcome {user.first_name}!")
                return redirect('dashboard')
            elif login_type == 'employee' and (is_employee or is_admin):
                login(request, user)
                messages.success(request, f"Welcome {user.first_name}!")
                return redirect('dashboard')
            else:
                # User exists but wrong login type selected
                if is_student:
                    messages.error(request, "This is a student account. Please select 'Student' and try again.")
                elif is_employee or is_admin:
                    messages.error(request, "This is an employee/admin account. Please select 'Employee / Admin' and try again.")
                else:
                    messages.error(request, "Your account type cannot be determined. Please contact admin.")
        else:
            messages.error(request, "Invalid ID or Password. Please check and try again.")

    return render(request, 'core/login.html')

@login_required
def dashboard(request):
    if hasattr(request.user, 'student_profile'):
        student = request.user.student_profile
        # Get attendance records
        today_attendance = Attendance.objects.filter(student=student, date=date.today()).first()
        all_attendance = student.attendance_records.all()[:30]  # Last 30 records
        
        # Calculate statistics
        total_classes = Attendance.objects.filter(student=student).count()
        present_count = Attendance.objects.filter(student=student, status='present').count()
        absent_count = Attendance.objects.filter(student=student, status='absent').count()
        leave_count = Attendance.objects.filter(student=student, status='leave').count()
        
        # Calculate attendance percentage
        if total_classes > 0:
            attendance_percentage = (present_count / total_classes) * 100
        else:
            attendance_percentage = 0
        
        context = {
            'student': student,
            'today_attendance': today_attendance,
            'attendance_records': all_attendance,
            'total_classes': total_classes,
            'present_count': present_count,
            'absent_count': absent_count,
            'leave_count': leave_count,
            'attendance_percentage': round(attendance_percentage, 2)
        }
        return render(request, 'core/student_dashboard.html', context)
    elif hasattr(request.user, 'employee_profile') or request.user.is_staff:
        # Pass all students if it's an employee/admin
        students = Student.objects.all()
        return render(request, 'core/employee_dashboard.html', {'students': students})
    
    return redirect('home')

def user_logout(request):
    logout(request)
    return redirect('home')


@login_required
def mark_attendance(request):
    """View to mark attendance with face recognition"""
    if not hasattr(request.user, 'student_profile'):
        messages.error(request, "Only students can mark attendance.")
        return redirect('dashboard')
    
    student = request.user.student_profile
    
    if request.method == 'POST':
        face_image_data = request.POST.get('face_image')
        
        if not face_image_data:
            messages.error(request, "Please capture your face for attendance.")
            return redirect('dashboard')

        register_photo_path = student.photo.path if student.photo else None
        if not register_photo_path:
            messages.error(request, "Registered photo not found. Please contact admin.")
            return redirect('dashboard')

        matched, distance = faces_match(face_image_data, register_photo_path)
        if not matched:
            messages.error(request, "Face does not match your registered photo. Attendance not marked.")
            return redirect('dashboard')

        try:
            attendance, created = Attendance.objects.update_or_create(
                student=student,
                date=date.today(),
                defaults={
                    'status': 'present',
                    'face_recognized': True
                }
            )
            
            messages.success(request, "Attendance marked successfully!")
            return redirect('dashboard')
        except Exception as e:
            messages.error(request, f"Error marking attendance: {str(e)}")
            return redirect('dashboard')
    
    return render(request, 'core/mark_attendance.html', {'student': student})


@require_http_methods(["POST"])
def api_mark_attendance(request):
    """API endpoint for marking attendance with face recognition"""
    if not hasattr(request.user, 'student_profile'):
        return JsonResponse({'success': False, 'message': 'Only students can mark attendance.'}, status=403)
    
    student = request.user.student_profile
    
    try:
        data = json.loads(request.body)
        face_image_data = data.get('face_image')
        
        if not face_image_data:
            return JsonResponse({'success': False, 'message': 'Face image is required.'})
        
        register_photo_path = student.photo.path if student.photo else None
        if not register_photo_path:
            return JsonResponse({'success': False, 'message': 'Registered photo not found.'}, status=500)

        matched, distance = faces_match(face_image_data, register_photo_path)
        if not matched:
            return JsonResponse({
                'success': False,
                'message': 'Face does not match your registered photo. Attendance not marked.'
            }, status=403)

        # Check if attendance already marked today
        existing = Attendance.objects.filter(student=student, date=date.today()).first()
        if existing:
            return JsonResponse({
                'success': True,
                'message': 'Attendance already marked today!',
                'status': existing.status
            })
        
        attendance = Attendance.objects.create(
            student=student,
            date=date.today(),
            status='present',
            face_recognized=True
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Attendance marked successfully!',
            'status': 'present'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error marking attendance: {str(e)}'
        }, status=500)
