from django.db import models
from django.contrib.auth.models import User
from datetime import date

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    enrollment_number = models.CharField(max_length=50, unique=True)
    mobile_number = models.CharField(max_length=15)
    address = models.TextField()
    parent_number = models.CharField(max_length=15)
    parent_email = models.EmailField(blank=True, null=True)
    student_class = models.CharField(max_length=50)
    photo = models.ImageField(upload_to='student_photos/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.enrollment_number}"

class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile')
    employee_id = models.CharField(max_length=50, unique=True)
    department = models.CharField(max_length=100)
    mobile_number = models.CharField(max_length=15)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.employee_id}"


class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField(default=date.today)
    status = models.CharField(max_length=20, choices=[
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('leave', 'Leave')
    ], default='absent')
    face_recognized = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.student.enrollment_number} - {self.date} - {self.status}"
