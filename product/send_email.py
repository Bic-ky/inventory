from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.http import HttpResponse
from xhtml2pdf import pisa
import os
from django.db.models import Sum
from django.utils.timezone import now
from .models import User, Delivery, MonthlyExpense

def send_monthly_summary(request):
    # Get the selected month
    filter_month = request.GET.get('month', now().strftime('%Y-%m'))
    year, month = map(int, filter_month.split('-'))

    # Calculate summary data
    drivers = User.objects.filter(role='DRIVER')
    summary_data = []
    total_jars = total_received = total_due = 0

    for driver in drivers:
        # Total jars delivered by the driver
        total_jars_driver = Delivery.objects.filter(driver=driver, date__year=year, date__month=month).aggregate(
            total=Sum('quantity'))['total'] or 0

        # Total amount collected by the driver
        amount_received = MonthlyExpense.objects.filter(
            expense_type=MonthlyExpense.DAILY_EXPENSE,
            user=driver,
            date__year=year,
            date__month=month
        ).aggregate(total=Sum('amount'))['total'] or 0

        # Total amount (assuming 1 jar = 40)
        total_amount = total_jars_driver * 40

        # Due amount
        due_amount = total_amount - amount_received

        # Add to summary
        summary_data.append({
            'name': driver.full_name,
            'total_jars': total_jars_driver,
            'total_amount': total_amount,
            'amount_received': amount_received,
            'due_amount': due_amount,
        })

        # Update overall totals
        total_jars += total_jars_driver
        total_received += amount_received
        total_due += due_amount

    # Render the HTML template with the calculated summary data
    html_content = render_to_string('plant/monthly_summary_pdf.html', {
        'summary_data': summary_data,
        'filter_month': filter_month,
        'total_jars': total_jars,
        'total_received': total_received,
        'total_due': total_due,
    })

    # Generate PDF from HTML
    pdf_file_path = "/plant/Monthly_Summary.pdf"  # Save the file temporarily
    with open(pdf_file_path, "wb") as pdf_file:
        pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)
        if pisa_status.err:
            return HttpResponse("Error generating PDF", status=500)

    # Send the PDF via email
    email = EmailMessage(
        subject=f"Monthly Summary for {filter_month}",
        body="Please find the attached monthly summary report.",
        from_email="yadavbicky0518@gmail.com",
        to=["yadavbicky0518@gmail.com"],
    )
    email.attach_file(pdf_file_path)
    email.send()

    # Optionally, delete the generated file after sending the email
    os.remove(pdf_file_path)

    return HttpResponse("Monthly summary PDF sent successfully.")
