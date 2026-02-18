FROM python:3.11-slim 
WORKDIR /app 
RUN pip install --no-cache-dir numpy==1.26.4 pandas==2.0.3 requests==2.31.0 scikit-learn==1.3.2 xgboost==2.0.3 tensorflow==2.14.0 
COPY alpha_stack_binance_only.py alpha_stack_prod.py ./ 
RUN mkdir -p /app/data 
VOLUME ["/app/data"] 
CMD ["python", "alpha_stack_prod.py", "--mode", "paper"] 
