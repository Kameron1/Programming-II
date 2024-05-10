import os
import numpy as np
import pandas as pd
import yfinance as yf
import multiprocessing as mp
from flask_cors import CORS
from flask import Flask, request, jsonify
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split

app = Flask(__name__)  # Initialize Flask application
CORS(app)  # Allow Cross-Origin Resource Sharing (CORS) for the app

# Define default budget percentages for different expenses
Budget = {
    "Rent": 30,
    "Utilities": 10,
    "Subscriptions": 5,
    "Groceries": 10,
    "Car Payment": 15,
    "Debt": 10,
    "Savings": 15,
    "Custom": 5
}

def fetch_sp500_tickers():
    # Fetch S&P 500 data from Wikipedia
    table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
    sp500_df = table[0]
    tickers = sp500_df['Symbol'].tolist()
    
    # Correcting specific ticker symbols that might not be formatted correctly
    tickers = [ticker.replace('.', '-') for ticker in tickers]
    
    return tickers

def predict_tomorrows_price_multiprocessing(ticker_symbol):
    try:
        # Fetch historical stock data for the past 51 days including the target (tomorrow's price)
        stock_data = yf.download(ticker_symbol, period="51d", interval="1d")
        if stock_data.empty:
            print(f"No data for {ticker_symbol}")
            return None
        # Calculate moving average (MA) for the past 10 days
        stock_data['MA_10'] = stock_data['Close'].rolling(window=10).mean()

        # Drop rows with missing values
        stock_data.dropna(inplace=True)

        # Feature engineering: Use 'Close' prices and 'MA_10' as features
        X = stock_data[['Close', 'MA_10']].values[:-1]  # Remove the last row to match with shifted y
        y = stock_data['Close'].shift(-1).dropna().values  # Shift y by -1 day

        # Split data into training and testing sets
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Train the linear regression model
        model = LinearRegression()
        model.fit(X_train, y_train)

        # Predict tomorrow's price using the last available data
        last_data_point = np.array([stock_data.iloc[-1]['Close'], stock_data.iloc[-1]['MA_10']]).reshape(1, -1)
        predicted_price = model.predict(last_data_point)
        
        # Calculate the percentage change
        current_price = stock_data.iloc[-1]['Close']
        percentage_change = ((predicted_price[0] - current_price) / current_price) * 100

        return {
            "Ticker": ticker_symbol,
            "Current Price": f"{current_price:.2f}",
            "Predicted Price": f"{predicted_price[0]:.2f}",
            "Percentage Change": f"{percentage_change:.2f}"
        }

    except Exception as e:
        print(f"Error processing {ticker_symbol}: {e}")
        return None

@app.route("/budget", methods=["POST"])
def budget():
    # Get expense data from the request
    data = request.get_json()
    Expenses = data.get("Expenses")
    Monthly_Income_After_Tax = data.get("Monthly_Income_After_Tax")
    Left_Over = Monthly_Income_After_Tax

    # Calculate budgeted expenses based on income and predefined percentages
    Budget_Expenses = {key: Monthly_Income_After_Tax * (value / 100) for key, value in Budget.items()}
    result = {}

    # Compare actual expenses with budgeted expenses and provide feedback
    for key, value in Expenses.items():
        if key in Budget_Expenses:
            if int(value) == Budget_Expenses[key]:
                result[key] = f"You are very close to going over Budget (yellow)"
            elif int(value) > Budget_Expenses[key]:
                result[key] = f"You should cutback by ${int(value) - Budget_Expenses[key]} (red)"
                Left_Over -= int(value)
            elif int(value) < Budget_Expenses[key]:
                result[key] = f"You are well under budget (green)"
                Left_Over -= int(value)
            else:
                Left_Over -= int(value)

    # Calculate and add remaining amount after expenses for investing
    result["Left Over"] = f"You have {Left_Over} left for investing"
    
    response = jsonify(result=result)  # Create JSON response
    response.headers.add('Access-Control-Allow-Origin', '*')  # Allow requests from any origin
    
    return response

