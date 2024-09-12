import requests
from locust import HttpUser, task, events, between, TaskSet

# Telegram Bot settings
TELEGRAM_API_TOKEN = "7532067489:AAF5qvxDNNB2-KqMN3GYCGGLYwuSJQ4MdEI"
CHAT_ID = "1130762888"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_API_TOKEN}/sendMessage"

# Failure counter
failure_count = 0

# Function to send a Telegram alert
def send_telegram_alert(message):
    data = {
        "chat_id": CHAT_ID,
        "text": message
    }
    try:
        response = requests.post(TELEGRAM_API_URL, data=data)
        if response.status_code == 200:
            print("Telegram message sent successfully!")
        else:
            print(f"Failed to send message: {response.status_code}")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

# Listener for all requests (successes and failures)
@events.request.add_listener
def request_alert(request_type, name, response_time, response_length, exception, **kwargs):
    global failure_count
    if exception:  # This indicates a failure
        failure_count += 1  # Increment failure counter
        if failure_count > 250:  # Trigger alert after 250 failures
            message = f"ALERT: More than 250 failures! Last failed request: {name}, Error: {exception}"
            send_telegram_alert(message)
            failure_count = 0  # Reset the counter after sending the alert

class WebsiteTasks(TaskSet):

    @task(1)
    def view_home(self):
        """Load the home page"""
        self.client.get("/")

    @task(2)
    def view_anggota(self):
        """Load the Anggota (members) page"""
        self.client.get("/anggota")

    @task(2)
    def view_admin(self):
        """Load the Admin page"""
        self.client.get("/admin")

    @task(3)
    def save_transaction(self):
        """Submit a save transaction form"""
        self.client.post("/save_transaksi", data={
            "role": "anggota",
            "id": "1",  # Simulate Anggota ID
            "nama_barang": "Laptop",
            "quantity": "2",
            "harga": "1500",
        })

    @task(1)
    def update_transaction(self):
        """Submit an update transaction form"""
        self.client.post("/update_transaksi", data={
            "transaksi_id": "1",
            "nama_barang": "Updated Laptop",
            "quantity": "3",
            "harga": "1600",
        })

    @task(1)
    def delete_transaction(self):
        """Submit a delete transaction form"""
        self.client.post("/delete_transaksi", data={
            "transaksi_id": "1"
        })

# Define the HttpUser class that will execute the tasks
class WebsiteUser(HttpUser):
    tasks = [WebsiteTasks]
    wait_time = between(1, 5)
