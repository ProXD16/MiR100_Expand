import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailSender:
    def __init__(self, sender_email="your_email@gmail.com", app_password="your_app_password"):
        self.sender_email = sender_email
        self.app_password = app_password
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587

    def send_email(self, recipient_email, subject, body, sender_name="MIR_Logger"):
        """Gửi email đến địa chỉ được chỉ định"""
        # Tạo đối tượng email
        msg = MIMEMultipart()
        msg['From'] = f"{sender_name} <{self.sender_email}>"
        msg['To'] = recipient_email
        msg['Subject'] = subject

        # Thêm nội dung email
        msg.attach(MIMEText(body, 'plain'))

        try:
            # Kết nối với server SMTP của Gmail
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()  # Bật chế độ TLS
            server.login(self.sender_email, self.app_password)

            # Gửi email
            server.sendmail(self.sender_email, recipient_email, msg.as_string())
            print(f"Email sent successfully to {recipient_email}")

            # Đóng kết nối
            server.quit()
            return True
        except Exception as e:
            print(f"Failed to send email: {str(e)}")
            return False

if __name__ == '__main__':
    # Thay thế thông tin xác thực thực tế tại đây
    sender_email = "duc0915304586@gmail.com"  # Thay bằng email của bạn
    app_password = "0915304586"  # Thay bằng App Password của bạn

    # Khởi tạo EmailSender
    email_sender = EmailSender(sender_email, app_password)

    # Gửi email thử nghiệm
    recipient = "dat0915304586@gmail.com"
    subject = "MIR_Logger Status Update"
    body = "This is a test email from MIR_Logger. Everything is running smoothly!"
    email_sender.send_email(recipient, subject, body)