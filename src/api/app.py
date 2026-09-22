from flask import Flask, jsonify, request, send_from_directory
from flask_swagger_ui import get_swaggerui_blueprint
import pandas as pd
import joblib
import os


app = Flask(__name__)


# ============================================================
# SWAGGER CONFIGURATION
# ============================================================

SWAGGER_URL = "/docs"
API_URL = "/swagger.json"

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        "app_name": "AI Log Debugger API"
    }
)

app.register_blueprint(
    swaggerui_blueprint,
    url_prefix=SWAGGER_URL
)


# Serve Swagger JSON file
@app.route("/swagger.json", methods=["GET"])
def swagger_json():
    return send_from_directory(
        os.path.dirname(__file__),
        "swagger.json"
    )


# ============================================================
# LOAD ML MODEL
# ============================================================

MODEL_PATH = "data/processed/isolation_forest_model.joblib"

model = joblib.load(MODEL_PATH)

print("ML model loaded successfully!")


# ============================================================
# HOME
# ============================================================

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "message": "AI Log Debugger API is running",
        "status": "success"
    })


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health", methods=["GET"])
def health():

    return jsonify({
        "status": "healthy"
    })


# ============================================================
# PREDICTION API
# ============================================================

@app.route("/predict", methods=["POST"])
def predict():

    data = request.get_json()

    # Check if input exists
    if not data:

        return jsonify({
            "error": "No input data provided"
        }), 400


    # Required features
    required_fields = [

        "severity",
        "is_error",
        "service_code",
        "message_length",
        "time_since_previous",
        "errors_in_last_minute",
        "warnings_in_last_minute",
        "service_error_rate"

    ]


    # Check for missing fields
    missing_fields = [

        field
        for field in required_fields
        if field not in data

    ]


    if missing_fields:

        return jsonify({

            "error": "Missing fields",
            "fields": missing_fields

        }), 400


    # ========================================================
    # CREATE DATAFRAME
    # ========================================================

    input_data = pd.DataFrame([data])


    # ========================================================
    # FEATURES USED BY ML MODEL
    # ========================================================

    feature_columns = [

        "severity",
        "is_error",
        "service_code",
        "message_length",
        "time_since_previous",
        "errors_in_last_minute",
        "warnings_in_last_minute",
        "service_error_rate"

    ]


    # ========================================================
    # ML MODEL PREDICTION
    # ========================================================

    prediction_value = model.predict(
        input_data[feature_columns]
    )[0]


    # Isolation Forest:
    # -1 = Anomaly
    #  1 = Normal

    if prediction_value == -1:

        ml_anomaly = 1

    else:

        ml_anomaly = 0


    # ========================================================
    # RULE-BASED ANOMALY DETECTION
    # ========================================================

    rule_anomaly = int(

        input_data["severity"].iloc[0] >= 1

    )


    # ========================================================
    # HYBRID ANOMALY DETECTION
    # ========================================================

    final_anomaly = int(

        (ml_anomaly == 1)
        or
        (rule_anomaly == 1)

    )


    # ========================================================
    # FINAL PREDICTION
    # ========================================================

    if final_anomaly == 1:

        prediction = "Anomaly"

    else:

        prediction = "Normal"


    severity = input_data["severity"].iloc[0]


    # ========================================================
    # API RESPONSE
    # ========================================================

    return jsonify({

        "prediction": prediction,

        "severity": int(severity),

        "ml_prediction":
            "Anomaly"
            if ml_anomaly == 1
            else "Normal",

        "rule_prediction":
            "Anomaly"
            if rule_anomaly == 1
            else "Normal",

        "message":
            "Prediction generated successfully"

    })


# ============================================================
# RUN FLASK SERVER
# ============================================================

if __name__ == "__main__":

    app.run(host="0.0.0.0", port=5000, debug=True)