import yfinance as yf
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression

# Ticker symbol of the stock (e.g., Apple Inc. is 'AAPL')
ticker_symbol = "AAPL"

# Fetch historical stock data for the past 51 days including the target (tomorrow's price)
stock_data = yf.download(ticker_symbol, period="51d", interval="1d")
stock_data1 = yf.download(ticker_symbol, period="1d", interval="1d")

stock_prices = stock_data1['Close'].values


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

# Make predictions on the testing set
predictions = model.predict(X_test)

# Predict tomorrow's price using the last available data
last_data_point = np.array([stock_data.iloc[-1]['Close'], stock_data.iloc[-1]['MA_10']]).reshape(1, -1)
predicted_price = model.predict(last_data_point)

print(f"Starting price for the past 10 days: {stock_prices[0]:.2f}")
print("Predicted price for tomorrow based on the past 50 days of data: {:.2f}".format(predicted_price[0]))