@app.route("/predict_saved_stocks", methods=["POST"])
def predict_saved_stocks():
    data = request.get_json()
    database = pd.read_csv("database.csv")
    row_index = database.index[database['Username'] == data['Username']].tolist()


    if row_index:
        tickers_string = database.at[row_index[0], 'Tickers']
        # Split the tickers string into a list, and strip extra quotes if necessary
        tickers = [ticker.strip().replace('"', '') for ticker in tickers_string.split(",")]

        data = {}

        for i in tickers:
            data[i] = predict_tomorrows_price_multiprocessing(i)

        return jsonify({"Tickers": data})
    else:
        return jsonify({"Error": "Username not found"})

@app.route("/predict_all_stocks", methods=["POST"])
def predict_all_stocks():
    pass

@app.route("/predict", methods=["GET"])
def predict():
    tickers = fetch_sp500_tickers()
    results = []
    
    # Define the number of processes to use (adjust as needed)
    num_processes = mp.cpu_count()  # Utilize all available CPU cores
    
    with mp.Pool(processes=num_processes) as pool:
        results = pool.map(predict_tomorrows_price_multiprocessing, tickers)
    
    # Filter out None results
    results = [result for result in results if result is not None]
    
    results_df = pd.DataFrame(results)
    results_df.to_csv('stock_predictions.csv', index=False)
    
    data = pd.read_csv('stock_predictions.csv')
    top_changes = data.sort_values(by='Percentage Change', ascending=False).head(10)
    
    # Convert DataFrame to dictionary
    top_changes_dict = top_changes.to_dict(orient='records')
    
    print("Top 10 stocks with the highest percentage changes:")
    return jsonify(top_changes_dict)

@app.route("/short_all_stocks", methods=["POST"])
def short_all_stocks():
    tickers = fetch_sp500_tickers()
    results = []
    
    # Define the number of processes to use (adjust as needed)
    num_processes = mp.cpu_count()  # Utilize all available CPU cores
    
    with mp.Pool(processes=num_processes) as pool:
        results = pool.map(predict_tomorrows_price_multiprocessing, tickers)
    
    # Filter out None results
    results = [result for result in results if result is not None]
    
    results_df = pd.DataFrame(results)
    results_df.to_csv('stock_predictions.csv', index=False)
    
    data = pd.read_csv('stock_predictions.csv')
    top_changes = data.sort_values(by='Percentage Change', ascending=True).head(10)
    
    # Convert DataFrame to dictionary
    top_changes_dict = top_changes.to_dict(orient='records')
    
    print("Top 10 stocks with the lowest percentage changes:")
    return jsonify(top_changes_dict)

@app.route("/insert", methods=["POST"])
def insert():
    data = request.get_json()
    current_dir = os.path.dirname(__file__)
    csv_path = os.path.abspath(os.path.join(current_dir, "../server/data/database.csv"))
    database = pd.read_csv(csv_path)

    row_index = database.index[database['Username'] == data['Username']].tolist()

    if row_index:
        for key, value in data.items():
            database.at[row_index[0], key] = value
    else:
        return jsonify({"Status": "Not Successful",
                        "Reason": "No username found"})

    database.to_csv(csv_path, index=False)

    return jsonify({"Status": "Successful"})
    
@app.route("/signupapi", methods=["POST"])
def signup():
    data = request.get_json()
    current_dir = os.path.dirname(__file__)
    csv_path = os.path.abspath(os.path.join(current_dir, "../server/data/database.csv"))
    database = pd.read_csv(csv_path)

    if 'Username' not in data:
        return jsonify({"Status": "Not Successful", "Reason": "No username provided"}), 400

    if data['Username'] in database['Username'].values:
        return jsonify({"Status": "Not Successful", "Reason": "Username already exists"}), 400
    
    new_data = pd.DataFrame([data])
    database = pd.concat([database, new_data], ignore_index=True)
    database.to_csv(csv_path, index=False)
    response = jsonify({"Status": "Successful"})

    return response, 200

if __name__ == '__main__':
    app.run(debug=True, port=4444)  # Run the Flask app in debug mode