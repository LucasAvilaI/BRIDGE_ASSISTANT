# utils/console.py

def log_test_header(test_id, model_key):
    print(f"\n{'='*60}")
    print(f"🧪 EVALUANDO: {test_id} | MODELO: {model_key}")
    print(f"{'-'*60}")

def log_result(status, extra_info=""):
    color = "✅" if status == "PASS" else "❌"
    print(f"{color} RESULTADO: {status} | {extra_info}")