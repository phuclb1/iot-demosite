from influxdb_client import InfluxDBClient
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures

token = "rwxEeiKenR5FgR6j6ZdCiTpc-4EERx9rQ53D9_DUgyNBapQdDSvgEg36knJ9NdbOaMT8K8_pnP2GEjzG-bAwgg=="
org = "test_org"
url = "http://localhost:8086"
bucket = 'test_bucket'

client = InfluxDBClient(url=url, token=token, org=org)
query_api = client.query_api()


query = f'''
from(bucket: "{bucket}")
  |> range(start: -7d)
  |> filter(fn: (r) => r._measurement == "temperature")
  |> filter(fn: (r) => r._field == "temperature")
  |> filter(fn: (r) => r.device_id == "QM30VT2-0001")
  |> keep(columns: ["_time", "_value"])
'''

tables = query_api.query(query)
#print(tables)
df = pd.DataFrame([{'time': record['_time'], "temperature": record['_value']} for table in tables for record in table.records])
df['time'] = pd.to_datetime(df['time'])


df['time_numeric'] = df['time'].astype(np.int64) // 10**9  # seconds since epoch

X = df[['time_numeric']]
y = df['temperature']

poly = PolynomialFeatures(degree=2, include_bias=False)



model = LinearRegression()
model.fit(X, y)


df['predicted_temp'] = model.predict(X)


latest = df['time'].max()
future_time = pd.date_range(start=latest, periods=25, freq='1h')

future_numeric = future_time.astype(np.int64) // 10**9
future_X = pd.DataFrame(future_numeric, columns=['time_numeric'])

future_preds = model.predict(future_X)


future_df = pd.DataFrame({
    "time": future_time,
    "predicted_temp": future_preds
})

# print(future_df)

plt.figure(figsize=(12,6))
plt.plot(df['time'], df['temperature'], label="Temperature", marker="o")
plt.plot(df['time'], df['predicted_temp'], label="Regression Fit", linestyle="--")
plt.plot(future_df['time'], future_df['predicted_temp'], label="Future Prediction", linestyle="dotted")
plt.xlabel("Time")
plt.ylabel("Temperature")
plt.title("Temperature Prediction (Linear Regression)")
plt.legend()
plt.show()

print(f"Slope (change per second): {model.coef_[0]}")
print(f"Intercept: {model.intercept_}")
