import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import joblib
import os

np.random.seed(42)
n_samples = 1000

data = {
    # Feature 1: Attendance (0.50 to 1.00)
    'attendance_rate': np.random.uniform(0.50, 1.00, n_samples),
    
    # Feature 2: Study Hours per week (1 to 20)
    'study_hours': np.random.randint(1, 20, n_samples),
    
    # Feature 3: Previous Grade / Baseline (50 to 100)
    'previous_grade': np.random.randint(50, 100, n_samples),
    
    # Feature 4: Stress Factor (Payment Delays 0 to 5)
    'payment_delays': np.random.randint(0, 5, n_samples),
}

df = pd.DataFrame(data)

# Formula: Base + (Attendance * 30) + (Study * 1.5) + (Prev * 0.4) - (Delays * 2)
# This simulates real life: Attendance matters most, delays hurt grades.
def calculate_final_grade(row):
    grade = 10 + (row['attendance_rate'] * 30) + \
                 (row['study_hours'] * 1.5) + \
                 (row['previous_grade'] * 0.4) - \
                 (row['payment_delays'] * 2)
    
    grade += np.random.normal(0, 2)
    return max(0, min(100, grade))

df['final_grade'] = df.apply(calculate_final_grade, axis=1)

X = df[['attendance_rate', 'study_hours', 'previous_grade', 'payment_delays']]
y = df['final_grade']

model = LinearRegression()
model.fit(X, y)

output_path = os.path.join(os.path.dirname(__file__), 'grade_predictor.pkl')
joblib.dump(model, output_path)

print(f"Model trained! Coefficients: {model.coef_}")
print(f"Model saved to: {output_path}")