from datetime import datetime, timedelta
from django import forms
from django.contrib.auth.forms import PasswordChangeForm

from .models import Attendance, SalaryRecord, User

class LoginForm(forms.Form):
    phone_number = forms.CharField(max_length=50)
    password = forms.CharField(widget=forms.PasswordInput)


class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    ROLE_CHOICES = User.ROLE_CHOICES

    # Create the ChoiceField for role
    role = forms.ChoiceField(choices=ROLE_CHOICES)

    class Meta:
        model = User
        fields = ['phone_number', 'role', 'full_name', 'password','address', 'country', 'city']


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})



class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['user', 'check_in', 'check_out']
        widgets = {
            'check_in': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control',
                },
                format='%Y-%m-%dT%H:%M'  # Exclude seconds
            ),
            'check_out': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control',
                },
                format='%Y-%m-%dT%H:%M'  # Exclude seconds
            ),
        }

    def __init__(self, *args, **kwargs):
        logged_in_user = kwargs.pop('logged_in_user', None)
        super().__init__(*args, **kwargs)

        now = datetime.now()
        today = now.strftime('%Y-%m-%dT00:00')  # Start of today without seconds
        tomorrow = (now + timedelta(days=1)).strftime('%Y-%m-%dT23:59')  # End of tomorrow without seconds

        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})
            if field_name in ['check_in', 'check_out']:
                field.widget.attrs['min'] = today
                field.widget.attrs['max'] = tomorrow

        if logged_in_user:
            self.fields['user'].initial = logged_in_user
            self.fields['user'].widget.attrs['readonly'] = True
            self.fields['user'].disabled = True  # Disables the field in the form


class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add form control attributes to the fields
        self.fields['old_password'].widget = forms.PasswordInput(attrs={'class': 'form-control'})
        self.fields['new_password1'].widget = forms.PasswordInput(attrs={'class': 'form-control'})
        self.fields['new_password2'].widget = forms.PasswordInput(attrs={'class': 'form-control'})



class SalaryRecordForm(forms.ModelForm):
    class Meta:
        model = SalaryRecord
        fields = ['user', 'month', 'base_salary', 'extra_hours', 'extra_payment', 'total_salary', 'remarks']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})