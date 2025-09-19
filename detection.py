import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from influxdb_client import InfluxDBClient

# InfluxDB Configuration
token = "rwxEeiKenR5FgR6j6ZdCiTpc-4EERx9rQ53D9_DUgyNBapQdDSvgEg36knJ9NdbOaMT8K8_pnP2GEjzG-bAwgg=="
org = "test_org"
url = "http://localhost:8086"
bucket = 'test_bucket'

client = InfluxDBClient(url=url, token=token, org=org)
query_api = client.query_api()

# Query temperature data from InfluxDB
query = f'''
from(bucket: "{bucket}")
  |> range(start: -7d)
  |> filter(fn: (r) => r._measurement == "temperature")
  |> filter(fn: (r) => r._field == "temperature")
  |> filter(fn: (r) => r.device_id == "QM30VT2-0001")
  |> keep(columns: ["_time", "_value"])
  |> sort(columns: ["_time"])
'''

try:
    tables = query_api.query(query)
    data_records = []
    for table in tables:
        for record in table.records:
            data_records.append({
                'time': record['_time'], 
                'temperature': record['_value']
            })
    
    df = pd.DataFrame(data_records)
    

    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time').reset_index(drop=True)
    
    df['time_numeric'] = df['time'].astype(np.int64) // 10**9  # Unix timestamp
    
    df['hour'] = df['time'].dt.hour
    df['day_of_week'] = df['time'].dt.dayofweek
    
    # Rolling statistics (if we have enough data)
    if len(df) >= 10:
        df['rolling_mean'] = df['temperature'].rolling(window=min(10, len(df)//2), center=True).mean()
        df['rolling_std'] = df['temperature'].rolling(window=min(10, len(df)//2), center=True).std()
        df['temp_diff'] = df['temperature'].diff().fillna(0)
    else:
        df['rolling_mean'] = df['temperature'].mean()
        df['rolling_std'] = df['temperature'].std()
        df['temp_diff'] = 0
    
    # Fill NaN values
    df = df.fillna(method='bfill').fillna(method='ffill')
    
    # Prepare features for anomaly detection
    # Use temperature and derived features
    feature_columns = ['temperature', 'hour', 'temp_diff']
    if len(df) >= 10:
        feature_columns.extend(['rolling_mean', 'rolling_std'])
    
    X = df[feature_columns].values
    
    # Standardize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Train Isolation Forest Model
    # Contamination should be a reasonable estimate of anomaly percentage
    contamination = min(0.1, max(0.01, 20/len(df)))  # Adaptive contamination rate
    
    model = IsolationForest(
        contamination=contamination,
        random_state=42,
        n_estimators=100
    )
    
    # Fit the model and predict anomalies
    df['anomaly'] = model.fit_predict(X_scaled)
    df['anomaly_score'] = model.decision_function(X_scaled)
    
    # Separate normal vs anomaly data
    normal_data = df[df['anomaly'] == 1]
    anomaly_data = df[df['anomaly'] == -1]
    
    print(f"\nAnomaly Detection Results:")
    print(f"Total data points: {len(df)}")
    print(f"Normal points: {len(normal_data)}")
    print(f"Anomalous points: {len(anomaly_data)}")
    print(f"Anomaly percentage: {len(anomaly_data)/len(df)*100:.2f}%")
    
    # Create visualizations
    fig, (ax) = plt.subplots(1, 1, figsize=(12, 3))
    
    # Plot 1: Temperature over time with anomalies highlighted
    ax.plot(normal_data['time'], normal_data['temperature'], 
             'b.', markersize=4, label='Normal', alpha=0.7)
    ax.plot(anomaly_data['time'], anomaly_data['temperature'], 
             'r.', markersize=8, label='Anomaly')
    ax.set_ylabel('Temperature')
    ax.set_title('Temperature Data with Detected Anomalies')
    ax.legend()
    ax.grid(True, alpha=0.3)
 
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=max(1, len(df)//10)))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    plt.tight_layout()
    plt.show()
    
    # Print detailed anomaly information

        # Summary statistics
    print("\n" + "="*50)
    print("SUMMARY STATISTICS:")
    print("="*50)
    print(f"Temperature Statistics:")
    print(f"  Mean: {df['temperature'].mean():.2f}")
    print(f"  Std:  {df['temperature'].std():.2f}")
    print(f"  Min:  {df['temperature'].min():.2f}")
    print(f"  Max:  {df['temperature'].max():.2f}")
    
    if not anomaly_data.empty:
        print(f"\nAnomaly Temperature Statistics:")
        print(f"  Mean: {anomaly_data['temperature'].mean():.2f}")
        print(f"  Std:  {anomaly_data['temperature'].std():.2f}")
        print(f"  Min:  {anomaly_data['temperature'].min():.2f}")
        print(f"  Max:  {anomaly_data['temperature'].max():.2f}")

except Exception as e:
    print(f"Error occurred: {str(e)}")
    print("Please check your InfluxDB connection and query parameters.")

finally:
    client.close()