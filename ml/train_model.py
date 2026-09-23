from pathlib import Path
import json, random
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "carbon_dataset.csv"
MODEL = ROOT / "ml" / "model.joblib"
METRICS = ROOT / "ml" / "metrics.json"

VEHICLES=["Car","Bus","Motorcycle","Truck","Train","EV"]
FUELS=["Petrol","Diesel","CNG","Electric","Hybrid"]

def make_dataset(n=1200):
    rng=np.random.default_rng(42)
    rows=[]
    fuel_factor={"Petrol":2.31,"Diesel":2.68,"CNG":2.0,"Electric":0.05,"Hybrid":1.2}
    vehicle_mult={"Car":1.0,"Bus":1.4,"Motorcycle":0.65,"Truck":1.8,"Train":0.45,"EV":0.35}
    for _ in range(n):
        vehicle=random.choice(VEHICLES); fuel=random.choice(FUELS)
        distance=float(rng.uniform(2,250))
        passengers=int(rng.integers(1,45 if vehicle in ["Bus","Train"] else 6))
        fuel_l=float(max(0,rng.normal(distance/12,2))) if fuel not in ["Electric"] else float(max(0,rng.normal(distance/80,.5)))
        electricity=float(max(0,rng.normal(distance/10,4)))
        grid=float(rng.uniform(.35,.95))
        renewable=float(rng.uniform(0,80))
        transport=fuel_l*fuel_factor[fuel]*vehicle_mult[vehicle]
        energy=electricity*grid*(1-renewable/100)
        passenger_eff=1/(0.65+0.35*passengers)
        co2=max(0.05, transport*passenger_eff+energy+float(rng.normal(0,.45)))
        rows.append([distance,fuel_l,passengers,electricity,grid,renewable,vehicle,fuel,co2])
    return pd.DataFrame(rows,columns=["distance_km","fuel_liters","passengers","electricity_kwh","grid_factor","renewable_share","vehicle_type","fuel_type","co2_kg"])

def main():
    df=make_dataset()
    df.to_csv(DATA,index=False)
    x=pd.get_dummies(df.drop(columns=["co2_kg"]),columns=["vehicle_type","fuel_type"],dtype=int)
    # Fixed columns guarantee API feature order.
    columns=["distance_km","fuel_liters","passengers","electricity_kwh","grid_factor","renewable_share"]
    columns += [f"vehicle_type_{v}" for v in VEHICLES]
    columns += [f"fuel_type_{f}" for f in FUELS]
    x=x.reindex(columns=columns,fill_value=0)
    y=df.co2_kg
    X_train,X_test,y_train,y_test=train_test_split(x,y,test_size=.2,random_state=42)
    model=RandomForestRegressor(n_estimators=220,max_depth=14,min_samples_leaf=2,random_state=42,n_jobs=-1)
    model.fit(X_train,y_train)
    pred=model.predict(X_test)
    metrics={"mae":round(float(mean_absolute_error(y_test,pred)),4),
             "rmse":round(float(np.sqrt(mean_squared_error(y_test,pred))),4),
             "r2":round(float(r2_score(y_test,pred)),4),
             "features":columns,"dataset_rows":len(df)}
    joblib.dump(model,MODEL)
    METRICS.write_text(json.dumps(metrics,indent=2))
    print(json.dumps(metrics,indent=2))

if __name__=="__main__":
    main()
