import logging
import azure.functions as func
import requests
import json
from azure.eventhub import EventHubProducerClient, EventData
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

app = func.FunctionApp()

@app.timer_trigger(schedule="*/30 * * * * *", arg_name="myTimer", run_on_startup=False, use_monitor=False)
def sales_api_function(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info("The timer is past due!")

    logging.info("Python timer trigger function executed.")

    # ----------------------------
    # ⚠️ Sensitive configs removed
    # Replace with your actual values in production
    # ----------------------------
    EVENT_HUB_NAMESPACE = "<your-eventhub-namespace>.servicebus.windows.net"
    EVENT_HUB_NAME = "<your-eventhub-name>"

    credential = DefaultAzureCredential()

    producer = EventHubProducerClient(
        fully_qualified_namespace=EVENT_HUB_NAMESPACE,
        eventhub_name=EVENT_HUB_NAME,
        credential=credential
    )

    def send_event(event):
        try:
            batch = producer.create_batch()
            batch.add(EventData(json.dumps(event, ensure_ascii=False)))
            producer.send_batch(batch)
            logging.info(f"✅ Sent record: {event.get('order_id', 'N/A')}")
        except Exception as e:
            logging.error(f"❌ Failed to send event: {e}")

    def handle_response(response):
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f"Error: {response.status_code}, {response.text}")
            return None

    def get_secret_from_keyvault(vault_url, secret_name):
        secret_client = SecretClient(vault_url=vault_url, credential=credential)
        retrieved_secret = secret_client.get_secret(secret_name)
        return retrieved_secret.value

    def get_superstore_data(base_url, api_key):
        sales_url = f"{base_url}/sales"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        response = requests.get(sales_url, headers=headers)
        return handle_response(response)

    def flatten_sales_data(sales_data):
        flattened_records = []
        for record in sales_data.get("sales", []):
            flattened_records.append({
                "order_id": record.get("order_id"),
                "status": record.get("status"),
                "created_at": record.get("created_at"),
                "customer_name": record.get("customer_name"),
                "customer_phone": record.get("customer_phone"),
                "shipping_city": record.get("shipping_city"),
                "sku": record.get("sku"),
                "product_name": record.get("product_name"),
                "product_category": record.get("product_category"),
                "qty": record.get("qty"),
                "delivery_agent": record.get("delivery_agent"),
                "customer_call_status": record.get("customer_call_status"),
                "agent_reached_customer": record.get("agent_reached_customer"),
                "return_status": record.get("return_status"),
                "return_reason": record.get("return_reason"),
                "return_requested_at": record.get("return_requested_at"),
                "return_approved_at": record.get("return_approved_at"),
                "return_shipped_back_at": record.get("return_shipped_back_at"),
                "return_received_at": record.get("return_received_at"),
                "return_refunded_at": record.get("return_refunded_at")
            })
        return flattened_records

    def fetch_sales_data():
        # ----------------------------
        # ⚠️ Replace with your values in production
        # ----------------------------
        base_url = "<your-api-base-url>"
        VAULT_URL = "<your-keyvault-url>"
        API_KEY_SECRET_NAME = "<your-secret-name>"

        salesapikey = get_secret_from_keyvault(VAULT_URL, API_KEY_SECRET_NAME)

        raw_sales_data = get_superstore_data(base_url, salesapikey)

        if raw_sales_data:
            transformed_data = flatten_sales_data(raw_sales_data)

            for record in transformed_data:
                send_event(record)

    # Run main
    fetch_sales_data()
