import duckdb
import pandas as pd
import google.generativeai as genai
import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import atexit
from dotenv import load_dotenv
import re
import random

# Initialize Flask App
app = Flask(__name__)


# Enable CORS
CORS(app)

load_dotenv()

# Set API Keys
MOTHERDUCK_TOKEN = os.getenv("MOTHERDUCK_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Google Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Connect to MotherDuck
conn = duckdb.connect(database=f"md:my_db?motherduck_token={MOTHERDUCK_TOKEN}")
conn.execute(f"INSTALL motherduck; LOAD motherduck;")

# Store uploaded tables for deletion on shutdown
uploaded_tables=[]
metadata_store = {}

@app.route("/")
def home():
    return render_template("index.html")

# Upload a dataset to MotherDuck from a CSV file
@app.route("/upload", methods=["POST"])
def upload_dataset():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    files = request.files.getlist("file")
    
    
    if not files:
        return jsonify({"error": "No selected file"}), 400

    for file in files:
        try:
            table_name = request.form.get("table_name", file.filename.split('.')[0])  # Use filename without extension
            table_name = re.sub(r'\W+', '_', table_name)  # Replace special characters with underscores

            # Check file extension and load dataset accordingly
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file, encoding='utf-8', on_bad_lines='skip')  # Handle potential encoding issues
            elif file.filename.endswith('.xlsx') or file.filename.endswith('.xls'):
                df = pd.read_excel(file)
            elif file.filename.endswith('.json'):
                df = pd.read_json(file)
            else:
                raise ValueError("Unsupported file format. Supported formats: CSV, Excel, JSON.")
            print(df)
            # Register the table in MotherDuck
            conn.register("temp_table", df)
            conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM temp_table;")
            print("check")
            # Store metadata
            metadata = get_metadata(df)
            uploaded_tables.append(table_name)
            metadata_store[table_name] = metadata

            print(f"✅ Dataset '{table_name}' uploaded and stored in MotherDuck.")

        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    print(f"📊 Uploaded tables: {uploaded_tables}")
    # Convert list to a comma-separated string
    uploaded_tables_str = ', '.join(uploaded_tables)

    # Return metadata and success message to frontend
    return jsonify({"success": True, "message": f"{uploaded_tables_str}"}), 200

# Convert a natural language query into SQL
def generate_sql_query(nl_query: str):
    
    prompt = f"""
    You are an expert SQL assistant working with DuckDB.
    Convert the following natural language query into a SQL query that works on the tables':
    table information: {metadata_store},
    Query: "{nl_query}"

    Guidelines:
    - If the query is related to the dataset, generate a valid SQL query that I can directly execute on dataset.
    - Use the correct column names and table names from the dataset provided.
    - If the query is not relevant to the dataset (e.g., personal questions, general knowledge, related to other dataset not mentioned here, non-related question or location-based queries), return the following message:
      ```
        None
      ```
    - Ensure the SQL syntax is valid for DuckDB.
    - 
    """
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(prompt)
    
    # Clean the query by removing markdown syntax 
    return response.text.replace("```sql", "").replace("```", "").strip()

# Executes the SQL query on MotherDuck and returns the results.
def execute_sql_query(sql_query: str):
    try:
        result = conn.execute(sql_query).fetchdf()
        return {"data": result.to_html(classes="styled-table", escape=False)}  # Convert to HTML table
    except Exception as e:
        return {"error": str(e)}, 500


# Extract metadata from a dataset
def get_metadata(data):
    return {
        "columns": data.columns.tolist(),
        "dtypes": data.dtypes.astype(str).to_dict(),
        "rows": len(data),
        "shape": data.shape,
        "summary": data.describe(include="all").to_dict()
    }

# Funny fallback function for unrelated queries
def funny_fallback():
    funny_sql_queries = [
        "SELECT 'I am not a philosopher, but I can query a database!' AS response;",
        "SELECT 'Error 404: Your question is too deep for me!' AS wisdom;",
        "SELECT 'Sorry, I only speak SQL, not riddles!' AS chatbot_confusion;",
        f"SELECT 'I have no idea where you are, but you are definitely online!' AS location_info;"
    ]

    funny_results = [
        "I'm an AI, not a detective! 🕵️‍♂️",
        "I tried asking the database, but it just shrugged. 🤷",
        "SQL only understands numbers and text, not existential crises! 😆",
        "If I had emotions, I'd be confused too. 😂",
        "Your question just crashed my humor module. Please reboot. 🔄"
    ]

    return {
        "sql_query": random.choice(funny_sql_queries),
        "results":  {"error": random.choice(funny_results)}
    }


# API endpoint to convert a natural language query into SQL and execute it
@app.route("/query", methods=["POST"])
def query():
    data = request.json # Get the JSON data from the request
    nl_query = data["query"]  # Extract the natural language query 

    sql_query = generate_sql_query(nl_query)
    if 'None' in sql_query:
        return jsonify(funny_fallback())
    
    results = execute_sql_query(sql_query)
    return jsonify({"sql_query": sql_query, "results": results})

# Delete all uploaded tables when the server shuts down
def delete_uploaded_tables():
    if conn:
        try:
            for table in uploaded_tables:
                conn.execute(f"DROP TABLE IF EXISTS {table};")
                print(f"🗑️ Table '{table}' deleted from MotherDuck.")
        except Exception as e:
            print(f"⚠️ Error deleting tables: {e}")
        finally:
            conn.close()  # Close the connection properly
            print("🔌 Database connection closed.")

# Register cleanup function on server exit
atexit.register(delete_uploaded_tables)

if __name__ == "__main__":
    app.run(debug=True)